"""Reference (correct) solution for the LDL-C GWAS follow-up problem.

Implements the three decision points described in the GeneBench Appendix:

  1. Reconstruct untreated LDL-C by audit-based regression calibration: estimate
     the treatment-induced offset (U - L) from the audit subset as a function of
     the refill proxy and self-reported statin use, then add it back to the
     treatment-distorted lab value (a variance-preserving / Tobin-style treatment
     correction). This recovers the untreated scale without the slope attenuation
     that a shrunken predict-U-hat regression would introduce.
  2. Reweight attendees back to the invited cohort with stabilized inverse-
     probability-of-attendance weights (eqs. 18-20).
  3. Apply variant QC (call-rate >= 0.95 AND Hardy-Weinberg p >= 1e-6, eq. 21)
     on the attendee subset before the final association scan.

The final weighted association scan (eqs. 22-23) reports the QC-passing variant
with the smallest p-value, its per-allele effect, and the weighted invited-cohort
mean of reconstructed untreated LDL-C.

Running this on the generated data yields the graded ground truth.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

CALLRATE_MIN = 0.95
HWE_P_MIN = 1e-6
WEIGHT_TRIM = (0.01, 0.99)
PI_CLIP = (0.05, 0.95)

# Predictors of the treatment offset (U - L), estimated on the audit subset.
# Refill intensity is the dominant driver of the treatment-induced LDL reduction.
OFFSET_PREDICTORS = ["refill_proxy", "self_report_statin"]
ATTENDANCE_PREDICTORS = ["capillary_ldl_mgdl", "age", "bmi", "sex", "dist_km",
                         "wave", "pc1", "self_report_statin"]
ASSOC_COVARIATES = ["age", "sex", "bmi", "pc1", "pc2"]


def _hwe_pvalue(geno: np.ndarray) -> float:
    """Chi-square (1 df) Hardy-Weinberg test from integer genotype calls."""
    g = geno[~np.isnan(geno)]
    g = np.rint(g).astype(int)
    n = g.size
    if n == 0:
        return 1.0
    n0 = int(np.sum(g == 0))
    n1 = int(np.sum(g == 1))
    n2 = int(np.sum(g == 2))
    p = (2 * n0 + n1) / (2 * n)          # ref allele freq
    q = 1.0 - p
    exp = np.array([p * p, 2 * p * q, q * q]) * n
    if np.any(exp <= 0):
        return 1.0
    obs = np.array([n0, n1, n2])
    stat = np.sum((obs - exp) ** 2 / exp)
    return float(stats.chi2.sf(stat, df=1))


def _call_rate(geno: np.ndarray) -> float:
    return float(np.mean(~np.isnan(geno)))


def reference_solution(data_dir: str) -> dict:
    data_dir = Path(data_dir)
    cohort = pd.read_csv(data_dir / "cohort.tsv.gz", sep="\t")
    audit = pd.read_csv(data_dir / "audit.tsv.gz", sep="\t")
    variants = pd.read_csv(data_dir / "variants.tsv.gz", sep="\t")

    cohort = cohort.copy()
    cohort["wave"] = cohort["invite_wave"] - 1
    geno_cols = list(variants["dosage_column"])

    attendees = cohort["attended_fasting_lab"] == 1

    # ---- Decision point 1: reconstruct untreated LDL via audit calibration ---
    # Estimate the treatment offset (U - L) on the audit, then add it back to L.
    audit_df = cohort.merge(audit, on="sample_id", how="inner")
    offset_y = (audit_df["baseline_ldl_mgdl"] - audit_df["lab_ldl_mgdl"]).astype(float)
    Xa = sm.add_constant(audit_df[OFFSET_PREDICTORS].astype(float))
    cal = sm.OLS(offset_y, Xa).fit()

    att = cohort[attendees].copy()
    Xpred = sm.add_constant(att[OFFSET_PREDICTORS].astype(float), has_constant="add")
    att["U_hat"] = att["lab_ldl_mgdl"].astype(float).values + cal.predict(Xpred).values

    # ---- Decision point 2: stabilized IPW weights (fit on all invitees) ------
    Z = sm.add_constant(cohort[ATTENDANCE_PREDICTORS].astype(float))
    prop = sm.Logit(cohort["attended_fasting_lab"].astype(float), Z).fit(disp=0)
    pi_hat = np.clip(prop.predict(Z).values, *PI_CLIP)
    Abar = cohort["attended_fasting_lab"].mean()
    w_all = Abar / pi_hat
    lo, hi = np.quantile(w_all, WEIGHT_TRIM)
    w_all = np.clip(w_all, lo, hi)
    att["w"] = w_all[attendees.values]

    # ---- Decision point 3: variant QC on the attendee subset -----------------
    qc_pass = []
    qc_detail = {}
    for col in geno_cols:
        g = att[col].to_numpy(dtype=float)
        cr = _call_rate(g)
        hwe = _hwe_pvalue(g)
        passed = (cr >= CALLRATE_MIN) and (hwe >= HWE_P_MIN)
        qc_detail[col] = {"call_rate": cr, "hwe_p": hwe, "pass": passed}
        if passed:
            qc_pass.append(col)

    # ---- Final weighted association scan over QC-passing variants ------------
    Xcov = att[ASSOC_COVARIATES].astype(float)
    y = att["U_hat"].astype(float).values
    w = att["w"].astype(float).values

    best = None  # (p, col, beta)
    for col in qc_pass:
        g = att[col].to_numpy(dtype=float)
        ok = ~np.isnan(g)
        design = pd.DataFrame({"geno": g[ok]})
        design = pd.concat([design.reset_index(drop=True),
                            Xcov[ok].reset_index(drop=True)], axis=1)
        design = sm.add_constant(design)
        fit = sm.WLS(y[ok], design, weights=w[ok]).fit()
        beta = float(fit.params["geno"])
        pval = float(fit.pvalues["geno"])
        if best is None or pval < best[0]:
            best = (pval, col, beta)

    lead_col = best[1]
    lead_beta = best[2]
    lead_index = int(variants.loc[variants["dosage_column"] == lead_col,
                                  "variant_index"].iloc[0])

    # ---- Weighted invited-cohort mean of reconstructed untreated LDL ---------
    mean_u = float(np.sum(w * y) / np.sum(w))

    return {
        "lead_variant_index": lead_index,
        "lead_beta_mgdl": round(lead_beta, 4),
        "source_mean_untreated_ldl_mgdl": round(mean_u, 4),
        "_diagnostics": {
            "n_attendees": int(attendees.sum()),
            "n_qc_pass": len(qc_pass),
            "lead_variant_p": best[0],
            "call_rate_v18": qc_detail["v18"]["call_rate"],
            "hwe_p_v19": qc_detail["v19"]["hwe_p"],
        },
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir")
    args = ap.parse_args()
    print(json.dumps(reference_solution(args.data_dir), indent=2))
