from __future__ import annotations

import json
import sys
from pathlib import Path

# Add scripts to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import runner


def test_manifest_consistency_matches_task_toml() -> None:
    manifest = json.loads(runner.MANIFEST_PATH.read_text(encoding="utf-8"))
    for item in manifest["tasks"]:
        tid = item["id"]
        tdir = runner.TASKS_DIR / tid
        assert tdir.is_dir()
        meta = runner.get_task_meta(tdir)
        assert item["tests_count"] == meta["total_tests"]
        assert meta["baseline_tests"] + meta["hidden_tests"] == meta["total_tests"]


def test_runner_rejects_skipped_tests(monkeypatch) -> None:
    plugin_code = """
import sys, pytest
class SkipOne:
    def pytest_collection_modifyitems(self, items):
        for item in items:
            if item.name == "test_far_future_auth_date_fails":
                item.add_marker(pytest.mark.skip(reason="test skip probe"))
sys.exit(pytest.main(sys.argv[1:], plugins=[SkipOne()]))
"""
    original_run = runner.subprocess.run

    def mock_run(cmd, **kwargs):
        if kwargs.get("cwd", "").endswith("reference_solution") and "/hidden/tests" in cmd[-1]:
            changed = ["uv", "run", "--no-project", "--with", "pytest", "python", "-c", plugin_code] + cmd[6:]
            return original_run(changed, **kwargs)
        return original_run(cmd, **kwargs)

    monkeypatch.setattr(runner.subprocess, "run", mock_run)
    assert runner.verify_task(runner.TASKS_DIR / "sec-01-clock-skew") is False
