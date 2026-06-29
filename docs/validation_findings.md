# LDL problem — blind-eval validation findings

Findings from a blind agent run on the reproduced LDL GWAS follow-up problem and
the follow-up estimator analysis. **Bottom line: the harness mechanics are sound,
but the single reproduced problem is under-validated — its grading target is a
biased, high-variance estimator, and two of its three decision points are
bypassable.** This is the paper's "extensive validation" step, which we had
skipped; a blind agent surfaced it.

## 1. The blind run

A separate (isolated, no repo/answer access) agent solved a held-out realization
(seed 80808). It produced:

- `lead_variant_index = 42` (correct)
- `lead_beta_mgdl = 10.69`
- `source_mean_untreated_ldl_mgdl = 120.97`

**Grader verdict: FAIL** — variant PASS, but β off 0.69 (> 0.40) and mean off
1.25 (> 1.00). The agent's reasoning was excellent: it cracked the genotype-QC
trap (v18/v19/v42 are one causal variant assayed three ways — dropout + HWE
artifacts), diagnosed treatment masking and selection bias, and chose to regress
**capillary LDL on genotype over the full cohort** (capillary is an unbiased
untreated proxy available for all 520, which sidesteps selection entirely).

## 2. The agent's estimator beats our "truth"

| Estimate (seed 80808) | β per allele |
|---|---|
| True generating coefficient (DGP) | 10.80 |
| Oracle (latent untreated U ~ g42, full cohort) | 10.76 |
| **Agent (capillary ~ g42, full cohort)** | **10.69** |
| **Our grader's truth (audit add-back + IPW + QC)** | **11.38** |

The agent's number is essentially the estimand; **our reference truth is the
outlier.**

## 3. Estimator-divergence analysis (30 seeds, 100–129)

| Quantity | Result |
|---|---|
| Defensible estimator (capillary-direct) within ±0.40 of **our truth** | **2 / 30** |
| mean \|capillary-direct − our truth\| | 1.97 mg/dL |
| **mean \|our truth − oracle\|** (error of our reference pipeline) | **2.00 mg/dL** |
| mean \|capillary-direct − oracle\| | **0.35 mg/dL** |

Lead variant is 42 in every seed (the QC trap is robust). But our reference
pipeline is systematically ~2 mg/dL off the estimand (up to ~5: seed 110, our
truth 15.2 vs oracle 10.3), and a defensible alternative almost never lands
inside our tolerance.

## 4. Variance decomposition (seeds 100–119)

Breaking the reference pipeline into stages, error vs the oracle:

| Estimator | mean signed error | std of error |
|---|---|---|
| add-back reconstruction on attendees (no IPW) | +0.61 | **1.52** |
| add-back + IPW (our reference truth) | +1.53 | **1.55** |

**The estimator's SD (~1.5 mg/dL) is ~4× the grading tolerance (±0.40).** The
attendee-restricted, audit-calibrated, IPW-weighted slope is inherently noisy
(offset model fit on 100 audited subjects; weighted slope on ~220 attendees).
No deterministic "correct" pipeline of this form can be graded at ±0.40 — any two
defensible implementations will disagree by far more than the tolerance.

## 5. Assessment (the three questions)

**vs. the paper's 42.4%?** Not comparable yet — our grader is miscalibrated
(truth ~2 mg/dL off the estimand), so it would fail almost every competent
analysis, giving an artificial ~0% unrelated to the paper.

**Genuinely hard / a good benchmark?** Mixed:
- The **genotype-QC trap is genuinely hard and good** — real multi-marker
  artifact reasoning; ablations fail by clear margins.
- The **treatment and selection decision points don't bite** as built: capillary
  LDL is a clean, treatment-free, full-cohort proxy, so an analyst can skip the
  audit calibration and IPW and regress capillary on genotype directly. Two of
  the three "decision points" are bypassable.
- The **grading target is wrong** (§2–4), and a good benchmark requires the data
  to "rule all but one out" with defensible analyses converging — neither holds.

**Implementation?**
- **Harness mechanics: solid.** Sandbox, agent loop, grader, runner, 17 tests —
  all correct. The machine graded a real blind agent end-to-end.
- **The LDL problem: flawed.** (i) The reference pipeline is a poor estimator
  (~2 mg/dL biased, SD ~1.5). (ii) The DGP trivializes the intended path (clean
  full-cohort capillary). The earlier "validation" on seed 7 (β=10.02 ≈ paper
  9.96) was a single lucky seed that masked a systematic problem.

## 6. The core tension (why the fix is non-trivial)

There is a real conflict between two of the paper's design constraints, as our
DGP is parameterized:

- To make **DP2 (selection / IPW) necessary**, the clean untreated signal must be
  **attendee-restricted** (so it must be transported to the invited cohort).
- But attendee-restricted, audit-calibrated estimation is **inherently
  high-variance** (~1.5 mg/dL here) → **ungradeable at ±0.40**.
- A **low-variance** estimator needs **full-cohort** clean data — but then DP2
  doesn't bite.

The paper makes ±0.40 work, so their realized "correct" estimator must be
low-variance (strong signal, mild selection, large effective N) while still
forcing the multi-stage path. Matching that requires DGP re-tuning the paper does
not fully specify.

## 7. Recommended fix (and status)

1. **Re-base the grading truth** to the genuinely-correct (oracle-consistent)
   estimator, per the paper's rule ("the MLE from the correct approach is the
   ground truth"), not our noisy pipeline output.
2. **Make the decision points bite** — re-tune the DGP so capillary is
   treatment-distorted (so capillary-direct is biased and fails), while keeping
   the correct estimator low-variance enough for ±0.40 (tune signal strength,
   selection severity, sample sizes, and/or tolerance).
3. **Re-validate across ≥30 seeds**: shortcuts/ablations fail by clear margins,
   defensible correct analyses converge within tolerance, lead always 42.

**Status: not yet fixed.** Diagnosis complete (this document). The fix is an
iterative DGP-design + validation task, in progress.
