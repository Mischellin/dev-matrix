"""Сборочный хук: кладёт в колесо задачи без эталонных решений."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

EXCLUDE = ("reference_solution", "__pycache__", ".pytest_cache", "*.pyc", ".venv")


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        staging = Path(tempfile.mkdtemp(prefix="devmatrix-tasks-")) / "tasks"
        shutil.copytree(
            Path(self.root) / "tasks", staging, ignore=shutil.ignore_patterns(*EXCLUDE)
        )
        build_data["force_include"][str(staging)] = "devmatrix/tasks"
