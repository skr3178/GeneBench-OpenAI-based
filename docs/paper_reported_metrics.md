# Paper-reported metrics (GeneBench, Li & Ho 2026)

Reference values from the **paper** for the full 103-problem benchmark, for
comparison against runs of this open harness. Transcribed from `genebench.pdf`
(Supplementary Table 2 + Results); the PDF is the authoritative source.
Machine-readable copy: [`paper_reported_metrics.json`](paper_reported_metrics.json).

> ⚠️ These numbers are for the **closed** 103-problem GeneBench suite (only the
> LDL problem is reproduced here). They are a yardstick for the *kind* of result
> the harness produces, **not** a target this repo can reproduce — our suite is
> one problem, and a model's score here is not comparable to the paper's.

## What each metric means

- **Mean (pass rate)** — binary grading (a run passes only if *all* graded fields pass);
  reported as the **unweighted mean of per-problem pass rates** over 103 problems.
- **95% CI** — hierarchical bootstrap, 20,000 resamples (resample problems, then runs within each).
- **Regime columns** — share of the 103 problems whose pass rate falls in `0%`, `>0–10%`, `>10–50%`, `≥50%`.
- **Avg tokens** — mean tokens in the full chain-of-thought trace + final response, **excluding tool calls** (omitted for Pro runs). GPT totals use internal accounting; non-GPT use OpenRouter accounting — **not directly comparable across the two groups**.
- **Reps** — mean / min / max valid runs per problem-model (overall mean 28.7, range 14–60).

## Benchmark-level facts

| Fact | Value |
|---|---|
| Problems / domains | 103 / 10 |
| Decision points per problem | 3–13 (median 6) |
| Pass rate vs. decision points | Spearman ρ = −0.32 |
| Best mainline GPT | GPT-5.5 `xhigh` — **25.0%** |
| Best Pro run | GPT-5.5 Pro — **33.2%** |
| Best external (non-GPT) | Gemini 3.1 Pro `high` — **11.2%** |
| LDL case-study realized truth | variant **42**, β **9.96** mg/dL (±0.40), mean **123.09** mg/dL (±1.00) |

## Supplementary Table 2 — overall pass rates

| Model setting | Mean | 95% CI | 0% | >0–10% | >10–50% | ≥50% | Avg tok | Reps (mean/min/max) |
|---|---|---|---|---|---|---|---|---|
| MiMo V2 Pro | 1.6% | [0.3, 3.8] | 89.3 | 9.7 | 0.0 | 1.0 | 20.5k | 20.0 / 20 / 20 |
| Kimi K2.5 | 1.8% | [0.6, 3.8] | 84.5 | 13.6 | 1.0 | 1.0 | 35.5k | 20.0 / 20 / 20 |
| Grok 4.20 (reasoning) | 2.1% | [0.6, 4.3] | 87.4 | 7.8 | 3.9 | 1.0 | 11.6k | 20.0 / 20 / 20 |
| Qwen 3.6 Plus | 2.7% | [0.9, 5.3] | 81.6 | 14.6 | 1.9 | 1.9 | 57.6k | 20.0 / 20 / 20 |
| MiMo V2.5 Pro | 3.0% | [1.3, 5.4] | 75.7 | 16.5 | 6.8 | 1.0 | 38.7k | 20.0 / 19 / 20 |
| GLM 5.1 (reasoning) | 4.2% | [2.1, 6.8] | 72.8 | 17.5 | 7.8 | 1.9 | 95.5k | 20.0 / 20 / 20 |
| Kimi K2.6 | 7.4% | [4.1, 11.4] | 65.0 | 21.4 | 8.7 | 4.9 | 74.8k | 20.0 / 20 / 20 |
| **Gemini 3.1 Pro (high)** | **11.2%** | [7.2, 15.7] | 55.3 | 19.4 | 16.5 | 8.7 | 23.5k | 40.0 / 40 / 40 |
| GPT-5 (none) | 1.9% | [0.5, 4.1] | 87.4 | 9.7 | 1.9 | 1.0 | 2.8k | 25.0 / 25 / 25 |
| GPT-5 (low) | 1.8% | [0.6, 3.4] | 79.6 | 17.5 | 1.9 | 1.0 | 5.6k | 36.6 / 24 / 53 |
| GPT-5 (medium) | 2.5% | [1.1, 4.5] | 74.8 | 19.4 | 4.9 | 1.0 | 10.0k | 51.0 / 37 / 59 |
| GPT-5 (high) | 3.5% | [1.6, 6.0] | 73.8 | 17.5 | 6.8 | 1.9 | 15.9k | 25.0 / 24 / 25 |
| GPT-5.2 (none) | 1.7% | [0.3, 4.1] | 90.3 | 5.8 | 2.9 | 1.0 | 1.6k | 25.0 / 24 / 25 |
| GPT-5.2 (low) | 2.3% | [0.6, 4.7] | 85.4 | 10.7 | 2.9 | 1.0 | 4.9k | 25.0 / 24 / 25 |
| GPT-5.2 (medium) | 4.0% | [1.7, 7.0] | 78.6 | 11.7 | 7.8 | 1.9 | 12.0k | 25.0 / 24 / 25 |
| GPT-5.2 (high) | 5.8% | [3.1, 9.1] | 66.0 | 20.4 | 11.7 | 1.9 | 15.5k | 39.7 / 32 / 40 |
| GPT-5.2 (xhigh) | 9.4% | [5.8, 13.6] | 55.3 | 23.3 | 14.6 | 6.8 | 37.6k | 20.4 / 14 / 25 |
| GPT-5.4 (none) | 2.0% | [0.5, 4.4] | 85.4 | 8.7 | 3.9 | 1.0 | 1.6k | 25.0 / 24 / 25 |
| GPT-5.4 (low) | 4.3% | [2.3, 6.6] | 70.9 | 15.5 | 12.6 | 1.0 | 9.8k | 25.0 / 24 / 25 |
| GPT-5.4 (medium) | 8.9% | [6.1, 12.2] | 47.6 | 28.2 | 21.4 | 2.9 | 19.4k | 49.9 / 48 / 50 |
| GPT-5.4 (high) | 16.0% | [11.1, 21.6] | 50.5 | 17.5 | 19.4 | 12.6 | 21.2k | 25.0 / 24 / 25 |
| GPT-5.4 (xhigh) | 19.0% | [13.3, 25.0] | 49.5 | 14.6 | 20.4 | 15.5 | 36.4k | 24.9 / 24 / 25 |
| GPT-5.5 (none) | 1.9% | [0.5, 4.2] | 90.3 | 4.9 | 3.9 | 1.0 | 0.6k | 25.0 / 24 / 25 |
| GPT-5.5 (low) | 3.2% | [1.1, 6.0] | 85.4 | 7.8 | 4.9 | 1.9 | 5.3k | 24.9 / 24 / 25 |
| GPT-5.5 (medium) | 9.2% | [5.7, 13.2] | 59.2 | 18.4 | 15.5 | 6.8 | 13.7k | 25.0 / 24 / 25 |
| GPT-5.5 (high) | 22.2% | [16.1, 28.6] | 40.8 | 20.4 | 17.5 | 21.4 | 17.7k | 48.1 / 29 / 59 |
| **GPT-5.5 (xhigh)** | **25.0%** | [18.5, 31.9] | 41.7 | 15.5 | 18.4 | 24.3 | 24.8k | 54.3 / 39 / 60 |
| GPT-5 Pro | 4.0% | [1.7, 7.0] | 68.0 | 26.2 | 2.9 | 2.9 | — | 39.2 / 25 / 40 |
| GPT-5.2 Pro | 10.8% | [6.4, 15.6] | 60.2 | 19.4 | 11.7 | 8.7 | — | 31.4 / 16 / 42 |
| GPT-5.4 Pro | 25.6% | [18.6, 32.8] | 51.5 | 7.8 | 14.6 | 26.2 | — | 20.0 / 20 / 20 |
| **GPT-5.5 Pro** | **33.2%** | [25.1, 41.5] | 49.5 | 10.7 | 10.7 | 33.0 | — | 19.6 / 16 / 20 |

*Regime cells are rounded to 0.1% and may not sum to exactly 100; the PDF is authoritative.*
