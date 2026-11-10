"""Pytest guard plugin to prevent tampering with pytest test primitives and execution."""
from __future__ import annotations

import json
import os

import pytest

# Snapshot genuine pytest functions and test execution runner at initial import time
_ORIG_RAISES = pytest.raises
_ORIG_SKIP = pytest.skip
_ORIG_FAIL = pytest.fail
_ORIG_XFAIL = pytest.xfail
_ORIG_EXIT = pytest.exit
_ORIG_RUNTEST = pytest.Function.runtest

_test_calls: list[dict[str, str]] = []


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    """Restore genuine pytest assertions and runner before setting up each test item."""
    pytest.raises = _ORIG_RAISES
    pytest.skip = _ORIG_SKIP
    pytest.fail = _ORIG_FAIL
    pytest.xfail = _ORIG_XFAIL
    pytest.exit = _ORIG_EXIT
    pytest.Function.runtest = _ORIG_RUNTEST


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_call(item: pytest.Item) -> None:
    """Ensure genuine pytest assertions and runner are active during test execution."""
    pytest.raises = _ORIG_RAISES
    pytest.skip = _ORIG_SKIP
    pytest.fail = _ORIG_FAIL
    pytest.xfail = _ORIG_XFAIL
    pytest.exit = _ORIG_EXIT
    pytest.Function.runtest = _ORIG_RUNTEST


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Track actual test executions during call phase."""
    if report.when == "call":
        _test_calls.append({"nodeid": report.nodeid, "outcome": report.outcome})


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Persist verified test execution report to file for runner verification."""
    report_file = os.environ.get("DEV_MATRIX_REPORT_FILE")
    if report_file:
        try:
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump({"exitstatus": int(exitstatus), "calls": _test_calls}, f)
        except OSError:
            pass
