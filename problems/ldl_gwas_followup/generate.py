"""Data-generating process for the LDL-C GWAS follow-up problem.

Faithful transcription of the data-generating process in the GeneBench Appendix
(Li & Ho, 2026), equations (6)-(16). The simulation produces three agent-visible
staged files and a hidden ground-truth file:

    cohort.tsv.gz    520 invited subjects, covariates, treatment proxies,
                     capillary LDL, attendee-only fasting-lab LDL, genotypes v01-v60
    audit.tsv.gz     100 audited attendees with historical untreated LDL (baseline)
    variants.tsv.gz  60 variants, 1-based variant_index, metadata
    truth.json       graded ground truth, computed by the reference solution on
                     the staged files (NOT staged to the agent)

Variant 42 is the sole causal locus. Variants 18 and 19 are genetically identical
to variant 42 but carry engineered QC artifacts (allele-specific dropout and
heterozygote inflation, respectively) so that a valid analysis must apply both a
call-rate and a Hardy-Weinberg filter before the final association scan.

The covariate distributions are not pinned by the paper; we choose centered,
realistic distributions consistent with the equations (age~55, BMI~27, etc.).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

N_INVITED = 520
N_VARIANTS = 60
N_AUDIT = 100
CAUSAL_J = 42          # 1-based causal variant index
DROPOUT_J = 18         # 1-based variant with allele-specific dropout (call-rate QC)
HET_INFLATE_J = 19     # 1-based variant with heterozygote inflation (HWE QC)

# 1-based indices with mild PC1-linked allele-frequency distortion (eq. 6).
PC1_DISTORTED = (6, 13)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def simulate(seed: int = 7) -> dict:
    """Run the full DGP and return a dict of latent + observed arrays/frames."""
    rng = np.random.default_rng(seed)
    n = N_INVITED

    # ---- Covariates (centered to match the equation offsets) -----------------
    age = np.clip(rng.normal(55.0, 7.0, n), 38.0, 78.0)
    sex = rng.integers(0, 2, n).astype(float)            # 0/1
    bmi = np.clip(rng.normal(27.0, 4.0, n), 17.0, 45.0)
    pc1 = rng.normal(0.0, 1.0, n)
    pc2 = rng.normal(0.0, 1.0, n)
    dist_km = np.clip(rng.normal(20.0, 8.0, n), 1.0, 60.0)
    invite_wave = rng.integers(1, 3, n).astype(int)      # 1 or 2
    wave = (invite_wave - 1).astype(float)               # 0/1 (eq. 13)

    # ---- Genotypes G_ij ~ Binomial(2, f_j), f_j in [0.08, 0.45] (eq. 6) -------
    freqs = rng.uniform(0.08, 0.45, N_VARIANTS)
    freqs[CAUSAL_J - 1] = 0.30                            # set so cohort mean ~123
    G_true = np.zeros((n, N_VARIANTS), dtype=float)
    for j in range(N_VARIANTS):
        jj = j + 1
        if jj in PC1_DISTORTED:
            # mild PC1-linked frequency distortion -> population structure that
            # induces spurious association unless PC1 is adjusted for.
            p_i = np.clip(freqs[j] + 0.12 * pc1, 0.02, 0.95)
            G_true[:, j] = rng.binomial(2, p_i)
        else:
            G_true[:, j] = rng.binomial(2, freqs[j], n)

    g42 = G_true[:, CAUSAL_J - 1]
    # Variants 18 and 19 are genetically identical to the causal variant 42.
    G_true[:, DROPOUT_J - 1] = g42
    G_true[:, HET_INFLATE_J - 1] = g42

    # ---- Untreated fasting LDL-C, single causal locus (eq. 7) ----------------
    eps = rng.normal(0.0, 10.0, n)
    U = (115.0
         + 0.55 * (age - 55.0)
         + 1.25 * (bmi - 27.0)
         + 2.5 * sex
         + 4.0 * pc1
         + 10.8 * g42
         + eps)

    # ---- Capillary proxy measured at invitation (eq. 8) ----------------------
    C = U + rng.normal(0.0, 8.0, n)

    # ---- Treatment as a function of latent untreated burden (eq. 9) ----------
    pr_S = _sigmoid(-0.95 + 0.05 * (U - 120.0) + 0.35 * sex + 0.3 * (bmi - 27.0))
    S = rng.binomial(1, pr_S).astype(float)

    # ---- Refill proxy for medication intensity (eq. 10) ----------------------
    R_tilde = rng.normal(0.65 * S + 0.25 * (U - 120.0) / 20.0 + 0.08 * sex, 0.22)
    R = np.clip(R_tilde, 0.0, 1.0)

    # ---- Imperfect self-report of statin use (eq. 11) ------------------------
    S_star = np.where(S == 1,
                      rng.binomial(1, 0.68, n),
                      rng.binomial(1, 0.03, n)).astype(float)

    # ---- Observed fasting-lab LDL-C, treatment-compressed (eq. 12) -----------
    zeta = rng.normal(0.0, 4.0, n)
    xi = rng.normal(0.0, 6.0, n)
    L = U - S * (16.0 + 24.0 * R + zeta) + xi

    # ---- Non-random attendance at the fasting-lab visit (eqs. 13-14) ---------
    C_mean, C_sd = C.mean(), C.std(ddof=0)
    zC = (C - C_mean) / C_sd
    pi_tilde = _sigmoid(-0.7
                        + 0.85 * zC
                        - 0.09 * (dist_km - 20.0) / 10.0
                        + 0.6 * wave
                        + 0.35 * S_star
                        + 0.12 * (age - 55.0) / 10.0)
    pi = np.clip(pi_tilde, 0.04, 0.96)
    A = rng.binomial(1, pi).astype(int)

    # ---- Observed genotype panel with two engineered QC failures -------------
    # The agent sees observed dosages; v18/v19 are corrupted, others are clean.
    G_obs = G_true.copy()

    C_med = np.quantile(C, 0.50)
    C_q78 = np.quantile(C, 0.78)

    # eq. 15: allele-specific dropout -> NA among high-LDL attendees with G18 == 0.
    drop_mask = (A == 1) & (C > C_med) & (G_true[:, DROPOUT_J - 1] == 0)
    G_obs[:, DROPOUT_J - 1] = np.where(drop_mask, np.nan, G_true[:, DROPOUT_J - 1])

    # eq. 16: heterozygote inflation -> code het as 2 among very-high-LDL attendees.
    inflate_mask = (A == 1) & (C > C_q78) & (G_true[:, HET_INFLATE_J - 1] == 1)
    G_obs[:, HET_INFLATE_J - 1] = np.where(inflate_mask, 2.0, G_true[:, HET_INFLATE_J - 1])

    # ---- Audit subset: random 100 attendees with historical untreated LDL ----
    attendee_idx = np.where(A == 1)[0]
    audit_idx = rng.choice(attendee_idx, size=min(N_AUDIT, attendee_idx.size),
                           replace=False)
    audit_idx.sort()

    sample_id = np.array([f"subj_{i:04d}" for i in range(n)])

    return dict(
        sample_id=sample_id, age=age, sex=sex, bmi=bmi, pc1=pc1, pc2=pc2,
        dist_km=dist_km, invite_wave=invite_wave, capillary=C, refill=R,
        self_report=S_star, attended=A, lab=L, U=U, G_obs=G_obs,
        audit_idx=audit_idx, freqs=freqs, seed=seed,
    )


def _build_frames(sim: dict):
    n = N_INVITED
    geno_cols = [f"v{j:02d}" for j in range(1, N_VARIANTS + 1)]

    cohort = pd.DataFrame({
        "sample_id": sim["sample_id"],
        "age": np.round(sim["age"], 2),
        "sex": sim["sex"].astype(int),
        "bmi": np.round(sim["bmi"], 2),
        "pc1": np.round(sim["pc1"], 4),
        "pc2": np.round(sim["pc2"], 4),
        "dist_km": np.round(sim["dist_km"], 2),
        "invite_wave": sim["invite_wave"],
        "capillary_ldl_mgdl": np.round(sim["capillary"], 2),
        "refill_proxy": np.round(sim["refill"], 4),
        "self_report_statin": sim["self_report"].astype(int),
        "attended_fasting_lab": sim["attended"].astype(int),
    })
    # fasting-lab LDL observed only for attendees.
    lab = np.where(sim["attended"] == 1, np.round(sim["lab"], 2), np.nan)
    cohort["lab_ldl_mgdl"] = lab
    # genotype dosage columns (NA preserved for dropout).
    G = sim["G_obs"]
    for j, col in enumerate(geno_cols):
        cohort[col] = G[:, j]

    audit = pd.DataFrame({
        "sample_id": sim["sample_id"][sim["audit_idx"]],
        "baseline_ldl_mgdl": np.round(sim["U"][sim["audit_idx"]], 2),
    })

    variants = pd.DataFrame({
        "variant_index": np.arange(1, N_VARIANTS + 1),
        "variant_id": [f"rs{100000 + j}" for j in range(1, N_VARIANTS + 1)],
        "chrom": rng_chrom(),
        "pos": np.arange(1, N_VARIANTS + 1) * 10000,
        "ref": np.repeat("A", N_VARIANTS),
        "alt": np.repeat("G", N_VARIANTS),
        "dosage_column": geno_cols,
        "alt_freq": np.round(sim["freqs"], 4),
    })
    return cohort, audit, variants


def rng_chrom():
    # deterministic chromosome labels (cosmetic metadata)
    return np.array([1 + (j % 22) for j in range(N_VARIANTS)])


def generate(seed: int = 7, outdir: str | os.PathLike = ".", write_truth: bool = True) -> dict:
    """Generate staged files into ``outdir``. Returns the realized ground truth."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    sim = simulate(seed)
    cohort, audit, variants = _build_frames(sim)

    cohort.to_csv(outdir / "cohort.tsv.gz", sep="\t", index=False, compression="gzip")
    audit.to_csv(outdir / "audit.tsv.gz", sep="\t", index=False, compression="gzip")
    variants.to_csv(outdir / "variants.tsv.gz", sep="\t", index=False, compression="gzip")

    truth = None
    if write_truth:
        # Compute the recoverable realized-data target via the reference pipeline.
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from reference_solution import reference_solution  # local import
        truth = reference_solution(str(outdir))
        with open(outdir / "truth.json", "w") as fh:
            json.dump(truth, fh, indent=2)
    return {"outdir": str(outdir), "seed": seed, "truth": truth}


if __name__ == "__main__":
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="Generate LDL GWAS follow-up staged data")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--outdir", default="_data")
    args = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).parent))
    res = generate(seed=args.seed, outdir=args.outdir)
    print(json.dumps(res, indent=2))
