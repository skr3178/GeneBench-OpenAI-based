# GeneBench — Open Harness Implementation Plan

## Context

`genebench.pdf` (Li & Ho, OpenAI/Herasight, Apr 2026) introduces **GeneBench**: a benchmark of
103 multi-stage genomics / quantitative-biology problems for AI agents. Each problem hands an
agent a *minimum viable prompt* plus messy *staged data files* in an isolated sandbox (standard
scientific Python, **no internet, no bioinformatics packages**). The agent must run an iterative
analysis — clean/correct data, diagnose QC and ascertainment issues, choose methods, revise when
intermediate results contradict the plan — and write a final `eval_answer.json`. Grading is
**binary**: every graded field must satisfy an exact-match or absolute-tolerance check. The
headline metric is the **unweighted mean of per-problem pass rates** over ~28 repeated runs.
Difficulty comes from cascaded **decision points** (3–13 per problem, median 6): substantive
inferential forks where a plausible wrong choice propagates downstream to a wrong graded answer.

**Why this plan exists / what we are building.** The user wants a *harness others can use to test
their own LLMs* on this style of problem. Crucial constraint: **the benchmark itself is closed** —
the 103 problems, their data generators, prompts, and graders are NOT in the paper. Only **one**
problem is fully specified: the **LDL-C GWAS follow-up** case study in the Appendix (data-generating
process eqs. 6–16, three decision points, grader targets). Therefore we cannot reproduce the
paper's *numbers*. Instead we build:

1. An **open harness** faithful to the paper's design + grading + aggregation protocol.
2. The **LDL GWAS reference problem**, fully reproduced from the Appendix, as a worked, verifiable
   example.
3. A **problem-authoring SDK** so the community can add the remaining problems and plug in any model.

This makes GeneBench-style evaluation runnable by others, with one ground-truth-checkable problem.

## Decisions (confirmed with user)

- **Sandbox:** start with **simple local execution** (subprocess in a temp workspace); add a
  Docker backend later behind the same interface.
- **Model adapter:** **Anthropic / Claude** first (native tool-use loop). Others later.
- **Scope:** this is a **plan only** — no code written yet.
- **Language:** Python 3.11; scientific stack matching the paper (numpy, pandas, scipy,
  scikit-learn, statsmodels, lifelines, matplotlib, seaborn).

## Target repository layout

```
genebench/
  pyproject.toml                 # package + deps + `genebench` CLI entrypoint
  README.md                      # what this is, what is/ isn't reproducible, quickstart
  genebench/
    __init__.py
    problem.py                   # Problem spec dataclass + loader
    grader.py                    # binary grader: exact-match + absolute tolerance
    sandbox/
      base.py                    # Sandbox interface (run_code, read/write files, manifest)
      local.py                   # LocalSandbox: subprocess in temp dir (Phase 2)
      docker.py                  # DockerSandbox: network-disabled container (later)
    agent.py                     # ReAct agent loop: prompt + manifest + schema -> eval_answer.json
    models/
      base.py                    # ModelClient interface (chat, tool-use, token accounting)
      anthropic_client.py        # Claude adapter (first)
    runner.py                    # N replicates per (problem, model); collect pass/fail + tokens
    aggregate.py                 # mean pass rate, hierarchical bootstrap CI, regimes, tokens, DP bins
    report.py                    # tables + Figure-4-style plots
    cli.py                       # genebench generate | run | grade | report
  problems/
    ldl_gwas_followup/
      meta.yaml                  # domain, decision_points=3, schema, tolerances, file manifest
      prompt.txt                 # Appendix Listing 1, verbatim
      generate.py                # DGP (eqs 6-16) -> cohort/audit/variants .tsv.gz + truth.json
      reference_solution.py      # 3-stage correct pipeline -> computes graded ground truth
      ablations.py               # wrong-but-plausible paths, to verify answer separation
      tests/test_ldl.py          # asserts truth + ablation separation (see Verification)
  docs/
    authoring.md                 # how to add a new problem (the SDK contract)
  tests/
    test_grader.py
    test_aggregate.py
```

## Phase 1 — LDL GWAS reference problem (most concrete, fully verifiable)

This is the anchor: the only problem with a published DGP and known answer, so we build it first.

**`generate.py` — data-generating process (Appendix eqs. 6–16).** Seeded RNG. N=520 invited,
60 variants, audit subset of 100 attendees, ~235 attendees.
- Covariates: `age`, `sex`, `bmi`, `pc1`, `pc2`, `dist_km`, `invite_wave` (with
  `wave = invite_wave - 1`).
- Genotypes `G_ij ~ Binomial(2, f_j)`, `f_j ∈ [0.08, 0.45]`, mild PC1-linked frequency distortion
  for variants 6 and 13. **Variant 42 is the sole causal locus.**
- Untreated LDL: `U = 115 + 0.55(age-55) + 1.25(bmi-27) + 2.5·sex + 4·PC1 + 10.8·G_42 + N(0,10²)`.
- Capillary proxy `C = U + N(0,8²)`; treatment `Pr(S=1)=logit⁻¹[-0.95+0.05(U-120)+0.35 sex+0.3(bmi-27)]`.
- Refill proxy `R̃ ~ N(0.65 S + 0.25 (U-120)/20 + 0.08 sex, 0.22²)`, `R = clip(R̃, 0, 1)`.
- Self-report `S* ~ Bernoulli(0.68 if S=1 else 0.03)`.
- Observed lab `L = U - S·(16 + 24R + N(0,4²)) + N(0,6²)` (attendees only).
- Attendance `π̃ = logit⁻¹[-0.7 + 0.85 z(C) - 0.09 (dist-20)/10 + 0.6 wave + 0.35 S* + 0.12 (age-55)/10]`,
  `Pr(A=1)=clip(π̃, 0.04, 0.96)`.
- Two built-in QC failures on the genotype panel: **variant 18** = G_42 but dropped to NA when
  `A=1 & C>median(C) & G̃18=0` (allele-specific dropout, attendee call rate ≈0.85); **variant 19**
  = G_42 but miscoded to 2 when `A=1 & C>Q0.78 & G̃19=1` (het inflation, HWE p≈5e-7).
- **Staged outputs** (named/structured exactly as Appendix Table 1 + p.7):
  - `cohort.tsv.gz` — 520 invitees: `sample_id`, `age, sex, bmi, pc1, pc2, dist_km, invite_wave`,
    `capillary_ldl_mgdl`, `refill_proxy`, `self_report_statin`, `attended_fasting_lab`,
    `lab_ldl_mgdl` (attendees only), genotype dosage columns `v01`–`v60`.
  - `audit.tsv.gz` — 100 audited attendees: `sample_id`, `baseline_ldl_mgdl` (= historical
    untreated LDL `U`).
  - `variants.tsv.gz` — 60 rows mapping `v01`–`v60` to 1-based `variant_index` + metadata.
  - `truth.json` — **not staged to the agent**; ground truth for the grader, computed by
    `reference_solution.py` on the generated data (the paper's "recoverable realized-data target").

**`reference_solution.py` — the 3 decision points (Appendix eqs. 17, 18–23).**
1. **Reconstruct untreated LDL:** regression calibration on the 100-row audit subset,
   `U ~ L + R + S* + age + sex + bmi`; predict `Û` for all attendees. (Minimal sufficient
   predictor set is `{L, R, C}`; demographics/S* are defensible additions.)
2. **IPW reweighting:** logistic `π̂ = Pr(A=1 | Z)` fit on all 520, `Z = {C, age, bmi, sex, dist,
   wave, PC1, S*}`; stabilized weights `w = Ā/π̂`, with `π̂` clipped to [0.05, 0.95] and weights
   trimmed at the 1st/99th percentiles.
3. **Variant QC on attendees:** keep `callrate ≥ 0.95` AND `HWE p ≥ 1e-6` → drops variants 18 and 19.
- **Final scan:** weighted additive regression `Û ~ G_j + X` on attendees (`X = age, sex, bmi, pc1,
  pc2`); lead = QC-passing variant with smallest p; report 1-based index, its per-allele β, and
  the weighted mean `Û`.

**`meta.yaml` — graded answer schema (Appendix Listing 1) + tolerances.**
- Schema: `{"answer": {"lead_variant_index": int, "lead_beta_mgdl": float,
  "source_mean_untreated_ldl_mgdl": float}, "reasoning": str}`.
- Tolerances: `lead_variant_index` exact; `lead_beta_mgdl` ±0.40 mg/dL; `source_mean_untreated_ldl_mgdl`
  ±1.00 mg/dL. `decision_points: 3`, `domain: statistical genetics`.

**`ablations.py` — wrong-but-plausible paths (must fail grading), reproducing the Appendix:**
naive scan on observed lab (β≈4.56), skip-all-QC (variant 18 leads, β≈13.23), skip-HWE (variant 19
leads, β≈9.30), calibrate-but-no-IPW (β≈8.28 / mean overshoots by ~6.6). These exercise the
grader's *answer separation* requirement.

## Phase 2 — Harness core

- **`problem.py`** — `Problem` spec: id, domain, prompt text, staged-file manifest, answer JSON
  schema, list of graded fields with `(type, tolerance)`, `decision_points`, path to a `generate`
  hook and a hidden `truth.json`. A loader reads a problem directory (`meta.yaml` + assets).
- **`grader.py`** — `grade(answer, truth, fields) -> {passed: bool, per_field: {...}}`. A run passes
  **iff all graded fields pass**: ints/strings exact-match; floats within absolute tolerance. Mirrors
  Methods ("pre-specified problem-specific target fields, exact-match rules, absolute tolerances").
- **`sandbox/local.py`** — `LocalSandbox`: per-run temp workspace, staged files copied in
  read-only, agent code run via subprocess with the scientific stack, captured stdout/stderr,
  wall-clock guard. Network is *not* hard-blocked in local mode (documented caveat); the Docker
  backend (`sandbox/docker.py`, later) adds `--network none` + the pinned image for faithful isolation.
- **`agent.py`** — ReAct loop. Initial messages in the paper's order: (1) system message describing
  the container/Python environment, (2) the problem prompt, (3) the JSON-schema + free-form
  `reasoning` requirement, (4) an enumeration of mounted file paths. Single tool: execute
  Python/bash in the sandbox; loop until the agent writes `eval_answer.json` or hits a step cap.
- **`runner.py`** — runs N replicate attempts per `(problem, model)`, grades each, records
  pass/fail, token counts, and validity (drop <1% invalid-trace runs, per Methods).

## Phase 3 — Model adapter + metrics

- **`models/anthropic_client.py`** — Claude tool-use loop conforming to `models/base.py`
  (`chat(messages, tools) -> (text, tool_calls, usage)`); token accounting = full reasoning trace +
  final response, excluding tool-call payloads (matches "Avg. tokens" definition). *(Before writing
  this, consult the latest Anthropic model IDs / tool-use API via the `claude-api` skill.)*
- **`aggregate.py`** — exactly the paper's metrics:
  - **Mean pass rate** = unweighted mean of per-problem pass rates.
  - **95% hierarchical bootstrap CI**: 20,000 resamples; resample problems, then runs *within* each
    sampled problem (matches Figure 4A / Supp. Table 2).
  - **Regime distribution**: share of problems at `0%`, `>0–10%`, `>10–50%`, `≥50%` pass rate.
  - **Avg tokens**, **mean/min/max reps** per problem.
  - **Pass rate vs. decision points** binned `3–4 / 5 / 6 / 7+` (Supp. Fig. 2).
- **`report.py`** — renders the Supp.-Table-2-style table and Figure-4-style plots (A overall bars
  with CIs, B regime stacks, C pass-rate-vs-tokens).

## Phase 4 — Authoring SDK + docs

- **`docs/authoring.md`** — the contract for adding a problem: directory layout, `meta.yaml` fields,
  the `generate.py` (RNG-seeded → staged files + `truth.json`) and `reference_solution.py` hooks,
  schema/tolerance conventions, and the design principles from Table 1 (recoverable target, unique
  identifiable answer, clear separation from incorrect answers, minimal viable prompt, threshold-
  robust QC, constructive staging).
- `genebench/cli.py` — `generate <problem>` (build staged data + truth), `run <problem> --model ...
  --reps N`, `grade`, `report`.

## Verification

- **Phase 1 (decisive, runs offline, no model needed):**
  - `generate.py` with a fixed seed produces the three `.tsv.gz` files with the right shapes
    (cohort 520×~70, audit 100×2, variants 60) and the engineered artifacts present (variant 18
    attendee call rate ≈0.85; variant 19 HWE p ≈5e-7).
  - `reference_solution.py` on that data yields **lead variant = 42**, **β ≈ 9.96 (±~0.4 across
    seeds)**, **mean ≈ 123** — i.e. near the paper's 9.96 / 123.09, validating the DGP transcription.
  - `ablations.py`: every wrong path lands **outside** tolerance vs. the computed truth (naive ≈4.56,
    skip-QC variant 18, skip-HWE variant 19, no-IPW mean overshoot) → confirms answer separation.
  - `tests/test_ldl.py` encodes all of the above as asserts.
- **Phase 2:** `tests/test_grader.py` (all-fields-pass logic, tolerance edges) and a smoke test that
  `LocalSandbox` runs the reference solution as if it were agent-submitted code and grades it `pass`.
- **Phase 3:** end-to-end `genebench run ldl_gwas_followup --model <claude> --reps 3`; confirm the
  loop reads files, executes code, writes a schema-valid `eval_answer.json`, and grades it;
  `aggregate.py` reproduces a hierarchical-bootstrap CI on synthetic pass/fail matrices that matches
  a hand-computed reference.
- **Cross-check vs. paper:** our LDL ground truth should sit within a few tenths of variant 42 /
  9.96 / 123.09; any larger gap flags a DGP transcription error to fix before proceeding.

## Out of scope / explicitly not reproducible

- The other 102 problems (closed; not in the paper) — the SDK enables the community to add them.
- The paper's reported per-model pass-rate numbers (depend on closed problems + provider behavior).
- Docker sandbox and non-Anthropic adapters are deferred (interfaces are designed to accept them).
