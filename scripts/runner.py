#!/usr/bin/env python3
"""
DevMatrix Task Runner & Suite Verifier.

Usage:
  # Self-verify the entire benchmark suite:
  python3 scripts/runner.py verify-suite

  # Prepare a clean workspace for an agent:
  python3 scripts/runner.py prepare --task <id> --out <path>

  # Evaluate a completed agent run against hidden acceptance tests:
  python3 scripts/runner.py evaluate --task <id> --workdir <path>
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
MANIFEST_PATH = TASKS_DIR / "manifest.json"


def run_pytest(cwd: Path, test_paths: list[str], pythonpath: str = "src") -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = pythonpath

    cmd = ["uv", "run", "--no-project", "--with", "pytest", "pytest", "-q"] + test_paths
    start_t = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )
    duration = time.perf_counter() - start_t

    return {
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "duration_s": round(duration, 3),
        "passed": proc.returncode == 0,
    }


def verify_task(task_dir: Path) -> bool:
    task_id = task_dir.name
    print(f"\n👉 Verifying task: {task_id}")

    seed_dir = task_dir / "seed"
    hidden_dir = task_dir / "hidden"
    ref_dir = task_dir / "reference_solution"

    # Step 1: Base seed must pass its baseline tests
    print("  1. Checking seed baseline tests... ", end="", flush=True)
    res_base = run_pytest(seed_dir, ["tests/"])
    if not res_base["passed"]:
        print(f"❌ FAILED (seed baseline tests should pass)\n{res_base['stdout']}")
        return False
    print("✅ Passed")

    # Step 2: Hidden tests must fail on the seed
    print("  2. Checking hidden tests fail on unpatched seed... ", end="", flush=True)
    res_hidden_on_seed = run_pytest(seed_dir, [str(hidden_dir / "tests")])
    if res_hidden_on_seed["passed"]:
        print("❌ FAILED (hidden tests must fail on vulnerable/unimplemented seed!)")
        return False
    print("✅ Correctly rejected")

    # Step 3: Hidden tests must pass on reference solution
    print("  3. Checking reference solution passes 100% of hidden tests... ", end="", flush=True)
    res_ref = run_pytest(ref_dir, [str(hidden_dir / "tests")])
    if not res_ref["passed"]:
        print(f"❌ FAILED (reference solution must pass all hidden tests)\n{res_ref['stdout']}")
        return False
    print("✅ Passed (100% verifier pass)")

    return True


def verify_suite() -> int:
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    tasks = manifest.get("tasks", [])
    print(f"===========================================================")
    print(f" DevMatrix Benchmark Suite Verification ({len(tasks)} tasks)")
    print(f"===========================================================")

    all_passed = True
    for item in tasks:
        t_dir = TASKS_DIR / item["id"]
        if not t_dir.is_dir():
            print(f"❌ Directory not found for task {item['id']}")
            all_passed = False
            continue
        if not verify_task(t_dir):
            all_passed = False

    print("\n-----------------------------------------------------------")
    if all_passed:
        print("🎉 ALL TASKS IN SUITE PASSED SELF-VERIFICATION!")
        return 0
    else:
        print("⚠️ SOME TASKS FAILED VERIFICATION.")
        return 1


def prepare_task(task_id: str, dest_dir: Path) -> None:
    task_dir = TASKS_DIR / task_id
    if not task_dir.is_dir():
        print(f"Error: task {task_id} not found", file=sys.stderr)
        sys.exit(1)

    seed_dir = task_dir / "seed"
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Copy seed files
    for item in seed_dir.iterdir():
        if item.name == ".venv":
            continue
        dest_item = dest_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest_item, dirs_exist_ok=True)
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

    hidden_tests = task_dir / "hidden" / "tests"
    print(f"Evaluating {workdir} against {task_id} hidden tests...")
    result = run_pytest(workdir, [str(hidden_tests)])
    print(f"Status: {'PASS' if result['passed'] else 'FAIL'} in {result['duration_s']}s")
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
