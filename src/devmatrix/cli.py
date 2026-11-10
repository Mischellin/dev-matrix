"""CLI DevMatrix: list / run / evaluate / submit / check-submissions."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

try:
    from devmatrix import runner
except ImportError:  # запуск из клона репозитория: runner лежит в scripts/
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    import runner  # type: ignore[no-redef]

UPSTREAM = "Mischellin/dev-matrix"
SCHEMA = 1
HASHED_PARTS = ("seed", "hidden", "prompt.md", "task.toml")
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".venv"}
MAX_REPORT_BYTES = 10_000
OPTIONAL_FIELDS = {"provider", "tokens", "cost_usd", "devmatrix_version", "claimed"}
MODEL_RE = r"[\w.\- /:+()]{1,100}"
REQUIRED_FIELDS = {
    "schema": int,
    "task_id": str,
    "model": str,
    "passed": bool,
    "passed_tests": int,
    "total_tests": int,
    "agent_seconds": (int, float),
    "tasks_hash": str,
    "created_at": str,
}


ALLOWED_FIELDS = set(REQUIRED_FIELDS) | OPTIONAL_FIELDS


def _version() -> str:
    try:
        return metadata.version("dev-matrix")
    except metadata.PackageNotFoundError:
        return "dev"


def model_slug(model: str) -> str:
    slug = re.sub(r"[^a-z0-9._-]+", "-", model.lower()).strip("-.")
    return slug or "unknown"


def task_hash(task_id: str) -> str:
    """Хеш условия и тестов задачи: по нему видно, что результат получен на текущей версии."""
    base = runner.TASKS_DIR / task_id
    h = hashlib.sha256()
    for part in HASHED_PARTS:
        p = base / part
        files = [p] if p.is_file() else sorted(f for f in p.rglob("*") if f.is_file())
        for f in files:
            rel = f.relative_to(base)
            if SKIP_DIRS & set(rel.parts) or f.suffix == ".pyc":
                continue
            h.update(rel.as_posix().encode())
            h.update(f.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def task_ids() -> list[str]:
    manifest = json.loads(runner.MANIFEST_PATH.read_text(encoding="utf-8"))
    return [t["id"] for t in manifest["tasks"]]


def cmd_list(_: argparse.Namespace) -> int:
    manifest = json.loads(runner.MANIFEST_PATH.read_text(encoding="utf-8"))
    for t in manifest["tasks"]:
        print(f"{t['id']:32} {t['difficulty']}  {t['tests_count']:>3} tests  {t['title']}")
    return 0


def _make_report(args: argparse.Namespace, task_id: str, res: dict[str, Any], agent_s: float):
    return {
        "schema": SCHEMA,
        "task_id": task_id,
        "model": args.model,
        "provider": args.provider,
        "passed": bool(res["passed"]),
        "passed_tests": res["counts"]["passed"],
        "total_tests": runner.get_task_meta(runner.TASKS_DIR / task_id)["total_tests"],
        "agent_seconds": round(agent_s, 1),
        "tokens": args.tokens,
        "cost_usd": args.cost,
        "tasks_hash": task_hash(task_id),
        "devmatrix_version": _version(),
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "claimed": True,  # токены, цена и время сообщены автором, не измерены нами
    }


def _save(report: dict[str, Any], out: Path) -> Path:
    if model_slug(report["model"]) == "unknown":
        print(
            "⚠️ По имени модели не получилось собрать каталог (будет «unknown») — "
            "используйте латиницу в --model.",
            file=sys.stderr,
        )
    path = out / model_slug(report["model"]) / f"{report['task_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _run_agent(cmd: str, workdir: Path, task_id: str, timeout: float) -> float:
    prompt = workdir / "TASK_PROMPT.md"
    cmd = cmd.replace("{prompt_file}", shlex.quote(str(prompt)))
    env = {**os.environ, "DEVMATRIX_TASK_ID": task_id, "DEVMATRIX_PROMPT": str(prompt)}
    start = time.monotonic()
    # Своя группа процессов: по таймауту убиваем и потомков агента, иначе они правят папку при проверке.
    proc = subprocess.Popen(cmd, shell=True, cwd=workdir, env=env, start_new_session=True)
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"⚠️ Агент превысил лимит {timeout:.0f} с — проверяем то, что есть.")
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
    return time.monotonic() - start


def cmd_run(args: argparse.Namespace) -> int:
    if args.all == bool(args.task):
        print("Укажите либо задачу, либо --all", file=sys.stderr)
        return 2
    ids = task_ids() if args.all else [args.task]
    failed = 0
    rows = []
    for tid in ids:
        if not (runner.TASKS_DIR / tid).is_dir():
            print(f"Нет задачи {tid}", file=sys.stderr)
            return 2
        workdir = Path(tempfile.mkdtemp(prefix=f"devmatrix-{tid}-"))
        runner.prepare_task(tid, workdir)
        agent_s = _run_agent(args.agent, workdir, tid, args.agent_timeout)
        res = runner.evaluate_task(tid, workdir)
        path = _save(_make_report(args, tid, res, agent_s), args.out)
        rows.append((tid, res["passed"], path))
        failed += 0 if res["passed"] else 1
        if not args.keep:
            shutil.rmtree(workdir, ignore_errors=True)
    print("\nИтог:")
    for tid, ok, path in rows:
        print(f"  {'✅' if ok else '❌'} {tid}  →  {path}")
    print(f"\nГотово. Отправить результаты: devmatrix submit --dir {args.out}")
    return 0 if failed == 0 else 1


def cmd_evaluate(args: argparse.Namespace) -> int:
    res = runner.evaluate_task(args.task, args.workdir)
    path = _save(_make_report(args, args.task, res, args.agent_seconds), args.out)
    print(f"Отчёт: {path}")
    return 0 if res["passed"] else 1


def validate_report(path: Path, root: Path | None = None) -> list[str]:
    """Возвращает список ошибок отчёта (пустой — отчёт годен)."""

    def _reject_constant(name: str) -> None:
        raise ValueError(f"недопустимое значение {name}")

    try:
        if path.stat().st_size > MAX_REPORT_BYTES:
            return [f"файл больше {MAX_REPORT_BYTES} байт"]
        r = json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_constant)
    except (OSError, ValueError) as e:
        return [f"не читается JSON: {e}"]
    if not isinstance(r, dict):
        return ["отчёт должен быть JSON-объектом"]
    errs = []
    unknown = set(r) - ALLOWED_FIELDS
    if unknown:
        errs.append(f"неизвестные поля: {', '.join(sorted(unknown))}")
    for key, typ in REQUIRED_FIELDS.items():
        if not isinstance(r.get(key), typ) or (typ is int and isinstance(r.get(key), bool)):
            errs.append(f"поле {key} отсутствует или неверного типа")
    if errs:
        return errs
    for key in ("tokens", "cost_usd"):
        v = r.get(key)
        if v is not None and (
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0
        ):
            errs.append(f"{key} должно быть неотрицательным числом или null")
    for key in ("provider", "devmatrix_version"):
        v = r.get(key)
        if v is not None and (not isinstance(v, str) or len(v) > 100):
            errs.append(f"{key} должно быть строкой до 100 символов или null")
    if (
        isinstance(r["agent_seconds"], bool)
        or not math.isfinite(r["agent_seconds"])
        or r["agent_seconds"] < 0
    ):
        errs.append("agent_seconds должно быть неотрицательным числом")
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", r["created_at"]):
        errs.append("created_at должно быть в формате YYYY-MM-DDTHH:MM:SSZ")
    if not re.fullmatch(r"[0-9a-f]{64}", r["tasks_hash"]):
        errs.append("tasks_hash должен быть sha256 в hex")
    if not re.fullmatch(MODEL_RE, r["model"]):
        errs.append("model: до 100 символов из букв, цифр и . - _ / : + ( ) и пробела")
    if r["schema"] != SCHEMA:
        errs.append(f"схема {r['schema']} не поддерживается")
    if r["task_id"] not in task_ids():
        return errs + [f"неизвестная задача {r['task_id']}"]
    if r["tasks_hash"] != task_hash(r["task_id"]):
        errs.append(
            "хеш задачи не совпадает с текущей версией набора — обновите devmatrix и повторите"
        )
    meta = runner.get_task_meta(runner.TASKS_DIR / r["task_id"])
    if r["total_tests"] != meta["total_tests"]:
        errs.append("total_tests не совпадает с задачей")
    if not 0 <= r["passed_tests"] <= r["total_tests"]:
        errs.append("passed_tests вне диапазона")
    if r["passed"] != (r["passed_tests"] == r["total_tests"]):
        errs.append("passed не согласуется с passed_tests")
    if path.name != f"{r['task_id']}.json" or path.parent.name != model_slug(r["model"]):
        errs.append(f"путь должен быть submissions/{model_slug(r['model'])}/{r['task_id']}.json")
    return errs


def cmd_check(args: argparse.Namespace) -> int:
    if not args.dir.is_dir():
        print(f"❌ Нет каталога {args.dir}", file=sys.stderr)
        return 1
    files = sorted(f for f in args.dir.rglob("*") if f.is_file() or f.is_symlink())
    bad = 0
    for f in files:
        rel = f.relative_to(args.dir)
        if rel.as_posix() == "README.md":
            continue
        if f.is_symlink() or f.suffix != ".json" or len(rel.parts) != 2:
            print(f"❌ {f}: допустимы только submissions/<модель>/<задача>.json")
            bad += 1
            continue
        errs = validate_report(f)
        for e in errs:
            print(f"❌ {f}: {e}")
        bad += bool(errs)
    print(f"Проверено файлов: {len(files)}, с ошибками: {bad}")
    return 1 if bad else 0


def _gh(*a: str, cwd: Path | None = None, capture: bool = False) -> str:
    r = subprocess.run(["gh", *a], cwd=cwd, check=True, text=True, capture_output=capture)
    return r.stdout.strip() if capture else ""


def _git(*a: str, cwd: Path) -> None:
    subprocess.run(["git", *a], cwd=cwd, check=True)


def cmd_submit(args: argparse.Namespace) -> int:
    files = sorted(args.dir.rglob("*.json"))
    if not files:
        print(f"В {args.dir} нет отчётов. Сначала: devmatrix run ...", file=sys.stderr)
        return 2
    reports = []
    for f in files:
        errs = validate_report(f)
        if errs:
            print(f"❌ {f}: {'; '.join(errs)}", file=sys.stderr)
            return 1
        reports.append((f, json.loads(f.read_text(encoding="utf-8"))))
    print("К отправке:")
    for f, r in reports:
        print(
            f"  {'✅' if r['passed'] else '❌'} {r['model']:30} {r['task_id']:28} "
            f"{r['passed_tests']}/{r['total_tests']}"
        )
    print("Токены, цена и время указаны вами и в таблице помечаются как «заявлено автором».")
    if not args.yes and not sys.stdin.isatty():
        print("Нет терминала для подтверждения: запустите с --yes.", file=sys.stderr)
        return 1
    if not args.yes and input("Отправить PR в публичный репозиторий? [y/N] ").lower() != "y":
        print("Отменено.")
        return 1
    if not shutil.which("gh"):
        print(
            f"\nУстановите gh (https://cli.github.com) либо откройте PR вручную: положите файлы в "
            f"submissions/ форка {UPSTREAM} и создайте pull request."
        )
        return 1
    user = _gh("api", "user", "-q", ".login", capture=True)
    _gh("repo", "fork", UPSTREAM, "--clone=false")
    work = Path(tempfile.mkdtemp(prefix="devmatrix-submit-"))
    try:
        fork = _gh(
            "repo",
            "view",
            f"{user}/{UPSTREAM.split('/')[1]}",
            "--json",
            "nameWithOwner",
            "-q",
            ".nameWithOwner",
            capture=True,
        )
        _gh("repo", "clone", fork, str(work / "repo"))
        repo = work / "repo"
        _git("remote", "add", "upstream", f"https://github.com/{UPSTREAM}.git", cwd=repo)
        _git("fetch", "-q", "upstream", "main", cwd=repo)
        branch = f"submit-{int(time.time())}"
        _git("checkout", "-q", "-b", branch, "upstream/main", cwd=repo)
        for f, r in reports:
            dest = repo / "submissions" / model_slug(r["model"]) / f.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
        _git("add", "submissions", cwd=repo)
        _git(
            "-c",
            "user.name=devmatrix",
            "-c",
            f"user.email={user}@users.noreply.github.com",
            "commit",
            "-q",
            "-m",
            f"submission: {', '.join(sorted({r['model'] for _, r in reports}))}",
            cwd=repo,
        )
        _git("push", "-q", "-u", "origin", branch, cwd=repo)
        _gh(
            "pr",
            "create",
            "--repo",
            UPSTREAM,
            "--head",
            f"{user}:{branch}",
            "--base",
            "main",
            "--title",
            f"Результаты: {', '.join(sorted({r['model'] for _, r in reports}))}",
            "--body",
            f"Отправлено через `devmatrix submit` (версия {_version()}). Файлов: {len(reports)}.",
            cwd=repo,
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return 0


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="devmatrix", description="DevMatrix: бенчмарк ИИ-агентов")
    p.add_argument("--version", action="version", version=_version())
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="список задач").set_defaults(fn=cmd_list)

    def common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--model", required=True, help="имя модели, например claude-sonnet-5-5")
        sp.add_argument("--provider", default=None)
        sp.add_argument("--tokens", type=int, default=None, help="токены (по вашим данным)")
        sp.add_argument("--cost", type=float, default=None, help="цена в USD (по вашим данным)")
        sp.add_argument("--out", type=Path, default=Path("devmatrix-results"))

    r = sub.add_parser("run", help="запустить агента на задаче и проверить результат")
    r.add_argument("task", nargs="?")
    r.add_argument("--all", action="store_true", help="весь пул")
    r.add_argument(
        "--agent",
        required=True,
        help="команда запуска агента в рабочей папке; {prompt_file} — путь к заданию",
    )
    r.add_argument("--agent-timeout", type=float, default=1800)
    r.add_argument("--keep", action="store_true", help="не удалять рабочие папки")
    common(r)
    r.set_defaults(fn=cmd_run)

    e = sub.add_parser("evaluate", help="проверить уже готовую рабочую папку")
    e.add_argument("task")
    e.add_argument("--workdir", required=True, type=Path)
    e.add_argument("--agent-seconds", type=float, default=0.0)
    common(e)
    e.set_defaults(fn=cmd_evaluate)

    s = sub.add_parser("submit", help="отправить результаты PR-ом в публичный репозиторий")
    s.add_argument("--dir", type=Path, default=Path("devmatrix-results"))
    s.add_argument("--yes", action="store_true")
    s.set_defaults(fn=cmd_submit)

    c = sub.add_parser("check-submissions", help="проверить отчёты (используется в CI)")
    c.add_argument("dir", type=Path, nargs="?", default=Path("submissions"))
    c.set_defaults(fn=cmd_check)

    args = p.parse_args(argv)
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
