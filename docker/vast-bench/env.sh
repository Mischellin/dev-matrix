# Общее окружение для entrypoint.sh, bench.sh и agent-opencode.sh (подключается через source).
# Свой HOME и XDG внутри контейнера: конфиг и состояние OpenCode не смешиваются с чужими.

export BENCH_HOME="${BENCH_HOME:-/workspace/bench-home}"
export HOME="$BENCH_HOME"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_STATE_HOME="$HOME/.local/state"
export XDG_CACHE_HOME="$HOME/.cache"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_STATE_HOME" "$XDG_CACHE_HOME"

export HF_HOME="${HF_HOME:-/workspace/hf}"
export RESULTS_DIR="${RESULTS_DIR:-/results}"
export VLLM_PORT="${VLLM_PORT:-8000}"
export VLLM_URL="http://127.0.0.1:${VLLM_PORT}"
export MODELS_TOML="${MODELS_TOML:-/opt/vast-bench/models.toml}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-/opt/uv-cache}"
export OPENCODE_DISABLE_AUTOUPDATE=1
mkdir -p "$HF_HOME" "$RESULTS_DIR"

# Быстрое скачивание, только если пакет hf_transfer действительно установлен.
if python3 -c "import hf_transfer" >/dev/null 2>&1; then
    export HF_HUB_ENABLE_HF_TRANSFER=1
fi
