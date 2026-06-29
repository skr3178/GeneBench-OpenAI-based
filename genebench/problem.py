"""Problem specification and loader for GeneBench problems.

A problem lives in a directory containing:
  meta.yaml              spec (domain, decision_points, schema, graded_fields, ...)
  prompt.txt             the minimum-viable prompt shown to the agent
  generate.py            generate(seed, outdir) -> writes staged files + truth.json
  reference_solution.py  reference_solution(data_dir) -> graded ground truth
  ablations.py           (optional) wrong-but-plausible paths for validation
"""
from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml


@dataclass
class Problem:
    id: str
    title: str
    domain: str
    decision_points: int
    directory: Path
    prompt: str
    staged_files: list[str]
    answer_file: str
    graded_fields: list[dict]
    meta: dict

    # ---- loading ------------------------------------------------------------
    @classmethod
    def load(cls, directory: str | Path) -> "Problem":
        directory = Path(directory)
        meta = yaml.safe_load((directory / "meta.yaml").read_text())
        prompt = (directory / "prompt.txt").read_text().strip()
        return cls(
            id=meta["id"],
            title=meta.get("title", meta["id"]),
            domain=meta.get("domain", "unknown"),
            decision_points=int(meta.get("decision_points", 0)),
            directory=directory,
            prompt=prompt,
            staged_files=list(meta.get("staged_files", [])),
            answer_file=meta.get("answer_file", "eval_answer.json"),
            graded_fields=list(meta.get("graded_fields", [])),
            meta=meta,
        )

    # ---- dynamic hooks ------------------------------------------------------
    def _load_callable(self, module_file: str, func_name: str) -> Callable:
        path = self.directory / module_file
        spec = importlib.util.spec_from_file_location(
            f"{self.id}_{Path(module_file).stem}", path)
        module = importlib.util.module_from_spec(spec)
        # allow intra-problem imports (e.g. ablations importing reference_solution)
        import sys
        sys.path.insert(0, str(self.directory))
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path = [p for p in sys.path if p != str(self.directory)]
        return getattr(module, func_name)

    def generate(self, seed: int, outdir: str | Path) -> dict:
        fn = self._load_callable("generate.py", "generate")
        return fn(seed=seed, outdir=str(outdir))

    def reference_solution(self, data_dir: str | Path) -> dict:
        fn = self._load_callable("reference_solution.py", "reference_solution")
        return fn(str(data_dir))

    def run_ablations(self, data_dir: str | Path) -> dict:
        fn = self._load_callable("ablations.py", "run_ablations")
        return fn(str(data_dir))

    # ---- truth --------------------------------------------------------------
    @staticmethod
    def load_truth(data_dir: str | Path) -> dict:
        return json.loads((Path(data_dir) / "truth.json").read_text())

    def graded_truth(self, data_dir: str | Path) -> dict:
        """Truth restricted to graded field names (drops diagnostics)."""
        truth = self.load_truth(data_dir)
        names = {f["name"] for f in self.graded_fields}
        return {k: v for k, v in truth.items() if k in names}
