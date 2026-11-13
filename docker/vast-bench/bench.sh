#!/usr/bin/env bash
# bench.sh <пресет>...  — прогон DevMatrix для каждой модели подряд, пока идёт одна, следующая докачивается.
# Результаты: $RESULTS_DIR/<пресет>/ (submissions/, vllm.log, opencode/, metrics/, run-info.json).
# Окружение: HF_TOKEN (если нужен), GPU_PRICE_USD_HOUR (цена инстанса за час, для cost_usd),
# VLLM_START_TIMEOUT (с, по умолчанию 1800), AGENT_TIMEOUT (с на задачу, 1800), OPENCODE_TIMEOUT (1500;
# обязан быть меньше AGENT_TIMEOUT минимум на 120),
# PURGE_WEIGHTS=1 (удалять веса модели после прогона, если не хватает диска), IMAGE_DIGEST (иначе в run-info.json берётся IMAGE_REVISION).
# Статусы run-info.json: done, done_partial (всё прошло, но часть задач невалидна — отчёты в invalid/, их надо повторить;
# vLLM здоров и OpenCode упал не на большинстве), interrupted (bench.sh остановлен INT/TERM во время модели), agent_failed (OpenCode упал на большинстве задач при здоровом vLLM), download_failed, vllm_failed (не поднялся), vllm_died (упал или был нездоров
# во время прогона — затронутые задачи убраны в invalid/), devmatrix_failed (сбой самого запуска или не все отчёты).
set -uo pipefail

BENCH_DIR="${VAST_BENCH_DIR:-/opt/vast-bench}"
# shellcheck source=env.sh
source "$BENCH_DIR/env.sh"

export PRESET="python3 $BENCH_DIR/preset.py"
START_TIMEOUT="${VLLM_START_TIMEOUT:-1800}"
HEALTH_POLL="${HEALTH_POLL:-5}"
AGENT_TIMEOUT="${AGENT_TIMEOUT:-1800}"
export OPENCODE_TIMEOUT="${OPENCODE_TIMEOUT:-1500}"
VLLM_PID=""
PREFETCH_PID=""
PREFETCH_KEY=""
DEVMATRIX_PID=""
CURRENT_KEY=""
failed=0

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; }

usage() {
    echo "Использование: bench.sh <пресет>...   (список: bench.sh --list)" >&2
    $PRESET list >&2
}

# Ждём здоровый сервер; условие ловит и успех, и падение процесса, и таймаут.
# 0 — готов, 1 — процесс умер, 2 — таймаут.
wait_health() {
    local pid=$1 deadline=$((SECONDS + START_TIMEOUT))
    until curl -fsS -m 3 "$VLLM_URL/health" >/dev/null 2>&1; do
        kill -0 "$pid" 2>/dev/null || return 1
        ((SECONDS < deadline)) || return 2
        sleep "$HEALTH_POLL"
    done
}

# vLLM жив и отвечает на /health.
vllm_healthy() {
    [[ -n $VLLM_PID ]] && kill -0 "$VLLM_PID" 2>/dev/null \
        && curl -fsS -m 5 "$VLLM_URL/health" >/dev/null 2>&1
}

# Итоговый статус прогона по коду devmatrix:
# classify_run <код> <отчётов> <задач> <маркеров> <vllm здоров: 1|0> [<из маркеров — упавший OpenCode>].
# Маркер пишет agent-opencode.sh в виде «<задача>: opencode_failed: …», по этому префиксу его и считаем.
# Нормальны только 0 (все пройдены) и 1 (часть не пройдена), и то лишь пока vLLM оставался здоровым и отчётов
# столько же, сколько задач: traceback Python тоже даёт код 1, но оставляет неполный набор отчётов.
# OpenCode упал на большинстве задач при здоровом vLLM (плохой конфиг, имя модели) — agent_failed.
# Если же невалидны лишь некоторые задачи (упавший OpenCode, vLLM здоров) — done_partial, а не done.
classify_run() {
    local rc=$1 submitted=$2 expected=$3 markers=$4 healthy=$5 agent_failed=${6:-0}
    if ((healthy != 1 || markers - agent_failed > 0)); then
        echo vllm_died
    elif ((agent_failed * 2 > expected)); then
        echo agent_failed
    elif ((rc > 1 || submitted != expected)); then
        echo devmatrix_failed
    elif ((markers > 0)); then
        echo done_partial
    else
        echo done
    fi
}

# Останавливаем vLLM вместе с дочерними процессами и ждём, пока освободится видеопамять.
stop_vllm() {
    [[ -n $VLLM_PID ]] || return 0
    kill -TERM -- "-$VLLM_PID" 2>/dev/null
    local deadline=$((SECONDS + 60))
    until ! kill -0 "$VLLM_PID" 2>/dev/null || ((SECONDS >= deadline)); do sleep 2; done
    kill -KILL -- "-$VLLM_PID" 2>/dev/null
    wait "$VLLM_PID" 2>/dev/null
    VLLM_PID=""
    deadline=$((SECONDS + 90))
    until [[ $(gpu_used_mib) -lt 1024 ]] || ((SECONDS >= deadline)); do sleep 3; done
}

gpu_used_mib() {
    nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null \
        | awk '{ if ($1 > m) m = $1 } END { print m + 0 }'
}

cleanup() {
    # Остановка посреди модели (INT/TERM, сбой): статус «running» в run-info.json не оставляем.
    if [[ -n $CURRENT_KEY ]]; then
        $PRESET run-info "$CURRENT_KEY" "$RESULTS_DIR/$CURRENT_KEY/run-info.json" interrupted 2>/dev/null
        CURRENT_KEY=""
    fi
    [[ -n $DEVMATRIX_PID ]] && kill -TERM -- "-$DEVMATRIX_PID" 2>/dev/null
    stop_vllm
    [[ -n $PREFETCH_PID ]] && kill -TERM -- "-$PREFETCH_PID" 2>/dev/null
}
trap cleanup EXIT
trap 'exit 130' INT TERM

# Конец модели на любом пути: PURGE_WEIGHTS=1 удаляет веса (в том числе недокачанные) и после сбоя тоже.
finish_model() {
    CURRENT_KEY=""
    if [[ ${PURGE_WEIGHTS:-0} == 1 ]]; then
        rm -rf "$HF_HOME/hub/models--${1//\//--}"
    fi
}

run_model() {
    local key=$1 next=${2:-} out hf_id served
    out="$RESULTS_DIR/$key"
    hf_id=$($PRESET get "$key" hf_id)
    served=$($PRESET get "$key" served_name)
    mkdir -p "$out"
    CURRENT_KEY=$key
    rm -rf "$out/submissions" "$out/metrics" "$out/opencode" "$out/invalid"
    $PRESET run-info "$key" "$out/run-info.json" running

    # Свои веса: ждём фоновую докачку, если она была запущена на прошлом шаге. Её лог остаётся в
    # download.prefetch.log; сбой докачки не молчит, а основной путь пробует скачать заново в download.log.
    if [[ -n $PREFETCH_PID ]]; then
        wait "$PREFETCH_PID" 2>/dev/null
        local prc=$?
        if [[ $PREFETCH_KEY == "$key" ]] && ((prc != 0)); then
            log "$key: фоновая докачка не удалась (код $prc), см. $out/download.prefetch.log; качаю заново"
        fi
        PREFETCH_PID=""
        PREFETCH_KEY=""
    fi
    if ! "$BENCH_DIR/download.sh" "$key" >"$out/download.log" 2>&1; then
        log "$key: не скачались веса, см. $out/download.log"
        $PRESET run-info "$key" "$out/run-info.json" download_failed
        finish_model "$hf_id"
        return 1
    fi

    # Пока идёт эта модель, качаем следующую.
    if [[ -n $next ]]; then
        mkdir -p "$RESULTS_DIR/$next"
        # Своя группа процессов (setsid): cleanup убивает hf вместе с потомками.
        setsid "$BENCH_DIR/download.sh" "$next" >"$RESULTS_DIR/$next/download.prefetch.log" 2>&1 &
        PREFETCH_PID=$!
        PREFETCH_KEY=$next
    fi

    local serve_args=()
    mapfile -t serve_args < <($PRESET serve-args "$key")
    log "$key: запускаю vLLM ($hf_id)"
    setsid vllm serve "$hf_id" --host 127.0.0.1 --port "$VLLM_PORT" "${serve_args[@]}" \
        >"$out/vllm.log" 2>&1 &
    VLLM_PID=$!
    wait_health "$VLLM_PID"
    local health=$?
    if ((health != 0)); then
        log "$key: vLLM не поднялся (код $health: 1 — упал, 2 — таймаут ${START_TIMEOUT} с), см. $out/vllm.log"
        stop_vllm
        $PRESET run-info "$key" "$out/run-info.json" vllm_failed
        finish_model "$hf_id"
        return 1
    fi

    # Конфиг провайдера для OpenCode: только в контейнерном XDG, без секретов.
    mkdir -p "$XDG_CONFIG_HOME/opencode"
    $PRESET opencode-config "$key" "$VLLM_URL/v1" >"$XDG_CONFIG_HOME/opencode/opencode.json"

    log "$key: devmatrix run --all"
    export BENCH_MODEL=$served BENCH_OUT=$out
    # В фоне и в своей группе процессов + wait: INT/TERM срабатывают сразу, а trap убивает всю группу.
    (cd "$out" && exec setsid devmatrix run --all --model "$served" --provider "vLLM self-hosted" \
        --out "$out/submissions" --agent-timeout "$AGENT_TIMEOUT" \
        --agent "$BENCH_DIR/agent-opencode.sh {prompt_file}") \
        >"$out/devmatrix.log" 2>&1 &
    DEVMATRIX_PID=$!
    wait "$DEVMATRIX_PID"
    local rc=$?
    DEVMATRIX_PID=""
    local healthy=0
    vllm_healthy && healthy=1

    # devmatrix сам код агента не смотрит: при мёртвом vLLM он сохранит «чистый ноль». Такие задачи агент
    # пометил файлом metrics/<задача>.invalid; fill-claims убирает их отчёты в invalid/ и пишет в run-info.json.
    local expected submitted markers agent_failed
    expected=$(devmatrix list | wc -l)
    submitted=$(find "$out/submissions" -name '*.json' 2>/dev/null | wc -l)
    markers=$(find "$out/metrics" -name '*.invalid' 2>/dev/null | wc -l)
    agent_failed=$(grep -lE '^[^:]+: opencode_failed' "$out"/metrics/*.invalid 2>/dev/null | wc -l)
    $PRESET fill-claims "$out/submissions" "$out/metrics" "${GPU_PRICE_USD_HOUR:--}" "vLLM self-hosted" \
        "$out/run-info.json" >>"$out/devmatrix.log" 2>&1
    local status
    status=$(classify_run "$rc" "$submitted" "$expected" "$markers" "$healthy" "$agent_failed")
    stop_vllm
    $PRESET run-info "$key" "$out/run-info.json" "$status"
    finish_model "$hf_id"
    log "$key: $status (devmatrix код $rc), результаты в $out"
    [[ $status == done_partial ]] && log "$key: часть задач невалидна (см. invalid/ и run-info.json), их надо повторить"
    [[ $status == done || $status == done_partial ]]
}

main() {
    if [[ ${1:-} == --list || $# -eq 0 ]]; then
        usage
        [[ $# -eq 0 ]] && return 2
        return 0
    fi
    check_timeouts || return 2
    local keys=("$@") k
    for k in "${keys[@]}"; do
        $PRESET get "$k" hf_id >/dev/null || return 2
    done
    command -v nvidia-smi >/dev/null || { log "нет nvidia-smi: контейнер запущен без GPU"; return 3; }

    local i
    for i in "${!keys[@]}"; do
        run_model "${keys[$i]}" "${keys[$((i + 1))]:-}" || failed=$((failed + 1))
    done
    log "готово, моделей с ошибкой: $failed. Забрать: rsync -av <инстанс>:$RESULTS_DIR/ ./vast-results/"
    ((failed == 0))
}

# GNU timeout агента живёт в своей группе процессов и переживает killpg devmatrix: лимит OpenCode обязан
# закончиться раньше лимита devmatrix с запасом.
check_timeouts() {
    if ((OPENCODE_TIMEOUT + 120 >= AGENT_TIMEOUT)); then
        log "OPENCODE_TIMEOUT ($OPENCODE_TIMEOUT) + 120 с должен быть меньше AGENT_TIMEOUT ($AGENT_TIMEOUT)"
        return 2
    fi
}

# Подключение через source (тесты) функции не запускает.
if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
    main "$@"
fi
