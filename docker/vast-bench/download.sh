#!/usr/bin/env bash
# download.sh <пресет>  — скачивание весов модели в $HF_HOME (идемпотентно: готовые файлы hf пропускает).
# Отдельный скрипт, а не функция bench.sh: его запускает и основной путь, и фоновая докачка следующей модели
# (новый bash функции родителя не видит).
set -uo pipefail

BENCH_DIR="${VAST_BENCH_DIR:-/opt/vast-bench}"
# shellcheck source=env.sh
source "$BENCH_DIR/env.sh"

key=${1:?нужен ключ пресета}
PRESET="python3 $BENCH_DIR/preset.py"
hf_id=$($PRESET get "$key" hf_id) || exit 2
args=()
while IFS= read -r pat; do
    [[ -n $pat ]] && args+=(--exclude "$pat")
done < <($PRESET get "$key" download_exclude)
if command -v hf >/dev/null 2>&1; then cli=hf; else cli=huggingface-cli; fi
printf '[%s] скачиваю %s\n' "$(date -u +%H:%M:%S)" "$hf_id" >&2
exec "$cli" download "$hf_id" "${args[@]}" >/dev/null
