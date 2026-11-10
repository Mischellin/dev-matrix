<div align="center">

# 📊 DevMatrix

### **Pragmatic Real-World AI Coding Agents Benchmark & Leaderboard**

[![GitHub Pages](https://img.shields.io/badge/Live_Dashboard-GitHub_Pages-2563eb.svg?style=flat-square&logo=github)](https://mischellin.github.io/dev-matrix/)
[![Models Evaluated](https://img.shields.io/badge/models_evaluated-10_frontier_models-8b5cf6.svg?style=flat-square)](data/models.json)
[![Evaluation Engine](https://img.shields.io/badge/eval_engine-Dev_Harness-emerald.svg?style=flat-square)](https://github.com/SDKN-Digital/dev-harness)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)](LICENSE)
[![Data Status](https://img.shields.io/badge/updated-November_2026-blue.svg?style=flat-square)](data/ratings.json)

**Pass Rate · Tokens per Pass · Median Latency · True API Cost · Cross-Family Multi-Agent Review**

[🌐 **Explore Interactive Web Dashboard**](https://mischellin.github.io/dev-matrix/) · [📖 Methodology](#-methodology) · [📊 Leaderboard](#-executive-leaderboard) · [💰 Cost-per-Pass Economics](#-cost-per-pass-economics)

---

</div>

## 🎯 What is DevMatrix?

Most existing LLM coding benchmarks evaluate models on isolated toy problems, synthetic unit puzzles, or single-file scripts. 

**DevMatrix** measures what actually matters when deploying autonomous AI software engineers in production:
1. **Real-World Software Engineering:** Multi-file repositories, real database migrations (Alembic/PostgreSQL), concurrency invariants, clock-skew security edge cases, and framework idioms.
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

| Task | Model | Status | Pass Rate | Time | Tokens | API Cost | Diff | Review Score |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `slottix-240` | **Claude 3.7 Sonnet** | ✅ PASS | 14/14 | 5.1m | 820k | $0.45 | +62/-8 | ⭐ 4.8/5.0 |
| `slottix-240` | **Codex Sol** | ✅ PASS | 14/14 | 6.4m | 1.1M | $0.52 | +58/-6 | ⭐ 4.7/5.0 |
| `slottix-240` | **MiniMax-M3.1-Flash** | ✅ PASS | 14/14 | 30.0m | 15.9M | $0.85 | +44/-11 | ⭐ 4.2/5.0 |
| `slottix-240` | **GLM-5.3** | ✅ PASS | 14/14 | 18.2m | 6.4M | $0.70 | +49/-9 | ⭐ 4.1/5.0 |
| `slottix-240` | **Gemini 3.8 Flash** | ✅ PASS | 14/14 | 12.5m | 7.5M | $0.22 | +71/-14 | ⭐ 4.0/5.0 |
| `pantry-8` | **Claude 3.7 Sonnet** | ✅ PASS | 14/14 | 7.3m | 1.2M | $0.75 | +210/-25 | ⭐ 4.9/5.0 |
| `pantry-8` | **Codex Sol** | ✅ PASS | 14/14 | 8.0m | 1.4M | $0.68 | +195/-30 | ⭐ 4.8/5.0 |
| `pantry-8` | **MiniMax-M3.1-Flash** | ✅ PASS | 14/14 | 23.9m | 16.5M | $0.95 | +650/-51 | ⭐ 4.0/5.0 |
| `pantry-8` | **GLM-5.3** | ✅ PASS | 14/14 | 21.0m | 8.9M | $0.88 | +280/-40 | ⭐ 4.3/5.0 |
| `arbita-12` | **Claude 3.7 Sonnet** | ✅ PASS | 10/10 | 3.8m | 640k | $0.38 | +85/-12 | ⭐ 4.9/5.0 |
| `arbita-12` | **Codex Sol** | ✅ PASS | 10/10 | 4.5m | 780k | $0.40 | +78/-10 | ⭐ 4.8/5.0 |
| `arbita-12` | **Gemini 4 Argon** | ✅ PASS | 10/10 | 20.0m | 4.2M | $0.90 | +95/-18 | ⭐ 4.5/5.0 |
| `arbita-12` | **Qwen 3.8 Max** | ✅ PASS | 10/10 | 17.0m | 3.8M | $0.65 | +90/-14 | ⭐ 4.3/5.0 |

---

## 📦 Anonymized Tasks Pool & Reproduction

The benchmark repository contains fully anonymized, self-contained tasks in [`tasks/`](tasks/):
- **Zero proprietary leakage:** All internal endpoints, credentials, and company identifiers replaced with generic domain contracts.
- **Self-contained seed environments:** Clean project roots with dependencies and passing baseline unit tests.
- **Deterministic acceptance suites:** Hidden test suites stored in `tasks/<id>/hidden/` that verify specific security, architectural, and algorithmic invariants.

| Task ID | Title | Domain | Class | Tests |
| :--- | :--- | :--- | :---: | :---: |
| [`sec-01-clock-skew`](tasks/sec-01-clock-skew) | **Validate WebApp Auth Clock Skew and Reject Future Timestamps** | Python / Security & Crypto | `S` (security) | 6 assertions |
| [`obs-02-query-redactor`](tasks/obs-02-query-redactor) | **Redact Sensitive Query Parameters from Server Access Logs** | Python / Observability & Security | `S` (security) | 34 assertions |
| [`algo-03-range-merger`](tasks/algo-03-range-merger) | **Robust Interval String Parser and Overlap Merger** | Python / Algorithms | `S` (algorithm) | 23 assertions |
| [`arch-04-tag-registry`](tasks/arch-04-tag-registry) | **Normalized Tag Registry with Alphabetical Ordering and Scope Protection** | Python / Data Architecture & Security | `M` (architecture) | 8 assertions |

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
