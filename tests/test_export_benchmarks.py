"""Сборка data/benchmark_runs.json из submissions/ и сводка в README."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import export_metrics  # noqa: E402


def _report(model: str, task: str, passed: bool, tests: tuple[int, int], seconds: float | None, **extra) -> dict:
    return {
        "schema": 1, "task_id": task, "model": model, "provider": "P", "passed": passed,
        "passed_tests": tests[0], "total_tests": tests[1], "agent_seconds": seconds,
        "tokens": None, "cost_usd": None, "tasks_hash": "h-" + task, **extra,
    }


def _write(root: Path, report: dict) -> None:
    d = root / report["model"]
    d.mkdir(exist_ok=True)
    (d / f"{report['task_id']}.json").write_text(json.dumps(report), encoding="utf-8")


def _hash(task_id: str) -> str:
    return "h-" + task_id


def test_groups_by_task_and_handles_nulls(tmp_path: Path) -> None:
    _write(tmp_path, _report("m-a", "t-1", True, (6, 6), 90.0))
    _write(tmp_path, _report("m-b", "t-1", False, (5, 6), None))
    _write(tmp_path, _report("m-a", "t-2", True, (3, 3), 30.0))

    runs = export_metrics.build_benchmark_runs(tmp_path, hash_of=_hash)

    assert [t["id"] for t in runs] == ["t-1", "t-2"]
    first = {r["model_name"]: r for r in runs[0]["runs"]}
    assert first["m-a"]["status"] == "PASS" and first["m-a"]["duration_min"] == 1.5
    assert first["m-b"]["status"] == "FAIL" and first["m-b"]["duration_min"] is None
    assert first["m-b"]["total_tokens"] is None and not first["m-b"]["outdated"]


def test_claimed_flag_is_not_taken_from_file(tmp_path: Path) -> None:
    _write(tmp_path, _report("m-a", "t-1", True, (1, 1), 1.0, claimed=False))
    run = export_metrics.build_benchmark_runs(tmp_path, hash_of=_hash)[0]["runs"][0]
    assert run["claimed"] is True


def test_report_from_older_task_version_is_marked_outdated(tmp_path: Path) -> None:
    _write(tmp_path, _report("m-a", "t-1", True, (1, 1), 1.0, tasks_hash="old"))
    run = export_metrics.build_benchmark_runs(tmp_path, hash_of=_hash)[0]["runs"][0]
    assert run["outdated"] is True


def test_broken_report_names_the_file(tmp_path: Path) -> None:
    d = tmp_path / "m-a"
    d.mkdir()
    (d / "t-1.json").write_text(json.dumps({"task_id": "t-1"}), encoding="utf-8")
    with pytest.raises(SystemExit, match="t-1.json"):
        export_metrics.build_benchmark_runs(tmp_path, hash_of=_hash)


def test_empty_directory(tmp_path: Path) -> None:
    assert export_metrics.build_benchmark_runs(tmp_path, hash_of=_hash) == []


def test_readme_summary_shows_passed_out_of_whole_suite() -> None:
    """В сводке README «пройдено» считается от размера всего пула, а не от числа отправленных задач."""
    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_readme.py")],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    assert "Generated" in out
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    suite = len(json.loads((ROOT / "tasks" / "manifest.json").read_text(encoding="utf-8"))["tasks"])
    assert f"/{suite} |" in readme
