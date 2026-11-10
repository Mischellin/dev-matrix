#!/usr/bin/env python3
"""
DevMatrix Benchmark Suite Runner & Verifier.

Commands:
  verify-suite: Verifies integrity of all anonymized benchmark tasks:
    1. Seed baseline tests pass on initial seed (exact expected count, zero skips/xfails).
    2. Hidden tests fail on initial vulnerable/unimplemented seed (actual test failure, zero infrastructure/collection errors).
    3. Reference solution passes 100% of hidden acceptance tests (exact count, zero skips/xfails).
    4. Reference solution passes 100% of baseline seed tests (no regressions, exact count, zero skips/xfails).
    5. Validates manifest.json and task.toml consistency.
  prepare: Copies anonymized seed + task prompt into target directory.
  evaluate: Runs baseline and hidden acceptance tests against agent's workdir.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
MANIFEST_PATH = TASKS_DIR / "manifest.json"
DEFAULT_TIMEOUT_S = 60.0


def _parse_pytest_summary(stdout: str) -> dict[str, int]:
    counts = {
        "passed": 0,
        "failed": 0,
        "deselected": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
        "errors": 0,
    }
    m_pass = re.search(r"(\d+)\s+passed", stdout)
    if m_pass:
        counts["passed"] = int(m_pass.group(1))
    m_fail = re.search(r"(\d+)\s+failed", stdout)
    if m_fail:
        counts["failed"] = int(m_fail.group(1))
    m_desel = re.search(r"(\d+)\s+deselected", stdout)
    if m_desel:
        counts["deselected"] = int(m_desel.group(1))
    m_skip = re.search(r"(\d+)\s+skipped", stdout)
    if m_skip:
        counts["skipped"] = int(m_skip.group(1))
    m_xfail = re.search(r"(\d+)\s+xfailed", stdout)
    if m_xfail:
        counts["xfailed"] = int(m_xfail.group(1))
    m_xpass = re.search(r"(\d+)\s+xpassed", stdout)
    if m_xpass:
        counts["xpassed"] = int(m_xpass.group(1))
    m_err = re.search(r"(\d+)\s+error", stdout)
    if m_err:
        counts["errors"] = int(m_err.group(1))
    return counts


def get_task_meta(task_dir: Path) -> dict[str, Any]:
    task_toml = task_dir / "task.toml"
    meta: dict[str, Any] = {
        "timeout_s": DEFAULT_TIMEOUT_S,
        "baseline_tests": 1,
        "hidden_tests": 1,
        "total_tests": 2,
    }
    if task_toml.exists():
        try:
            data = tomllib.loads(task_toml.read_text(encoding="utf-8"))
            verifier = data.get("verifier", {})
            meta["timeout_s"] = float(verifier.get("timeout_s", DEFAULT_TIMEOUT_S))
            meta["baseline_tests"] = int(verifier.get("baseline_tests", 1))
            meta["hidden_tests"] = int(verifier.get("hidden_tests", 1))
            meta["total_tests"] = int(
                verifier.get(
                    "total_tests",
                    meta["baseline_tests"] + meta["hidden_tests"],
                )
            )
        except (tomllib.TOMLDecodeError, OSError, ValueError):
            pass
    return meta


def run_pytest(
    cwd: Path,
    test_paths: list[str],
    timeout_s: float = DEFAULT_TIMEOUT_S,
    expected_exact_tests: int | None = None,
    min_passed_tests: int = 1,
) -> dict[str, Any]:
    cwd = cwd.resolve()
    env = os.environ.copy()
    src_path = str(cwd / "src")
    env["PYTHONPATH"] = src_path
    # Prevent external environment or user flags from filtering/tampering with acceptance tests
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("PYTEST_CONFIG", None)
    env.pop("PYTEST_PLUGINS", None)

    # Use fully controlled pytest config (-c /dev/null) to ignore arbitrary candidate settings
    uv_bin = shutil.which("uv")
    if uv_bin:
        cmd = [
            uv_bin,
            "run",
            "--no-project",
            "--with",
            "pytest==8.3.4",
            "pytest",
        ]
    else:
        cmd = [
            sys.executable,
            "-m",
            "pytest",
        ]

    # Ensure isolated empty pytest config exists to prevent loading candidate pyproject.toml
    empty_ini = Path("/tmp/dev_matrix_empty.ini")
    if not empty_ini.exists():
        empty_ini.write_text("[pytest]\n", encoding="utf-8")

    cmd.extend([
        "-q",
        "-c",
        str(empty_ini),
        "--rootdir",
        str(cwd),
        "-p",
        "no:cacheprovider",
        "-o",
        f"pythonpath={src_path}",
        "-o",
        "python_files=test_*.py *_test.py",
        "-o",
        "python_classes=Test* *Test",
        "-o",
        "python_functions=test_*",
        "-o",
        "testpaths=",
        "-o",
        "addopts=",
    ])

    cmd.extend([str(Path(p).resolve()) for p in test_paths])

    start_t = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_s,
        )
        duration = time.perf_counter() - start_t
        counts = _parse_pytest_summary(proc.stdout)
        passed = proc.returncode == 0
        err_msg = proc.stderr

        if passed:
            if counts["deselected"] > 0:
                passed = False
                err_msg = (
                    f"Error: Mandatory tests were deselected ({counts['deselected']} deselected). "
                    f"All suite tests must be executed.\n{proc.stderr}"
                )
            elif counts["skipped"] > 0:
                passed = False
                err_msg = (
                    f"Error: Tests were skipped ({counts['skipped']} skipped). "
                    f"All suite tests must be executed without skipping.\n{proc.stderr}"
                )
            elif counts["xfailed"] > 0:
                passed = False
                err_msg = (
                    f"Error: Tests were xfailed ({counts['xfailed']} xfailed). "
                    f"All suite tests must pass normally.\n{proc.stderr}"
                )
            elif counts["xpassed"] > 0:
                passed = False
                err_msg = (
                    f"Error: Unexpected xpasses ({counts['xpassed']} xpassed).\n{proc.stderr}"
                )
            elif expected_exact_tests is not None and counts["passed"] != expected_exact_tests:
                passed = False
                err_msg = (
                    f"Error: Expected exactly {expected_exact_tests} tests to pass, but {counts['passed']} passed.\n{proc.stderr}"
                )
            elif counts["passed"] < min_passed_tests:
                passed = False
                err_msg = (
                    f"Error: Expected at least {min_passed_tests} tests to pass, but only {counts['passed']} passed.\n{proc.stderr}"
                )

        return {
            "exit_code": proc.returncode if passed else (proc.returncode or 1),
            "stdout": proc.stdout,
            "stderr": err_msg,
            "duration_s": round(duration, 3),
            "passed": passed,
            "timed_out": False,
            "counts": counts,
        }
    except subprocess.TimeoutExpired as e:
        duration = time.perf_counter() - start_t
        out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        return {
            "exit_code": 124,
            "stdout": out,
            "stderr": f"Execution timed out after {timeout_s}s\n{err}",
            "duration_s": round(duration, 3),
            "passed": False,
            "timed_out": True,
            "counts": {
                "passed": 0,
                "failed": 0,
                "deselected": 0,
                "skipped": 0,
                "xfailed": 0,
                "xpassed": 0,
                "errors": 1,
            },
        }


def verify_task(task_dir: Path) -> bool:
    task_id = task_dir.name
    meta = get_task_meta(task_dir)
    timeout_s = meta["timeout_s"]
    exp_base = meta["baseline_tests"]
    exp_hidden = meta["hidden_tests"]
    print(f"\n👉 Verifying task: {task_id}")

    seed_dir = task_dir / "seed"
    hidden_dir = task_dir / "hidden"
    ref_dir = task_dir / "reference_solution"

    # Step 1: Base seed must pass its baseline tests
    print(f"  1. Checking seed baseline tests ({exp_base} tests)... ", end="", flush=True)
    res_base = run_pytest(
        seed_dir,
        [str(seed_dir / "tests")],
        timeout_s=timeout_s,
        expected_exact_tests=exp_base,
    )
    if not res_base["passed"]:
        print(f"❌ FAILED (seed baseline tests should pass)\n{res_base['stdout']}\n{res_base['stderr']}")
        return False
    print("✅ Passed")

    # Step 2: Hidden tests must fail on the seed (due to actual test failures, NOT collection/infrastructure errors)
    print("  2. Checking hidden tests fail on unpatched seed... ", end="", flush=True)
    res_hidden_on_seed = run_pytest(seed_dir, [str(hidden_dir / "tests")], timeout_s=timeout_s)
    cnt = res_hidden_on_seed["counts"]
    if res_hidden_on_seed["timed_out"]:
        print(f"❌ FAILED (hidden tests timed out on seed instead of failing cleanly)\n{res_hidden_on_seed['stderr']}")
        return False
    if cnt["errors"] > 0:
        print(f"❌ FAILED (hidden tests produced collection/syntax error on seed instead of test failure!)\n{res_hidden_on_seed['stderr']}")
        return False
    if cnt["failed"] == 0 or res_hidden_on_seed["passed"]:
        print("❌ FAILED (hidden tests must fail on vulnerable/unimplemented seed!)")
        return False
    print("✅ Correctly rejected")

    # Step 3: Hidden tests must pass on reference solution
    print(f"  3. Checking reference solution passes 100% of hidden tests ({exp_hidden} tests)... ", end="", flush=True)
    res_ref_hidden = run_pytest(
        ref_dir,
        [str(hidden_dir / "tests")],
        timeout_s=timeout_s,
        expected_exact_tests=exp_hidden,
    )
    if not res_ref_hidden["passed"]:
        print(f"❌ FAILED (reference solution must pass all hidden tests)\n{res_ref_hidden['stdout']}\n{res_ref_hidden['stderr']}")
        return False
    print("✅ Passed")

    # Step 4: Baseline tests must also pass on reference solution (no regressions)
    print(f"  4. Checking reference solution preserves baseline seed tests ({exp_base} tests)... ", end="", flush=True)
    res_ref_seed = run_pytest(
        ref_dir,
        [str(seed_dir / "tests")],
        timeout_s=timeout_s,
        expected_exact_tests=exp_base,
    )
    if not res_ref_seed["passed"]:
        print(f"❌ FAILED (reference solution broke baseline tests)\n{res_ref_seed['stdout']}\n{res_ref_seed['stderr']}")
        return False
    print("✅ Passed")

    return True


def verify_suite() -> int:
    if not MANIFEST_PATH.exists():
        print(f"Error: manifest not found at {MANIFEST_PATH}", file=sys.stderr)
        return 1

    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    tasks = manifest.get("tasks", [])
    print("===========================================================")
    print(f" DevMatrix Benchmark Suite Verification ({len(tasks)} tasks)")
    print("===========================================================")

    all_passed = True

    # Validate metadata consistency first
    print("\n📋 Checking manifest.json <-> task.toml consistency...")
    for item in tasks:
        t_id = item["id"]
        t_path = TASKS_DIR / t_id
        if not t_path.is_dir():
            print(f"❌ Task directory missing: {t_path}")
            all_passed = False
            continue

        meta = get_task_meta(t_path)
        manifest_count = item.get("tests_count")
        toml_count = meta.get("total_tests")
        calculated_count = meta.get("baseline_tests", 0) + meta.get("hidden_tests", 0)

        if manifest_count != toml_count or toml_count != calculated_count:
            print(
                f"❌ Count mismatch for {t_id}: manifest={manifest_count}, "
                f"task.toml={toml_count}, baseline+hidden={calculated_count}"
            )
            all_passed = False
        else:
            print(f"  • {t_id}: {toml_count} tests consistent")

    if not all_passed:
        print("⚠️ METADATA INCONSISTENCY DETECTED.")
        return 1

    for item in tasks:
        t_id = item["id"]
        t_path = TASKS_DIR / t_id
        if not verify_task(t_path):
            all_passed = False

    print("\n-----------------------------------------------------------")
    if all_passed:
        print("🎉 ALL TASKS IN SUITE PASSED SELF-VERIFICATION!")
        return 0
    else:
        print("⚠️ SOME TASKS FAILED VERIFICATION.")
        return 1


IGNORE_PATTERNS = {".venv", "__pycache__", ".pytest_cache"}


def prepare_task(task_id: str, dest_dir: Path) -> None:
    task_dir = TASKS_DIR / task_id
    if not task_dir.is_dir():
        print(f"Error: task {task_id} not found", file=sys.stderr)
        sys.exit(1)

    if dest_dir.exists():
        existing = [p for p in dest_dir.iterdir() if p.name not in {".git"}]
        if existing:
            print(
                f"Error: destination directory '{dest_dir}' is not empty (contains {len(existing)} items). "
                "Workspace must be empty.",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        dest_dir.mkdir(parents=True, exist_ok=True)

    seed_dir = task_dir / "seed"

    # Copy seed files excluding caches
    for item in seed_dir.iterdir():
        if item.name in IGNORE_PATTERNS or item.name.endswith(".egg-info"):
            continue
        dest_item = dest_dir / item.name
        if item.is_dir():
            shutil.copytree(
                item,
                dest_item,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "*.egg-info"),
            )
        else:
            shutil.copy2(item, dest_item)

    # Copy prompt.md
    shutil.copy2(task_dir / "prompt.md", dest_dir / "TASK_PROMPT.md")
    print(f"Prepared clean workspace for {task_id} at {dest_dir}")


def evaluate_task(task_id: str, workdir: Path) -> dict[str, Any]:
    task_dir = TASKS_DIR / task_id
    if not task_dir.is_dir():
        print(f"Error: task {task_id} not found", file=sys.stderr)
        sys.exit(1)

    meta = get_task_meta(task_dir)
    timeout_s = meta["timeout_s"]
    expected_tests = meta["total_tests"]

    seed_tests = task_dir / "seed" / "tests"
    hidden_tests = task_dir / "hidden" / "tests"

    print(f"Evaluating {workdir} against {task_id} baseline & hidden tests...")

    # Run both baseline (seed) tests and hidden acceptance tests
    test_paths = []
    if seed_tests.exists():
        test_paths.append(str(seed_tests))
    if hidden_tests.exists():
        test_paths.append(str(hidden_tests))

    result = run_pytest(
        workdir,
        test_paths,
        timeout_s=timeout_s,
        expected_exact_tests=expected_tests,
    )

    if result["passed"]:
        print(f"Status: ✅ PASS ({result['counts']['passed']}/{expected_tests} tests in {result['duration_s']}s)")
    else:
        status_note = "TIMEOUT" if result.get("timed_out") else "FAIL"
        print(f"Status: ❌ {status_note} in {result['duration_s']}s")
        if result["stdout"]:
            print(result["stdout"])
        if result["stderr"]:
            print(result["stderr"], file=sys.stderr)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="DevMatrix Task Runner & Suite Verifier")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # verify-suite
    subparsers.add_parser("verify-suite", help="Self-verify the entire benchmark suite")

    # prepare
    prep_p = subparsers.add_parser("prepare", help="Prepare a clean workspace for an agent")
    prep_p.add_argument("--task", required=True, help="Task ID")
    prep_p.add_argument("--out", required=True, type=Path, help="Destination directory")

    # evaluate
    eval_p = subparsers.add_parser("evaluate", help="Evaluate a completed agent workdir")
    eval_p.add_argument("--task", required=True, help="Task ID")
    eval_p.add_argument("--workdir", required=True, type=Path, help="Agent workdir")

    args = parser.parse_args()

    if args.command == "verify-suite":
        sys.exit(verify_suite())
    elif args.command == "prepare":
        prepare_task(args.task, args.out)
    elif args.command == "evaluate":
        res = evaluate_task(args.task, args.workdir)
        sys.exit(0 if res["passed"] else 1)


if __name__ == "__main__":
    main()
