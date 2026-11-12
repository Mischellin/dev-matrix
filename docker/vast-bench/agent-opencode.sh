#!/usr/bin/env bash
# Агент для `devmatrix run --agent`: один запуск OpenCode в подготовленной рабочей папке (cwd).
# Вызов: agent-opencode.sh <файл с заданием>. Окружение задаёт bench.sh: BENCH_MODEL, BENCH_OUT,
# VLLM_URL; DEVMATRIX_TASK_ID выставляет сам devmatrix. Токены задачи — дельта счётчиков /metrics vLLM
# (запросы идут строго по одному, так что дельта относится только к этой задаче).
set -uo pipefail

# shellcheck source=env.sh
source /opt/vast-bench/env.sh

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

p0=$(counter vllm:prompt_tokens_total)
g0=$(counter vllm:generation_tokens_total)
c0=$(counter vllm:prompt_tokens_cached_total)

# --auto: без интерактивных подтверждений прав (внутри одноразового контейнера); модель — provider/model.
timeout -k 15 "$limit" opencode run \
    --model "vllm/$BENCH_MODEL" --format json --auto --print-logs --dir "$PWD" \
    "$(cat "$prompt_file")" \
    >"$BENCH_OUT/opencode/$task.jsonl" 2>"$BENCH_OUT/opencode/$task.err"
rc=$?

p1=$(counter vllm:prompt_tokens_total)
g1=$(counter vllm:generation_tokens_total)
c1=$(counter vllm:prompt_tokens_cached_total)

cat >"$BENCH_OUT/metrics/$task.json" <<JSON
{"task_id": "$task", "opencode_exit": $rc, "prompt_tokens": $((p1 - p0)), "completion_tokens": $((g1 - g0)), "prompt_tokens_cached": $((c1 - c0))}
JSON
# Код выхода агента devmatrix не интересует: результат решают скрытые тесты.
exit 0
