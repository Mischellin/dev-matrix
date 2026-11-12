from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "docker" / "vast-bench"
SCRIPTS = sorted(BENCH.glob("*.sh"))

sys.dont_write_bytecode = True  # не создавать __pycache__ в docker/vast-bench
spec = importlib.util.spec_from_file_location("vast_preset", BENCH / "preset.py")
preset = importlib.util.module_from_spec(spec)
sys.modules["vast_preset"] = preset
spec.loader.exec_module(preset)

EXPECTED_HF_IDS = {
    "openai/gpt-oss-20b",
    "mistralai/Devstral-Small-2-24B-Instruct-2512",
    "Qwen/Qwen3.8-27B-FP8",
    "CohereLabs/North-Mini-Code-1.0",
    "Kwaipilot/KAT-Coder-V2.5-Dev",
}


def _models() -> dict[str, dict]:
    return tomllib.loads((BENCH / "models.toml").read_text(encoding="utf-8"))["models"]


def test_models_toml_presets_are_complete() -> None:
    models = _models()
    assert preset.problems(models) == []
    assert {m["hf_id"] for m in models.values()} == EXPECTED_HF_IDS


def test_served_names_are_valid_devmatrix_models() -> None:
    from devmatrix import cli

    names = [m["served_name"] for m in _models().values()]
    assert len(set(names)) == len(names)
    for n in names:
        assert re.fullmatch(cli.MODEL_RE, n)
        assert cli.model_slug(n) != "unknown"


def test_serve_args_contain_parsers_and_limits() -> None:
    for key, m in _models().items():
        args = preset.serve_args(m)
        assert "--enable-auto-tool-choice" in args, key
        assert args[args.index("--tool-call-parser") + 1] == m["tool_call_parser"]
        assert args[args.index("--max-model-len") + 1] == str(m["max_model_len"])
        assert 0 < m["gpu_memory_utilization"] <= 0.95


def test_opencode_config_points_to_local_vllm() -> None:
    m = _models()["north-mini-code"]
    cfg = preset.opencode_config(m, "http://localhost:8000/v1")
    prov = cfg["provider"]["vllm"]
    assert prov["options"]["baseURL"] == "http://localhost:8000/v1"
    assert cfg["model"] == f"vllm/{m['served_name']}"
    assert prov["models"][m["served_name"]]["interleaved"] == {"field": "reasoning"}


def test_fill_claims_adds_tokens_and_cost(tmp_path) -> None:
    sub, met = tmp_path / "sub", tmp_path / "met"
    (sub / "m").mkdir(parents=True)
    met.mkdir()
    (sub / "m" / "t1.json").write_text(json.dumps({"task_id": "t1", "agent_seconds": 3600.0}))
    (met / "t1.json").write_text(json.dumps({"prompt_tokens": 100, "completion_tokens": 20}))
    assert preset.fill_claims(sub, met, 0.5, "vLLM self-hosted") == 1
    r = json.loads((sub / "m" / "t1.json").read_text())
    assert (r["tokens"], r["cost_usd"], r["provider"]) == (120, 0.5, "vLLM self-hosted")


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_scripts_pass_bash_n(script: Path) -> None:
    subprocess.run(["bash", "-n", str(script)], check=True)


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck не установлен")
@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_scripts_pass_shellcheck(script: Path) -> None:
    subprocess.run(["shellcheck", "-x", "-e", "SC1091", str(script)], check=True)


SECRET_RE = re.compile(
    r"hf_[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_\w{20,}|sk-[A-Za-z0-9]{20,}"
    r"|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|(?i:(?:token|secret|password|api_?key)\s*[=:]\s*[\"']?[A-Za-z0-9_\-]{16,})"
)


def test_no_secret_looking_strings() -> None:
    files = [p for p in BENCH.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    files.append(ROOT / ".github" / "workflows" / "vast-bench-image.yml")
    assert len(files) > 5
    for f in files:
        assert not SECRET_RE.search(f.read_text(encoding="utf-8")), f


def test_dockerfile_has_no_weights_or_secret_args() -> None:
    text = (BENCH / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"^ARG VLLM_TAG=\S+", text, re.MULTILINE)
    assert re.search(r"^ARG OPENCODE_VERSION=\d+\.\d+\.\d+", text, re.MULTILINE)
    code = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
    assert not re.search(r"HF_TOKEN|GITHUB_TOKEN|huggingface-cli download|hf download", code)
