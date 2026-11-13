"""Сборка data/benchmark_runs.json из submissions/."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import export_metrics  # noqa: E402


def _report(model: str, task: str, passed: bool, tests: tuple[int, int], seconds: float | None) -> dict:
    return {
        "schema": 1, "task_id": task, "model": model, "provider": "P", "passed": passed,
        "passed_tests": tests[0], "total_tests": tests[1], "agent_seconds": seconds,
        "tokens": None, "cost_usd": None, "claimed": True,
    }


def test_build_benchmark_runs_groups_by_task(tmp_path: Path) -> None:
    for model, task, passed, tests, sec in (
        ("m-a", "t-1", True, (6, 6), 90.0),
        ("m-b", "t-1", False, (5, 6), None),
        ("m-a", "t-2", True, (3, 3), 30.0),
    ):
        d = tmp_path / model
        d.mkdir(exist_ok=True)
        (d / f"{task}.json").write_text(json.dumps(_report(model, task, passed, tests, sec)), encoding="utf-8")

    runs = export_metrics.build_benchmark_runs(tmp_path)

    assert [t["id"] for t in runs] == ["t-1", "t-2"]
    first = {r["model_name"]: r for r in runs[0]["runs"]}
    assert first["m-a"]["status"] == "PASS" and first["m-a"]["duration_min"] == 1.5
    assert first["m-b"]["status"] == "FAIL" and first["m-b"]["duration_min"] is None
    assert first["m-b"]["total_tokens"] is None and first["m-b"]["claimed"] is True


def test_build_benchmark_runs_empty(tmp_path: Path) -> None:
    assert export_metrics.build_benchmark_runs(tmp_path) == []
