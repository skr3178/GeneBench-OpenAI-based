# GeneBench (open harness)

An open, runnable harness in the spirit of **GeneBench** (Li & Ho, 2026) — a
benchmark for AI agents on realistic, multi-stage scientific data analysis in
genetics and quantitative biology. Each problem gives an agent a sparse prompt
plus messy, synthetically-generated data files; the agent must work through a
chain of dependent **decision points** (data cleaning, QC, bias correction,
method choice) and write a final `eval_answer.json`, which is **binary-graded**
against a recoverable ground truth under absolute tolerances.

> **Scope / honesty.** The original GeneBench benchmark (103 problems) is closed:
> the paper releases the full data-generating process for **exactly one** problem
> (the LDL-C GWAS follow-up case study). This repo therefore provides (1) a
> faithful harness implementing the paper's design + grading, and (2) that one
> problem fully reproduced and verified against the paper's reported answer. The
> problem-authoring contract lets you add more problems (see `docs/authoring.md`).

## What works today

- **Reference problem `ldl_gwas_followup`** — the Appendix case study, fully
  reproduced from the data-generating equations (6–16). Three decision points:
  1. reconstruct untreated LDL-C from the audit subset (treatment add-back),
  2. reweight attendees to the invited cohort with stabilized IPW,
  3. variant QC (call-rate + Hardy–Weinberg) before the association scan.
  Recovers **variant 42, β ≈ 10.0 mg/dL** (paper 9.96), invited-cohort mean
  ≈ 122 (paper 123.09). All four wrong-path ablations fail grading.
- **Harness core** — `Problem` spec/loader, binary `grade()`, and a CLI.

## Quickstart

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e .

# generate staged data + hidden ground truth for the reference problem
genebench generate ldl_gwas_followup --outdir _data

# inspect the agent-visible inputs
ls _data            # cohort.tsv.gz  audit.tsv.gz  variants.tsv.gz  (+ truth.json, hidden)

# run the reference solution and grade it; check ablations all fail
genebench verify ldl_gwas_followup
```

Grade an arbitrary answer file:

```bash
genebench grade ldl_gwas_followup _data my_eval_answer.json
```

## Tests

```bash
# (if your shell injects PYTHONPATH, e.g. ROS, prefix to isolate plugins)
PYTHONPATH= PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest
```

## Layout

```
genebench/            harness: problem.py, grader.py, cli.py  (sandbox/agent: WIP)
problems/
  ldl_gwas_followup/  meta.yaml, prompt.txt, generate.py,
                      reference_solution.py, ablations.py, tests/
tests/                harness unit tests
PLAN.md               full implementation plan and problem inventory
```

## Roadmap

- Local execution sandbox + agent loop (Anthropic/Claude adapter first), then Docker.
- Aggregation/metrics matching the paper (mean pass rate, hierarchical bootstrap
  CIs, regime distribution, pass-rate vs decision-points).
- Additional authored problems via the SDK.
