#!/usr/bin/env bash
# Агент для `devmatrix run --agent`: один запуск OpenCode в подготовленной рабочей папке (cwd).
# Вызов: agent-opencode.sh <файл с заданием>. Окружение задаёт bench.sh: BENCH_MODEL, BENCH_OUT,
# VLLM_URL; DEVMATRIX_TASK_ID выставляет сам devmatrix. Токены задачи — дельта счётчиков /metrics vLLM
# (запросы идут строго по одному, так что дельта относится только к этой задаче).
# Мёртвый vLLM — не провал модели: если /health не отвечает до или после запуска OpenCode, пишем маркер
# $BENCH_OUT/metrics/<задача>.invalid и выходим с кодом 3. devmatrix код агента не смотрит и всё равно сохранит
# отчёт, поэтому bench.sh по маркеру убирает такой отчёт из submissions/. Так же помечается упавший OpenCode
# (код не 0 и не 124) без единого сгенерированного токена.
set -uo pipefail

# shellcheck source=env.sh
source "${VAST_BENCH_DIR:-/opt/vast-bench}/env.sh"

prompt_file="${1:?нужен путь к файлу с заданием}"
task="${DEVMATRIX_TASK_ID:?нет DEVMATRIX_TASK_ID}"
: "${BENCH_MODEL:?нет BENCH_MODEL}" "${BENCH_OUT:?нет BENCH_OUT}"
limit="${OPENCODE_TIMEOUT:-1500}"
mkdir -p "$BENCH_OUT/opencode" "$BENCH_OUT/metrics"

# Сумма счётчика по всем меткам; нет метрики — 0.
counter() {
    curl -fsS -m 10 "$VLLM_URL/metrics" 2>/dev/null \
        | awk -v n="$1" '$0 ~ "^"n"(\\{| )" { s += $NF } END { printf "%.0f\n", s }'
}

# /health с тремя попытками: одиночный таймаут под нагрузкой ещё не смерть сервера.
healthy() {
    local i
    for i in 1 2 3; do
        curl -fsS -m 5 "$VLLM_URL/health" >/dev/null 2>&1 && return 0
        sleep "${HEALTH_RETRY_SLEEP:-2}"
    done
    return 1
}

invalid() {
    printf '%s: %s\n' "$task" "$1" >"$BENCH_OUT/metrics/$task.invalid"
    exit 3
}

healthy || invalid "vLLM не отвечает на /health перед запуском OpenCode"

p0=$(counter vllm:prompt_tokens_total)
g0=$(counter vllm:generation_tokens_total)
c0=$(counter vllm:prompt_tokens_cached_total)

# --auto: без интерактивных подтверждений прав (внутри одноразового контейнера); модель — provider/model.
timeout -k 15 "$limit" opencode run \
    --model "vllm/$BENCH_MODEL" --format json --auto --print-logs --dir "$PWD" \
    "$(cat "$prompt_file")" \
    >"$BENCH_OUT/opencode/$task.jsonl" 2>"$BENCH_OUT/opencode/$task.err"
rc=$?

healthy || invalid "vLLM не отвечает на /health после запуска OpenCode (код OpenCode $rc)"

p1=$(counter vllm:prompt_tokens_total)
g1=$(counter vllm:generation_tokens_total)
c1=$(counter vllm:prompt_tokens_cached_total)

# OpenCode упал (не 0 и не таймаут 124), а vLLM ничего не сгенерировал: плохой конфиг или имя модели,
# это не результат модели. Маркер начинается с opencode_failed — по нему bench.sh считает такие задачи.
if [[ $rc != 0 && $rc != 124 ]] && (( g1 - g0 == 0 )); then
    invalid "opencode_failed: OpenCode завершился с кодом $rc, vLLM не сгенерировал токенов (см. opencode/$task.err)"
fi

cat >"$BENCH_OUT/metrics/$task.json" <<JSON
{"task_id": "$task", "opencode_exit": $rc, "prompt_tokens": $((p1 - p0)), "completion_tokens": $((g1 - g0)), "prompt_tokens_cached": $((c1 - c0))}
JSON
# Код выхода OpenCode devmatrix не интересует: результат решают скрытые тесты (а сбой vLLM — маркер выше).
exit 0
