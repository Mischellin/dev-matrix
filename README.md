<div align="center">

# 📊 DevMatrix

### **Pragmatic Real-World AI Coding Agents Benchmark & Leaderboard**

[![GitHub Pages](https://img.shields.io/badge/Live_Dashboard-GitHub_Pages-2563eb.svg?style=flat-square&logo=github)](https://mischellin.github.io/dev-matrix/)
[![Models Evaluated](https://img.shields.io/badge/models_in_matrix-10-8b5cf6.svg?style=flat-square)](data/models.json)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)](LICENSE)
[![Data Status](https://img.shields.io/badge/updated-November_2026-blue.svg?style=flat-square)](data/ratings.json)

**Pass Rate · Tokens per Pass · Median Latency · True API Cost · Cross-Family Multi-Agent Review**

[🌐 **Explore Interactive Web Dashboard**](https://mischellin.github.io/dev-matrix/) · [📖 Methodology](#-methodology) · [📊 Leaderboard](#-executive-leaderboard) · [💰 Cost-per-Pass Economics](#-cost-per-pass-economics)

---

</div>

## 🎯 What is DevMatrix?

Most existing LLM coding benchmarks evaluate models on isolated toy problems, synthetic unit puzzles, or single-file scripts. 

**DevMatrix** measures what actually matters when deploying autonomous AI software engineers in production:
1. **Real-World Software Engineering:** Multi-file repositories, self-contained modules with hidden acceptance tests: security edge cases (clock skew, log redaction), algorithms, data architecture, Kubernetes admission policy and 1C:Enterprise BSL logic.
2. **Deterministic Hard Verification:** Every task executes inside an isolated `git worktree`. Success requires passing 100% of hidden acceptance tests and preserving all existing suite assertions.
3. **Multi-Agent Cross-Family Review:** Completed solutions are evaluated by an independent reviewer from an **entirely different model family** (e.g., Claude reviewed by Codex/GPT, Codex reviewed by Sonnet). Reviewers detect subtle regressions, rubric compliance, and overengineering.
4. **True Economics (Tokens & Cost per Pass):** A cheap model with an 80% failure rate that takes 20 retries is vastly more expensive than a premium model that solves the problem on the first attempt. DevMatrix reports the **true expenditure per accepted task**.

---

## 🏆 Executive Leaderboard

### Role: Autonomous Executor (`executor`)
Ratings are computed dynamically on a 1.0–5.0 scale with Bayesian prior ($w=3$, prior=$3.0$), factoring task complexity, reviewer strictness adjustment, and scope penalty factor.

| Model | Provider | Python | Web | Infra | 1C / Logic | Text / Specs | Prior + Obs |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Codex Sol (GPT-SWE)** | OpenAI | **4.42** | **4.00** | **4.50** | 3.50 | 3.50 | n=1 |
| **MiniMax-M3.1-Flash** | MiniMax | **4.20** | 3.80 | **4.00** | 3.00 | 3.50 | n=10 |
| **Grok 4.7** | xAI | **4.17** | 3.50 | 3.82 | 2.50 | 3.00 | n=5 |
| **GLM-5.3** | Zhipu AI | **4.10** | 3.90 | 3.70 | 3.00 | 3.80 | n=10 |
| **Codex Luna (Fast SWE)** | OpenAI | 3.63 | 3.50 | 3.50 | 3.00 | 3.00 | n=1 |
| **Claude 3.7 Sonnet** | Anthropic | 3.55 | **4.00** | **4.00** | **4.50** | **4.50** | n=2 |
| **GPT-6 Astra** | OpenAI | 3.37 | 3.00 | 3.00 | 3.00 | 3.00 | n=2 |
| **Gemini 3.8 Flash** | Google | 3.31 | 3.50 | 3.00 | 2.50 | 3.50 | n=1 |
| **Gemini 4 Argon** | Google | 3.00 | 3.00 | 3.00 | 3.00 | 3.00 | n=0 |
| **Qwen 3.8 Max** | Alibaba | 3.00 | 3.00 | 3.00 | 3.00 | 3.00 | n=0 |

> **Scope Factor Multipliers:** In Scope = `1.0`, Superfluous changes = `0.9`, Incomplete changes = `0.8`.

---

### Role: Multi-Agent Code Reviewer (`reviewer`)
How accurately does each model catch genuine bugs (P0/P1) without false-positive hallucinations when auditing code written by other model families?

| Reviewer Model | Family | Accuracy (% Confirmed) | Bias / Strictness | Total Reviews |
| :--- | :--- | :---: | :---: | :---: |
| **Codex Luna (Fast SWE)** | `codex` | — | `+0.000` | 11 |
| **Gemini 4 Argon** | `gemini` | — | `+0.000` | 19 |
| **Gemini 3.8 Flash** | `gemini` | — | `+0.212` | 169 |
| **GPT-6 Astra** | `codex` | 100.0% | `-0.433` | 37 |
| **Qwen 3.8 Max** | `qwen` | — | `-0.033` | 64 |
| **Claude 3.7 Sonnet** | `claude` | 100.0% | `+0.000` | 17 |

---

## ⚡ Direct Head-to-Head Comparison on Historical Validation Suite

Tested under identical isolated runtime conditions with full hidden test suites.

_Per-task run results will be published after the public tasks are evaluated._

---

## 📦 Anonymized Tasks Pool & Reproduction

The benchmark repository contains fully anonymized, self-contained tasks in [`tasks/`](tasks/):
- **Zero proprietary leakage:** All internal endpoints, credentials, and company identifiers replaced with generic domain contracts.
- **Self-contained seed environments:** Clean project roots with dependencies and passing baseline unit tests.
- **Deterministic acceptance suites:** Hidden test suites stored in `tasks/<id>/hidden/` that verify specific security, architectural, and algorithmic invariants.

| Task ID | Title | Domain | Class | Tests |
| :--- | :--- | :--- | :---: | :---: |
| [`sec-01-clock-skew`](tasks/sec-01-clock-skew) | **Validate WebApp Auth Clock Skew and Reject Future Timestamps** | Python / Security & Crypto | `S` (security) | 6 tests |
| [`obs-02-query-redactor`](tasks/obs-02-query-redactor) | **Redact Sensitive Query Parameters from Server Access Logs** | Python / Observability & Security | `S` (security) | 37 tests |
| [`algo-03-range-merger`](tasks/algo-03-range-merger) | **Robust Interval String Parser and Overlap Merger** | Python / Algorithms | `S` (algorithm) | 27 tests |
| [`arch-04-tag-registry`](tasks/arch-04-tag-registry) | **Normalized Tag Registry with Alphabetical Ordering and Scope Protection** | Python / Data Architecture & Security | `M` (architecture) | 8 tests |
| [`infra-05-k8s-pod-admission`](tasks/infra-05-k8s-pod-admission) | **Kubernetes Pod Security and Topology Spread Admission Mutator** | Infra / Kubernetes & Platform Engineering | `M` (infrastructure) | 20 tests |
| [`onec-06-payment-allocator`](tasks/onec-06-payment-allocator) | **1C:Enterprise BSL Payment Allocation and FIFO Order Matching** | 1С / Enterprise BSL & Accounting | `M` (feature) | 16 tests |
| [`auth-07-claim-roles`](tasks/auth-07-claim-roles) | **Derive Gateway Permissions from Role Claims Instead of OAuth Scope** | Python / Authorization & Identity | `M` (bugfix) | 14 tests |
| [`authz-12-uniform-404`](tasks/authz-12-uniform-404) | **Uniform NotFound for Missing and Unauthorized Documents** | Python / Security & Access Control | `M` (security) | 15 tests |
| [`flag-10-feature-flag-router`](tasks/flag-10-feature-flag-router) | **Mount a Sub-API Only When a Feature Flag Is Enabled** | Python / Feature Flags & Routing | `M` (feature) | 16 tests |
| [`host-08-host-header-guard`](tasks/host-08-host-header-guard) | **Host Header Allow-List for a DNS-Rebinding Guard** | Python / Web Security | `M` (bugfix) | 15 tests |
| [`idem-13-idempotent-signup`](tasks/idem-13-idempotent-signup) | **Idempotent, Retry-Safe Business Self-Registration** | Python / Idempotency & Distributed Consistency | `M` (bugfix) | 17 tests |
| [`scrub-09-metadata-scrubber`](tasks/scrub-09-metadata-scrubber) | **Redact Sensitive Event Metadata Recursively** | Python / Security & Data Privacy | `M` (security) | 15 tests |
| [`tenant-11-scoped-listing`](tasks/tenant-11-scoped-listing) | **Scope Document Listing and Total Count by Role and Client Assignment** | Python / Multi-tenant Access Control | `M` (security) | 16 tests |

### Quick start with the `devmatrix` CLI:
```bash
uvx --from git+https://github.com/Mischellin/dev-matrix devmatrix list
# Run your agent on every task (the command runs in the prepared workspace;
# {prompt_file} is the path to TASK_PROMPT.md) and check it against hidden tests:
uvx --from git+https://github.com/Mischellin/dev-matrix devmatrix run --all \
    --model my-model --agent 'my-agent --prompt-file {prompt_file}'
# Send the results to the leaderboard as a pull request (needs the `gh` CLI):
uvx --from git+https://github.com/Mischellin/dev-matrix devmatrix submit
```
Token counts, cost and time are reported by you and are shown as "claimed by author".
The hidden tests are public, so submissions are not a trusted ranking.

### Reproduce or Evaluate Locally:
> **Requirements**: Python `>= 3.11` and [`uv`](https://astral.sh/uv) (recommended) or `pytest >= 8.0`.

```bash
# 1. Verify the entire benchmark suite and all reference solutions:
python3 scripts/runner.py verify-suite

# 2. Prepare an isolated workspace for your AI agent:
python3 scripts/runner.py prepare --task sec-01-clock-skew --out /tmp/agent-workdir

# 3. Point your coding agent (Claude Code, Codex, Antigravity, OpenCode) to /tmp/agent-workdir
# Agent reads TASK_PROMPT.md, makes code edits and tests locally.

# 4. Evaluate the agent's workdir against hidden acceptance assertions:
python3 scripts/runner.py evaluate --task sec-01-clock-skew --workdir /tmp/agent-workdir
```

---

## 🐳 Контейнер для vast.ai

Образ `ghcr.io/mischellin/dev-matrix-vast-bench` (сборка — `docker/vast-bench/`, workflow `vast-bench-image.yml`, запуск вручную или тегом `vast-bench-*`) содержит vLLM, OpenCode и `devmatrix`. Весов и секретов в нём нет. Новый пакет ghcr по умолчанию **приватный**: после первой сборки один раз откройте GitHub → Packages → `dev-matrix-vast-bench` → Package settings → Change visibility → Public, иначе vast.ai не сможет скачать образ без токена. Только модели, которые помещаются на **одну** карту (без tensor parallel).

1. Арендуйте инстанс с этим образом (GPU по `min_gpu_gb` из [`models.toml`](docker/vast-bench/models.toml), диск от 200 ГБ), дайте ему свою метку, например `devmatrix-bench`. **После прогона удалите инстанс**, иначе аренда идёт дальше.
2. Переменные окружения: `HF_TOKEN` (если репозиторий модели требует вход), `GPU_PRICE_USD_HOUR` (цена инстанса за час из vast.ai — для `cost_usd`), по желанию `PURGE_WEIGHTS=1` (удалять веса готовой модели, если мало диска). Переменные, заданные в настройках инстанса vast.ai, в ssh-сессии могут быть не видны: проверьте `echo "${GPU_PRICE_USD_HOUR:-нет}"`, при необходимости выполните `export GPU_PRICE_USD_HOUR=… HF_TOKEN=…` в сессии (не вписывайте значение токена в команду, которая попадёт в историю общего журнала) или добавьте их в `/etc/environment`.
3. На инстансе по ssh запускайте прогон внутри `tmux` (или `nohup … &`): прогон идёт часами, обрыв ssh иначе убьёт его вместе с vLLM.
   ```bash
   /opt/vast-bench/entrypoint.sh list                       # пресеты
   tmux new -s bench
   /opt/vast-bench/entrypoint.sh bench gpt-oss-20b devstral-small-2   # модели подряд
   # или: nohup /opt/vast-bench/entrypoint.sh bench gpt-oss-20b devstral-small-2 >/results/bench.out 2>&1 &
   ```
   Пока идёт одна модель, следующая докачивается в фоне. Для каждой: скачивание → `vllm serve` → `devmatrix run --all` с агентом OpenCode → остановка vLLM.
4. Забрать результаты и отправить их со своей машины, где есть `gh` (в контейнере токена нет):
   ```bash
   rsync -av -e 'ssh -p <порт>' root@<хост>:/results/ ./vast-results/
   devmatrix submit --dir vast-results/<пресет>/submissions
   ```
   В `/results/<пресет>/`: `submissions/` (отчёты devmatrix), `vllm.log`, `opencode/`, `metrics/`, `run-info.json` (статус, тег vLLM, версии, GPU, флаги, ревизия образа), при падении vLLM во время прогона — `invalid/` (см. ниже).

**Падение vLLM.** Агент проверяет `/health` до и после запуска OpenCode; если vLLM не отвечает, задача получает маркер `metrics/<задача>.invalid`, а её отчёт переносится из `submissions/` в `invalid/` и перечисляется в `run-info.json` (`invalid_tasks`) — мёртвый сервер не считается провалом модели, и такой «ноль» нельзя отправить. Статус `vllm_died` в `run-info.json` значит, что прогон надо повторить; `devmatrix_failed` — сбой самого запуска или не все отчёты на месте. Так же помечается задача, где OpenCode упал (код не 0 и не 124), а vLLM не сгенерировал ни одного токена; если так вышло на большинстве задач, статус — `agent_failed` (проверьте `opencode/*.err`, имя модели и конфиг). `OPENCODE_TIMEOUT` должен быть меньше `AGENT_TIMEOUT` минимум на 120 с, иначе `bench.sh` не стартует. Лог фоновой докачки следующей модели — `download.prefetch.log`; её сбой выводится в консоль, веса тогда качаются заново (`download.log`). Токены с отрицательной дельтой (счётчики vLLM сбросились) записываются как `null`.

**Какой пресет на какую карту** (`min_gpu_gb` из `models.toml`; для North Mini Code это оценка, а не измерение):

| Карта | Пресеты |
|---|---|
| 24 ГБ и 32 ГБ | `gpt-oss-20b` (MXFP4, веса ~14 ГБ) |
| 40 ГБ | `gpt-oss-20b`, `north-mini-code` (официальный FP8, веса ~32 ГБ; впритык — оценка) |
| 48 ГБ | всё выше, плюс `devstral-small-2`, `qwen3-8-27b` |
| 80 ГБ | всё выше, плюс `kat-coder-v2-5-dev` — **единственный пресет, которому нужна карта 80 ГБ** (BF16 69 ГБ с онлайн-квантованием; официального FP8/AWQ у автора нет), для дешёвых прогонов его можно пропустить |

Порядок для небольшого бюджета: `gpt-oss-20b`, `devstral-small-2`, `qwen3-8-27b`, `north-mini-code`, затем `kat-coder-v2-5-dev`.

**Оговорки.** Результаты получены на квантованных моделях: готовые MXFP4/FP8-чекпойнты (gpt-oss-20b, Devstral, Qwen3.8, North Mini Code) и онлайн-квантование vLLM `--quantization fp8_per_tensor` из BF16 для KAT-Coder (для него нужна карта класса 80 ГБ: BF16-чекпойнт 69 ГБ может целиком лечь в видеопамять до сжатия). Они несопоставимы с другими квантованиями и с API-версиями тех же моделей. North Mini Code по коду vLLM v0.33.0 загружается, но запуском не проверен, и пакет `cohere_melody` для его парсеров в образ не установлен. Токены — сумма дельт счётчиков `vllm:prompt_tokens` и `vllm:generation_tokens` за задачу; `cost_usd` = `agent_seconds / 3600 × GPU_PRICE_USD_HOUR` (только время работы агента, без скачивания и загрузки модели). Как и всё остальное в `devmatrix submit`, эти значения — «заявлено автором». Не проверено запуском: парсеры tool-call/reasoning для моделей, где карточка их не называет (пометки — в `notes` пресетов), и сборка образа.

---

## 🔬 Methodology

```
┌────────────────────────────────────────────────────────┐
│               Task Specification & Base Commit         │
└───────────────────────────┬────────────────────────────┘
                            │ Isolated git worktree
                            ▼
┌────────────────────────────────────────────────────────┐
│          Autonomous Coding Agent (Executor)            │
│   • Multi-file edits                                   │
│   • Tool calls & terminal commands                     │
└───────────────────────────┬────────────────────────────┘
                            │ Check execution
                            ▼
┌────────────────────────────────────────────────────────┐
│         Verifier: Hidden Acceptance Test Suite         │
│   • 100% tests must pass (Zero tolerance)             │
│   • Existing tests must remain unbroken                │
└───────────────────────────┬────────────────────────────┘
                            │ If PASSED
                            ▼
┌────────────────────────────────────────────────────────┐
│     Independent Multi-Agent Reviewer (Other Family)    │
│   • P0/P1 findings & security audit                    │
│   • Complexity & quality score (1-5)                   │
└────────────────────────────────────────────────────────┘
```

1. **Deterministic Verifier ($Q_V$):**
   - The agent does not see the hidden acceptance tests.
   - All tests run in clean sandbox environments.
2. **Review Strictness Calibration:**
   - Every reviewer's bias is normalized relative to global reviewer mean ($(\mu_r - \mu) \cdot \frac{n}{n+3}$).
   - Accuracy is measured by whether findings are verified as true positives or discarded as hallucinations.
3. **Tokens & Cost per Pass ($C_P$):**
   $$\text{Tokens per Pass} = \frac{\sum \text{Total Tokens of all attempts}}{\text{Passed Runs}}$$

---

## 🚀 Running and Reproducing

Data files are stored in [`data/`](data/) in machine-readable JSON format:
- `data/ratings.json`: Full 3D matrix (Model × Role × Domain).
- `data/models.json`: Model parameters, context windows, and token pricing.
- `data/benchmark_runs.json`: Detailed execution metrics across tasks.

To refresh and update README tables:
```bash
python3 scripts/export_metrics.py
python3 scripts/generate_readme.py
```

---

## 📄 License

DevMatrix is open-source software licensed under the [MIT License](LICENSE).
