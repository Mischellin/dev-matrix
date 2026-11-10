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
