#!/usr/bin/env bash
# Точка входа: готовит окружение и запускает команду. `bench ...` — то же, что bench.sh.
set -euo pipefail

# shellcheck source=env.sh
source /opt/vast-bench/env.sh

case "${1:-}" in
    bench) shift; exec /opt/vast-bench/bench.sh "$@" ;;
    list) exec python3 /opt/vast-bench/preset.py list ;;
    *) exec "$@" ;;
esac
