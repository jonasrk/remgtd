"""The only module that runs RemCTL. remgtd only ever calls read commands."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


class RemctlError(RuntimeError):
    """RemCTL is missing, failed, or returned something unreadable."""


def find_remctl(configured: str = "") -> str:
    candidates = []
    if configured:
        candidates.append(Path(configured).expanduser())
    on_path = shutil.which("remctl")
    if on_path:
        candidates.append(Path(on_path))
    candidates += [Path.home() / "bin" / "remctl", Path.home() / ".local" / "bin" / "remctl"]
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    raise RemctlError(
        "remctl not found. Install RemCTL (https://github.com/viticci/remctl) "
        "or set `remctl` in the config."
    )


class Remctl:
    def __init__(self, path: str, timeout: float = 60.0) -> None:
        self.path = path
        self.timeout = timeout

    def json(self, *args: str) -> Any:
        env = {**os.environ, "REMCTL_SKIP_ONBOARD": "1"}
        try:
            proc = subprocess.run(
                [self.path, *args],
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=self.timeout,
                env=env,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RemctlError(f"remctl {' '.join(args)}: {exc}") from exc
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip().splitlines()
            raise RemctlError(f"remctl {' '.join(args)} failed: {detail[-1] if detail else proc.returncode}")
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise RemctlError(f"remctl {' '.join(args)}: output is not JSON") from exc

    def export(self) -> list[dict[str, Any]]:
        return self.json("--format", "json", "export")

    def lists(self) -> list[dict[str, Any]]:
        return self.json("--format", "json", "lists")

    def smart_lists(self) -> list[dict[str, Any]]:
        return self.json("smart-lists", "--json")

    def show(self, list_name: str) -> list[dict[str, Any]]:
        return self.json("--format", "json", "show", list_name)
