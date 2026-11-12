from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_generator_output_equals_committed_readme() -> None:
    spec = importlib.util.spec_from_file_location("generate_readme", ROOT / "scripts" / "generate_readme.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.build_readme() == (ROOT / "README.md").read_text(encoding="utf-8")
