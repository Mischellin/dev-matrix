"""Pytest guard plugin to prevent tampering with pytest test primitives."""
from __future__ import annotations

import pytest

# Snapshot genuine pytest functions at initial import time before candidate code runs
_ORIG_RAISES = pytest.raises
_ORIG_SKIP = pytest.skip
_ORIG_FAIL = pytest.fail
_ORIG_XFAIL = pytest.xfail
_ORIG_EXIT = pytest.exit


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    """Restore genuine pytest assertions before setting up each test item."""
    pytest.raises = _ORIG_RAISES
    pytest.skip = _ORIG_SKIP
    pytest.fail = _ORIG_FAIL
    pytest.xfail = _ORIG_XFAIL
    pytest.exit = _ORIG_EXIT


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_call(item: pytest.Item) -> None:
    """Ensure genuine pytest assertions are active during test execution."""
    pytest.raises = _ORIG_RAISES
    pytest.skip = _ORIG_SKIP
    pytest.fail = _ORIG_FAIL
    pytest.xfail = _ORIG_XFAIL
    pytest.exit = _ORIG_EXIT
