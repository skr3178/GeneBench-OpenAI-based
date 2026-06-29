"""Wrong-but-plausible analysis paths for the LDL-C GWAS follow-up problem.

Each ablation omits exactly one of the three required corrections. The benchmark
is valid only if each lands clearly OUTSIDE the graded tolerances of the reference
answer (verifying "clear separation from incorrect answers"). This mirrors the
ablation table in the GeneBench Appendix:

  naive_lab     : skip calibration -> use treatment-masked lab LDL (effect attenuated)
  skip_ipw      : skip attendance reweighting (invited-cohort mean is selection-biased)
  skip_qc       : skip all variant QC (dropout variant v18 wins with inflated effect)
  skip_hwe      : call-rate QC only, skip Hardy-Weinberg (het-inflated v19 wins)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from reference_solution import (
    ASSOC_COVARIATES, ATTENDANCE_PREDICTORS, CALLRATE_MIN, HWE_P_MIN,
    OFFSET_PREDICTORS, PI_CLIP, WEIGHT_TRIM, _call_rate, _hwe_pvalue,
)


def _load(data_dir):
    data_dir = Path(data_dir)
    cohort = pd.read_csv(data_dir / "cohort.tsv.gz", sep="\t")
    variants = pd.read_csv(data_dir / "variants.tsv.gz", sep="\t")
    audit = pd.read_csv(data_dir / "audit.tsv.gz", sep="\t")
    cohort["wave"] = cohort["invite_wave"] - 1
    return cohort, audit, variants


def _ipw_weights(cohort):
    Z = sm.add_constant(cohort[ATTENDANCE_PREDICTORS].astype(float))
    prop = sm.Logit(cohort["attended_fasting_lab"].astype(float), Z).fit(disp=0)
    pi = np.clip(prop.predict(Z).values, *PI_CLIP)
    w = cohort["attended_fasting_lab"].mean() / pi
    lo, hi = np.quantile(w, WEIGHT_TRIM)
    return np.clip(w, lo, hi)


def _addback_uhat(cohort, audit, att_mask):
    adf = cohort.merge(audit, on="sample_id", how="inner")
    y = (adf["baseline_ldl_mgdl"] - adf["lab_ldl_mgdl"]).astype(float)
    cal = sm.OLS(y, sm.add_constant(adf[OFFSET_PREDICTORS].astype(float))).fit()
    att = cohort[att_mask]
    Xp = sm.add_constant(att[OFFSET_PREDICTORS].astype(float), has_constant="add")
    return att["lab_ldl_mgdl"].astype(float).values + cal.predict(Xp).values


def _scan(att, y, w, geno_cols, variants, qc_cols):
    Xcov = att[ASSOC_COVARIATES].astype(float)
    best = None
    for col in qc_cols:
        g = att[col].to_numpy(dtype=float)
        ok = ~np.isnan(g)
        design = pd.concat([pd.DataFrame({"geno": g[ok]}).reset_index(drop=True),
                            Xcov[ok].reset_index(drop=True)], axis=1)
        fit = sm.WLS(y[ok], sm.add_constant(design), weights=w[ok]).fit()
        p, b = float(fit.pvalues["geno"]), float(fit.params["geno"])
        if best is None or p < best[0]:
            best = (p, col, b)
    idx = int(variants.loc[variants["dosage_column"] == best[1], "variant_index"].iloc[0])
    return idx, best[2]


def _qc_filter(att, geno_cols, use_callrate=True, use_hwe=True):
    out = []
    for col in geno_cols:
        g = att[col].to_numpy(dtype=float)
        ok = (not use_callrate) or (_call_rate(g) >= CALLRATE_MIN)
        ok = ok and ((not use_hwe) or (_hwe_pvalue(g) >= HWE_P_MIN))
        if ok:
            out.append(col)
    return out


def run_ablations(data_dir: str) -> dict:
    cohort, audit, variants = _load(data_dir)
    geno_cols = list(variants["dosage_column"])
    att_mask = cohort["attended_fasting_lab"] == 1
    att = cohort[att_mask].copy()
    w = _ipw_weights(cohort)[att_mask.values]
    w_ones = np.ones_like(w)
    uhat = _addback_uhat(cohort, audit, att_mask)
    lab = att["lab_ldl_mgdl"].astype(float).values

    full_qc = _qc_filter(att, geno_cols, True, True)
    callrate_only = _qc_filter(att, geno_cols, True, False)
    no_qc = geno_cols

    res = {}
    # naive: treatment-masked lab outcome (skip calibration), correct IPW + QC
    idx, b = _scan(att, lab, w, geno_cols, variants, full_qc)
    res["naive_lab"] = {"lead_variant_index": idx, "lead_beta_mgdl": round(b, 4),
                        "source_mean_untreated_ldl_mgdl": round(float(np.sum(w * lab) / np.sum(w)), 4)}
    # skip IPW: correct calibration + QC but unweighted (selection-biased mean)
    idx, b = _scan(att, uhat, w_ones, geno_cols, variants, full_qc)
    res["skip_ipw"] = {"lead_variant_index": idx, "lead_beta_mgdl": round(b, 4),
                       "source_mean_untreated_ldl_mgdl": round(float(uhat.mean()), 4)}
    # skip all QC: dropout variant can win
    idx, b = _scan(att, uhat, w, geno_cols, variants, no_qc)
    res["skip_qc"] = {"lead_variant_index": idx, "lead_beta_mgdl": round(b, 4),
                      "source_mean_untreated_ldl_mgdl": round(float(np.sum(w * uhat) / np.sum(w)), 4)}
    # call-rate QC only (skip HWE): het-inflated variant can win
    idx, b = _scan(att, uhat, w, geno_cols, variants, callrate_only)
    res["skip_hwe"] = {"lead_variant_index": idx, "lead_beta_mgdl": round(b, 4),
                       "source_mean_untreated_ldl_mgdl": round(float(np.sum(w * uhat) / np.sum(w)), 4)}
    return res


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir")
    args = ap.parse_args()
    print(json.dumps(run_ablations(args.data_dir), indent=2))
