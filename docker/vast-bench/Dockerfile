# Образ для прогона DevMatrix на арендованном GPU (vast.ai): vLLM + OpenCode + CLI devmatrix.
# Без весов моделей и без секретов: веса качаются на инстансе в $HF_HOME, HF_TOKEN передаётся env.
#
# Сборка из корня репозитория:
#   docker build -f docker/vast-bench/Dockerfile -t dev-matrix-vast-bench .
#
# Тег vLLM: проверены по Docker Hub v0.31.0, v0.32.0, v0.33.0 (существуют); архитектуры из models.toml
# (GptOss, Mistral3, Qwen3_5, Qwen3_5Moe, Cohere2Moe) и парсеры найдены в исходниках v0.33.0.
# Для более новых архитектур поднимите тег: --build-arg VLLM_TAG=<тег>. Сборка образа не запускалась.
ARG VLLM_TAG=v0.33.0
FROM vllm/vllm-openai:${VLLM_TAG}

ARG VLLM_TAG
ARG OPENCODE_VERSION=1.19.5
ARG NODE_VERSION=26.13.1
ARG UV_VERSION=0.13.8
ARG IMAGE_REVISION=unknown

ENV DEBIAN_FRONTEND=noninteractive \
    VLLM_TAG=${VLLM_TAG} \
    IMAGE_REVISION=${IMAGE_REVISION} \
    UV_CACHE_DIR=/opt/uv-cache \
    UV_TOOL_DIR=/opt/uv-tools \
    UV_TOOL_BIN_DIR=/usr/local/bin \
    UV_PYTHON_INSTALL_DIR=/opt/uv-python \
    UV_PYTHON_PREFERENCE=only-managed \
    HF_HOME=/workspace/hf \
    RESULTS_DIR=/results

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl ca-certificates xz-utils jq procps rsync \
    && rm -rf /var/lib/apt/lists/*

# uv: из релиза GitHub, версия закреплена.
RUN curl -fsSL "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-x86_64-unknown-linux-gnu.tar.gz" \
    | tar -xz -C /usr/local/bin --strip-components=1 uv-x86_64-unknown-linux-gnu/uv uv-x86_64-unknown-linux-gnu/uvx

# Node LTS (нужен OpenCode) и сам OpenCode; postinstall npm-пакета скачивает бинарник, скрипты не отключаем.
RUN curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
    | tar -xJ -C /usr/local --strip-components=1 \
    && npm install -g --no-audit --no-fund "opencode-ai@${OPENCODE_VERSION}" \
    && opencode --version

# hf_transfer ускоряет скачивание весов (если пакета нет — bench.sh работает без него).
RUN uv pip install --system hf_transfer || echo "hf_transfer не установлен, скачивание будет обычным"

# CLI devmatrix: отдельное окружение на Python 3.12 от uv, чтобы не трогать Python vLLM.
COPY . /opt/dev-matrix
RUN uv tool install --python 3.12 /opt/dev-matrix \
    && devmatrix --version \
    && devmatrix list | head -3 \
    # runner проверяет задачи через uv run --with pytest: прогреваем кэш, чтобы не качать на инстансе
    && uv run --no-project --python 3.12 --with pytest==8.3.4 python -c "import pytest" \
    && python3 -c "import tomllib"

COPY docker/vast-bench/ /opt/vast-bench/
RUN chmod +x /opt/vast-bench/*.sh /opt/vast-bench/preset.py \
    # ssh-сессии не наследуют ENV образа: env.sh подхватывает эти значения из image.env
    && printf ': "${VLLM_TAG:=%s}"\n: "${IMAGE_REVISION:=%s}"\n: "${UV_PYTHON_INSTALL_DIR:=%s}"\n: "${UV_PYTHON_PREFERENCE:=%s}"\n' \
        "$VLLM_TAG" "$IMAGE_REVISION" "$UV_PYTHON_INSTALL_DIR" "$UV_PYTHON_PREFERENCE" >/opt/vast-bench/image.env \
    && ln -s /opt/vast-bench/bench.sh /usr/local/bin/bench.sh \
    && ln -s /opt/vast-bench/agent-opencode.sh /usr/local/bin/agent-opencode.sh \
    && mkdir -p /workspace /results

WORKDIR /workspace
# Базовый образ задаёт ENTRYPOINT ["vllm", "serve"], его заменяем.
ENTRYPOINT ["/opt/vast-bench/entrypoint.sh"]
CMD ["sleep", "infinity"]
