"""Поведение shell-логики vast-bench без GPU и Docker: поддельные curl/opencode/nvidia-smi в PATH."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "docker" / "vast-bench"

sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "src"))  # devmatrix без установки пакета, как в test_cli.py


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    """Окружение со скриптами из репозитория и поддельными командами; HEALTH — файл «сервер здоров»."""
    fake = tmp_path / "bin"
    fake.mkdir()
    # /health отвечает, пока есть файл $FAKE_HEALTH; /metrics отдаёт $FAKE_METRICS.
    _script(
        fake / "curl",
        'url="${*: -1}"\n'
        'case "$url" in\n'
        '  */health) [[ -f $FAKE_HEALTH ]] ;;\n'
        '  */metrics) cat "$FAKE_METRICS" ;;\n'
        "esac\n",
    )
    # «Агент»: по FAKE_KILL_DURING гасит сервер во время работы, как упавший vLLM.
    _script(fake / "opencode", 'if [[ -n ${FAKE_KILL_DURING:-} ]]; then rm -f "$FAKE_HEALTH"; fi\n')
    _script(fake / "nvidia-smi", "echo 0\n")
    health = tmp_path / "healthy"
    health.touch()
    metrics = tmp_path / "metrics.txt"
    metrics.write_text("vllm:prompt_tokens_total 100\nvllm:generation_tokens_total 20\n")
    return {
        **os.environ,
        "PATH": f"{fake}:{os.environ['PATH']}",
        "VAST_BENCH_DIR": str(BENCH),
        "BENCH_HOME": str(tmp_path / "home"),
        "RESULTS_DIR": str(tmp_path / "results"),
        "HF_HOME": str(tmp_path / "hf"),
        "FAKE_HEALTH": str(health),
        "FAKE_METRICS": str(metrics),
        "VLLM_START_TIMEOUT": "1",
        "HEALTH_POLL": "0.1",
        "HEALTH_RETRY_SLEEP": "0",
    }


def _script(path: Path, body: str) -> None:
    path.write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8")
    path.chmod(0o755)


def _bash(code: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", f'source "{BENCH}/bench.sh"\n{code}'],
        env=env, capture_output=True, text=True, timeout=30, check=False,
    )  # fmt: skip


def test_wait_health_success(env) -> None:
    r = _bash("sleep 30 & pid=$!; wait_health $pid; echo rc=$?; kill $pid", env)
    assert "rc=0" in r.stdout, r.stderr


def test_wait_health_server_crashed(env) -> None:
    Path(env["FAKE_HEALTH"]).unlink()
    r = _bash("sleep 0.1 & pid=$!; wait $pid; wait_health $pid; echo rc=$?", env)
    assert "rc=1" in r.stdout, r.stderr


def test_wait_health_timeout(env) -> None:
    Path(env["FAKE_HEALTH"]).unlink()
    r = _bash("sleep 30 & pid=$!; wait_health $pid; echo rc=$?; kill $pid", env)
    assert "rc=2" in r.stdout, r.stderr


def test_vllm_healthy_needs_live_process_and_health(env) -> None:
    r = _bash(
        "sleep 30 & VLLM_PID=$!; vllm_healthy && echo up;"
        f' rm -f "{env["FAKE_HEALTH"]}"; vllm_healthy || echo no_health;'
        f' touch "{env["FAKE_HEALTH"]}"; kill $VLLM_PID; wait $VLLM_PID 2>/dev/null;'
        " vllm_healthy || echo no_process",
        env,
    )
    assert r.stdout.split() == ["up", "no_health", "no_process"], r.stderr


@pytest.mark.parametrize(
    ("rc", "submitted", "expected", "markers", "healthy", "status"),
    [
        (0, 3, 3, 0, 1, "done"),
        (1, 3, 3, 0, 1, "done"),  # часть задач не пройдена — нормальный итог
        (2, 3, 3, 0, 1, "devmatrix_failed"),
        (1, 1, 3, 0, 1, "devmatrix_failed"),  # traceback Python: код 1, но отчётов меньше, чем задач
        (0, 0, 3, 0, 1, "devmatrix_failed"),
        (1, 3, 3, 0, 0, "vllm_died"),  # сервер умер — код devmatrix не важен
        (0, 3, 3, 2, 1, "vllm_died"),  # сервер ожил, но агент ставил маркеры
        (2, 1, 3, 1, 0, "vllm_died"),
    ],
)
def test_classify_run(env, rc, submitted, expected, markers, healthy, status) -> None:
    r = _bash(f"classify_run {rc} {submitted} {expected} {markers} {healthy}", env)
    assert r.stdout.strip() == status, r.stderr


def _run_agent(env: dict[str, str], tmp_path: Path, **extra: str) -> subprocess.CompletedProcess[str]:
    out = tmp_path / "out"
    prompt = tmp_path / "prompt.md"
    prompt.write_text("задача")
    return subprocess.run(
        [str(BENCH / "agent-opencode.sh"), str(prompt)],
        env={**env, "BENCH_MODEL": "m", "BENCH_OUT": str(out), "DEVMATRIX_TASK_ID": "t1", **extra},
        cwd=tmp_path, capture_output=True, text=True, timeout=30, check=False,
    )  # fmt: skip


def test_agent_records_metrics_when_healthy(env, tmp_path) -> None:
    r = _run_agent(env, tmp_path)
    assert r.returncode == 0, r.stderr
    m = json.loads((tmp_path / "out" / "metrics" / "t1.json").read_text())
    assert m["opencode_exit"] == 0
    assert not (tmp_path / "out" / "metrics" / "t1.invalid").exists()


def test_agent_marks_dead_server_before_run(env, tmp_path) -> None:
    Path(env["FAKE_HEALTH"]).unlink()
    r = _run_agent(env, tmp_path)
    assert r.returncode == 3
    assert (tmp_path / "out" / "metrics" / "t1.invalid").is_file()
    assert not (tmp_path / "out" / "metrics" / "t1.json").exists()


def test_agent_marks_server_dying_during_run(env, tmp_path) -> None:
    r = _run_agent(env, tmp_path, FAKE_KILL_DURING="1")
    assert r.returncode == 3
    assert "после" in (tmp_path / "out" / "metrics" / "t1.invalid").read_text()
    assert not (tmp_path / "out" / "metrics" / "t1.json").exists()


def _report(sub: Path, task_id: str) -> Path:
    from devmatrix import cli

    res = {"passed": False, "counts": {"passed": 0}}
    args = SimpleNamespace(model="m-fp8", provider=None, tokens=None, cost=None)
    return cli._save(cli._make_report(args, task_id, res, 12.5), sub)


def test_fill_claims_negative_delta_and_marker_pass_validate_report(tmp_path) -> None:
    import importlib.util

    from devmatrix import cli

    spec = importlib.util.spec_from_file_location("vast_preset_shell", BENCH / "preset.py")
    preset = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(preset)

    t_ok, t_neg, t_bad = cli.task_ids()[:3]
    sub, met = tmp_path / "submissions", tmp_path / "metrics"
    met.mkdir()
    for t in (t_ok, t_neg, t_bad):
        _report(sub, t)
    (met / f"{t_ok}.json").write_text(json.dumps({"prompt_tokens": 100, "completion_tokens": 20}))
    (met / f"{t_neg}.json").write_text(json.dumps({"prompt_tokens": -5, "completion_tokens": 20}))
    (met / f"{t_bad}.json").write_text(json.dumps({"prompt_tokens": 7, "completion_tokens": 3}))
    (met / f"{t_bad}.invalid").write_text("vLLM мёртв")
    info = tmp_path / "run-info.json"
    info.write_text("{}")

    assert preset.fill_claims(sub, met, 0.5, "vLLM self-hosted", info) == 2

    reports = sorted(sub.rglob("*.json"))
    assert len(reports) == 2
    for f in reports:
        assert cli.validate_report(f) == [], f
    by_task = {f.stem: json.loads(f.read_text()) for f in reports}
    assert by_task[t_ok]["tokens"] == 120
    assert by_task[t_neg]["tokens"] is None
    # задача с маркером ушла из submissions/ и не может быть отправлена
    assert not list(sub.rglob(f"{t_bad}.json"))
    moved = tmp_path / "invalid" / "m-fp8" / f"{t_bad}.json"
    assert moved.is_file()
    assert json.loads(moved.read_text())["tokens"] is None
    assert json.loads(info.read_text())["invalid_tasks"] == [t_bad]


def test_agent_marks_opencode_crash_without_generation(env, tmp_path) -> None:
    _script(Path(env["PATH"].split(":")[0]) / "opencode", "exit 2\n")
    r = _run_agent(env, tmp_path)
    assert r.returncode == 3
    assert (tmp_path / "out" / "metrics" / "t1.invalid").read_text().startswith("t1: opencode_failed")
    assert not (tmp_path / "out" / "metrics" / "t1.json").exists()


def test_agent_keeps_opencode_timeout_and_crash_with_generation(env, tmp_path) -> None:
    fake = Path(env["PATH"].split(":")[0])
    _script(fake / "opencode", "exit 124\n")  # таймаут — результат модели
    assert _run_agent(env, tmp_path).returncode == 0
    # упал, но токены генерировались: это уже работа модели
    _script(fake / "opencode", 'echo "vllm:generation_tokens_total 50" >> "$FAKE_METRICS"; exit 2\n')
    assert _run_agent(env, tmp_path).returncode == 0
    assert not (tmp_path / "out" / "metrics" / "t1.invalid").exists()


@pytest.mark.parametrize(
    ("markers", "agent_failed", "healthy", "status"),
    [
        (4, 4, 1, "agent_failed"),  # из 6 задач большинство — упавший OpenCode
        (2, 2, 1, "done_partial"),  # меньшинство: прогон жив, задачи в invalid/
        (0, 0, 1, "done"),
        (3, 2, 1, "vllm_died"),  # есть и маркеры мёртвого сервера
        (4, 4, 0, "vllm_died"),  # сервер мёртв в конце — важнее
    ],
)
def test_classify_run_agent_failed(env, markers, agent_failed, healthy, status) -> None:
    r = _bash(f"classify_run 0 6 6 {markers} {healthy} {agent_failed}", env)
    assert r.stdout.strip() == status, r.stderr


def test_main_refuses_opencode_timeout_close_to_agent_timeout(env) -> None:
    r = _bash("OPENCODE_TIMEOUT=1500 AGENT_TIMEOUT=1600 main gpt-oss-20b; echo rc=$?", env)
    assert "rc=2" in r.stdout
    assert "OPENCODE_TIMEOUT" in r.stderr


def test_env_defaults_without_image_env(env) -> None:
    clean = {k: v for k, v in env.items() if not k.startswith(("UV_PYTHON", "VLLM_TAG", "IMAGE_REVISION"))}
    r = _bash("echo $UV_PYTHON_INSTALL_DIR $UV_PYTHON_PREFERENCE $VLLM_TAG $IMAGE_REVISION", clean)
    assert r.stdout.split() == ["/opt/uv-python", "only-managed", "unknown", "unknown"], r.stderr


# Прогон run_model целиком на поддельных hf/vllm/devmatrix: пока «идёт» текущая модель, hf качает следующую.
def _prefetch_env(env: dict[str, str], tmp_path: Path, **extra: str) -> dict[str, str]:
    fake = Path(env["PATH"].split(":")[0])
    _script(fake / "vllm", '[[ ${1:-} == serve ]] && exec sleep 60\necho "vllm 0.0"\n')
    _script(
        fake / "hf",
        'echo "$*" >>"$FAKE_HF_LOG"\n'
        'if [[ -n ${FAKE_HF_FAIL_ONCE:-} && "$*" == *"$FAKE_HF_FAIL_ONCE"* && ! -f $FAKE_HF_LOG.failed ]]; then\n'
        '  touch "$FAKE_HF_LOG.failed"; echo "сеть недоступна" >&2; exit 1\n'
        "fi\n",
    )
    _script(
        fake / "devmatrix",
        'if [[ $1 == list ]]; then echo t1; exit 0; fi\n'
        # пока «идёт» модель, ждём, что hf позвали за следующей
        'for _ in $(seq 100); do\n'
        '  grep -q "${FAKE_WAIT_FOR:-.}" "$FAKE_HF_LOG" 2>/dev/null && break; sleep 0.1\n'
        "done\n"
        'grep -q "${FAKE_WAIT_FOR:-.}" "$FAKE_HF_LOG" 2>/dev/null && echo seen >"$FAKE_SEEN"\n',
    )
    return {
        **env,
        "MODELS_TOML": str(BENCH / "models.toml"),
        "FAKE_HF_LOG": str(tmp_path / "hf.log"),
        "FAKE_SEEN": str(tmp_path / "seen"),
        **extra,
    }


def test_prefetch_calls_hf_for_next_model_while_current_runs(env, tmp_path) -> None:
    e = _prefetch_env(env, tmp_path, FAKE_WAIT_FOR="Devstral-Small-2")
    r = _bash("run_model gpt-oss-20b devstral-small-2; echo rc=$?", e)
    log = (tmp_path / "hf.log").read_text()
    assert "openai/gpt-oss-20b" in log, r.stderr
    assert "Devstral-Small-2" in log, r.stderr
    # devmatrix «увидел» докачку следующей модели ещё до своего завершения
    assert (tmp_path / "seen").read_text().strip() == "seen", r.stderr
    assert (tmp_path / "results" / "devstral-small-2" / "download.prefetch.log").is_file()


def test_prefetch_failure_is_reported_and_log_kept(env, tmp_path) -> None:
    e = _prefetch_env(env, tmp_path, FAKE_WAIT_FOR="Devstral-Small-2", FAKE_HF_FAIL_ONCE="Devstral-Small-2")
    r = _bash("run_model gpt-oss-20b devstral-small-2; run_model devstral-small-2; echo end", e)
    assert "фоновая докачка не удалась" in r.stderr
    res = tmp_path / "results" / "devstral-small-2"
    assert "сеть недоступна" in (res / "download.prefetch.log").read_text()
    # основной путь скачал заново в отдельный лог
    assert (res / "download.log").is_file()
    assert (tmp_path / "hf.log").read_text().count("Devstral-Small-2") == 2


def test_run_model_all_opencode_failed_with_healthy_vllm_is_agent_failed(env, tmp_path) -> None:
    # Сценарий Devstral: vLLM здоров, на всех задачах маркеры «<задача>: opencode_failed …» в реальном формате агента.
    e = _prefetch_env(env, tmp_path)
    _script(
        Path(env["PATH"].split(":")[0]) / "devmatrix",
        'if [[ $1 == list ]]; then printf "t%s\\n" 1 2 3; exit 0; fi\n'
        'mkdir -p "$BENCH_OUT/metrics"\n'
        'for t in t1 t2 t3; do\n'
        '  printf "%s: opencode_failed: OpenCode завершился с кодом 2, vLLM не сгенерировал токенов (см. opencode/%s.err)\\n"'
        ' "$t" "$t" >"$BENCH_OUT/metrics/$t.invalid"\n'
        "done\n",
    )
    r = _bash("run_model gpt-oss-20b; echo rc=$?", e)
    info = json.loads((tmp_path / "results" / "gpt-oss-20b" / "run-info.json").read_text())
    assert info["status"] == "agent_failed", r.stderr


def test_agent_does_not_pass_secrets_to_opencode(env, tmp_path) -> None:
    fake = Path(env["PATH"].split(":")[0])
    _script(fake / "opencode", 'env >"$FAKE_ENV_DUMP"\n')
    dump = tmp_path / "opencode.env"
    secrets = {
        "HF_TOKEN": "x", "HUGGING_FACE_HUB_TOKEN": "x", "VAST_API_KEY": "x", "GITHUB_TOKEN": "x",
        "MY_SECRET": "x", "DB_PASSWORD": "x",
    }  # fmt: skip
    r = _run_agent(env, tmp_path, FAKE_ENV_DUMP=str(dump), **secrets)
    assert r.returncode == 0, r.stderr
    names = {ln.split("=", 1)[0] for ln in dump.read_text().splitlines()}
    assert not names & set(secrets)
    assert {"HOME", "XDG_CONFIG_HOME", "PATH"} <= names


def _fake_privileged_env(env: dict[str, str], tmp_path: Path) -> Path:
    """Поддельные id (root для `id -u`, 1000 для `id -u agent`), setpriv и chown: пишут вызовы в журнал."""
    fake = Path(env["PATH"].split(":")[0])
    log = tmp_path / "priv.log"
    _script(fake / "id", '[[ $# -ge 2 ]] && echo 1000 || echo 0\n')
    _script(fake / "setpriv", 'echo "setpriv $*" >>"$FAKE_PRIV_LOG"\nshift 4\nexec "$@"\n')
    _script(fake / "chown", 'echo "chown $*" >>"$FAKE_PRIV_LOG"\n')
    return log


def test_agent_runs_opencode_as_unprivileged_user(env, tmp_path) -> None:
    log = _fake_privileged_env(env, tmp_path)
    r = _run_agent(env, tmp_path, FAKE_PRIV_LOG=str(log))
    assert r.returncode == 0, r.stderr
    lines = log.read_text().splitlines()
    assert any(ln.startswith("chown -R agent: ") and str(tmp_path) in ln for ln in lines), lines
    assert any(ln.startswith("setpriv --reuid=agent --regid=agent") and "--no-new-privs" in ln for ln in lines)
    assert json.loads((tmp_path / "out" / "metrics" / "t1.json").read_text())["opencode_exit"] == 0


def test_agent_stays_as_is_without_agent_user_or_when_not_root(env, tmp_path) -> None:
    log = _fake_privileged_env(env, tmp_path)
    assert _run_agent(env, tmp_path, FAKE_PRIV_LOG=str(log), AGENT_USER="").returncode == 0
    assert not log.exists()
    # не root: id -u даёт 1000 и без пользователя
    _script(Path(env["PATH"].split(":")[0]) / "id", "echo 1000\n")
    assert _run_agent(env, tmp_path, FAKE_PRIV_LOG=str(log)).returncode == 0
    assert not log.exists()


def _purge_env(env: dict[str, str], tmp_path: Path, **extra: str) -> dict[str, str]:
    e = _prefetch_env(env, tmp_path, PURGE_WEIGHTS="1", **extra)
    model_dir = tmp_path / "hf" / "hub" / "models--openai--gpt-oss-20b"
    model_dir.mkdir(parents=True)
    (model_dir / "weights").write_text("x")
    return e


def test_purge_weights_after_download_failure(env, tmp_path) -> None:
    e = _purge_env(env, tmp_path)
    _script(Path(env["PATH"].split(":")[0]) / "hf", "exit 1\n")
    r = _bash("run_model gpt-oss-20b; echo rc=$?", e)
    assert "rc=1" in r.stdout, r.stderr
    assert not (tmp_path / "hf" / "hub" / "models--openai--gpt-oss-20b").exists()
    info = json.loads((tmp_path / "results" / "gpt-oss-20b" / "run-info.json").read_text())
    assert info["status"] == "download_failed"


def test_purge_weights_after_vllm_failure(env, tmp_path) -> None:
    e = _purge_env(env, tmp_path)
    _script(Path(env["PATH"].split(":")[0]) / "vllm", "exit 1\n")
    Path(env["FAKE_HEALTH"]).unlink()  # сервер не отвечает, процесс сразу умер
    r = _bash("run_model gpt-oss-20b; echo rc=$?", e)
    assert "rc=1" in r.stdout, r.stderr
    assert not (tmp_path / "hf" / "hub" / "models--openai--gpt-oss-20b").exists()
    info = json.loads((tmp_path / "results" / "gpt-oss-20b" / "run-info.json").read_text())
    assert info["status"] == "vllm_failed"


def test_sigterm_marks_current_model_interrupted(env, tmp_path) -> None:
    e = _prefetch_env(env, tmp_path)
    _script(Path(env["PATH"].split(":")[0]) / "devmatrix", 'if [[ $1 == list ]]; then echo t1; exit 0; fi\nexec sleep 60\n')
    proc = subprocess.Popen(
        ["bash", "-c", f'source "{BENCH}/bench.sh"\ntrap cleanup EXIT\ntrap "exit 130" INT TERM\nrun_model gpt-oss-20b'],
        env=e, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )  # fmt: skip
    info_path = tmp_path / "results" / "gpt-oss-20b" / "run-info.json"
    for _ in range(100):
        if info_path.exists() and (tmp_path / "results" / "gpt-oss-20b" / "devmatrix.log").exists():
            break
        time.sleep(0.1)
    time.sleep(0.5)
    proc.terminate()
    proc.wait(timeout=30)
    assert json.loads(info_path.read_text())["status"] == "interrupted"


def test_download_passes_all_excludes_to_legacy_cli(env, tmp_path) -> None:
    fake = Path(env["PATH"].split(":")[0])
    log = tmp_path / "cli.log"
    _script(fake / "huggingface-cli", 'echo "$*" >>"$FAKE_CLI_LOG"\n')
    # без hf в PATH: подменяем command -v через PATH, где hf нет (системного hf в fake нет)
    e = {**env, "MODELS_TOML": str(BENCH / "models.toml"), "FAKE_CLI_LOG": str(log)}
    e["PATH"] = f"{fake}:/usr/bin:/bin"
    if shutil.which("hf", path=e["PATH"]):
        pytest.skip("в PATH есть hf")
    r = subprocess.run([str(BENCH / "download.sh"), "gpt-oss-20b"], env=e, capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr
    assert log.read_text().strip() == "download openai/gpt-oss-20b --exclude original/* metal/*"
