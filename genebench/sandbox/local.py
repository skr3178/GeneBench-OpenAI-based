"""Local subprocess sandbox.

Runs agent-authored code in a temporary workspace using the harness's own
Python interpreter (so the scientific stack is available). This is the simple
first backend: it does NOT hard-block network access or strictly enforce
read-only staged files. A Docker backend (``--network none`` + pinned image)
will provide stronger isolation behind the same interface.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from genebench.sandbox.base import ExecResult

DEFAULT_TIMEOUT = 180.0


class LocalSandbox:
    def __init__(self, workspace: str | Path | None = None,
                 python_executable: str = sys.executable,
                 default_timeout: float = DEFAULT_TIMEOUT):
        self._owns_workspace = workspace is None
        self.workspace = Path(workspace) if workspace else Path(tempfile.mkdtemp(prefix="gb_ws_"))
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.python_executable = python_executable
        self.default_timeout = default_timeout

    # ---- setup --------------------------------------------------------------
    def setup(self, staged_files: list[tuple[Path, str]]) -> None:
        for src, dest_name in staged_files:
            dest = self.workspace / dest_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    # ---- execution ----------------------------------------------------------
    def _run(self, args: list[str], timeout: float | None) -> ExecResult:
        try:
            proc = subprocess.run(
                args, cwd=str(self.workspace), capture_output=True, text=True,
                timeout=timeout or self.default_timeout,
            )
            return ExecResult(proc.stdout, proc.stderr, proc.returncode)
        except subprocess.TimeoutExpired as e:
            return ExecResult(e.stdout or "", e.stderr or "", -1, timed_out=True)

    def run_python(self, code: str, timeout: float | None = None) -> ExecResult:
        script = self.workspace / "_agent_snippet.py"
        script.write_text(code)
        return self._run([self.python_executable, str(script)], timeout)

    def run_bash(self, command: str, timeout: float | None = None) -> ExecResult:
        return self._run(["bash", "-lc", command], timeout)

    # ---- files --------------------------------------------------------------
    def read_file(self, name: str) -> str | None:
        path = self.workspace / name
        if not path.exists():
            return None
        return path.read_text()

    def exists(self, name: str) -> bool:
        return (self.workspace / name).exists()

    def list_files(self) -> list[str]:
        return sorted(p.name for p in self.workspace.iterdir() if p.is_file())

    def cleanup(self) -> None:
        if self._owns_workspace and self.workspace.exists():
            shutil.rmtree(self.workspace, ignore_errors=True)
