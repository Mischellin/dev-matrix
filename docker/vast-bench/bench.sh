#!/usr/bin/env bash
# bench.sh <пресет>...  — прогон DevMatrix для каждой модели подряд, пока идёт одна, следующая докачивается.
# Результаты: $RESULTS_DIR/<пресет>/ (submissions/, vllm.log, opencode/, metrics/, run-info.json).
# Окружение: HF_TOKEN (если нужен), GPU_PRICE_USD_HOUR (цена инстанса за час, для cost_usd),
# VLLM_START_TIMEOUT (с, по умолчанию 1800), AGENT_TIMEOUT (с на задачу, 1800), OPENCODE_TIMEOUT (1500),
# PURGE_WEIGHTS=1 (удалять веса модели после прогона, если не хватает диска), IMAGE_DIGEST.
set -uo pipefail

# shellcheck source=env.sh
source /opt/vast-bench/env.sh

PRESET="python3 /opt/vast-bench/preset.py"
START_TIMEOUT="${VLLM_START_TIMEOUT:-1800}"
AGENT_TIMEOUT="${AGENT_TIMEOUT:-1800}"
export OPENCODE_TIMEOUT="${OPENCODE_TIMEOUT:-1500}"
VLLM_PID=""
PREFETCH_PID=""
failed=0

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; }

usage() {
    echo "Использование: bench.sh <пресет>...   (список: bench.sh --list)" >&2
    $PRESET list >&2
}

# Скачивание весов в $HF_HOME (идемпотентно: готовые файлы hf пропускает).
download() {
    local key=$1 hf_id pat cli
    hf_id=$($PRESET get "$key" hf_id)
    local args=()
    while IFS= read -r pat; do
        [[ -n $pat ]] && args+=(--exclude "$pat")
    done < <($PRESET get "$key" download_exclude)
    if command -v hf >/dev/null 2>&1; then cli=hf; else cli=huggingface-cli; fi
    log "скачиваю $hf_id"
    "$cli" download "$hf_id" "${args[@]}" >/dev/null
}

# Ждём здоровый сервер; условие ловит и успех, и падение процесса, и таймаут.
# 0 — готов, 1 — процесс умер, 2 — таймаут.
wait_health() {
    local pid=$1 deadline=$((SECONDS + START_TIMEOUT))
    until curl -fsS -m 3 "$VLLM_URL/health" >/dev/null 2>&1; do
        kill -0 "$pid" 2>/dev/null || return 1
        ((SECONDS < deadline)) || return 2
        sleep 5
    done
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
    stop_vllm
    [[ -n $PREFETCH_PID ]] && kill "$PREFETCH_PID" 2>/dev/null
}
trap cleanup EXIT
trap 'exit 130' INT TERM

run_model() {
    local key=$1 next=${2:-} out hf_id served
    out="$RESULTS_DIR/$key"
    hf_id=$($PRESET get "$key" hf_id)
    served=$($PRESET get "$key" served_name)
    mkdir -p "$out"
    rm -rf "$out/submissions" "$out/metrics" "$out/opencode"
    $PRESET run-info "$key" "$out/run-info.json" running

    # Свои веса: ждём фоновую докачку, если она была запущена на прошлом шаге, иначе качаем сами.
    if [[ -n $PREFETCH_PID ]]; then
        wait "$PREFETCH_PID" 2>/dev/null
        PREFETCH_PID=""
    fi
    if ! download "$key" >"$out/download.log" 2>&1; then
        log "$key: не скачались веса, см. $out/download.log"
        $PRESET run-info "$key" "$out/run-info.json" download_failed
        return 1
    fi

    # Пока идёт эта модель, качаем следующую.
    if [[ -n $next ]]; then
        mkdir -p "$RESULTS_DIR/$next"
        (download "$next" >"$RESULTS_DIR/$next/download.log" 2>&1) &
        PREFETCH_PID=$!
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
        return 1
    fi

    # Конфиг провайдера для OpenCode: только в контейнерном XDG, без секретов.
    mkdir -p "$XDG_CONFIG_HOME/opencode"
    $PRESET opencode-config "$key" "$VLLM_URL/v1" >"$XDG_CONFIG_HOME/opencode/opencode.json"

    log "$key: devmatrix run --all"
    export BENCH_MODEL=$served BENCH_OUT=$out
    (cd "$out" && devmatrix run --all --model "$served" --provider "vLLM self-hosted" \
        --out "$out/submissions" --agent-timeout "$AGENT_TIMEOUT" \
        --agent "/opt/vast-bench/agent-opencode.sh {prompt_file}") \
        >"$out/devmatrix.log" 2>&1
    local rc=$?
    # 0 — все задачи пройдены, 1 — часть не пройдена (это нормальный итог), остальное — сбой самого запуска.
    local status=done
    if ((rc > 1)); then status=devmatrix_failed; fi

    $PRESET fill-claims "$out/submissions" "$out/metrics" "${GPU_PRICE_USD_HOUR:--}" "vLLM self-hosted" \
        >>"$out/devmatrix.log" 2>&1
    stop_vllm
    $PRESET run-info "$key" "$out/run-info.json" "$status"
    if [[ ${PURGE_WEIGHTS:-0} == 1 ]]; then
        rm -rf "$HF_HOME/hub/models--${hf_id//\//--}"
    fi
    log "$key: $status (devmatrix код $rc), результаты в $out"
    [[ $status == done ]]
}

main() {
    if [[ ${1:-} == --list || $# -eq 0 ]]; then
        usage
        [[ $# -eq 0 ]] && return 2
        return 0
    fi
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

main "$@"
