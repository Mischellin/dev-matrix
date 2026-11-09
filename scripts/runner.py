#!/usr/bin/env python3
"""
DevMatrix Benchmark Suite Runner & Verifier.

Commands:
  verify-suite: Verifies integrity of all anonymized benchmark tasks:
    1. Seed baseline tests pass on initial seed.
    2. Hidden tests fail on initial vulnerable/unimplemented seed.
    3. Reference solution passes 100% of hidden acceptance tests.
    4. Reference solution passes 100% of baseline seed tests (no regressions).
  prepare: Copies anonymized seed + task prompt into target directory.
  evaluate: Runs baseline and hidden acceptance tests against agent's workdir.
"""

from __future__ import annotations

import argparse
import json
import os
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


def get_task_timeout(task_dir: Path) -> float:
    task_toml = task_dir / "task.toml"
    if task_toml.exists():
        try:
            data = tomllib.loads(task_toml.read_text(encoding="utf-8"))
            return float(data.get("verifier", {}).get("timeout_s", DEFAULT_TIMEOUT_S))
        except (tomllib.TOMLDecodeError, OSError, ValueError):
            return DEFAULT_TIMEOUT_S
    return DEFAULT_TIMEOUT_S


def run_pytest(
    cwd: Path,
    test_paths: list[str],
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    cwd = cwd.resolve()
    env = os.environ.copy()
    src_path = str(cwd / "src")
    env["PYTHONPATH"] = src_path

    cmd = ["uv", "run", "--no-project", "--with", "pytest", "pytest", "-q"]

    # Explicitly configure pytest to use target workdir and pythonpath
    pyproject = cwd / "pyproject.toml"
    if pyproject.exists():
        cmd.extend(["-c", str(pyproject)])
    cmd.extend(["-o", f"pythonpath={src_path}"])
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
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_s": round(duration, 3),
            "passed": proc.returncode == 0,
            "timed_out": False,
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
        }


def verify_task(task_dir: Path) -> bool:
    task_id = task_dir.name
    timeout_s = get_task_timeout(task_dir)
    print(f"\n👉 Verifying task: {task_id}")

    seed_dir = task_dir / "seed"
    hidden_dir = task_dir / "hidden"
    ref_dir = task_dir / "reference_solution"

    # Step 1: Base seed must pass its baseline tests
    print("  1. Checking seed baseline tests... ", end="", flush=True)
    res_base = run_pytest(seed_dir, [str(seed_dir / "tests")], timeout_s=timeout_s)
    if not res_base["passed"]:
        print(f"❌ FAILED (seed baseline tests should pass)\n{res_base['stdout']}\n{res_base['stderr']}")
        return False
    print("✅ Passed")

    # Step 2: Hidden tests must fail on the seed
    print("  2. Checking hidden tests fail on unpatched seed... ", end="", flush=True)
    res_hidden_on_seed = run_pytest(seed_dir, [str(hidden_dir / "tests")], timeout_s=timeout_s)
    if res_hidden_on_seed["passed"]:
        print("❌ FAILED (hidden tests must fail on vulnerable/unimplemented seed!)")
        return False
    print("✅ Correctly rejected")

    # Step 3: Hidden tests must pass on reference solution
    print("  3. Checking reference solution passes 100% of hidden tests... ", end="", flush=True)
    res_ref_hidden = run_pytest(ref_dir, [str(hidden_dir / "tests")], timeout_s=timeout_s)
    if not res_ref_hidden["passed"]:
        print(f"❌ FAILED (reference solution must pass all hidden tests)\n{res_ref_hidden['stdout']}\n{res_ref_hidden['stderr']}")
        return False
    print("✅ Passed")

    # Step 4: Baseline tests must also pass on reference solution (no regressions)
    print("  4. Checking reference solution preserves baseline seed tests... ", end="", flush=True)
    res_ref_seed = run_pytest(ref_dir, [str(seed_dir / "tests")], timeout_s=timeout_s)
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
    for item in tasks:
        t_id = item["id"]
        t_path = TASKS_DIR / t_id
        if not t_path.is_dir():
            print(f"❌ Task directory missing: {t_path}")
            all_passed = False
            continue

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

    timeout_s = get_task_timeout(task_dir)
    seed_tests = task_dir / "seed" / "tests"
    hidden_tests = task_dir / "hidden" / "tests"

    print(f"Evaluating {workdir} against {task_id} baseline & hidden tests...")

    # Run both baseline (seed) tests and hidden acceptance tests
    test_paths = []
    if seed_tests.exists():
        test_paths.append(str(seed_tests))
    if hidden_tests.exists():
        test_paths.append(str(hidden_tests))

    result = run_pytest(workdir, test_paths, timeout_s=timeout_s)

    if result["passed"]:
        print(f"Status: ✅ PASS in {result['duration_s']}s")
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
