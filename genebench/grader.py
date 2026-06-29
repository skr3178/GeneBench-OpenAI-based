"""Binary grader for GeneBench problems.

A run passes iff EVERY graded field satisfies its check (Methods: "pre-specified
problem-specific target fields, exact-match rules, and absolute numeric
tolerances. A run is counted as passing only if all graded fields satisfied
their respective constraints").

Field check rules (from a problem's ``meta.yaml`` ``graded_fields``):
  - match: exact            -> int/str equality (and exact float equality)
  - tolerance: <float>      -> abs(estimate - truth) <= tolerance
"""
from __future__ import annotations

from dataclasses import dataclass, field as _field
from typing import Any


@dataclass
class FieldResult:
    name: str
    passed: bool
    estimate: Any
    truth: Any
    reason: str


@dataclass
class GradeResult:
    passed: bool
    fields: list[FieldResult] = _field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "fields": [
                {"name": f.name, "passed": f.passed, "estimate": f.estimate,
                 "truth": f.truth, "reason": f.reason}
                for f in self.fields
            ],
        }


def _coerce_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def grade_field(spec: dict, estimate: Any, truth: Any) -> FieldResult:
    name = spec["name"]
    ftype = spec.get("type", "float")
    tol = spec.get("tolerance")
    exact = spec.get("match") == "exact" or tol is None

    if estimate is None:
        return FieldResult(name, False, estimate, truth, "missing field in answer")

    if ftype == "int" or (exact and ftype != "float"):
        try:
            ok = int(estimate) == int(truth) if ftype == "int" else estimate == truth
        except (TypeError, ValueError):
            ok = estimate == truth
        return FieldResult(name, ok, estimate, truth,
                           "exact match" if ok else "exact mismatch")

    if exact:  # exact float / string
        ok = estimate == truth
        return FieldResult(name, ok, estimate, truth,
                           "exact match" if ok else "exact mismatch")

    est = _coerce_number(estimate)
    tru = _coerce_number(truth)
    if est is None or tru is None:
        return FieldResult(name, False, estimate, truth, "non-numeric value")
    delta = abs(est - tru)
    ok = delta <= tol + 1e-12
    return FieldResult(name, ok, estimate, truth,
                       f"|{est:.4g} - {tru:.4g}| = {delta:.4g} {'<=' if ok else '>'} {tol}")


def grade(answer: dict, truth: dict, graded_fields: list[dict]) -> GradeResult:
    """Grade an agent ``answer`` against ``truth`` using the field specs.

    ``answer`` is the parsed eval_answer.json; the graded values are read from
    ``answer['answer']`` if present, else from ``answer`` directly.
    """
    values = answer.get("answer", answer) if isinstance(answer, dict) else {}
    results = [grade_field(spec, values.get(spec["name"]), truth.get(spec["name"]))
               for spec in graded_fields]
    return GradeResult(passed=all(r.passed for r in results), fields=results)
