#!/usr/bin/env bash
# Агент для `devmatrix run --agent`: один запуск OpenCode в подготовленной рабочей папке (cwd).
# Вызов: agent-opencode.sh <файл с заданием>. Окружение задаёт bench.sh: BENCH_MODEL, BENCH_OUT,
# VLLM_URL; DEVMATRIX_TASK_ID выставляет сам devmatrix. Токены задачи — дельта счётчиков /metrics vLLM
# (запросы идут строго по одному, так что дельта относится только к этой задаче).
# Мёртвый vLLM — не провал модели: если /health не отвечает до или после запуска OpenCode, пишем маркер
# $BENCH_OUT/metrics/<задача>.invalid и выходим с кодом 3. devmatrix код агента не смотрит и всё равно сохранит
# отчёт, поэтому bench.sh по маркеру убирает такой отчёт из submissions/. Так же помечается упавший OpenCode
# (код не 0 и не 124) без единого сгенерированного токена.
# Изоляция: из-под root (в образе) OpenCode запускается от пользователя $AGENT_USER (по умолчанию agent) через
# setpriv; ему отдаются только рабочая папка задачи ($PWD) и свежий HOME на эту задачу. Скрытые тесты, эталоны и
# /results закрыты правами 0700 для root (см. Dockerfile). Вне образа (нет пользователя или не root) запуск
# остаётся прежним (HOME тоже свой на задачу).
# HOME и XDG — отдельный каталог на каждую задачу под $AGENT_HOMES (владелец root): история сессий OpenCode и
# подложенные ~/.config/opencode/AGENTS.md не переходят ни в другую задачу, ни к другой модели. Каталог удаляется
# при любом выходе (trap). opencode.json копируется в root-владельный ~/.config/opencode (агенту только чтение).
# chown -R делается только по рабочей папке задачи и по свежему кэшу uv в HOME, общие каталоги не трогаются; не
# удался chown или создание HOME — задача невалидна (маркер, код 3).
# uv агента: свой UV_CACHE_DIR в HOME (копия прогретого кэша с одним pytest, $AGENT_UV_CACHE_SRC); UV_TOOL_DIR и
# UV_TOOL_BIN_DIR не отдаются (там root-владельные /opt/uv-tools и /usr/local/bin). Рядом с uv в образе системно
# стоит pytest, так что работают и `uv run --with pytest pytest`, и `python -m pytest`.
# После OpenCode все процессы пользователя агента убиваются (pkill -KILL) до чтения счётчиков /metrics: иначе
# оставшийся сервер агента раздувает токены следующих задач и может менять следующую рабочую папку.
# Переменные с секретами (HF_TOKEN и всё, что похоже на токен/пароль/ключ) OpenCode не получает.
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

# Имена переменных, которые нельзя отдавать агенту: известные токены и всё, что похоже на секрет.
secret_unsets() {
    local v
    for v in HF_TOKEN HUGGING_FACE_HUB_TOKEN $(compgen -e | grep -iE 'TOKEN|SECRET|PASSWORD|PASSWD|API_?KEY|CREDENTIAL|PRIVATE_KEY'); do
        printf '%s\n' "$v"
    done | sort -u | sed 's/^/-u\n/'
}

AGENT_HOMES="${AGENT_HOMES:-/workspace/agent-homes}"
AGENT_UV_CACHE_SRC="${AGENT_UV_CACHE_SRC:-/opt/agent-uv-cache}"
agent_user=${AGENT_USER-agent}
drop=0 # 1 — из-под root ронять права до $agent_user
[[ -n $agent_user && $(id -u) == 0 ]] && id -u "$agent_user" >/dev/null 2>&1 && drop=1
task_home=""

# Процессы агента живы (зомби не в счёт: PID 1 контейнера может их не подбирать).
agent_procs_alive() {
    ps -u "$agent_user" -o stat= 2>/dev/null | grep -qv '^Z'
}

# Убиваем всех оставшихся процессов пользователя агента и ждём, пока не останется ни одного. 1 — не вышло.
kill_agent_procs() {
    ((drop)) || return 0
    local deadline=$((SECONDS + ${AGENT_KILL_WAIT:-15}))
    pkill -KILL -u "$agent_user" 2>/dev/null
    while agent_procs_alive; do
        ((SECONDS < deadline)) || return 1
        sleep 0.2
        pkill -KILL -u "$agent_user" 2>/dev/null
    done
    return 0
}

cleanup() {
    kill_agent_procs
    [[ -n $task_home ]] && rm -rf -- "$task_home"
    return 0
}
trap cleanup EXIT

# Свежий HOME на задачу: под $AGENT_HOMES (root), владелец агент; opencode.json — root-владельный, только чтение.
make_task_home() {
    local src="$XDG_CONFIG_HOME/opencode/opencode.json"
    [[ -f $src ]] || { echo "нет $src" >&2; return 1; }
    mkdir -p "$AGENT_HOMES" || return 1
    task_home=$(mktemp -d "$AGENT_HOMES/task.XXXXXX") || return 1
    mkdir -p "$task_home/.config/opencode" "$task_home/.local/share" "$task_home/.local/state" "$task_home/.cache" || return 1
    [[ -d $AGENT_UV_CACHE_SRC ]] && { cp -a "$AGENT_UV_CACHE_SRC" "$task_home/.cache/uv" || return 1; }
    cp "$src" "$task_home/.config/opencode/opencode.json" || return 1
    chmod 755 "$task_home/.config/opencode" || return 1
    chmod 644 "$task_home/.config/opencode/opencode.json" || return 1
    if ((drop)); then
        # Каталог свежий и частный: рекурсивно только кэш; .config/opencode остаётся у root.
        chown "$agent_user:" "$task_home" "$task_home/.config" "$task_home/.local" "$task_home/.local/share" \
            "$task_home/.local/state" || return 1
        chown -R "$agent_user:" "$task_home/.cache" || return 1
        chown -R "$agent_user:" "$PWD" || return 1
    fi
}

# Аргументы `env` для OpenCode: убрать секреты и root-пути, задать HOME, XDG и кэш uv в каталоге задачи.
agent_env() {
    local v
    secret_unsets
    for v in UV_TOOL_DIR UV_TOOL_BIN_DIR BENCH_HOME BENCH_OUT RESULTS_DIR HF_HOME MODELS_TOML; do
        printf -- '-u\n%s\n' "$v"
    done
    printf '%s\n' "HOME=$task_home" "XDG_CONFIG_HOME=$task_home/.config" "XDG_DATA_HOME=$task_home/.local/share" \
        "XDG_STATE_HOME=$task_home/.local/state" "XDG_CACHE_HOME=$task_home/.cache" \
        "UV_CACHE_DIR=$task_home/.cache/uv" "UV_LINK_MODE=copy"
}

make_task_home || invalid "agent_setup_failed: не удалось подготовить HOME/права агента (см. stderr agent-opencode.sh)"

env_args=()
mapfile -t env_args < <(agent_env)
prefix=()
((drop)) && prefix=(setpriv "--reuid=$agent_user" "--regid=$agent_user" --init-groups --no-new-privs)

# --auto: без интерактивных подтверждений прав (внутри одноразового контейнера); модель — provider/model.
timeout -k 15 "$limit" "${prefix[@]}" env "${env_args[@]}" opencode run \
    --model "vllm/$BENCH_MODEL" --format json --auto --print-logs --dir "$PWD" \
    "$(cat "$prompt_file")" \
    >"$BENCH_OUT/opencode/$task.jsonl" 2>"$BENCH_OUT/opencode/$task.err"
rc=$?

kill_agent_procs || invalid "не удалось убить оставшиеся процессы пользователя $agent_user (код OpenCode $rc)"
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
