# Образ для прогона DevMatrix на арендованном GPU (vast.ai): vLLM + OpenCode + CLI devmatrix.
# Без весов моделей и без секретов: веса качаются на инстансе в $HF_HOME, HF_TOKEN передаётся env.
#
# Сборка из корня репозитория:
#   docker build -f docker/vast-bench/Dockerfile -t dev-matrix-vast-bench .
#
# Тег vLLM: проверены по Docker Hub v0.31.0, v0.32.0, v0.33.0 (существуют); архитектуры из models.toml
# (GptOss, Mistral3, Qwen3_5, Qwen3_5Moe, Cohere2Moe) и парсеры найдены в исходниках v0.33.0.
# Для более новых архитектур поднимите тег: --build-arg VLLM_TAG=<тег>.
# Образ собирает workflow vast-bench-image.yml. Первые реальные прогоны шли на образе из этого Dockerfile с тегом
# vast-bench-rc1 (до пина mistral_common и правок models.toml: их тогда внесли руками на инстансе); сборки rc2/rc3
# и новее содержат всё это в Dockerfile и models.toml.
#
# Защита эталонов. Агент (OpenCode) читает файловую систему контейнера, поэтому:
#  - .dockerignore не пускает в контекст tasks/*/reference_solution, submissions и tests;
#  - скрытые тесты (tasks/*/hidden) devmatrix нужны при проверке, они лежат в установленном пакете
#    /opt/uv-tools (колесо без reference_solution); /opt/dev-matrix после установки удаляется;
#  - /opt/uv-tools, /opt/uv-cache и /results закрыты правами 0700 для root, а OpenCode запускается от
#    непривилегированного пользователя agent (agent-opencode.sh через setpriv), владеющего только рабочей папкой
#    задачи и своим HOME на эту задачу (удаляется после неё). Проверяет devmatrix и пишет результаты root, агент их
#    не видит. Проверка запускает код агента от root (scripts/runner.py не меняем): см. README, раздел про изоляцию.
#  - pytest 8.3.4 стоит системно, и рядом лежит прогретый кэш uv только с pytest (/opt/agent-uv-cache, читается
#    всеми): агент гоняет тесты без root-кэша /opt/uv-cache, где колесо со скрытыми тестами.
# Агент по-прежнему читает всё остальное в образе (vLLM, исходники публичного репозитория не секрет), но не
# решения и не скрытые тесты. Публичный репозиторий задач в сети доступен всем — защита от поиска по
# файловой системе, не от доступа в интернет.
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

# pytest для агента: `python -m pytest` на системном Python vLLM (версия та же, что у runner).
RUN uv pip install --system "pytest==8.3.4" && python3 -m pytest --version

# Парсеры tool-call/reasoning North-Mini-Code (cohere_command4) работают через cohere_melody (по карточке модели).
RUN uv pip install --system "cohere_melody>=0.9.0" \
    && python3 -c "import cohere_melody"

# Базовый образ vllm/vllm-openai:v0.33.0 несёт mistral_common 1.13.0, несовместимый с этим vLLM:
# vllm/parser/mistral.py вызывает GrammarFactory.get_lark_from_jinja() без нового обязательного аргумента
# force_tool_names, и каждый chat-запрос с tools к Devstral отвечает 400. Закрепляем 1.12.0.
# Убрать пин, когда vLLM начнёт передавать force_tool_names (проверять при подъёме VLLM_TAG).
# uv pip check печатает конфликты требований, если пин что-то нарушил (не валит сборку: в базовом образе
# конфликты могут быть и без нас, смотрите вывод сборки).
RUN uv pip install --system "mistral_common==1.12.0" \
    && { uv pip check --system || echo "ВНИМАНИЕ: uv pip check нашёл конфликты после пина mistral_common"; }

# CLI devmatrix: отдельное окружение на Python 3.12 от uv, чтобы не трогать Python vLLM.
COPY . /opt/dev-matrix
RUN uv tool install --python 3.12 /opt/dev-matrix \
    && devmatrix --version \
    && devmatrix list | head -3 \
    # runner проверяет задачи через uv run --with pytest: прогреваем кэш, чтобы не качать на инстансе
    && uv run --no-project --python 3.12 --with pytest==8.3.4 python -c "import pytest" \
    && python3 -c "import tomllib" \
    # исходники не нужны: пакет (с hidden, без reference_solution) уже установлен в /opt/uv-tools
    && rm -rf /opt/dev-matrix \
    # прогретый кэш uv только с pytest для агента (отдельный от /opt/uv-cache, где колесо с hidden); агент копирует его
    # в свой HOME на задачу, окружения-симлинки не нужны
    && UV_CACHE_DIR=/opt/agent-uv-cache uv run --no-project --python 3.12 --with pytest==8.3.4 python -c "import pytest" \
    && find /opt/agent-uv-cache -maxdepth 1 -name 'environments*' -exec rm -rf {} + \
    && chmod -R a+rX /opt/agent-uv-cache /opt/uv-python

COPY docker/vast-bench/ /opt/vast-bench/
RUN chmod +x /opt/vast-bench/*.sh /opt/vast-bench/preset.py \
    # ssh-сессии не наследуют ENV образа: env.sh подхватывает эти значения из image.env
    && printf ': "${VLLM_TAG:=%s}"\n: "${IMAGE_REVISION:=%s}"\n: "${UV_PYTHON_INSTALL_DIR:=%s}"\n: "${UV_PYTHON_PREFERENCE:=%s}"\n' \
        "$VLLM_TAG" "$IMAGE_REVISION" "$UV_PYTHON_INSTALL_DIR" "$UV_PYTHON_PREFERENCE" >/opt/vast-bench/image.env \
    && ln -s /opt/vast-bench/bench.sh /usr/local/bin/bench.sh \
    && ln -s /opt/vast-bench/agent-opencode.sh /usr/local/bin/agent-opencode.sh \
    && mkdir -p /workspace /results \
    # непривилегированный пользователь для OpenCode; скрытые тесты и результаты закрыты от него
    && useradd --create-home --home-dir /home/agent --shell /bin/bash agent \
    && chmod 700 /opt/uv-tools /opt/uv-cache /results

WORKDIR /workspace
# Базовый образ задаёт ENTRYPOINT ["vllm", "serve"], его заменяем.
ENTRYPOINT ["/opt/vast-bench/entrypoint.sh"]
CMD ["sleep", "infinity"]
