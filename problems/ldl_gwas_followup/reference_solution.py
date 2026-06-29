"""Reference (correct) solution for the LDL-C GWAS follow-up problem.

The three decision points:

  1. Reconstruct untreated LDL-C. Capillary LDL is treatment-distorted; estimate
     the treatment reduction (baseline - capillary) on the audit subset as a
     function of refill intensity and self-reported statin use, then add it back
     to capillary for EVERY subject. (Capillary is available for all invitees, so
     this reconstruction is full-cohort.)
  2. Use the full invited cohort. The reconstruction above uses capillary (all
     520 subjects), so the association and the cohort mean are estimated on the
     full cohort -- NOT restricted to the selection-biased attendee subset.
  3. Variant QC. Drop variants failing call-rate (>=0.95) or Hardy-Weinberg
     (p>=1e-6) -- removes the dropout variant 18 and the het-miscoded variant 19,
     which are degraded copies of the causal variant 42.

The final scan reports the QC-passing variant with the smallest p-value, its
per-allele effect on reconstructed untreated LDL, and the invited-cohort mean of
reconstructed untreated LDL. Running this on the generated data yields the truth.
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
OFFSET_PREDICTORS = ["refill_proxy", "self_report_statin"]
ASSOC_COVARIATES = ["age", "sex", "bmi", "pc1", "pc2"]


def _hwe_pvalue(geno: np.ndarray) -> float:
    g = np.rint(geno[~np.isnan(geno)]).astype(int)
    n = g.size
    if n == 0:
        return 1.0
    n0, n1, n2 = int((g == 0).sum()), int((g == 1).sum()), int((g == 2).sum())
    p = (2 * n0 + n1) / (2 * n)
    exp = np.array([p * p, 2 * p * (1 - p), (1 - p) ** 2]) * n
    if np.any(exp <= 0):
        return 1.0
    stat = np.sum((np.array([n0, n1, n2]) - exp) ** 2 / exp)
    return float(stats.chi2.sf(stat, df=1))


def _call_rate(geno: np.ndarray) -> float:
    return float(np.mean(~np.isnan(geno)))


def reference_solution(data_dir: str) -> dict:
    data_dir = Path(data_dir)
    cohort = pd.read_csv(data_dir / "cohort.tsv.gz", sep="\t")
    audit = pd.read_csv(data_dir / "audit.tsv.gz", sep="\t")
    variants = pd.read_csv(data_dir / "variants.tsv.gz", sep="\t")
    geno_cols = list(variants["dosage_column"])

    # ---- Decision point 1: reconstruct untreated LDL (treatment add-back) ----
    aud = cohort.merge(audit, on="sample_id", how="inner")
    offset_y = (aud["baseline_ldl_mgdl"] - aud["capillary_ldl_mgdl"]).astype(float)
    cal = sm.OLS(offset_y, sm.add_constant(aud[OFFSET_PREDICTORS].astype(float))).fit()
    Xpred = sm.add_constant(cohort[OFFSET_PREDICTORS].astype(float), has_constant="add")
    cohort = cohort.copy()
    cohort["U_hat"] = cohort["capillary_ldl_mgdl"].astype(float).values + cal.predict(Xpred).values

    # ---- Decision point 2: full invited cohort (no attendee restriction) -----
    y = cohort["U_hat"].astype(float).values
    Xcov = cohort[ASSOC_COVARIATES].astype(float)

    # ---- Decision point 3: variant QC on the full cohort ---------------------
    qc_pass, qc_detail = [], {}
    for col in geno_cols:
        g = cohort[col].to_numpy(dtype=float)
        cr, hwe = _call_rate(g), _hwe_pvalue(g)
        ok = (cr >= CALLRATE_MIN) and (hwe >= HWE_P_MIN)
        qc_detail[col] = {"call_rate": cr, "hwe_p": hwe}
        if ok:
            qc_pass.append(col)

    # ---- Final association scan over QC-passing variants ----------------------
    best = None
    for col in qc_pass:
        g = cohort[col].to_numpy(dtype=float)
        ok = ~np.isnan(g)
        design = pd.concat([pd.DataFrame({"geno": g[ok]}).reset_index(drop=True),
                            Xcov[ok].reset_index(drop=True)], axis=1)
        fit = sm.OLS(y[ok], sm.add_constant(design)).fit()
        p, b = float(fit.pvalues["geno"]), float(fit.params["geno"])
        if best is None or p < best[0]:
            best = (p, col, b)

    lead_index = int(variants.loc[variants["dosage_column"] == best[1], "variant_index"].iloc[0])
    return {
        "lead_variant_index": lead_index,
        "lead_beta_mgdl": round(best[2], 4),
        "source_mean_untreated_ldl_mgdl": round(float(np.mean(y)), 4),
        "_diagnostics": {
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
    print(json.dumps(reference_solution(ap.parse_args().data_dir), indent=2))
