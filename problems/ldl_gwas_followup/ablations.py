"""Wrong-but-plausible analysis paths for the LDL-C GWAS follow-up problem.

Each omits exactly one required correction and must land clearly OUTSIDE the
graded tolerances of the reference answer:

  capillary_direct : skip treatment add-back (DP1) -> treated-scale, attenuated
  attendee_only    : restrict to the selected attendee subset (DP2) -> biased
  naive_lab        : use the treated, attendee-only fasting lab directly (DP1+DP2)
  skip_qc          : skip all variant QC (DP3) -> dropout variant v18 wins
  skip_hwe         : call-rate QC only, skip Hardy-Weinberg (DP3) -> v19 wins
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from reference_solution import (
    ASSOC_COVARIATES, CALLRATE_MIN, HWE_P_MIN, OFFSET_PREDICTORS,
    _call_rate, _hwe_pvalue,
)


def _load(data_dir):
    data_dir = Path(data_dir)
    cohort = pd.read_csv(data_dir / "cohort.tsv.gz", sep="\t")
    audit = pd.read_csv(data_dir / "audit.tsv.gz", sep="\t")
    variants = pd.read_csv(data_dir / "variants.tsv.gz", sep="\t")
    return cohort, audit, variants


def _reconstruct(cohort, audit):
    aud = cohort.merge(audit, on="sample_id", how="inner")
    cal = sm.OLS((aud["baseline_ldl_mgdl"] - aud["capillary_ldl_mgdl"]).astype(float),
                 sm.add_constant(aud[OFFSET_PREDICTORS].astype(float))).fit()
    Xp = sm.add_constant(cohort[OFFSET_PREDICTORS].astype(float), has_constant="add")
    return cohort["capillary_ldl_mgdl"].astype(float).values + cal.predict(Xp).values


def _qc(cohort, geno_cols, use_callrate=True, use_hwe=True):
    out = []
    for col in geno_cols:
        g = cohort[col].to_numpy(dtype=float)
        ok = (not use_callrate) or (_call_rate(g) >= CALLRATE_MIN)
        ok = ok and ((not use_hwe) or (_hwe_pvalue(g) >= HWE_P_MIN))
        if ok:
            out.append(col)
    return out


def _scan(cohort, y, mask, qc_cols, variants):
    sub = cohort[mask]
    Xcov = sub[ASSOC_COVARIATES].astype(float)
    yv = y[mask.values]
    best = None
    for col in qc_cols:
        g = sub[col].to_numpy(dtype=float)
        ok = ~np.isnan(g)
        d = pd.concat([pd.DataFrame({"geno": g[ok]}).reset_index(drop=True),
                       Xcov[ok].reset_index(drop=True)], axis=1)
        fit = sm.OLS(yv[ok], sm.add_constant(d)).fit()
        p, b = float(fit.pvalues["geno"]), float(fit.params["geno"])
        if best is None or p < best[0]:
            best = (p, col, b)
    idx = int(variants.loc[variants["dosage_column"] == best[1], "variant_index"].iloc[0])
    return {"lead_variant_index": idx, "lead_beta_mgdl": round(best[2], 4),
            "source_mean_untreated_ldl_mgdl": round(float(np.mean(yv)), 4)}


def run_ablations(data_dir: str) -> dict:
    cohort, audit, variants = _load(data_dir)
    geno_cols = list(variants["dosage_column"])
    full = pd.Series(True, index=cohort.index)
    att = cohort["attended_fasting_lab"] == 1
    uhat = _reconstruct(cohort, audit)
    full_qc = _qc(cohort, geno_cols, True, True)

    res = {}
    res["capillary_direct"] = _scan(cohort, cohort["capillary_ldl_mgdl"].astype(float).values,
                                    full, full_qc, variants)
    res["attendee_only"] = _scan(cohort, uhat, att, full_qc, variants)
    res["naive_lab"] = _scan(cohort, cohort["lab_ldl_mgdl"].astype(float).values, att, full_qc, variants)
    res["skip_qc"] = _scan(cohort, uhat, full, geno_cols, variants)
    res["skip_hwe"] = _scan(cohort, uhat, full, _qc(cohort, geno_cols, True, False), variants)
    return res


if __name__ == "__main__":
    import argparse
    print(json.dumps(run_ablations(argparse.ArgumentParser().parse_args().__dict__.get("data_dir")
                                   or __import__("sys").argv[1]), indent=2))
