#!/usr/bin/env python3
"""Помощник bench.sh: читает models.toml, собирает аргументы vllm, конфиг OpenCode и run-info.json."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODELS_TOML = Path(os.environ.get("MODELS_TOML", HERE / "models.toml"))
REQUIRED = {
    "hf_id": str,
    "served_name": str,
    "max_model_len": int,
    "gpu_memory_utilization": float,
    "min_gpu_gb": int,
    "dtype": str,
    "tool_call_parser": str,
    "extra_args": list,
    "download_exclude": list,
    "notes": str,
}
OPTIONAL = {"quantization": str, "reasoning_parser": str, "interleaved_field": str}
PROVIDER_ID = "vllm"


def load() -> dict[str, dict]:
    return tomllib.loads(MODELS_TOML.read_text(encoding="utf-8"))["models"]


def preset(key: str) -> dict:
    models = load()
    if key not in models:
        sys.exit(f"Нет пресета {key!r}. Доступны: {', '.join(models)}")
    return models[key]


def problems(models: dict[str, dict]) -> list[str]:
    errs = []
    for key, m in models.items():
        for field, typ in REQUIRED.items():
            if not isinstance(m.get(field), typ) or isinstance(m.get(field), bool):
                errs.append(f"{key}: поле {field} отсутствует или не {typ.__name__}")
        for field, typ in OPTIONAL.items():
            if field in m and not isinstance(m[field], typ):
                errs.append(f"{key}: поле {field} не {typ.__name__}")
        unknown = set(m) - set(REQUIRED) - set(OPTIONAL)
        if unknown:
            errs.append(f"{key}: неизвестные поля {sorted(unknown)}")
    return errs


def serve_args(m: dict) -> list[str]:
    a = [
        "--served-model-name", m["served_name"],
        "--max-model-len", str(m["max_model_len"]),
        "--gpu-memory-utilization", str(m["gpu_memory_utilization"]),
        "--dtype", m["dtype"],
        "--enable-auto-tool-choice",
        "--tool-call-parser", m["tool_call_parser"],
    ]  # fmt: skip
    if m.get("quantization"):
        a += ["--quantization", m["quantization"]]
    if m.get("reasoning_parser"):
        a += ["--reasoning-parser", m["reasoning_parser"]]
    return a + list(m["extra_args"])


def opencode_config(m: dict, base_url: str) -> dict:
    model: dict = {
        "name": m["served_name"],
        "limit": {"context": m["max_model_len"], "output": min(16384, m["max_model_len"] // 4)},
    }
    if m.get("interleaved_field"):
        model["interleaved"] = {"field": m["interleaved_field"]}
    return {
        "$schema": "https://opencode.ai/config.json",
        "model": f"{PROVIDER_ID}/{m['served_name']}",
        "autoupdate": False,
        "share": "disabled",
        "provider": {
            PROVIDER_ID: {
                "npm": "@ai-sdk/openai-compatible",
                "name": "Local vLLM",
                "options": {"baseURL": base_url, "apiKey": "EMPTY"},
                "models": {m["served_name"]: model},
            }
        },
    }


def _out(cmd: list[str]) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return r.stdout.strip()


def run_info(key: str, path: Path, status: str) -> None:
    m = preset(key)
    info = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    gpu = _out(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"])
    info.update(
        {
            "preset": key,
            "status": status,
            "hf_id": m["hf_id"],
            "served_name": m["served_name"],
            "vllm_args": serve_args(m),
            "vllm_tag": os.environ.get("VLLM_TAG", "unknown"),
            "vllm_version": (_out(["vllm", "--version"]).splitlines() or ["unknown"])[-1],
            "opencode_version": _out(["opencode", "--version"]),
            "image_revision": os.environ.get("IMAGE_REVISION", "unknown"),
            "image_digest": os.environ.get("IMAGE_DIGEST", "unknown"),
            "gpu": gpu.splitlines(),
            "gpu_price_usd_hour": os.environ.get("GPU_PRICE_USD_HOUR") or None,
            "model_notes": m["notes"],
        }
    )
    info.setdefault("started_at", now)
    if status != "running":
        info["finished_at"] = now
    path.write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fill_claims(sub_dir: Path, metrics_dir: Path, price: float | None, provider: str) -> int:
    """Дописывает в отчёты devmatrix токены (из дельт /metrics vLLM) и цену GPU-часов."""
    n = 0
    for f in sorted(sub_dir.rglob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        r["provider"] = provider
        mf = metrics_dir / f"{r['task_id']}.json"
        if mf.is_file():
            t = json.loads(mf.read_text(encoding="utf-8"))
            r["tokens"] = int(t["prompt_tokens"]) + int(t["completion_tokens"])
        if price is not None:
            r["cost_usd"] = round(r["agent_seconds"] / 3600 * price, 4)
        f.write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        n += 1
    return n


def main(argv: list[str]) -> int:
    cmd, *a = argv or ["help"]
    if cmd == "list":
        for k, m in load().items():
            print(f"{k:22} {m['hf_id']:48} >= {m['min_gpu_gb']} ГБ")
    elif cmd == "get":  # get <key> <field>
        v = preset(a[0]).get(a[1], "")
        print("\n".join(map(str, v)) if isinstance(v, list) else v)
    elif cmd == "serve-args":
        print("\n".join(serve_args(preset(a[0]))))
    elif cmd == "opencode-config":  # opencode-config <key> <base_url>
        print(json.dumps(opencode_config(preset(a[0]), a[1]), indent=2, ensure_ascii=False))
    elif cmd == "run-info":  # run-info <key> <file> <status>
        run_info(a[0], Path(a[1]), a[2])
    elif cmd == "fill-claims":  # fill-claims <submissions> <metrics> <price|-> <provider>
        price = None if a[2] in ("", "-") else float(a[2])
        print(f"Отчётов дополнено: {fill_claims(Path(a[0]), Path(a[1]), price, a[3])}")
    elif cmd == "check":
        errs = problems(load())
        print("\n".join(errs) or "ok")
        return 1 if errs else 0
    else:
        print("usage: preset.py list|get|serve-args|opencode-config|run-info|fill-claims|check")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
