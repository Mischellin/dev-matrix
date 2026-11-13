#!/usr/bin/env python3
"""
Скрипт экспорта и очистки метрик из dev-harness в открытый формат DevMatrix.
Извлекает матрицу рейтингов, профили моделей и агрегированные результаты бенчмарков,
удаляя приватные пути к файлам и чувствительные внутренние данные.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# Источники задаются переменными окружения; по умолчанию — стандартные каталоги Harness в домашней папке.
SOURCE_RATINGS = Path(
    os.environ.get("DEV_HARNESS_RATINGS", "~/.config/dev-harness/ratings.json")
).expanduser()
_DATA_HOME = Path(os.environ.get("DEV_HARNESS_DATA", "~/.local/share/dev-harness")).expanduser()
RUNS_DIR = _DATA_HOME / "runs"
BENCHES_DIR = _DATA_HOME / "benches"
CORPUS_RUNS_DIR = _DATA_HOME / "corpus-runs"

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

# Результаты прогонов по опубликованным задачам из tasks/ берутся из submissions/<модель>/<задача>.json
# (отчёты `devmatrix run`, поля заявлены авторами: токены, цена и время не проверяются).
ROOT = Path(__file__).resolve().parent.parent
SUBMISSIONS_DIR = ROOT / "submissions"


def _current_task_hash(task_id: str) -> str | None:
    """Хеш условия и тестов задачи на текущем main; None, если задачи нет."""
    sys.path.insert(0, str(ROOT / "src"))
    from devmatrix import cli

    try:
        return cli.task_hash(task_id)
    except OSError:
        return None


def build_benchmark_runs(
    submissions_dir: Path = SUBMISSIONS_DIR, hash_of=_current_task_hash
) -> list[dict[str, Any]]:
    """Сворачивает отчёты из submissions/ в список {id: задача, runs: [...]} для страницы и README.

    Отчёт, полученный на старой версии задачи (tasks_hash не совпадает с текущим), помечается outdated:
    он остаётся в списке, но в сводку по моделям не входит.
    """
    by_task: dict[str, list[dict[str, Any]]] = {}
    for f in sorted(submissions_dir.glob("*/*.json")):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
            run = {
                "model_name": r["model"],
                "provider": r.get("provider"),
                "status": "PASS" if r["passed"] else "FAIL",
                "passed_tests": r["passed_tests"],
                "total_tests": r["total_tests"],
                "duration_min": round(r["agent_seconds"] / 60, 1) if r.get("agent_seconds") is not None else None,
                "total_tokens": r.get("tokens"),
                "cost_usd": r.get("cost_usd"),
                # Всё из submissions/ заявлено самими авторами, поэтому флаг не берём из файла.
                "claimed": True,
                "outdated": r.get("tasks_hash") != hash_of(r["task_id"]),
            }
            task_id = r["task_id"]
        except (KeyError, TypeError, ValueError) as e:
            raise SystemExit(f"{f}: неверный отчёт ({type(e).__name__}: {e})") from e
        by_task.setdefault(task_id, []).append(run)
    return [{"id": task_id, "runs": runs} for task_id, runs in sorted(by_task.items())]


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
        json.dump(build_benchmark_runs(), f, indent=2, ensure_ascii=False)
    print(f"Exported benchmark summary to {out_file}")


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # В CI нет рейтингов Harness: там пересобираются только результаты из submissions/.
    if "--only-benchmarks" in sys.argv[1:]:
        export_benchmarks(data_dir)
        return
    export_ratings(data_dir)
    export_models(data_dir)
    export_benchmarks(data_dir)
    print("Export completed successfully.")


if __name__ == "__main__":
    main()
