"""Unit tests for the binary grader."""
from genebench.grader import grade

FIELDS = [
    {"name": "idx", "type": "int", "match": "exact"},
    {"name": "beta", "type": "float", "tolerance": 0.40},
    {"name": "mean", "type": "float", "tolerance": 1.00},
]
TRUTH = {"idx": 42, "beta": 10.0, "mean": 123.0}


def _grade(idx, beta, mean):
    return grade({"answer": {"idx": idx, "beta": beta, "mean": mean}}, TRUTH, FIELDS)


def test_all_fields_pass():
    assert _grade(42, 10.3, 123.8).passed


def test_tolerance_edge_inclusive():
    assert _grade(42, 10.40, 124.00).passed       # exactly on the boundary
    assert not _grade(42, 10.41, 123.0).passed     # just outside beta tol


def test_any_field_failure_fails_run():
    assert not _grade(41, 10.0, 123.0).passed      # wrong index
    assert not _grade(42, 8.0, 123.0).passed       # beta off
    assert not _grade(42, 10.0, 130.0).passed      # mean off


def test_missing_field_fails():
    res = grade({"answer": {"idx": 42, "beta": 10.0}}, TRUTH, FIELDS)
    assert not res.passed
    assert any(f.name == "mean" and not f.passed for f in res.fields)


def test_accepts_flat_answer():
    # answer values at top level (no nested "answer" key)
    assert grade({"idx": 42, "beta": 10.0, "mean": 123.0}, TRUTH, FIELDS).passed
