#!/usr/bin/env python3
"""
Генератор README.md для DevMatrix на основе актуальных данных из data/*.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


def load_json(filename: str):
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def build_readme() -> str:
    ratings = load_json("ratings.json")
    models = load_json("models.json")
    benchmarks = load_json("benchmark_runs.json")

    # Extract executor cells
    cells = ratings.get("cells", [])
    executor_cells = [c for c in cells if c.get("role") == "executor"]
    
    # Unique models
    model_keys = sorted({c["model"] for c in executor_cells})

    # Build matrix map: model -> domain -> rating
    matrix = {}
    for c in executor_cells:
        matrix.setdefault(c["model"], {})[c["domain"]] = {
            "rating": c.get("rating", 3.0),
            "obs": c.get("observations", 0)
        }

    # Sort models by Python rating descending
    sorted_models = sorted(
        model_keys,
        key=lambda m: matrix.get(m, {}).get("Python", {}).get("rating", 0),
        reverse=True
    )

    # Leaderboard Table
    table_rows = []
    table_rows.append("| Model | Provider | Python | Web | Infra | 1C / Logic | Text / Specs | Prior + Obs |")
    table_rows.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

    for m in sorted_models:
        info = models.get(m, {})
        name = info.get("name", m)
        provider = info.get("provider", "—")
        row_vals = []
        total_obs = 0
        for d in ["Python", "Web", "Infra", "1С", "Тексты"]:
            cell = matrix.get(m, {}).get(d, {"rating": 3.0, "obs": 0})
            r = cell["rating"]
            total_obs += cell["obs"]
            badge = f"**{r:.2f}**" if r >= 4.0 else f"{r:.2f}"
            row_vals.append(badge)
        table_rows.append(f"| **{name}** | {provider} | {row_vals[0]} | {row_vals[1]} | {row_vals[2]} | {row_vals[3]} | {row_vals[4]} | n={total_obs} |")

    leaderboard_table = "\n".join(table_rows)

    # Reviewer Table
    rev_rows = []
    rev_rows.append("| Reviewer Model | Family | Accuracy (% Confirmed) | Bias / Strictness | Total Reviews |")
    rev_rows.append("| :--- | :--- | :---: | :---: | :---: |")
    for r in ratings.get("reviewers", []):
        m_id = r.get("model", "")
        if m_id in ("auto", "claude:default", "codex:default", "opencode:default"):
            continue
        info = models.get(m_id, {})
        name = info.get("name", m_id)
        fam = info.get("family", "—")
        acc = f"{r['accuracy'] * 100:.1f}%" if r.get("accuracy") is not None else "—"
        shift = f"{r['bias']:+.3f}" if r.get("bias") is not None else "+0.000"
        revs = r.get("reviews", 0)
        rev_rows.append(f"| **{name}** | `{fam}` | {acc} | `{shift}` | {revs} |")
    reviewer_table = "\n".join(rev_rows)

    # Tasks Benchmark Table
    task_rows = []
    task_rows.append("| Task | Model | Status | Pass Rate | Time | Tokens | API Cost | Diff | Review Score |")
    task_rows.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    for t in benchmarks:
        t_id = t["id"]
        for r in t["runs"]:
            status_badge = "✅ PASS" if r["status"] == "PASS" else "❌ FAIL"
            time_str = f"{r['duration_min']:.1f}m"
            tok_str = f"{r['total_tokens'] / 1_000_000:.1f}M" if r['total_tokens'] >= 1_000_000 else f"{r['total_tokens'] / 1_000:.0f}k"
            cost_str = f"${r['cost_usd']:.2f}"
            diff_str = f"+{r['diff_stat']['added']}/-{r['diff_stat']['removed']}"
            score_str = f"⭐ {r['review_score']:.1f}/5.0"
            task_rows.append(f"| `{t_id}` | **{r['model_name']}** | {status_badge} | {r['passed_tests']}/{r['total_tests']} | {time_str} | {tok_str} | {cost_str} | {diff_str} | {score_str} |")
    benchmark_table = "\n".join(task_rows)
    if not benchmarks:
        benchmark_table = "_Per-task run results will be published after the public tasks are evaluated._"

    # Load Tasks Manifest
    manifest_file = ROOT / "tasks" / "manifest.json"
    manifest_rows = []
    if manifest_file.exists():
        with open(manifest_file, encoding="utf-8") as f:
            manifest_data = json.load(f)
        manifest_rows.append("| Task ID | Title | Domain | Class | Tests |")
        manifest_rows.append("| :--- | :--- | :--- | :---: | :---: |")
        for t in manifest_data.get("tasks", []):
            manifest_rows.append(f"| [`{t['id']}`](tasks/{t['id']}) | **{t['title']}** | {t['domain']} | `{t['difficulty']}` ({t['class']}) | {t['tests_count']} tests |")
    manifest_table = "\n".join(manifest_rows)

    readme_content = f"""<div align="center">

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

{leaderboard_table}

> **Scope Factor Multipliers:** In Scope = `1.0`, Superfluous changes = `0.9`, Incomplete changes = `0.8`.

---

### Role: Multi-Agent Code Reviewer (`reviewer`)
How accurately does each model catch genuine bugs (P0/P1) without false-positive hallucinations when auditing code written by other model families?

{reviewer_table}

---

## ⚡ Direct Head-to-Head Comparison on Historical Validation Suite

Tested under identical isolated runtime conditions with full hidden test suites.

{benchmark_table}

---

## 📦 Anonymized Tasks Pool & Reproduction

The benchmark repository contains fully anonymized, self-contained tasks in [`tasks/`](tasks/):
- **Zero proprietary leakage:** All internal endpoints, credentials, and company identifiers replaced with generic domain contracts.
- **Self-contained seed environments:** Clean project roots with dependencies and passing baseline unit tests.
- **Deterministic acceptance suites:** Hidden test suites stored in `tasks/<id>/hidden/` that verify specific security, architectural, and algorithmic invariants.

{manifest_table}

### Quick start with the `devmatrix` CLI:
```bash
uvx --from git+https://github.com/Mischellin/dev-matrix devmatrix list
# Run your agent on every task (the command runs in the prepared workspace;
# {{prompt_file}} is the path to TASK_PROMPT.md) and check it against hidden tests:
uvx --from git+https://github.com/Mischellin/dev-matrix devmatrix run --all \\
    --model my-model --agent 'my-agent --prompt-file {{prompt_file}}'
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

1. Арендуйте инстанс с этим образом (GPU по `min_gpu_gb` из [`models.toml`](docker/vast-bench/models.toml), диск от 200 ГБ), дайте ему свою метку, например `devmatrix-bench`. **Сначала скопируйте результаты (шаг 4), затем удалите инстанс** — иначе аренда идёт дальше, а при удалении без копии результаты пропадут.
2. Переменные окружения: `HF_TOKEN` (если репозиторий модели требует вход), `GPU_PRICE_USD_HOUR` (цена инстанса за час из vast.ai — для `cost_usd`), по желанию `PURGE_WEIGHTS=1` (удалять веса готовой модели, если мало диска). Переменные, заданные в настройках инстанса vast.ai, в ssh-сессии могут быть не видны: проверьте `echo "${{GPU_PRICE_USD_HOUR:-нет}}"`, при необходимости выполните `export GPU_PRICE_USD_HOUR=… HF_TOKEN=…` в сессии (не вписывайте значение токена в команду, которая попадёт в историю общего журнала) или добавьте их в `/etc/environment`.
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

**Что измерено на первых прогонах** (vast.ai, vLLM v0.33.0, OpenCode 1.19.5):
- `gpt-oss-20b` на RTX 4090: 13 задач за ~9 мин; прогон обошёлся в ~$0,5 при $0,5/ч, считая скачивание и запуск (~15 мин).
- `devstral-small-2` (FP8) на RTX A6000: 1 ч 53 мин; две задачи упёрлись в лимит OpenCode 1500 с (14 млн и 1,8 млн токенов). Для плотных моделей от 24B на A6000 закладывайте бюджет времени и денег в 2–3 раза больше, чем для `gpt-oss-20b`.
- `qwen3-8-27b` до конца не прогонялся (vLLM поднимался на A6000 с `--max-num-seqs 32`, см. ниже).
- `devstral-small-2` и `qwen3-8-27b` требуют карт от 40–48 ГБ.

**Грабли.**
- **`mistral_common` 1.13.0 в базовом образе несовместим с vLLM 0.33.0**: `vllm/parser/mistral.py` вызывает `GrammarFactory.get_lark_from_jinja()` без нового обязательного аргумента `force_tool_names`, и каждый chat-запрос с tools к Devstral получает 400. В `Dockerfile` закреплён `mistral_common==1.12.0`; пин можно снять, когда vLLM начнёт передавать аргумент.
- **`qwen3-8-27b`**: без `--max-num-seqs 32` vLLM падает с «max_num_seqs (256) exceeds available Mamba cache blocks (226)». Флаг добавлен в `extra_args`, агент гоняет задачи по одной.
- **`north-mini-code`**: `--moe-backend triton` из карточки на Ampere падает («FP8 MoE backend TRITON does not support ... W8A8 per-channel»), из `extra_args` убран; без него vLLM поднялся на A6000. Поведение на Ada/Hopper с флагом из карточки не проверено.
- На рабочей станции может не быть `rsync` — копируйте результаты через `scp -r -P <порт> root@<хост>:/results/ ./vast-results/`.
- В `run-info.json` поле `image_digest` берётся из `IMAGE_DIGEST`, а если он не задан — из `IMAGE_REVISION` (источник указан в `image_digest_source`).
- Статус `vllm_died` при здоровом vLLM и упавшем на всех задачах OpenCode был ошибкой подсчёта маркеров; теперь такой прогон получает `agent_failed`.

**Результаты — с инстанса до удаления.** Сначала скопируйте `/results/` к себе (`scp`/`rsync`) и убедитесь, что файлы на месте, и только потом удаляйте инстанс. Не настраивайте автоуничтожение по бюджетному предохранителю без шага копирования: иначе прогон за деньги пропадёт вместе с диском.

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
   - Every reviewer's bias is normalized relative to global reviewer mean ($(\\mu_r - \\mu) \\cdot \\frac{{n}}{{n+3}}$).
   - Accuracy is measured by whether findings are verified as true positives or discarded as hallucinations.
3. **Tokens & Cost per Pass ($C_P$):**
   $$\\text{{Tokens per Pass}} = \\frac{{\\sum \\text{{Total Tokens of all attempts}}}}{{\\text{{Passed Runs}}}}$$

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
"""
    return readme_content


def main() -> None:
    readme_text = build_readme()
    readme_path = ROOT / "README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_text)
    print(f"Generated {readme_path}")


if __name__ == "__main__":
    main()
