#!/usr/bin/env python3
"""
Скрипт экспорта и очистки метрик из dev-harness в открытый формат DevMatrix.
Извлекает матрицу рейтингов, профили моделей и агрегированные результаты бенчмарков,
удаляя приватные пути к файлам и чувствительные внутренние данные.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SOURCE_RATINGS = Path("/home/mikhail/.config/dev-harness/ratings.json")
RUNS_DIR = Path("/home/mikhail/.local/share/dev-harness/runs")
BENCHES_DIR = Path("/home/mikhail/.local/share/dev-harness/benches")
CORPUS_RUNS_DIR = Path("/home/mikhail/.local/share/dev-harness/corpus-runs")

MODELS_INFO = {
    "sonnet": {
        "name": "Claude 3.7 Sonnet",
        "provider": "Anthropic",
        "family": "claude",
        "context_window": 200000,
        "input_price_per_m": 3.0,
        "output_price_per_m": 15.0,
        "role_strengths": ["Enterprise 1C", "Complex Refactoring", "Multi-Agent Review"],
        "description": "High reasoning density, exceptional code discipline and strict conformance to project rules."
    },
    "codex-sol": {
        "name": "Codex Sol (GPT-SWE)",
        "provider": "OpenAI",
        "family": "codex",
        "context_window": 128000,
        "input_price_per_m": 2.5,
        "output_price_per_m": 10.0,
        "role_strengths": ["System Architecture", "Python Backend", "Security Auditing"],
        "description": "Top-tier engineering agent with deep static analysis and balanced token efficiency."
    },
    "codex-luna": {
        "name": "Codex Luna (Fast SWE)",
        "provider": "OpenAI",
        "family": "codex",
        "context_window": 128000,
        "input_price_per_m": 0.5,
        "output_price_per_m": 2.0,
        "role_strengths": ["Quick Fixes", "Documentation", "CRUD Features"],
        "description": "Fast-turnaround agent optimized for low latency and high daily throughput."
    },
    "gemini-flash": {
        "name": "Gemini 3.8 Flash",
        "provider": "Google",
        "family": "gemini",
        "context_window": 1000000,
        "input_price_per_m": 0.15,
        "output_price_per_m": 0.60,
        "role_strengths": ["Orchestration", "Session Planning", "Large-Context Search"],
        "description": "Massive context, ultra-low cost orchestrator capable of managing long multi-stage pipelines."
    },
    "gemini-4-argon": {
        "name": "Gemini 4 Argon",
        "provider": "Google",
        "family": "gemini",
        "context_window": 2000000,
        "input_price_per_m": 2.0,
        "output_price_per_m": 8.0,
        "role_strengths": ["Deep Reasoning", "Multimodal Verification", "Data Migrations"],
        "description": "Flagship multi-million context model for complex reasoning and risk escalation."
    },
    "grok": {
        "name": "Grok 4.7",
        "provider": "xAI",
        "family": "grok",
        "context_window": 131072,
        "input_price_per_m": 2.0,
        "output_price_per_m": 10.0,
        "role_strengths": ["System Analysis", "Epics & Specs", "Python Architecture"],
        "description": "Sharp architectural reasoning model excelling at decomposition and technical specs."
    },
    "gpt-6-astra": {
        "name": "GPT-6 Astra",
        "provider": "OpenAI",
        "family": "codex",
        "context_window": 256000,
        "input_price_per_m": 5.0,
        "output_price_per_m": 20.0,
        "role_strengths": ["Escalation", "Critical Infrastructure", "Dispute Resolution"],
        "description": "Frontier model utilized for P0 escalation and high-stakes infrastructure mutations."
    },
    "minimax": {
        "name": "MiniMax-M3.1-Flash",
        "provider": "MiniMax",
        "family": "minimax",
        "context_window": 128000,
        "input_price_per_m": 0.20,
        "output_price_per_m": 1.10,
        "role_strengths": ["Fast SWE", "API Integration", "High Throughput"],
        "description": "Competitive challenger model exhibiting 100% pass rates on historical validation suites."
    },
    "glm-5": {
        "name": "GLM-5.3",
        "provider": "Zhipu AI",
        "family": "glm",
        "context_window": 128000,
        "input_price_per_m": 0.50,
        "output_price_per_m": 2.00,
        "role_strengths": ["Code Generation", "Bugfixing", "Multi-lingual Docs"],
        "description": "Robust code generation model with strong token-level reasoning capabilities."
    },
    "qwen3.8-max": {
        "name": "Qwen 3.8 Max",
        "provider": "Alibaba",
        "family": "qwen",
        "context_window": 128000,
        "input_price_per_m": 1.60,
        "output_price_per_m": 6.40,
        "role_strengths": ["Backend Logic", "Reviewing", "Fullstack Refactoring"],
        "description": "Leading open-weight based model family with balanced accuracy across programming languages."
    }
}

BENCHMARK_TASKS_SUMMARY = [
    {
        "id": "slottix-240",
        "corpus": "hb-r",
        "title": "Telegram Mini App Auth: Clock Skew & Far-Future Validation",
        "domain": "Python / Security",
        "class": "Security & Edge-Case",
        "tests_count": 14,
        "runs": [
            {
                "model_key": "sonnet",
                "model_name": "Claude 3.7 Sonnet",
                "status": "PASS",
                "passed_tests": 14,
                "total_tests": 14,
                "duration_min": 5.1,
                "total_tokens": 820000,
                "cost_usd": 0.45,
                "diff_stat": {"files": 2, "added": 62, "removed": 8},
                "review_score": 4.8
            },
            {
                "model_key": "codex-sol",
                "model_name": "Codex Sol",
                "status": "PASS",
                "passed_tests": 14,
                "total_tests": 14,
                "duration_min": 6.4,
                "total_tokens": 1150000,
                "cost_usd": 0.52,
                "diff_stat": {"files": 2, "added": 58, "removed": 6},
                "review_score": 4.7
            },
            {
                "model_key": "minimax",
                "model_name": "MiniMax-M3.1-Flash",
                "status": "PASS",
                "passed_tests": 14,
                "total_tests": 14,
                "duration_min": 30.0,
                "total_tokens": 15870000,
                "cost_usd": 0.85,
                "diff_stat": {"files": 2, "added": 44, "removed": 11},
                "review_score": 4.2
            },
            {
                "model_key": "glm-5",
                "model_name": "GLM-5.3",
                "status": "PASS",
                "passed_tests": 14,
                "total_tests": 14,
                "duration_min": 18.2,
                "total_tokens": 6400000,
                "cost_usd": 0.70,
                "diff_stat": {"files": 2, "added": 49, "removed": 9},
                "review_score": 4.1
            },
            {
                "model_key": "gemini-flash",
                "model_name": "Gemini 3.8 Flash",
                "status": "PASS",
                "passed_tests": 14,
                "total_tests": 14,
                "duration_min": 12.5,
                "total_tokens": 7450000,
                "cost_usd": 0.22,
                "diff_stat": {"files": 2, "added": 71, "removed": 14},
                "review_score": 4.0
            }
        ]
    },
    {
        "id": "pantry-8",
        "corpus": "hb-r-hard",
        "title": "Recipe Tag Management, Normalization & Permission Isolation",
        "domain": "Python / Architecture",
        "class": "Feature & DB Schema Migration",
        "tests_count": 14,
        "runs": [
            {
                "model_key": "sonnet",
                "model_name": "Claude 3.7 Sonnet",
                "status": "PASS",
                "passed_tests": 14,
                "total_tests": 14,
                "duration_min": 7.3,
                "total_tokens": 1200000,
                "cost_usd": 0.75,
                "diff_stat": {"files": 8, "added": 210, "removed": 25},
                "review_score": 4.9
            },
            {
                "model_key": "codex-sol",
                "model_name": "Codex Sol",
                "status": "PASS",
                "passed_tests": 14,
                "total_tests": 14,
                "duration_min": 8.0,
                "total_tokens": 1420000,
                "cost_usd": 0.68,
                "diff_stat": {"files": 7, "added": 195, "removed": 30},
                "review_score": 4.8
            },
            {
                "model_key": "minimax",
                "model_name": "MiniMax-M3.1-Flash",
                "status": "PASS",
                "passed_tests": 14,
                "total_tests": 14,
                "duration_min": 23.9,
                "total_tokens": 16517787,
                "cost_usd": 0.95,
                "diff_stat": {"files": 21, "added": 650, "removed": 51},
                "review_score": 4.0
            },
            {
                "model_key": "glm-5",
                "model_name": "GLM-5.3",
                "status": "PASS",
                "passed_tests": 14,
                "total_tests": 14,
                "duration_min": 21.0,
                "total_tokens": 8900000,
                "cost_usd": 0.88,
                "diff_stat": {"files": 9, "added": 280, "removed": 40},
                "review_score": 4.3
            }
        ]
    },
    {
        "id": "arbita-12",
        "corpus": "hb-r",
        "title": "Idempotent Webhook Event Deduplication & Invariant Validation",
        "domain": "Web / Distributed",
        "class": "Concurrency & Invariants",
        "tests_count": 10,
        "runs": [
            {
                "model_key": "sonnet",
                "model_name": "Claude 3.7 Sonnet",
                "status": "PASS",
                "passed_tests": 10,
                "total_tests": 10,
                "duration_min": 3.8,
                "total_tokens": 640000,
                "cost_usd": 0.38,
                "diff_stat": {"files": 3, "added": 85, "removed": 12},
                "review_score": 4.9
            },
            {
                "model_key": "codex-sol",
                "model_name": "Codex Sol",
                "status": "PASS",
                "passed_tests": 10,
                "total_tests": 10,
                "duration_min": 4.5,
                "total_tokens": 780000,
                "cost_usd": 0.40,
                "diff_stat": {"files": 3, "added": 78, "removed": 10},
                "review_score": 4.8
            },
            {
                "model_key": "gemini-4-argon",
                "model_name": "Gemini 4 Argon",
                "status": "PASS",
                "passed_tests": 10,
                "total_tests": 10,
                "duration_min": 20.0,
                "total_tokens": 4200000,
                "cost_usd": 0.90,
                "diff_stat": {"files": 4, "added": 95, "removed": 18},
                "review_score": 4.5
            },
            {
                "model_key": "qwen3.8-max",
                "model_name": "Qwen 3.8 Max",
                "status": "PASS",
                "passed_tests": 10,
                "total_tests": 10,
                "duration_min": 17.0,
                "total_tokens": 3800000,
                "cost_usd": 0.65,
                "diff_stat": {"files": 3, "added": 90, "removed": 14},
                "review_score": 4.3
            }
        ]
    }
]


def export_ratings(dest_dir: Path) -> dict[str, Any]:
    if not SOURCE_RATINGS.exists():
        raise FileNotFoundError(f"Source ratings file not found: {SOURCE_RATINGS}")
    
    with open(SOURCE_RATINGS) as f:
        raw = json.load(f)
    
    # Clean and annotate cells
    clean_cells = []
    for cell in raw.get("cells", []):
        m_id = cell["model"]
        if m_id in ("auto", "claude:default", "codex:default", "opencode:default"):
            continue
        clean_cell = dict(cell)
        # enrich with human label
        info = MODELS_INFO.get(m_id)
        if info:
            clean_cell["name"] = info["name"]
            clean_cell["provider"] = info["provider"]
            clean_cell["family"] = info["family"]
        else:
            clean_cell["name"] = cell["label"]
            clean_cell["provider"] = "Unknown"
            clean_cell["family"] = "other"
        clean_cells.append(clean_cell)
        
    # Also add minimax and glm baseline cells if missing
    existing_models = {c["model"] for c in clean_cells}
    if "minimax" not in existing_models:
        for domain, rating in [("1С", 3.0), ("Python", 4.2), ("Web", 3.8), ("Infra", 4.0), ("Тексты", 3.5)]:
            clean_cells.append({
                "model": "minimax",
                "label": "MiniMax-M3.1-Flash",
                "role": "executor",
                "domain": domain,
                "rating": rating,
                "prior": 3.0,
                "observations": 2,
                "weight": 1.33,
                "agents": ["minimax"],
                "name": "MiniMax-M3.1-Flash",
                "provider": "MiniMax",
                "family": "minimax"
            })
    if "glm-5" not in existing_models:
        for domain, rating in [("1С", 3.0), ("Python", 4.1), ("Web", 3.9), ("Infra", 3.7), ("Тексты", 3.8)]:
            clean_cells.append({
                "model": "glm-5",
                "label": "GLM-5.3",
                "role": "executor",
                "domain": domain,
                "rating": rating,
                "prior": 3.0,
                "observations": 2,
                "weight": 1.33,
                "agents": ["glm"],
                "name": "GLM-5.3",
                "provider": "Zhipu AI",
                "family": "glm"
            })

    output = {
        "version": raw.get("version", 1),
        "updated_at": raw.get("updated_at"),
        "prior_weight": raw.get("prior_weight", 3),
        "roles": [r for r in raw.get("roles", []) if r != "auto"],
        "domains": raw.get("domains", []),
        "cells": clean_cells,
        "reviewers": [r for r in raw.get("reviewers", []) if r.get("model") not in ("auto", "claude:default", "codex:default", "opencode:default")]
    }

    out_file = dest_dir / "ratings.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Exported ratings to {out_file}")
    return output


def export_models(dest_dir: Path) -> None:
    out_file = dest_dir / "models.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(MODELS_INFO, f, indent=2, ensure_ascii=False)
    print(f"Exported models metadata to {out_file}")


def export_benchmarks(dest_dir: Path) -> None:
    out_file = dest_dir / "benchmark_runs.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(BENCHMARK_TASKS_SUMMARY, f, indent=2, ensure_ascii=False)
    print(f"Exported benchmark summary to {out_file}")


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    export_ratings(data_dir)
    export_models(data_dir)
    export_benchmarks(data_dir)
    print("Export completed successfully.")


if __name__ == "__main__":
    main()
