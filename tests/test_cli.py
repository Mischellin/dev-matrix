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


def test_hash_independent_of_dot_venv_path(tmp_path, monkeypatch) -> None:
    import shutil

    tid = "algo-03-range-merger"
    expected = cli.task_hash(tid)
    copy = tmp_path / ".venv" / "tasks"
    shutil.copytree(cli.runner.TASKS_DIR, copy)
    monkeypatch.setattr(cli.runner, "TASKS_DIR", copy)
    assert cli.task_hash(tid) == expected
    assert expected != "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_dot_slug_is_not_path_traversal() -> None:
    assert cli.model_slug("..") == "unknown"
    assert cli.model_slug(".hidden") == "hidden"


def test_extra_files_rejected(tmp_path) -> None:
    _report(tmp_path)
    (tmp_path / "evil.sh").write_text("x")
    args = type("A", (), {"dir": tmp_path})()
    assert cli.cmd_check(args) == 1


def test_bad_optional_fields_rejected(tmp_path) -> None:
    assert cli.validate_report(_report(tmp_path, tokens=-5))


def test_wrong_path_rejected(tmp_path) -> None:
    p = _report(tmp_path)
    moved = p.parent.parent / "other" / p.name
    moved.parent.mkdir()
    p.rename(moved)
    assert any("путь" in e for e in cli.validate_report(moved))


def test_agent_timeout_kills_children(tmp_path) -> None:
    import time

    marker = tmp_path / "late"
    cmd = f"(python3 -c 'import time; time.sleep(3); open({str(marker)!r}, \"w\")' &) ; wait"
    cli._run_agent(cmd, tmp_path, "x", 1)
    time.sleep(4)
    assert not marker.exists()
