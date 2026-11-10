from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from devmatrix import cli


def _report(tmp_path: Path, **over) -> Path:
    tid = "algo-03-range-merger"
    r = {
        "schema": 1,
        "task_id": tid,
        "model": "My Model",
        "passed": True,
        "passed_tests": 27,
        "total_tests": 27,
        "agent_seconds": 1.0,
        "tasks_hash": cli.task_hash(tid),
        "created_at": "2026-11-10T00:00:00Z",
    }
    r.update(over)
    p = tmp_path / cli.model_slug(r["model"]) / f"{r['task_id']}.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(r), encoding="utf-8")
    return p


def test_valid_report(tmp_path) -> None:
    assert cli.validate_report(_report(tmp_path)) == []


def test_stale_hash_rejected(tmp_path) -> None:
    assert any("хеш" in e for e in cli.validate_report(_report(tmp_path, tasks_hash="0" * 64)))


def test_inconsistent_passed_rejected(tmp_path) -> None:
    errs = cli.validate_report(_report(tmp_path, passed=True, passed_tests=3))
    assert any("согласуется" in e for e in errs)


def test_unknown_task_rejected(tmp_path) -> None:
    assert cli.validate_report(_report(tmp_path, task_id="nope"))


def test_model_slug() -> None:
    assert cli.model_slug("Claude Sonnet 5.5") == "claude-sonnet-5.5"
