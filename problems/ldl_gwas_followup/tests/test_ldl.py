"""End-to-end verification for the LDL-C GWAS follow-up reference problem.

Validates (no LLM required):
  * the DGP transcription recovers the paper's realized target (variant 42,
    per-allele effect near 9.96 mg/dL, invited-cohort mean near 123 mg/dL),
  * the engineered QC artifacts are present (v18 low call rate, v19 HWE failure),
  * the reference solution PASSES the binary grader,
  * every wrong-but-plausible ablation FAILS the grader (answer separation).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from genebench.grader import grade
from genebench.problem import Problem

PROBLEM_DIR = Path(__file__).resolve().parents[1]
SEED = 7


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    data_dir = tmp_path_factory.mktemp("ldl_data")
    problem = Problem.load(PROBLEM_DIR)
    problem.generate(seed=SEED, outdir=data_dir)
    truth = problem.graded_truth(data_dir)
    full_truth = Problem.load_truth(data_dir)
    return problem, data_dir, truth, full_truth


def test_ground_truth_is_sane(prepared):
    _, _, truth, full = prepared
    assert truth["lead_variant_index"] == 42
    # realized per-allele effect near the causal coefficient (10.8 mg/dL)
    assert 9.0 <= truth["lead_beta_mgdl"] <= 13.0
    # invited-cohort mean untreated LDL in a plausible range
    assert 118.0 <= truth["source_mean_untreated_ldl_mgdl"] <= 126.0
    # engineered QC artifacts present (full-cohort)
    diag = full["_diagnostics"]
    assert diag["call_rate_v18"] < 0.95          # fails call-rate QC
    assert diag["hwe_p_v19"] < 1e-6              # fails Hardy-Weinberg QC
    assert diag["n_qc_pass"] == 58               # 60 - 2 corrupted


def test_reference_solution_passes(prepared):
    problem, data_dir, truth, _ = prepared
    answer = {"answer": problem.reference_solution(data_dir), "reasoning": "reference"}
    result = grade(answer, truth, problem.graded_fields)
    assert result.passed, result.to_dict()


@pytest.mark.parametrize("name", ["capillary_direct", "attendee_only", "naive_lab",
                                  "skip_qc", "skip_hwe"])
def test_ablations_fail(prepared, name):
    problem, data_dir, truth, _ = prepared
    ablations = problem.run_ablations(data_dir)
    answer = {"answer": ablations[name], "reasoning": name}
    result = grade(answer, truth, problem.graded_fields)
    assert not result.passed, f"ablation {name} unexpectedly passed: {result.to_dict()}"


def test_determinism(prepared, tmp_path):
    problem, _, _, full = prepared
    problem.generate(seed=SEED, outdir=tmp_path)
    again = Problem.load_truth(tmp_path)
    assert again["lead_variant_index"] == full["lead_variant_index"]
    assert again["lead_beta_mgdl"] == full["lead_beta_mgdl"]
