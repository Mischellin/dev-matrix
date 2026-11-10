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

### Quick start with the `devmatrix` CLI:
```bash
uvx --from git+https://github.com/Mischellin/dev-matrix devmatrix list
# Run your agent on every task (the command runs in the prepared workspace;
# {prompt_file} is the path to TASK_PROMPT.md) and check it against hidden tests:
uvx --from git+https://github.com/Mischellin/dev-matrix devmatrix run --all     --model my-model --agent 'my-agent --prompt-file {prompt_file}'
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
