# Tables from GeneBench Paper

Extracted from `genebench.pdf` — *GeneBench: Assessing AI Agents for Multi-Stage Inference Problems in Genomics and Quantitative Biology* (Jeremy Li, Andrew Ho; April 23, 2026).

---

## Table 1: Primary design constraints in GeneBench

Together, these are intended to keep the graded endpoint scientifically identifiable while preserving realistic ambiguity, data error, and multi-stage analysis complexity.

### Ground truth and identifiability

| Principle | Benchmark requirement | Failure mode if violated |
|---|---|---|
| Recoverable target | Agents are graded on recovering the quantity that is actually recoverable from agent-visible data, and not the hidden data-generating parameters. | Correct analyses can be marked wrong because the parameter under which data were generated is unrecoverable (e.g., due to sampling variation in the DGP). |
| Unique, identifiable answer | The staged evidence along with a minimum viable prompt supports one uniquely defensible answer. If multiple approaches would ordinarily appear defensible, the data contain some empirical signature that rules all but one out. | The task becomes under-specified, and success depends on guessing the benchmark designer's preferred pipeline rather than reasoning from the evidence. |
| Clear separation from incorrect answers | A comprehensive ablation suite demonstrates that plausible wrong analyses and shortcut methods yield materially different answers and fail by clear margins. | Wrong analyses land too close to the target, so grading depends on tolerance tuning rather than scientific correctness. |

### Problem specification

| Principle | Benchmark requirement | Failure mode if violated |
|---|---|---|
| Minimal viable prompt | The scientific question, graded estimand, conventions, and output format are defined on the agent-visible surface, but the prompt does not hint at the method, QC path, or intermediate workflow. | The task either collapses into prompt following or leaves multiple defensible interpretations of what answer should be reported. |
| Threshold-robust QC | When QC is part of the solution, nearby reasonable thresholds lead to the same graded outcome. | The benchmark measures arbitrary cutoff choice rather than recognition of the QC problem. |

### Scientific workflow fidelity

| Principle | Benchmark requirement | Failure mode if violated |
|---|---|---|
| Constructive staging | Simulating data allows us to tune each detail of the data-generating process so realism, multi-stage inference, effect sizes, and diagnostic clues can be precisely controlled. | Difficulty, answer separation, and correctness become difficult to calibrate. |
| Multi-stage inference | Upstream filtering, representation, and adjustment-model decisions materially affect the final graded endpoint. | The benchmark reflects smaller units of end-to-end analysis rather than the full flow. |
| Literature-defensible solution | The intended correct solution involves standard or otherwise well-supported methods. | Success depends on benchmark-specific machinery, ad-hoc designer choices, rather than scientific judgment. |

---

## Table 2: Representative excerpts from the model-reported reasoning of selected GPT-5.4 and GPT-5.5 comparisons

In each case, both models identify or note the relevant local signal, but the stronger model carries the diagnostic through to a corresponding change in the downstream analytical choice.

| Problem | GPT-5.4 | GPT-5.5 |
|---|---|---|
| **Somatic signature deconvolution with FFPE and kataegis:** FFPE strand bias and localized kataegis bursts both inflate APOBEC (SBS2/SBS13) exposures and must be filtered before per-sample signature deconvolution. | Tests removing kataegis, observes the estimate change, then deliberately retains them. *"Removing very clustered kataegis-like mutations reduced β to about 0.72, indicating that some of the association is carried by clustered APOBEC events; because the target parameter is the total SBS2+SBS13 fraction, I retained those clustered mutations in the primary estimate."* | Removes kataegis clusters explicitly before deconvolution. *"used a high-confidence mutation set ... and removed localized kataegis/clustered bursts defined as ≥6 same-sample same-chromosome mutations within 10 kb."* |
| **SNP heritability of cortisol in a multi-ancestry cohort:** including ancestry-PC fixed effects beyond the true ancestry axes absorbs heritable signal and biases h² toward zero. | Adds many ancestry PCs and reports a strongly attenuated h². *"computed 20 genotype principal components from standardized dosages ... included them as additional fixed covariates ... The resulting SNP heritability estimate was h² = σ²_g/(σ²_g + σ²_e) = 0.122."* | Uses two scree-elbow PCs and recovers a value near the truth. *"the supplied PC1 matched the first genotype PC, and I included the first two genotype PCs as fixed effects based on the GRM eigenvalue elbow ... REML ... estimated h² = σ²_g/(σ²_g + σ²_e) = 0.403 on the log-cortisol scale."* |
| **Multi-signal fine-mapping with a sign-flipped palindromic variant:** rs100055 has a palindromic A/T allele pair and a sign-flipped summary effect; the agent must detect the LD/z inconsistency, flip the effect, and carry the flipped direction through to the reported sign. | Flips the sign for internal LD coherence but reports the original unflipped direction in the final answer. *"applied the minimal sign correction needed for local z–LD coherence there before fine-mapping ... Effect directions reported in the answer are from the original REF/ALT-aligned summary betas: ALT increases the trait for both rs100020 and rs100055."* | Carries the QC sign correction through to the final reported direction. *"rs100055 had an LD-sign inconsistency with its high-LD neighbors; flipping its effect sign made the regional z-score pattern coherent, so I treated it as a strand/sign QC correction ... the ALT allele T at rs100020 increases the trait, while the ALT allele T at rs100055 decreases the trait."* |

---

## Supplementary Table 1: Twenty-three representative GeneBench problems

**DP** = decision points: substantive inferential forks where a plausible wrong choice leads to a qualitatively different answer. **GPT-5.5** reports pass rate for GPT-5.5 at the xhigh reasoning setting over repeated runs.

### Genetics-backed drug discovery

| Problem | DP | GPT-5.5 | Skills tested | Graded quantities | Staged files |
|---|---|---|---|---|---|
| **LDL GWAS follow-up** Estimate the GWAS effect on untreated fasting LDL-C from a two-phase cohort with medication masking and selective follow-up. | 3 | 42.4% | Medication calibration from audit subset; IPW for selective attendance; genotype QC | Lead variant index; per-allele effect (mg/dL); invited-cohort mean untreated fasting LDL-C (mg/dL) | cohort (dosages, proxy LDL-C, covariates); audit (historical untreated LDL-C); variants (metadata) |
| **TWAS panel QC and colocalization** Identify the causal gene at a GWAS locus using expression models affected by degraded-library contamination. | 6 | 0.0% | RNA library QC; holdout-prediction validation; conditional signal analysis; colocalization; gene-window restriction; allele harmonization | Causal gene index; residual z-statistic; shared-signal posterior probability | gwas_sumstats (GWAS); gene_weights (models); eqtl_sumstats; ld_reference; gene_annotations; variant_manifest; library_qc; panel_holdout_predictions |
| **Multi-signal colocalization and cis-MR** Identify the gene–tissue pair that shares a causal signal with disease and estimate the corresponding cis-MR effect at a multi-signal locus. | 3 | 100.0% | Multi-signal conditional decomposition; ancestry-matched LD choice; colocalization; conditional cis-MR | Gene; tissue; colocated SNP; cis-MR effect | gwas_sumstats; eQTL panels (GENEA/GENEB by tissue); study_metadata; gene_info; ancestry-specific LD matrices |
| **Cross-platform pQTL colocalization and conditional cis-MR** Disentangle affinity artifacts, assay-specific binding effects, and shared signals across three assays and a disease GWAS. | 7 | 0.0% | Multi-signal conditional decomposition; cross-platform affinity contrast; colocalization (ABF); representative variant selection; conditional cis-MR | Assay-specific variant; follow-up variant; log-OR per SD protein | variant_info (metadata); trait_metadata (assays); ld_matrix; ld_variant_order; somascan; olink; massspec; disease_gwas |
| **CRISPR screen fitness inference with guide confounding** Infer gene-level fitness effects from a pooled screen with seed toxicity, copy-number bias, nonlinear GC-content effects, censoring, and inactive guides. | 6 | 0.0% | Staged technical-bias regression; inactive-guide Bayes-factor detection; left-censored Tobit model; guide-level QC | Top depleted gene; second gene; direct log₂ depletion | guide_counts (per-guide counts); guide_features (GC, seed, CN); gene_panel; screen_metadata |
| **Pharmacogenomic time-to-event MSM** Estimate genotype-specific treatment hazard ratios from EHR data with time-varying treatment–confounder feedback. | 6 | 75.0% | Treatment–confounder feedback; person-interval expansion; stabilized IPTW; pooled logistic MSM; wash-in lag specification | Responder genotype; HR noncarriers; HR carriers | patients (genotypes, outcomes, covariates); labs (longitudinal biomarker); data_dictionary |

### Population, quantitative, and microbial genetics

| Problem | DP | GPT-5.5 | Skills tested | Graded quantities | Staged files |
|---|---|---|---|---|---|
| **ARG-based recombination hotspot detection** Localize a recombination hotspot and estimate its intensity from local ARG segments despite formatting inconsistencies, unit mismatches, and low-support trees. | 4 | 94.3% | Posterior filtering; unit normalization; adjacent-tree collapse; breakpoint KDE; branch-length weighting | Hotspot center (bp); hotspot multiplier | local_trees (intervals, tree summaries); region_info (chromosome length) |
| **Two-pulse admixture timing** Estimate admixture times and admixture proportion from local-ancestry tract lengths under censoring and genetic map errors. | 4 | 12.5% | Mixture-of-exponentials fitting; right-censoring correction; phase-switch fragment merging; genetic map unit QC; left-truncation | Recent time (generations); ancient time (generations); recent pulse weight | segments (tract calls, posteriors); genetic_map (2 swapped chroms); chrom_lengths |
| **Direct and genetic nurture PGS effects** Estimate direct and genetic nurture PGS effects from transmitted and non-transmitted alleles under assortative mating with incomplete trios. | 6 | 0.0% | Family PGS decomposition; transmitted / non-transmitted separation; assortative mating correction; duo-family handling; missing-data encoding | Direct PGS effect (β_direct) | trios.npy (child, mother, father genotypes); weights (PGS weights); phenotypes; family_meta (duo flags, sibship); marker_qc |
| **Cortisol SNP heritability** Estimate cortisol SNP heritability after recovering noisy collection-site labels and adjusting for multi-ancestry population structure. | 4 | 88.9% | Phenotype transform; center recovery from metadata; recomputed PCs; variance-component heritability estimation; center-linked ancestry interaction control | SNP heritability (h²) | genotypes (dosages); samples; variants; phenotype; covariates (PC1, demographics, noisy center metadata) |
| **Metagenomic differential abundance and strain deconvolution** Identify differentially abundant microbial species and estimate strain-mixture proportions under compositional bias and batch effects. | 6 | 16.7% | Spike-in normalization; mock-community calibration; species selection; strain-panel orientation; batch-specific allele-flip correction | Case-associated species; log₂ fold-change; strain-A fraction (cases); strain-A fraction (controls) | species_counts (sample-by-species); sample_metadata; sample_qc; ref_counts; ref_qc; strain panels |

### Clinical screening and liquid biopsy

| Problem | DP | GPT-5.5 | Skills tested | Graded quantities | Staged files |
|---|---|---|---|---|---|
| **NIPT fetal-fraction estimation and mosaic trisomy detection** Estimate fetal fraction and detect mosaic trisomy in cfDNA with allele-biased SNPs, GC bias, and a maternal CNV. | 4 | 0.0% | Allelic-bias SNP filtering; target-chromosome exclusion; GC correction; maternal CNV detection | Karyotype; FF; coverage shift (δ); mosaic fraction | informative_snps (allele counts); test_counts (sample bins); controls; bin_metadata; analysis_manifest |
| **Tumor-versus-CH cfDNA deconvolution** Separate tumor-derived variants from clonal hematopoiesis-derived variants in plasma cfDNA and estimate tumor fraction. | 7 | 50.0% | Stratum-aware PON calling; simplex/duplex artifact QC; fragment-based tumor-vs-CH classification; tumor-fraction estimation | Tumor-locus count; CH-locus count; tumor fraction | control_counts (control by locus); case_counts (sample by locus); molecule_profiles (fragment bins); locus_catalog |
| **cfDNA methylation deconvolution** Estimate tumor fraction and tumor-specific methylation profiles from plasma cfDNA using matched leukocytes and a biased reference atlas. | 7 | 0.0% | Control-locus QC; separate nonconversion estimation; patient-specific background choice; marker restriction; reference calibration; back-calculation | Nonconversion rate; tumor fraction; tumor methylation at region R17 | plasma_counts (cfDNA); leukocyte_counts (matched normal); reference_regions (atlas) |

### Cancer and immunogenomics

| Problem | DP | GPT-5.5 | Skills tested | Graded quantities | Staged files |
|---|---|---|---|---|---|
| **APOBEC mutational signature attribution** Estimate the effect of genotype on APOBEC-associated mutational signatures after removing FFPE artifacts and kataegic clusters. | 4 | 63.0% | Mutation-level QC; kataegis detection; signature attribution; confounder-adjusted regression | APOBEC logit effect | mutations (per-SNV calls); sample_metadata; signature_profiles |
| **Presentation-competent clonal neoantigen burden** Identify the tumor with the highest presentation-competent clonal neoantigen burden under HLA loss, germline leakage, and subclonality. | 5 | 0.0% | FFPE artifact detection; LOH-germline filtering; integrated DNA/RNA HLA competence; expression gating; clonality estimation | Highest-burden tumor; clonal burden; total neoantigens | sample_manifest (tumor purity); hla_status; somatic_calls; expression_by_variant; binding_predictions |
| **HRD genomic scar scoring** Compute HRD genomic scar scores from allele-specific copy number despite WGD misclassification and segmentation noise. | 6 | 5.7% | Copy-number-scale inference; telomere/centromere masking; segment merging; ploidy-adjusted LST; scar scoring | GIS per sample; HRD status | segments (allele-specific CN); snps (BAF); sample_metadata; chrom_lengths; masks |

### Functional, deconvolution, and spatial genomics

| Problem | DP | GPT-5.5 | Skills tested | Graded quantities | Staged files |
|---|---|---|---|---|---|
| **Perturb-seq effects of STAT1 knockdown** Estimate the effect of STAT1 knockdown on IFN response and STAT1 expression under ambient guide contamination and perturbation escape. | 4 | 0.0% | Ambient-aware singlet calling; escape filtering; batch-phase standardization; gene-set scoring | IFN-response effect; STAT1 expression effect | guide_counts (per-cell guides); empty_guide_counts (ambient); expression_counts; cell_meta; guide_map; gene_sets |
| **Bulk RNA-seq deconvolution** Estimate the genotype effect on dendritic cell fraction from bulk RNA-seq under reference-panel mismatch, site confounding, and outlier samples. | 5 | 9.8% | Calibrator-based scaling; high-variance gene filtering; eQTL-marker exclusion; outlier detection; site-adjusted regression | Target cell type; logit effect | bulk_expression; scrna_reference (single-cell reference); sample_metadata (site, genotype); calibration_cell_fractions |
| **Spatial tumor cis-eQTL mapping** Identify the malignant-cell-autonomous cis-eQTL from spatial transcriptomics in the presence of spot swapping, neighborhood effects, and CN artifacts. | 4 | 2.3% | Spot-swapping correction; deconvolution; tumor-dominant spot selection; CN adjustment; candidate classification | Target gene; direct effect; context gene; artifact gene | spot_counts; spot_meta; donor_variant; reference_profiles; spot_auxiliary; candidate_genes |

### Other applications

| Problem | DP | GPT-5.5 | Skills tested | Graded quantities | Staged files |
|---|---|---|---|---|---|
| **Variant penetrance in panel sequencing under verification bias** Estimate the effect of a variant on confirmed diagnosis from clinical panel sequencing under kit-specific dropout and nonrandom case review. | 5 | 0.0% | Kit-specific calibration (binomial mixture); IPW for verification bias; collider avoidance; logistic regression; risk prediction | Carrier log-OR (β_carrier); predicted risk for female carrier at age_z = 0, pc1 = 0 | people (roster, partial diagnoses, covariates); counts (focal-site counts); controls (kit-specific wells) |
| **Low-template SNP mixture kinship inference** Estimate POI mixture weight and sibling-versus-unrelated LR from a low-template SNP mixture with degraded replicate profiles. | 4 | 0.0% | All-state τ calibration; blank-locus QC; degraded-replicate detection; per-locus mixture likelihood; kinship LR | POI mixture weight; log₁₀ LR (sibling vs. unrelated) | panel_manifest (AFs, efficiency); poi_genotypes; blank_controls; control_replicates; mixture_raw; poi_support_calls (deconvolution export) |
| **Microexon PSI** Estimate PSI for a 16 bp microexon under read-length bias, cryptic splice donors, and condition–batch imbalance. | 6 | 9.6% | Sample QC; unannotated junction discovery; cryptic donor detection; read-length bias modeling; calibration extrapolation; batch correction | PSI (control); PSI (treated); ΔPSI | sample_metadata (condition, batch, read length); event_catalog; junction_meta; junction_counts; annotation.gtf.gz |

---

## Supplementary Table 2: Values underlying Figure 4

Overall pass rate is the unweighted mean of per-problem pass rates across the 103 benchmark problems. The 95% confidence intervals match Figure 4A. Avg. tokens reports mean tokens used (chain-of-thought trace and final response, excluding tool calls, rounded to nearest 0.1k). GPT-family rows report reasoning effort, with GPT-5 shown from none through high and later mainline GPT models shown from none through xhigh.

| Model setting | Mean | 95% CI | 0% | >0–10% | >10–50% | ≥50% | Avg. tokens | Mean reps | Min | Max |
|---|---|---|---|---|---|---|---|---|---|---|
| MiMo V2 Pro | 1.6% | [0.3, 3.8] | 89.3% | 9.7% | 0.0% | 1.0% | 20.5k | 20.0 | 20 | 20 |
| Kimi K2.5 | 1.8% | [0.6, 3.8] | 84.5% | 13.6% | 1.0% | 1.0% | 35.5k | 20.0 | 20 | 20 |
| Grok 4.20 (reasoning enabled) | 2.1% | [0.6, 4.3] | 87.4% | 7.8% | 3.9% | 1.0% | 11.6k | 20.0 | 20 | 20 |
| Qwen 3.6 Plus | 2.7% | [0.9, 5.3] | 81.6% | 14.6% | 1.9% | 1.9% | 57.6k | 20.0 | 20 | 20 |
| MiMo V2.5 Pro | 3.0% | [1.3, 5.4] | 75.7% | 16.5% | 6.8% | 1.0% | 38.7k | 20.0 | 19 | 20 |
| GLM 5.1 | 4.2% | [2.1, 6.8] | 72.8% | 17.5% | 7.8% | 1.9% | 95.5k | 20.0 | 20 | 20 |
| Kimi K2.6 | 7.4% | [4.1, 11.4] | 65.0% | 21.4% | 8.7% | 4.9% | 74.8k | 20.0 | 20 | 40 |
| Gemini 3.1 Pro (high) | 11.2% | [7.2, 15.7] | 55.3% | 19.4% | 16.5% | 8.7% | 23.5k | 40.0 | 40 | 40 |
| GPT-5 (none) | 1.9% | [0.5, 4.1] | 87.4% | 9.7% | 1.9% | 1.0% | 2.8k | 25.0 | 25 | 25 |
| GPT-5 (low) | 1.8% | [0.6, 3.4] | 79.6% | 17.5% | 1.9% | 1.0% | 5.6k | 36.6 | 24 | 53 |
| GPT-5 (medium) | 2.5% | [1.1, 4.5] | 74.8% | 19.4% | 4.9% | 1.0% | 51.0k | 25.0 | 37 | 59 |
| GPT-5 (high) | 3.5% | [1.6, 6.0] | 73.8% | 17.5% | 6.8% | 1.9% | 15.9k | 25.0 | 24 | 25 |
| GPT-5.2 (none) | 1.7% | [0.3, 4.1] | 90.3% | 5.8% | 2.9% | 1.0% | 1.0k | 25.0 | 24 | 25 |
| GPT-5.2 (low) | 2.3% | [0.6, 4.7] | 85.4% | 10.7% | 2.9% | 1.0% | 4.9k | 25.0 | 24 | 25 |
| GPT-5.2 (medium) | 4.0% | [1.7, 7.0] | 78.6% | 11.7% | 7.8% | 1.9% | 12.0k | 25.0 | 24 | 25 |
| GPT-5.2 (high) | 5.8% | [3.1, 9.1] | 66.0% | 20.4% | 11.7% | 1.9% | 15.5k | 39.7 | 32 | 40 |
| GPT-5.2 (xhigh) | 9.4% | [5.8, 13.6] | 55.3% | 23.3% | 14.6% | 6.8% | 37.6k | 20.4 | 14 | 25 |
| GPT-5.4 (none) | 2.0% | [0.5, 4.4] | 86.4% | 6.8% | 3.9% | 1.0% | 1.6k | 25.0 | 24 | 25 |
| GPT-5.4 (low) | 4.3% | [2.3, 6.6] | 70.9% | 15.5% | 12.6% | 1.0% | 9.8k | 25.0 | 24 | 25 |
| GPT-5.4 (medium) | 8.9% | [6.1, 12.2] | 47.6% | 28.2% | 21.4% | 2.9% | 19.4k | 49.9 | 48 | 50 |
| GPT-5.4 (high) | 16.0% | [11.1, 21.6] | 50.5% | 17.5% | 19.4% | 12.6% | 21.2k | 25.0 | 24 | 25 |
| GPT-5.4 (xhigh) | 19.0% | [13.3, 25.0] | 49.5% | 14.6% | 20.4% | 15.5% | 36.4k | 24.9 | 24 | 25 |
| GPT-5.5 (none) | 1.9% | [0.5, 4.2] | 90.3% | 4.9% | 3.9% | 1.0% | 0.6k | 24.9 | 24 | 25 |
| GPT-5.5 (low) | 3.2% | [1.1, 6.0] | 85.4% | 7.8% | 4.9% | 1.9% | 5.3k | 24.9 | 24 | 25 |
| GPT-5.5 (medium) | 9.2% | [5.7, 13.2] | 59.2% | 18.4% | 15.5% | 6.8% | 13.7k | 25.0 | 24 | 25 |
| GPT-5.5 (high) | 22.2% | [16.1, 28.6] | 40.8% | 20.4% | 17.5% | 21.4% | 17.7k | 48.1 | 29 | 59 |
| GPT-5.5 (xhigh) | 25.0% | [18.5, 31.9] | 41.7% | 15.5% | 18.4% | 24.3% | 24.8k | 54.3 | 39 | 60 |
| GPT-5 Pro | 4.0% | [1.7, 7.0] | 68.0% | 26.2% | 2.9% | 2.9% | – | 39.2 | 25 | 40 |
| GPT-5.2 Pro | 10.8% | [6.4, 15.6] | 60.2% | 19.4% | 11.7% | 8.7% | – | 31.4 | 16 | 42 |
| GPT-5.4 Pro | 25.6% | [18.6, 32.8] | 51.5% | 7.8% | 14.6% | 26.2% | – | 20.0 | 20 | 20 |
| GPT-5.5 Pro | 33.2% | [25.1, 41.5] | 49.5% | 6.8% | 10.7% | 33.0% | – | 19.6 | 16 | 20 |

---

## Appendix Table 1: Notation used in the LDL case study

Observed quantities map directly to agent-visible columns; derived or latent quantities are computed from those files or introduced during the analysis; standard notation and transforms are listed for reference.

### Observed quantities

| Symbol | Meaning | Agent-visible variable(s) |
|---|---|---|
| i ∈ I = {1, …, N} | Invitee index in the invited cohort, with N = 520. | rows |
| j = 1, …, 60 | Variants in variants.tsv.gz. | variant_index; v01–v60 |
| G_ij ∈ {0, 1, 2, NA} | Additive genotype dosage for invitee i at variant j; NA denotes a missing genotype call. | v01–v60 |
| U_i | Untreated fasting LDL-C; observed only for i ∈ D and latent otherwise. | baseline_ldl_mgdl for audited attendees only |
| L_i | Observed fasting-lab LDL-C; observed only when A_i = 1. | lab_ldl_mgdl |
| C_i | Observed capillary LDL-C. | capillary_ldl_mgdl |
| A_i | Indicator for attendance at the fasting-lab visit. | attended_fasting_lab |
| S*_i | Self-reported statin use. | self_report_statin |
| R_i | Refill-based treatment proxy. | refill_proxy |
| dist_i ∈ ℝ₊ | Travel distance in km. | dist_km |

### Derived or latent quantities

| Symbol | Meaning | Agent-visible variable(s) |
|---|---|---|
| S_i | True statin exposure. | Not directly observed |
| wave_i ∈ {0, 1} | Zero-based invitation wave, defined as the agent-visible invite_wave minus 1; thus wave_i = 1 corresponds to invite_wave=2 in cohort.tsv.gz. | invite_wave |
| A = {i : A_i = 1} | Fasting-lab attendee subset. | attended_fasting_lab |
| D ⊆ A | Audited attendee subset with observed U_i. | sample_id |
| X_i | Association-model covariates: (age_i, sex_i, BMI_i, PC1_i, PC2_i). | age, sex, bmi, pc1, pc2 |
| Z_i | Attendance-model covariates: (C_i, age_i, BMI_i, sex_i, dist_i, wave_i, PC1_i, S*_i). | capillary_ldl_mgdl, age, bmi, sex, dist_km, invite_wave, pc1, self_report_statin |
| Û_i | Audit-calibrated prediction of untreated fasting LDL-C for attendee i. | lab_ldl_mgdl, refill_proxy, self_report_statin, capillary_ldl_mgdl, age, sex, bmi, baseline_ldl_mgdl |
| π_i | Attendance probability Pr(A_i = 1 \| Z_i). | attended_fasting_lab, capillary_ldl_mgdl, age, bmi, sex, dist_km, invite_wave, pc1, self_report_statin |
| w_i | Stabilized inverse-probability attendance weight Ā/π̂_i. | attended_fasting_lab; π̂_i |
| J_QC | Variant set passing attendee-subset call-rate and Hardy–Weinberg filters. | — |
| p_j | Final weighted-association p-value for variant j. | Û_i, G_ij, X_i |

### Standard notation and transforms

| Symbol | Meaning | Agent-visible variable(s) |
|---|---|---|
| 1(·) | Indicator function. | — |
| z(C_i) = (C_i − C̄)/s_C | Standardized capillary LDL-C in the realized invited cohort, where C̄ and s_C are the empirical mean and standard deviation of C. | capillary_ldl_mgdl |
| Q_q(C) | Empirical q-quantile of C. | capillary_ldl_mgdl |
| min{max{x, a}, b} | Truncation of x to the interval [a, b]. | — |
| ̂ | Estimated quantity computed from the agent-visible files. | — |

*The values against which outputs are graded (i.e. the ground truth values) are variant 42, 9.96 mg/dL, and 123.09 mg/dL, with grading tolerances of ±0.40 mg/dL for the effect estimate and ±1.00 mg/dL for the mean.*

---

## Appendix Table 2: Ablation results for the intended analysis and representative wrong approaches

The top block lists calibration specifications that pass the graded tolerance; all retain the minimum-sufficient surrogate set {L_i, R_i, C_i}. The remaining rows drop one of those surrogates or skip a decision point, and each fails on at least one graded quantity even when the lead variant is still ranked correctly. Values are rounded to two decimal places.

| Analysis | Pass? | Lead variant | Effect estimate (mg/dL) | Effect error (mg/dL) | Reported mean LDL-C (mg/dL) | Mean error (mg/dL) |
|---|---|---|---|---|---|---|
| correct | Pass | 42 | 9.96 | 0.00 | 123.09 | 0.00 |
| calibrated_no_selfreport_weighted | Pass | 42 | 9.86 | −0.10 | 123.36 | 0.27 |
| calibrated_no_demographics_weighted | Pass | 42 | 10.27 | 0.32 | 123.36 | 0.27 |
| calibrated_minimal_LRC_weighted | Pass | 42 | 10.20 | 0.25 | 123.69 | 0.59 |
| raw_lab_unweighted | Fail | 42 | 4.56 | −5.39 | 110.48 | −12.61 |
| raw_lab_weighted | Fail | 42 | 6.70 | −3.26 | 109.18 | −13.92 |
| self_report_plus30_unweighted | Fail | 42 | 4.77 | −5.18 | 123.12 | 0.02 |
| self_report_plus30_weighted | Fail | 42 | 7.77 | −2.19 | 117.97 | −5.12 |
| calibrated_unweighted | Fail | 42 | 8.28 | −1.68 | 129.65 | 6.56 |
| calibrated_no_refill_weighted | Fail | 42 | 9.28 | −0.68 | 122.84 | −0.25 |
| calibrated_no_capillary_proxy_weighted | Fail | 42 | 9.28 | −0.68 | 124.93 | 1.84 |
| calibrated_lab_only_weighted | Fail | 42 | 1.66 | −8.29 | 127.85 | 4.76 |
| capillary_proxy_unweighted | Fail | 42 | 10.84 | 0.89 | 131.99 | 8.89 |
| capillary_proxy_weighted | Fail | 42 | 13.14 | 3.19 | 123.45 | 0.36 |
| calibrated_weighted_no_covariates | Fail | 42 | 10.63 | 0.67 | 123.09 | 0.00 |
