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
    original_popen = runner.subprocess.Popen

    def mock_popen(cmd, **kwargs):
        if kwargs.get("cwd", "").endswith("reference_solution") and "/hidden/tests" in cmd[-1]:
            changed = ["uv", "run", "--no-project", "--with", "pytest", "python", "-c", plugin_code] + cmd[6:]
            return original_popen(changed, **kwargs)
        return original_popen(cmd, **kwargs)

    monkeypatch.setattr(runner.subprocess, "Popen", mock_popen)
    assert runner.verify_task(runner.TASKS_DIR / "sec-01-clock-skew") is False


def test_runner_rejects_xfailed_tests(monkeypatch) -> None:
    plugin_code = """
import sys, pytest
class XfailOne:
    def pytest_collection_modifyitems(self, items):
        for item in items:
            if item.name == "test_far_future_auth_date_fails":
                item.add_marker(pytest.mark.xfail(run=False, reason="test xfail probe"))
sys.exit(pytest.main(sys.argv[1:], plugins=[XfailOne()]))
"""
    original_popen = runner.subprocess.Popen

    def mock_popen(cmd, **kwargs):
        if kwargs.get("cwd", "").endswith("reference_solution") and "/hidden/tests" in cmd[-1]:
            changed = ["uv", "run", "--no-project", "--with", "pytest", "python", "-c", plugin_code] + cmd[6:]
            return original_popen(changed, **kwargs)
        return original_popen(cmd, **kwargs)

    monkeypatch.setattr(runner.subprocess, "Popen", mock_popen)
    assert runner.verify_task(runner.TASKS_DIR / "sec-01-clock-skew") is False


def test_runner_rejects_collection_errors_as_valid_failure(monkeypatch) -> None:
    original_run_pytest = runner.run_pytest

    def mock_run(cwd, test_paths, **kwargs):
        # Simulate collection error (syntax error or import error) on seed
        if str(cwd).endswith("seed") and any("/hidden/tests" in p for p in test_paths):
            return {
                "exit_code": 2,
                "stdout": "ERROR collecting test_foo.py\n1 error in 0.05s",
                "stderr": "SyntaxError: invalid syntax",
                "duration_s": 0.05,
                "passed": False,
                "timed_out": False,
                "counts": {"passed": 0, "failed": 0, "deselected": 0, "skipped": 0, "xfailed": 0, "xpassed": 0, "errors": 1},
            }
        return original_run_pytest(cwd, test_paths, **kwargs)

    monkeypatch.setattr(runner, "run_pytest", mock_run)
    # verify_task must NOT accept collection error as clean test rejection
    assert runner.verify_task(runner.TASKS_DIR / "sec-01-clock-skew") is False


def test_runner_rejects_spoofed_pytest_in_candidate_workdir(tmp_path: Path) -> None:
    # Candidate places a spoofed pytest.py in src/
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)

    fake_pytest = src_dir / "pytest.py"
    fake_pytest.write_text("""
def console_main():
    print("27 passed in 0.01s")
    return 0

def main(*args, **kwargs):
    print("27 passed in 0.01s")
    return 0
""")

    ranges_file = src_dir / "ranges.py"
    ranges_file.write_text("def parse_ranges(*args): raise NotImplementedError('unimplemented')\\n")

    res = runner.evaluate_task("algo-03-range-merger", tmp_path)
    assert res["passed"] is False

