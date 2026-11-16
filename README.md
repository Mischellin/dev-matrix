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

| Model | Tasks passed | Tests passed |
| :--- | :---: | :---: |
| **DeepSeek V4 Pro** | 13/13 | 222/222 |
| **DeepSeek V4.1 Flash 1017** | 13/13 | 222/222 |
| **GLM-5.3** | 13/13 | 222/222 |
| **Kimi K3-256K** | 13/13 | 222/222 |
| **Qwen3.8 Flash via Alibaba** | 13/13 | 222/222 |
| **GLM-5.2 via Alibaba** | 12/13 | 221/222 |
| **Kimi K3.1 Pro** | 12/13 | 221/222 |
| **Qwen3.7 Max via Alibaba** | 12/13 | 221/222 |
| **Kimi for Coding** | 12/13 | 220/222 |
| **Qwen4 Max Preview** | 12/13 | 220/222 |
| **Inkling 2 Small Free** | 11/13 | 219/222 |
| **GLM-5.3-Flash** | 11/13 | 218/222 |
| **Iceman Free** | 11/13 | 218/222 |
| **Qwen3.8 Max via Alibaba** | 11/13 | 190/222 |
| **Qwen3.7 Plus via Alibaba** | 10/13 | 217/222 |
| **MiniMax M3.1 Flash** | 6/13 | 142/206 |

*GLM-5.3: prompt-v2 rerun (v1 hidden-access violations recorded, v1 run replaced)*
*Kimi K3.1 Pro: prompt-v2 rerun (v1 hidden-access violations recorded, v1 run replaced)*

_Results come from [`submissions/`](submissions/); time, tokens and cost are reported by the submitter ("claimed by author"). The hidden tests are public, so this is not a trusted ranking. Runs marked outdated were made on an older version of the task and are not counted in the summary. Runs marked INVALID were withdrawn after audit (see [`data/run_overrides.json`](data/run_overrides.json)) and are not counted in the summary either. After merging a PR with results, run `python3 scripts/export_metrics.py --only-benchmarks && python3 scripts/generate_readme.py` and commit `data/benchmark_runs.json` and `README.md` (the Pages deploy rebuilds the page itself)._

| Task | Model | Status | Tests | Time | Tokens | API Cost |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `algo-03-range-merger` | **DeepSeek V4 Pro** | ✅ PASS | 27/27 | 1.0m | — | — |
| `algo-03-range-merger` | **DeepSeek V4.1 Flash 1017** | ✅ PASS | 27/27 | 0.7m | — | — |
| `algo-03-range-merger` | **GLM-5.2 via Alibaba** | ✅ PASS | 27/27 | 3.3m | — | — |
| `algo-03-range-merger` | **GLM-5.3** | ✅ PASS | 27/27 | 2.2m | — | — |
| `algo-03-range-merger` | **GLM-5.3-Flash** | ✅ PASS | 27/27 | 1.4m | — | — |
| `algo-03-range-merger` | **Iceman Free** | ✅ PASS | 27/27 | 1.4m | — | — |
| `algo-03-range-merger` | **Inkling 2 Small Free** | ✅ PASS | 27/27 | 0.8m | — | — |
| `algo-03-range-merger` | **Kimi for Coding** | ✅ PASS | 27/27 | 1.8m | — | — |
| `algo-03-range-merger` | **Kimi K3-256K** | ✅ PASS | 27/27 | 0.9m | — | — |
| `algo-03-range-merger` | **Kimi K3.1 Pro** | ✅ PASS | 27/27 | 3.7m | — | — |
| `algo-03-range-merger` | **MiniMax M3.1 Flash** | ✅ PASS | 27/27 | 3.0m | — | — |
| `algo-03-range-merger` | **Qwen3.7 Max via Alibaba** | ✅ PASS | 27/27 | 1.4m | — | — |
| `algo-03-range-merger` | **Qwen3.7 Plus via Alibaba** | ✅ PASS | 27/27 | 3.3m | — | — |
| `algo-03-range-merger` | **Qwen3.8 Flash via Alibaba** | ✅ PASS | 27/27 | 1.8m | — | — |
| `algo-03-range-merger` | **Qwen3.8 Max via Alibaba** | ✅ PASS | 27/27 | 17.1m | — | — |
| `algo-03-range-merger` | **Qwen4 Max Preview** | ✅ PASS | 27/27 | 2.0m | — | — |
| `arch-04-tag-registry` | **DeepSeek V4 Pro** | ✅ PASS | 8/8 | 0.8m | — | — |
| `arch-04-tag-registry` | **DeepSeek V4.1 Flash 1017** | ✅ PASS | 8/8 | 0.7m | — | — |
| `arch-04-tag-registry` | **GLM-5.2 via Alibaba** | ✅ PASS | 8/8 | 3.3m | — | — |
| `arch-04-tag-registry` | **GLM-5.3** | ✅ PASS | 8/8 | 2.0m | — | — |
| `arch-04-tag-registry` | **GLM-5.3-Flash** | ✅ PASS | 8/8 | 1.6m | — | — |
| `arch-04-tag-registry` | **Iceman Free** | ✅ PASS | 8/8 | 1.1m | — | — |
| `arch-04-tag-registry` | **Inkling 2 Small Free** | ✅ PASS | 8/8 | 0.6m | — | — |
| `arch-04-tag-registry` | **Kimi for Coding** | ✅ PASS | 8/8 | 1.4m | — | — |
| `arch-04-tag-registry` | **Kimi K3-256K** | ✅ PASS | 8/8 | 2.8m | — | — |
| `arch-04-tag-registry` | **Kimi K3.1 Pro** | ✅ PASS | 8/8 | 2.5m | — | — |
| `arch-04-tag-registry` | **MiniMax M3.1 Flash** | ❌ FAIL | 2/8 | 30.0m | — | — |
| `arch-04-tag-registry` | **Qwen3.7 Max via Alibaba** | ✅ PASS | 8/8 | 1.3m | — | — |
| `arch-04-tag-registry` | **Qwen3.7 Plus via Alibaba** | ✅ PASS | 8/8 | 1.9m | — | — |
| `arch-04-tag-registry` | **Qwen3.8 Flash via Alibaba** | ✅ PASS | 8/8 | 1.5m | — | — |
| `arch-04-tag-registry` | **Qwen3.8 Max via Alibaba** | ✅ PASS | 8/8 | 3.7m | — | — |
| `arch-04-tag-registry` | **Qwen4 Max Preview** | ✅ PASS | 8/8 | 2.2m | — | — |
| `auth-07-claim-roles` | **DeepSeek V4 Pro** | ✅ PASS | 14/14 | 1.4m | — | — |
| `auth-07-claim-roles` | **DeepSeek V4.1 Flash 1017** | ✅ PASS | 14/14 | 1.1m | — | — |
| `auth-07-claim-roles` | **GLM-5.2 via Alibaba** | ✅ PASS | 14/14 | 2.9m | — | — |
| `auth-07-claim-roles` | **GLM-5.3** | ✅ PASS | 14/14 | 4.6m | — | — |
| `auth-07-claim-roles` | **GLM-5.3-Flash** | ✅ PASS | 14/14 | 4.0m | — | — |
| `auth-07-claim-roles` | **Iceman Free** | ✅ PASS | 14/14 | 1.9m | — | — |
| `auth-07-claim-roles` | **Inkling 2 Small Free** | ✅ PASS | 14/14 | 1.2m | — | — |
| `auth-07-claim-roles` | **Kimi for Coding** | ✅ PASS | 14/14 | 1.5m | — | — |
| `auth-07-claim-roles` | **Kimi K3-256K** | ✅ PASS | 14/14 | 1.2m | — | — |
| `auth-07-claim-roles` | **Kimi K3.1 Pro** | ✅ PASS | 14/14 | 5.6m | — | — |
| `auth-07-claim-roles` | **MiniMax M3.1 Flash** | ❌ FAIL | 4/14 | 30.0m | — | — |
| `auth-07-claim-roles` | **Qwen3.7 Max via Alibaba** | ✅ PASS | 14/14 | 1.3m | — | — |
| `auth-07-claim-roles` | **Qwen3.7 Plus via Alibaba** | ✅ PASS | 14/14 | 2.1m | — | — |
| `auth-07-claim-roles` | **Qwen3.8 Flash via Alibaba** | ✅ PASS | 14/14 | 1.8m | — | — |
| `auth-07-claim-roles` | **Qwen3.8 Max via Alibaba** | ✅ PASS | 14/14 | 6.8m | — | — |
| `auth-07-claim-roles` | **Qwen4 Max Preview** | ✅ PASS | 14/14 | 3.7m | — | — |
| `authz-12-uniform-404` | **DeepSeek V4 Pro** | ✅ PASS | 15/15 | 1.2m | — | — |
| `authz-12-uniform-404` | **DeepSeek V4.1 Flash 1017** | ✅ PASS | 15/15 | 0.8m | — | — |
| `authz-12-uniform-404` | **GLM-5.2 via Alibaba** | ✅ PASS | 15/15 | 4.9m | — | — |
| `authz-12-uniform-404` | **GLM-5.3** | ✅ PASS — audit requalified: false positive | 15/15 | 3.9m | — | — |
| `authz-12-uniform-404` | **GLM-5.3-Flash** | ✅ PASS | 15/15 | 4.1m | — | — |
| `authz-12-uniform-404` | **Iceman Free** | ✅ PASS | 15/15 | 1.8m | — | — |
| `authz-12-uniform-404` | **Inkling 2 Small Free** | ✅ PASS | 15/15 | 0.8m | — | — |
| `authz-12-uniform-404` | **Kimi for Coding** | ✅ PASS | 15/15 | 2.9m | — | — |
| `authz-12-uniform-404` | **Kimi K3-256K** | ✅ PASS | 15/15 | 2.4m | — | — |
| `authz-12-uniform-404` | **Kimi K3.1 Pro** | ✅ PASS | 15/15 | 6.5m | — | — |
| `authz-12-uniform-404` | **MiniMax M3.1 Flash** | ✅ PASS | 15/15 | 2.9m | — | — |
| `authz-12-uniform-404` | **Qwen3.7 Max via Alibaba** | ✅ PASS | 15/15 | 1.4m | — | — |
| `authz-12-uniform-404` | **Qwen3.7 Plus via Alibaba** | ✅ PASS | 15/15 | 3.2m | — | — |
| `authz-12-uniform-404` | **Qwen3.8 Flash via Alibaba** | ✅ PASS | 15/15 | 4.2m | — | — |
| `authz-12-uniform-404` | **Qwen3.8 Max via Alibaba** | ✅ PASS | 15/15 | 8.3m | — | — |
| `authz-12-uniform-404` | **Qwen4 Max Preview** | ✅ PASS — audit requalified: false positive | 15/15 | 4.1m | — | — |
| `flag-10-feature-flag-router` | **DeepSeek V4 Pro** | ✅ PASS | 16/16 | 1.5m | — | — |
| `flag-10-feature-flag-router` | **DeepSeek V4.1 Flash 1017** | ✅ PASS | 16/16 | 1.4m | — | — |
| `flag-10-feature-flag-router` | **GLM-5.2 via Alibaba** | ✅ PASS | 16/16 | 5.5m | — | — |
| `flag-10-feature-flag-router` | **GLM-5.3** | ✅ PASS | 16/16 | 4.3m | — | — |
| `flag-10-feature-flag-router` | **GLM-5.3-Flash** | ✅ PASS | 16/16 | 4.1m | — | — |
| `flag-10-feature-flag-router` | **Iceman Free** | ✅ PASS | 16/16 | 1.5m | — | — |
| `flag-10-feature-flag-router` | **Inkling 2 Small Free** | ✅ PASS | 16/16 | 1.4m | — | — |
| `flag-10-feature-flag-router` | **Kimi for Coding** | ✅ PASS | 16/16 | 2.2m | — | — |
| `flag-10-feature-flag-router` | **Kimi K3-256K** | ✅ PASS | 16/16 | 1.8m | — | — |
| `flag-10-feature-flag-router` | **Kimi K3.1 Pro** | ✅ PASS | 16/16 | 4.8m | — | — |
| `flag-10-feature-flag-router` | **MiniMax M3.1 Flash** | 🚫 INVALID — pass revoked: audit found write:parent-path (hidden-access violation) | 16/16 | 6.5m | — | — |
| `flag-10-feature-flag-router` | **Qwen3.7 Max via Alibaba** | ✅ PASS | 16/16 | 1.6m | — | — |
| `flag-10-feature-flag-router` | **Qwen3.7 Plus via Alibaba** | ✅ PASS | 16/16 | 2.3m | — | — |
| `flag-10-feature-flag-router` | **Qwen3.8 Flash via Alibaba** | ✅ PASS | 16/16 | 2.9m | — | — |
| `flag-10-feature-flag-router` | **Qwen3.8 Max via Alibaba** | ✅ PASS | 16/16 | 13.2m | — | — |
| `flag-10-feature-flag-router` | **Qwen4 Max Preview** | ✅ PASS | 16/16 | 4.5m | — | — |
| `host-08-host-header-guard` | **DeepSeek V4 Pro** | ✅ PASS | 15/15 | 3.4m | — | — |
| `host-08-host-header-guard` | **DeepSeek V4.1 Flash 1017** | ✅ PASS | 15/15 | 2.6m | — | — |
| `host-08-host-header-guard` | **GLM-5.2 via Alibaba** | ✅ PASS | 15/15 | 15.8m | — | — |
| `host-08-host-header-guard` | **GLM-5.3** | ✅ PASS — audit requalified: false positive | 15/15 | 9.6m | — | — |
| `host-08-host-header-guard` | **GLM-5.3-Flash** | ✅ PASS | 15/15 | 9.2m | — | — |
| `host-08-host-header-guard` | **Iceman Free** | ✅ PASS | 15/15 | 1.7m | — | — |
| `host-08-host-header-guard` | **Inkling 2 Small Free** | ✅ PASS | 15/15 | 3.8m | — | — |
| `host-08-host-header-guard` | **Kimi for Coding** | ✅ PASS | 15/15 | 5.7m | — | — |
| `host-08-host-header-guard` | **Kimi K3-256K** | ✅ PASS | 15/15 | 5.1m | — | — |
| `host-08-host-header-guard` | **Kimi K3.1 Pro** | ✅ PASS | 15/15 | 5.7m | — | — |
| `host-08-host-header-guard` | **MiniMax M3.1 Flash** | ❌ FAIL | 0/15 | 30.0m | — | — |
| `host-08-host-header-guard` | **Qwen3.7 Max via Alibaba** | ✅ PASS | 15/15 | 2.6m | — | — |
| `host-08-host-header-guard` | **Qwen3.7 Plus via Alibaba** | ❌ FAIL | 14/15 | 5.5m | — | — |
| `host-08-host-header-guard` | **Qwen3.8 Flash via Alibaba** | ✅ PASS | 15/15 | 7.1m | — | — |
| `host-08-host-header-guard` | **Qwen3.8 Max via Alibaba** | ✅ PASS | 15/15 | 15.9m | — | — |
| `host-08-host-header-guard` | **Qwen4 Max Preview** | ✅ PASS | 15/15 | 6.5m | — | — |
| `idem-13-idempotent-signup` | **DeepSeek V4 Pro** | ✅ PASS | 17/17 | 1.8m | — | — |
| `idem-13-idempotent-signup` | **DeepSeek V4.1 Flash 1017** | ✅ PASS | 17/17 | 1.8m | — | — |
| `idem-13-idempotent-signup` | **GLM-5.2 via Alibaba** | ✅ PASS | 17/17 | 8.6m | — | — |
| `idem-13-idempotent-signup` | **GLM-5.3** | ✅ PASS — audit requalified: false positive | 17/17 | 5.1m | — | — |
| `idem-13-idempotent-signup` | **GLM-5.3-Flash** | ✅ PASS | 17/17 | 7.8m | — | — |
| `idem-13-idempotent-signup` | **Iceman Free** | ✅ PASS | 17/17 | 2.6m | — | — |
| `idem-13-idempotent-signup` | **Inkling 2 Small Free** | ✅ PASS | 17/17 | 1.8m | — | — |
| `idem-13-idempotent-signup` | **Kimi for Coding** | ✅ PASS | 17/17 | 3.4m | — | — |
| `idem-13-idempotent-signup` | **Kimi K3-256K** | ✅ PASS | 17/17 | 2.0m | — | — |
| `idem-13-idempotent-signup` | **Kimi K3.1 Pro** | ✅ PASS | 17/17 | 7.0m | — | — |
| `idem-13-idempotent-signup` | **MiniMax M3.1 Flash** | ✅ PASS | 17/17 | 6.9m | — | — |
| `idem-13-idempotent-signup` | **Qwen3.7 Max via Alibaba** | ✅ PASS | 17/17 | 2.2m | — | — |
| `idem-13-idempotent-signup` | **Qwen3.7 Plus via Alibaba** | ✅ PASS | 17/17 | 4.1m | — | — |
| `idem-13-idempotent-signup` | **Qwen3.8 Flash via Alibaba** | ✅ PASS | 17/17 | 4.1m | — | — |
| `idem-13-idempotent-signup` | **Qwen3.8 Max via Alibaba** | ✅ PASS | 17/17 | 9.2m | — | — |
| `idem-13-idempotent-signup` | **Qwen4 Max Preview** | ✅ PASS | 17/17 | 4.0m | — | — |
| `infra-05-k8s-pod-admission` | **DeepSeek V4 Pro** | ✅ PASS | 20/20 | 2.0m | — | — |
| `infra-05-k8s-pod-admission` | **DeepSeek V4.1 Flash 1017** | ✅ PASS | 20/20 | 1.8m | — | — |
| `infra-05-k8s-pod-admission` | **GLM-5.2 via Alibaba** | ❌ FAIL | 19/20 | 9.0m | — | — |
| `infra-05-k8s-pod-admission` | **GLM-5.3** | ✅ PASS | 20/20 | 8.7m | — | — |
| `infra-05-k8s-pod-admission` | **GLM-5.3-Flash** | ❌ FAIL — audit noted shell:parent-path | 18/20 | 10.1m | — | — |
| `infra-05-k8s-pod-admission` | **Iceman Free** | ❌ FAIL | 17/20 | 2.0m | — | — |
| `infra-05-k8s-pod-admission` | **Inkling 2 Small Free** | ❌ FAIL | 18/20 | 1.7m | — | — |
| `infra-05-k8s-pod-admission` | **Kimi for Coding** | ❌ FAIL | 18/20 | 3.4m | — | — |
| `infra-05-k8s-pod-admission` | **Kimi K3-256K** | ✅ PASS | 20/20 | 2.7m | — | — |
| `infra-05-k8s-pod-admission` | **Kimi K3.1 Pro** | ❌ FAIL | 19/20 | 7.1m | — | — |
| `infra-05-k8s-pod-admission` | **MiniMax M3.1 Flash** | ❌ FAIL | 7/20 | 30.0m | — | — |
| `infra-05-k8s-pod-admission` | **Qwen3.7 Max via Alibaba** | ❌ FAIL | 19/20 | 2.2m | — | — |
| `infra-05-k8s-pod-admission` | **Qwen3.7 Plus via Alibaba** | ❌ FAIL | 17/20 | 4.0m | — | — |
| `infra-05-k8s-pod-admission` | **Qwen3.8 Flash via Alibaba** | ✅ PASS | 20/20 | 6.8m | — | — |
| `infra-05-k8s-pod-admission` | **Qwen3.8 Max via Alibaba** | ❌ FAIL | 18/20 | 10.7m | — | — |
| `infra-05-k8s-pod-admission` | **Qwen4 Max Preview** | ❌ FAIL | 18/20 | 7.7m | — | — |
| `obs-02-query-redactor` | **DeepSeek V4 Pro** | ✅ PASS | 37/37 | 7.8m | — | — |
| `obs-02-query-redactor` | **DeepSeek V4.1 Flash 1017** | ✅ PASS | 37/37 | 6.7m | — | — |
| `obs-02-query-redactor` | **GLM-5.2 via Alibaba** | ✅ PASS | 37/37 | 19.3m | — | — |
| `obs-02-query-redactor` | **GLM-5.3** | ✅ PASS | 37/37 | 23.0m | — | — |
| `obs-02-query-redactor` | **GLM-5.3-Flash** | ❌ FAIL | 35/37 | 22.7m | — | — |
| `obs-02-query-redactor` | **Iceman Free** | ❌ FAIL | 36/37 | 5.7m | — | — |
| `obs-02-query-redactor` | **Inkling 2 Small Free** | ❌ FAIL | 36/37 | 8.7m | — | — |
| `obs-02-query-redactor` | **Kimi for Coding** | ✅ PASS | 37/37 | 10.2m | — | — |
| `obs-02-query-redactor` | **Kimi K3-256K** | ✅ PASS | 37/37 | 9.2m | — | — |
| `obs-02-query-redactor` | **Kimi K3.1 Pro** | ✅ PASS | 37/37 | 9.7m | — | — |
| `obs-02-query-redactor` | **MiniMax M3.1 Flash** | ✅ PASS | 37/37 | 9.7m | — | — |
| `obs-02-query-redactor` | **Qwen3.7 Max via Alibaba** | ✅ PASS | 37/37 | 16.2m | — | — |
| `obs-02-query-redactor` | **Qwen3.7 Plus via Alibaba** | ❌ FAIL | 36/37 | 15.6m | — | — |
| `obs-02-query-redactor` | **Qwen3.8 Flash via Alibaba** | ✅ PASS | 37/37 | 21.6m | — | — |
| `obs-02-query-redactor` | **Qwen3.8 Max via Alibaba** | ❌ FAIL | 7/37 | 30.0m | — | — |
| `obs-02-query-redactor` | **Qwen4 Max Preview** | ✅ PASS | 37/37 | 16.4m | — | — |
| `onec-06-payment-allocator` | **DeepSeek V4 Pro** | ✅ PASS | 16/16 | 2.0m | — | — |
| `onec-06-payment-allocator` | **DeepSeek V4.1 Flash 1017** | ✅ PASS | 16/16 | 1.9m | — | — |
| `onec-06-payment-allocator` | **GLM-5.2 via Alibaba** | ✅ PASS | 16/16 | 6.9m | — | — |
| `onec-06-payment-allocator` | **GLM-5.3** | ✅ PASS | 16/16 | 5.3m | — | — |
| `onec-06-payment-allocator` | **GLM-5.3-Flash** | ✅ PASS | 16/16 | 10.1m | — | — |
| `onec-06-payment-allocator` | **Iceman Free** | ✅ PASS | 16/16 | 1.7m | — | — |
| `onec-06-payment-allocator` | **Inkling 2 Small Free** | ✅ PASS | 16/16 | 1.0m | — | — |
| `onec-06-payment-allocator` | **Kimi for Coding** | ✅ PASS | 16/16 | 4.2m | — | — |
| `onec-06-payment-allocator` | **Kimi K3-256K** | ✅ PASS | 16/16 | 2.0m | — | — |
| `onec-06-payment-allocator` | **Kimi K3.1 Pro** | ✅ PASS | 16/16 | 6.1m | — | — |
| `onec-06-payment-allocator` | **MiniMax M3.1 Flash** | ❌ FAIL | 6/16 | 30.0m | — | — |
| `onec-06-payment-allocator` | **Qwen3.7 Max via Alibaba** | ✅ PASS | 16/16 | 2.9m | — | — |
| `onec-06-payment-allocator` | **Qwen3.7 Plus via Alibaba** | ✅ PASS | 16/16 | 3.1m | — | — |
| `onec-06-payment-allocator` | **Qwen3.8 Flash via Alibaba** | ✅ PASS | 16/16 | 4.2m | — | — |
| `onec-06-payment-allocator` | **Qwen3.8 Max via Alibaba** | ✅ PASS | 16/16 | 11.6m | — | — |
| `onec-06-payment-allocator` | **Qwen4 Max Preview** | ✅ PASS | 16/16 | 4.5m | — | — |
| `scrub-09-metadata-scrubber` | **DeepSeek V4 Pro** | ✅ PASS | 15/15 | 1.1m | — | — |
| `scrub-09-metadata-scrubber` | **DeepSeek V4.1 Flash 1017** | ✅ PASS | 15/15 | 1.9m | — | — |
| `scrub-09-metadata-scrubber` | **GLM-5.2 via Alibaba** | ✅ PASS | 15/15 | 7.7m | — | — |
| `scrub-09-metadata-scrubber` | **GLM-5.3** | ✅ PASS | 15/15 | 10.3m | — | — |
| `scrub-09-metadata-scrubber` | **GLM-5.3-Flash** | ✅ PASS | 15/15 | 11.3m | — | — |
| `scrub-09-metadata-scrubber` | **Iceman Free** | ✅ PASS | 15/15 | 2.1m | — | — |
| `scrub-09-metadata-scrubber` | **Inkling 2 Small Free** | ✅ PASS | 15/15 | 2.2m | — | — |
| `scrub-09-metadata-scrubber` | **Kimi for Coding** | ✅ PASS | 15/15 | 3.0m | — | — |
| `scrub-09-metadata-scrubber` | **Kimi K3-256K** | ✅ PASS | 15/15 | 2.9m | — | — |
| `scrub-09-metadata-scrubber` | **Kimi K3.1 Pro** | ✅ PASS | 15/15 | 4.2m | — | — |
| `scrub-09-metadata-scrubber` | **MiniMax M3.1 Flash** | ❌ FAIL | 5/15 | 30.0m | — | — |
| `scrub-09-metadata-scrubber` | **Qwen3.7 Max via Alibaba** | ✅ PASS | 15/15 | 1.7m | — | — |
| `scrub-09-metadata-scrubber` | **Qwen3.7 Plus via Alibaba** | ✅ PASS | 15/15 | 4.4m | — | — |
| `scrub-09-metadata-scrubber` | **Qwen3.8 Flash via Alibaba** | ✅ PASS | 15/15 | 4.7m | — | — |
| `scrub-09-metadata-scrubber` | **Qwen3.8 Max via Alibaba** | ✅ PASS | 15/15 | 21.2m | — | — |
| `scrub-09-metadata-scrubber` | **Qwen4 Max Preview** | ✅ PASS | 15/15 | 6.9m | — | — |
| `sec-01-clock-skew` | **DeepSeek V4 Pro** | ✅ PASS | 6/6 | 1.1m | — | — |
| `sec-01-clock-skew` | **DeepSeek V4.1 Flash 1017** | ✅ PASS | 6/6 | 1.1m | — | — |
| `sec-01-clock-skew` | **GLM-5.2 via Alibaba** | ✅ PASS | 6/6 | 3.1m | — | — |
| `sec-01-clock-skew` | **GLM-5.3** | ✅ PASS | 6/6 | 3.2m | — | — |
| `sec-01-clock-skew` | **GLM-5.3-Flash** | ✅ PASS | 6/6 | 2.3m | — | — |
| `sec-01-clock-skew` | **Iceman Free** | ✅ PASS | 6/6 | 1.4m | — | — |
| `sec-01-clock-skew` | **Inkling 2 Small Free** | ✅ PASS | 6/6 | 0.8m | — | — |
| `sec-01-clock-skew` | **Kimi for Coding** | ✅ PASS | 6/6 | 1.5m | — | — |
| `sec-01-clock-skew` | **Kimi K3-256K** | ✅ PASS | 6/6 | 1.9m | — | — |
| `sec-01-clock-skew` | **Kimi K3.1 Pro** | ✅ PASS | 6/6 | 2.7m | — | — |
| `sec-01-clock-skew` | **MiniMax M3.1 Flash** | ✅ PASS | 6/6 | 3.2m | — | — |
| `sec-01-clock-skew` | **Qwen3.7 Max via Alibaba** | ✅ PASS | 6/6 | 1.2m | — | — |
| `sec-01-clock-skew` | **Qwen3.7 Plus via Alibaba** | ✅ PASS | 6/6 | 2.0m | — | — |
| `sec-01-clock-skew` | **Qwen3.8 Flash via Alibaba** | ✅ PASS | 6/6 | 3.9m | — | — |
| `sec-01-clock-skew` | **Qwen3.8 Max via Alibaba** | ✅ PASS | 6/6 | 5.8m | — | — |
| `sec-01-clock-skew` | **Qwen4 Max Preview** | ✅ PASS | 6/6 | 4.3m | — | — |
| `tenant-11-scoped-listing` | **DeepSeek V4 Pro** | ✅ PASS | 16/16 | 1.3m | — | — |
| `tenant-11-scoped-listing` | **DeepSeek V4.1 Flash 1017** | ✅ PASS | 16/16 | 0.9m | — | — |
| `tenant-11-scoped-listing` | **GLM-5.2 via Alibaba** | ✅ PASS | 16/16 | 7.2m | — | — |
| `tenant-11-scoped-listing` | **GLM-5.3** | ✅ PASS | 16/16 | 6.8m | — | — |
| `tenant-11-scoped-listing` | **GLM-5.3-Flash** | ✅ PASS | 16/16 | 5.2m | — | — |
| `tenant-11-scoped-listing` | **Iceman Free** | ✅ PASS | 16/16 | 1.7m | — | — |
| `tenant-11-scoped-listing` | **Inkling 2 Small Free** | ✅ PASS | 16/16 | 1.0m | — | — |
| `tenant-11-scoped-listing` | **Kimi for Coding** | ✅ PASS | 16/16 | 1.8m | — | — |
| `tenant-11-scoped-listing` | **Kimi K3-256K** | ✅ PASS | 16/16 | 2.9m | — | — |
| `tenant-11-scoped-listing` | **Kimi K3.1 Pro** | ✅ PASS | 16/16 | 3.8m | — | — |
| `tenant-11-scoped-listing` | **MiniMax M3.1 Flash** | ✅ PASS | 16/16 | 7.0m | — | — |
| `tenant-11-scoped-listing` | **Qwen3.7 Max via Alibaba** | ✅ PASS | 16/16 | 1.2m | — | — |
| `tenant-11-scoped-listing` | **Qwen3.7 Plus via Alibaba** | ✅ PASS | 16/16 | 2.4m | — | — |
| `tenant-11-scoped-listing` | **Qwen3.8 Flash via Alibaba** | ✅ PASS | 16/16 | 3.4m | — | — |
| `tenant-11-scoped-listing` | **Qwen3.8 Max via Alibaba** | ✅ PASS | 16/16 | 17.8m | — | — |
| `tenant-11-scoped-listing` | **Qwen4 Max Preview** | ✅ PASS | 16/16 | 3.6m | — | — |

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

Образ `ghcr.io/mischellin/dev-matrix-vast-bench` (сборка — `docker/vast-bench/`, workflow `vast-bench-image.yml`, запуск вручную или тегом `vast-bench-*`) содержит vLLM, OpenCode и `devmatrix`. Весов и секретов в нём нет. Образ собирается в GitHub Actions; первые реальные прогоны шли на образе из этого Dockerfile с тегом `vast-bench-rc1` (до пина `mistral_common` и правок `models.toml`: их внесли руками на инстансе, теперь они в `Dockerfile` и `models.toml`, сборки rc2/rc3 и новее их содержат). Новый пакет ghcr по умолчанию **приватный**: после первой сборки один раз откройте GitHub → Packages → `dev-matrix-vast-bench` → Package settings → Change visibility → Public, иначе vast.ai не сможет скачать образ без токена. Только модели, которые помещаются на **одну** карту (без tensor parallel).

1. Арендуйте инстанс с этим образом (GPU по `min_gpu_gb` из [`models.toml`](docker/vast-bench/models.toml), диск от 200 ГБ), дайте ему свою метку, например `devmatrix-bench`. **Сначала скопируйте результаты (шаг 4), затем удалите инстанс** — иначе аренда идёт дальше, а при удалении без копии результаты пропадут.
2. Переменные окружения: `HF_TOKEN` (если репозиторий модели требует вход), `GPU_PRICE_USD_HOUR` (цена инстанса за час из vast.ai — для `cost_usd`), по желанию `PURGE_WEIGHTS=1` (удалять веса модели после прогона, в том числе после ошибки скачивания или запуска vLLM, если мало диска). Переменные, заданные в настройках инстанса vast.ai, в ssh-сессии могут быть не видны: проверьте `echo "${GPU_PRICE_USD_HOUR:-нет}"`, при необходимости выполните `export GPU_PRICE_USD_HOUR=… HF_TOKEN=…` в tmux-сессии, где запускаете прогон (не вписывайте значение токена в команду, которая попадёт в историю общего журнала), либо положите их в файл только для root (`install -m 0600 /dev/null /root/bench.env`, строки `HF_TOKEN=…`) и укажите `BENCH_ENV_FILE=/root/bench.env`: `bench.sh` подключит его сам и откажется читать файл, доступный группе или всем. **Не** кладите токен в `/etc/environment` (режим 0644, его читает любой процесс контейнера, включая агента) и не выполняйте `hf auth login` (токен ляжет в `$HF_HOME` файлом); `bench-home` и `$HF_HOME` закрыты правами 0700 для root.
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

**Изоляция агента.** OpenCode читает файловую систему контейнера, поэтому эталонные решения и скрытые тесты спрятаны от него. `.dockerignore` не пускает в контекст сборки `tasks/*/reference_solution`, `submissions` и `tests`. Скрытые тесты (`tasks/*/hidden`) `devmatrix` нужны при проверке, поэтому они остаются в установленном пакете (`/opt/uv-tools`, колесо без `reference_solution`), а каталог исходников `/opt/dev-matrix` после установки удаляется. `/opt/uv-tools`, `/opt/uv-cache` и `/results` закрыты правами 0700 для root, и `agent-opencode.sh` запускает OpenCode от непривилегированного пользователя `agent` (через `setpriv`, с `no-new-privs`), которому принадлежат только рабочая папка задачи и его HOME. HOME и все XDG-каталоги — свежие на каждую задачу (`/workspace/agent-homes/task.*`, родитель принадлежит root, каталог удаляется при любом выходе): история сессий OpenCode и подложенный `~/.config/opencode/AGENTS.md` не переходят ни в другую задачу, ни к другой модели; `opencode.json` лежит в root-владельном `~/.config/opencode` (агенту только чтение). Не удался `chown` или создание HOME — задача невалидна (маркер, код 3). После OpenCode все процессы пользователя `agent` убиваются (`pkill -KILL`) до чтения счётчиков `/metrics`, так что оставшийся сервер агента не раздувает токены следующих задач. Для тестов у агента свой `UV_CACHE_DIR` в HOME (копия прогретого кэша только с `pytest==8.3.4`, не root-овый `/opt/uv-cache`), `UV_TOOL_DIR` ему не отдаётся, а `pytest==8.3.4` стоит и системно: работают `uv run --with pytest pytest` и `python -m pytest`. Токены (`HF_TOKEN`, всё, что похоже на токен, пароль или ключ) агент в окружении не получает. Агент по-прежнему читает остальные файлы образа, а публичный репозиторий задач доступен всем в интернете; защита — от поиска решений и скрытых тестов по файловой системе контейнера, а не от интернета. **Ограничение: проверка запускает код агента от root.** `scripts/runner.py` (публичный раннер, его семантику мы не меняем) гоняет `pytest` от того пользователя, под которым работает `devmatrix` (в контейнере — root), в рабочей папке агента с `pythonpath=<папка>/src`; код из `src/` может изменить `/opt/uv-tools`, скопировать скрытые тесты или переписать `/results`. Смягчения внутри контейнера: `UV_NO_CONFIG=1` (агентский `uv.toml` не перенастроит `uv` раннера); после каждой модели `bench.sh` сверяет хэши установленного пакета `devmatrix` в `$UV_TOOL_DIR` и отчётов уже завершённых моделей; при расхождении статус `integrity_failed`, отчёты уходят из `submissions/` в `integrity_failed/` и их нельзя отправлять. Это дешёвая проверка, а не граница доверия: **результаты — заявленные автором прогона, лидерборд не доверенный; для доверенного замера запускайте оценку отдельно** (отчёты и рабочие папки агента — на чистой машине, не в этом контейнере). В контейнере не должно быть читаемых всем секретов: токен — только в окружении сессии или в root-файле 0600 (см. выше). Изоляция проверена тестами скриптов, но не запуском образа с настоящим пользователем.

**Падение vLLM.** Агент проверяет `/health` до и после запуска OpenCode; если vLLM не отвечает, задача получает маркер `metrics/<задача>.invalid`, а её отчёт переносится из `submissions/` в `invalid/` и перечисляется в `run-info.json` (`invalid_tasks`) — мёртвый сервер не считается провалом модели, и такой «ноль» нельзя отправить. Статус `done_partial` значит, что vLLM здоров и OpenCode упал не на большинстве задач, но часть отчётов лежит в `invalid/` — эти задачи надо повторить; `interrupted` — `bench.sh` остановили (INT/TERM) во время этой модели (devmatrix, процессы агента и vLLM гасятся первыми, отчёты уходят в `interrupted/`, статус пишется без `vllm --version` и `nvidia-smi`, чтобы уложиться в 10 с `docker stop`); `integrity_failed` — см. ограничение выше. Коды выхода `bench.sh`: 0 — все модели `done`; 1 — есть модель с ошибкой; 2 — неверные аргументы или окружение; 3 — нет GPU; **4 — ошибок нет, но у части моделей `done_partial`** (повторите их задачи); 130 — остановлен INT/TERM. Статус `vllm_died` в `run-info.json` значит, что прогон надо повторить; `devmatrix_failed` — сбой самого запуска или не все отчёты на месте. Так же помечается задача, где OpenCode упал (код не 0 и не 124), а vLLM не сгенерировал ни одного токена; если так вышло на большинстве задач, статус — `agent_failed` (проверьте `opencode/*.err`, имя модели и конфиг). `OPENCODE_TIMEOUT` должен быть меньше `AGENT_TIMEOUT` минимум на 120 с, иначе `bench.sh` не стартует. Лог фоновой докачки следующей модели — `download.prefetch.log`; её сбой выводится в консоль, веса тогда качаются заново (`download.log`). Токены с отрицательной дельтой (счётчики vLLM сбросились) записываются как `null`.

**Какой пресет на какую карту** (`min_gpu_gb` из `models.toml`; для North Mini Code это оценка, а не измерение):

| Карта | Пресеты |
|---|---|
| 24 ГБ и 32 ГБ | `gpt-oss-20b` (MXFP4, веса ~14 ГБ) |
| 40 ГБ | `gpt-oss-20b`, `north-mini-code` (официальный FP8, веса ~32 ГБ; впритык — оценка) |
| 48 ГБ (`min_gpu_gb = 48`) | всё выше, плюс `devstral-small-2`, `qwen3-8-27b` |
| 80 ГБ | всё выше, плюс `kat-coder-v2-5-dev` — **единственный пресет, которому нужна карта 80 ГБ** (BF16 69 ГБ с онлайн-квантованием; официального FP8/AWQ у автора нет), для дешёвых прогонов его можно пропустить |

Порядок для небольшого бюджета: `gpt-oss-20b`, `devstral-small-2`, `qwen3-8-27b`, `north-mini-code`, затем `kat-coder-v2-5-dev`.

**Оговорки.** Результаты получены на квантованных моделях: готовые MXFP4/FP8-чекпойнты (gpt-oss-20b, Devstral, Qwen3.8, North Mini Code) и онлайн-квантование vLLM `--quantization fp8_per_tensor` из BF16 для KAT-Coder (для него нужна карта класса 80 ГБ: BF16-чекпойнт 69 ГБ может целиком лечь в видеопамять до сжатия). Они несопоставимы с другими квантованиями и с API-версиями тех же моделей. North Mini Code: vLLM v0.33.0 поднимается на Ampere (A6000) без `--moe-backend triton`, пакет `cohere_melody` для его парсеров установлен в образ; полный прогон бенчмарка не выполнялся. Токены — сумма дельт счётчиков `vllm:prompt_tokens` и `vllm:generation_tokens` за задачу; `cost_usd` = `agent_seconds / 3600 × GPU_PRICE_USD_HOUR` (только время работы агента, без скачивания и загрузки модели). Как и всё остальное в `devmatrix submit`, эти значения — «заявлено автором». Не проверено запуском: парсеры tool-call/reasoning для моделей, где карточка их не называет (пометки — в `notes` пресетов), и полные прогоны `qwen3-8-27b` и `north-mini-code`.

**Что измерено на первых прогонах** (vast.ai, vLLM v0.33.0, OpenCode 1.19.5):
- `gpt-oss-20b` на RTX 4090: 13 задач, время работы агента ~9 мин, ~$0,08 за GPU-время агента при $0,5/ч; скачивание и запуск vLLM — ещё ~15 мин, так что арендуйте инстанс примерно на 30 мин (~$0,25–0,3). Прогон дошёл до конца: 8 из 13 задач до исключения одного результата.
- `devstral-small-2` (FP8) на RTX A6000: 1 ч 53 мин (113 мин) против ~9 мин у `gpt-oss-20b`, то есть примерно в 12 раз дольше, а не в 2–3; две задачи упёрлись в лимит OpenCode 1500 с (14 млн и 1,8 млн токенов). Плотные и медленные модели обходятся на порядок дороже `gpt-oss-20b`: закладывайте бюджет времени и денег соответственно.
- `qwen3-8-27b` до конца не прогонялся (vLLM поднимался на A6000 с `--max-num-seqs 32`, см. ниже).
- `devstral-small-2` и `qwen3-8-27b` требуют карты на 48 ГБ (`min_gpu_gb = 48`), на 40 ГБ они не помещаются.

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
- `data/run_overrides.json`: Audit overrides for benchmark runs (status requalification, e.g. withdrawn INVALID runs, and per-model notes).

To refresh and update README tables:
```bash
python3 scripts/export_metrics.py
python3 scripts/generate_readme.py
```

---

## 📄 License

DevMatrix is open-source software licensed under the [MIT License](LICENSE).
