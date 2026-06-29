"""Sandbox interface for executing agent-authored code against staged data.

The harness mounts a problem's staged files into a sandbox workspace, lets the
agent execute code there, and reads back the ``eval_answer.json`` it produces.
LocalSandbox (subprocess) is the first backend; a network-disabled Docker
backend can implement the same interface later.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class ExecResult:
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool = False

    def format(self, max_chars: int = 12000) -> str:
        out = []
        if self.timed_out:
            out.append("[execution timed out]")
        out.append(f"[exit code: {self.returncode}]")
        if self.stdout:
            out.append("--- stdout ---\n" + self.stdout)
        if self.stderr:
            out.append("--- stderr ---\n" + self.stderr)
        text = "\n".join(out)
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n... [truncated, {len(text)} chars total]"
        return text


class Sandbox(Protocol):
    workspace: Path

    def setup(self, staged_files: list[tuple[Path, str]]) -> None:
        """Copy ``(src_path, dest_name)`` files into the workspace."""

    def run_python(self, code: str, timeout: float | None = None) -> ExecResult: ...

    def run_bash(self, command: str, timeout: float | None = None) -> ExecResult: ...

    def read_file(self, name: str) -> str | None: ...

    def exists(self, name: str) -> bool: ...

    def cleanup(self) -> None: ...
