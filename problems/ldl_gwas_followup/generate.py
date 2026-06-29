"""Data-generating process for the LDL-C GWAS follow-up problem.

GeneBench-style multi-stage problem (inspired by the Appendix LDL case study,
re-tuned so all three decision points are genuinely necessary AND the correct
estimator is low-variance enough to grade at tight tolerance; see
docs/validation_findings.md for why the literal Appendix DGP was not gradeable).

Three decision points, each of which biases the answer if missed:
  1. Treatment masking. Capillary LDL (measured at invitation, available for ALL
     subjects) and fasting-lab LDL are both lowered by statin treatment. The
     untreated target must be reconstructed by adding back the treatment effect,
     calibrated on the audit subset (which carries historical UNTREATED LDL).
     -> a naive scan on capillary/lab is biased toward zero.
  2. Selection. The fasting-lab phenotype and the audit baseline are observed
     only for the non-random subset who attended the follow-up visit (enriched
     for high LDL). The invited-cohort estimand must be recovered on the FULL
     cohort (capillary is available for everyone); restricting to attendees is
     selection-biased.
     -> a naive analysis on attendees over-states the effect and the mean.
  3. Variant QC. Variant 18 (allele-specific dropout -> low call rate) and
     variant 19 (heterozygote miscoding -> Hardy-Weinberg violation) are degraded
     copies of the causal variant 42 and must be removed before ranking.

Staged files: cohort.tsv.gz, audit.tsv.gz, variants.tsv.gz, plus a hidden
truth.json computed by the reference solution.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

N_INVITED = 520
N_VARIANTS = 60
N_AUDIT = 150
CAUSAL_J = 42
DROPOUT_J = 18
HET_INFLATE_J = 19
PC1_DISTORTED = (6, 13)
CAP_NOISE_SD = 4.0      # capillary measurement noise (precise, but treatment-distorted)
LAB_NOISE_SD = 4.0


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def simulate(seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    n = N_INVITED

    # ---- Covariates --------------------------------------------------------
    age = np.clip(rng.normal(55.0, 7.0, n), 38.0, 78.0)
    sex = rng.integers(0, 2, n).astype(float)
    bmi = np.clip(rng.normal(27.0, 4.0, n), 17.0, 45.0)
    pc1 = rng.normal(0.0, 1.0, n)
    pc2 = rng.normal(0.0, 1.0, n)
    dist_km = np.clip(rng.normal(20.0, 8.0, n), 1.0, 60.0)
    invite_wave = rng.integers(1, 3, n).astype(int)
    wave = (invite_wave - 1).astype(float)

    # ---- Genotypes ---------------------------------------------------------
    freqs = rng.uniform(0.08, 0.45, N_VARIANTS)
    freqs[CAUSAL_J - 1] = 0.30
    G_true = np.zeros((n, N_VARIANTS))
    for j in range(N_VARIANTS):
        if (j + 1) in PC1_DISTORTED:
            p_i = np.clip(freqs[j] + 0.12 * pc1, 0.02, 0.95)
            G_true[:, j] = rng.binomial(2, p_i)
        else:
            G_true[:, j] = rng.binomial(2, freqs[j], n)
    g42 = G_true[:, CAUSAL_J - 1]
    G_true[:, DROPOUT_J - 1] = g42
    G_true[:, HET_INFLATE_J - 1] = g42

    # ---- Untreated fasting LDL-C (latent target) ---------------------------
    U = (115.0 + 0.55 * (age - 55.0) + 1.25 * (bmi - 27.0) + 2.5 * sex
         + 4.0 * pc1 + 10.8 * g42 + rng.normal(0.0, 10.0, n))

    # ---- Treatment: who is treated depends on severity; intensity does not -
    pr_S = _sigmoid(-0.95 + 0.05 * (U - 120.0) + 0.35 * sex + 0.3 * (bmi - 27.0))
    S = rng.binomial(1, pr_S).astype(float)
    intensity = np.where(S == 1, rng.uniform(0.2, 1.0, n), 0.0)   # clean treatment-intensity
    refill = np.clip(intensity + rng.normal(0.0, 0.05, n), 0.0, 1.0)
    S_star = np.where(S == 1, rng.binomial(1, 0.68, n), rng.binomial(1, 0.03, n)).astype(float)

    # treatment lowers measured LDL by an amount driven by intensity (recoverable
    # from refill once calibrated on the audit's untreated baseline)
    treat_reduction = S * (10.0 + 30.0 * intensity + rng.normal(0.0, 3.0, n))
    current = U - treat_reduction                       # treated phenotype

    # ---- Observed phenotypes ----------------------------------------------
    capillary = current + rng.normal(0.0, CAP_NOISE_SD, n)        # ALL subjects
    lab = current + rng.normal(0.0, LAB_NOISE_SD, n)             # attendees only (below)

    # ---- Non-random attendance --------------------------------------------
    C_mean, C_sd = capillary.mean(), capillary.std(ddof=0)
    zC = (capillary - C_mean) / C_sd
    pi = np.clip(_sigmoid(-0.7 + 0.85 * zC - 0.09 * (dist_km - 20.0) / 10.0
                          + 0.6 * wave + 0.35 * S_star + 0.12 * (age - 55.0) / 10.0),
                 0.04, 0.96)
    A = rng.binomial(1, pi).astype(int)

    # ---- Genotype QC artifacts (degrade copies of the causal variant) ------
    # Defined over the FULL cohort so the QC filters trigger on the analysis set.
    G_obs = G_true.copy()
    C_med = np.quantile(capillary, 0.50)
    C_q70 = np.quantile(capillary, 0.70)
    drop = (capillary > C_med) & (G_true[:, DROPOUT_J - 1] == 0)        # ~low call rate
    G_obs[:, DROPOUT_J - 1] = np.where(drop, np.nan, G_true[:, DROPOUT_J - 1])
    inflate = (capillary > C_q70) & (G_true[:, HET_INFLATE_J - 1] == 1)  # het -> hom (HWE fail)
    G_obs[:, HET_INFLATE_J - 1] = np.where(inflate, 2.0, G_true[:, HET_INFLATE_J - 1])

    # ---- Audit subset: random attendees with historical untreated LDL ------
    att_idx = np.where(A == 1)[0]
    audit_idx = np.sort(rng.choice(att_idx, size=min(N_AUDIT, att_idx.size), replace=False))

    sample_id = np.array([f"subj_{i:04d}" for i in range(n)])
    return dict(sample_id=sample_id, age=age, sex=sex, bmi=bmi, pc1=pc1, pc2=pc2,
                dist_km=dist_km, invite_wave=invite_wave, capillary=capillary,
                refill=refill, self_report=S_star, attended=A, lab=lab, U=U,
                G_obs=G_obs, audit_idx=audit_idx, freqs=freqs, seed=seed)


def _build_frames(sim):
    geno_cols = [f"v{j:02d}" for j in range(1, N_VARIANTS + 1)]
    cohort = pd.DataFrame({
        "sample_id": sim["sample_id"],
        "age": np.round(sim["age"], 2), "sex": sim["sex"].astype(int),
        "bmi": np.round(sim["bmi"], 2), "pc1": np.round(sim["pc1"], 4),
        "pc2": np.round(sim["pc2"], 4), "dist_km": np.round(sim["dist_km"], 2),
        "invite_wave": sim["invite_wave"],
        "capillary_ldl_mgdl": np.round(sim["capillary"], 2),
        "refill_proxy": np.round(sim["refill"], 4),
        "self_report_statin": sim["self_report"].astype(int),
        "attended_fasting_lab": sim["attended"].astype(int),
    })
    cohort["lab_ldl_mgdl"] = np.where(sim["attended"] == 1, np.round(sim["lab"], 2), np.nan)
    for j, col in enumerate(geno_cols):
        cohort[col] = sim["G_obs"][:, j]

    audit = pd.DataFrame({
        "sample_id": sim["sample_id"][sim["audit_idx"]],
        "baseline_ldl_mgdl": np.round(sim["U"][sim["audit_idx"]], 2),
    })
    variants = pd.DataFrame({
        "variant_index": np.arange(1, N_VARIANTS + 1),
        "variant_id": [f"rs{100000 + j}" for j in range(1, N_VARIANTS + 1)],
        "chrom": [1 + (j % 22) for j in range(N_VARIANTS)],
        "pos": np.arange(1, N_VARIANTS + 1) * 10000,
        "ref": np.repeat("A", N_VARIANTS), "alt": np.repeat("G", N_VARIANTS),
        "dosage_column": geno_cols, "alt_freq": np.round(sim["freqs"], 4),
    })
    return cohort, audit, variants


def generate(seed: int = 7, outdir=".", write_truth: bool = True) -> dict:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    sim = simulate(seed)
    cohort, audit, variants = _build_frames(sim)
    cohort.to_csv(outdir / "cohort.tsv.gz", sep="\t", index=False, compression="gzip")
    audit.to_csv(outdir / "audit.tsv.gz", sep="\t", index=False, compression="gzip")
    variants.to_csv(outdir / "variants.tsv.gz", sep="\t", index=False, compression="gzip")

    truth = None
    if write_truth:
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from reference_solution import reference_solution
        truth = reference_solution(str(outdir))
        with open(outdir / "truth.json", "w") as fh:
            json.dump(truth, fh, indent=2)
    return {"outdir": str(outdir), "seed": seed, "truth": truth}


if __name__ == "__main__":
    import argparse
    import sys
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--outdir", default="_data")
    args = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).parent))
    print(json.dumps(generate(seed=args.seed, outdir=args.outdir), indent=2))
