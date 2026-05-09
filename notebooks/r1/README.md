# Rationale 1

*Decoding Plant Stress: Machine Learning Approaches to Gene Expression and Regulatory Networks.*

Rationale 1's four questions all draw on the AtGenExpress abiotic stress microarray dataset (Kilian et al. 2007), with R1-Q4 additionally pulling in Wang 2023 RNA-seq data as a cross-platform test set.

## Notebooks in this rationale

- **`r1_orientation.ipynb`** — AtGenExpress on-ramp. Walks through the dataset structure (eight stresses + control, shoot and root tissue, time course up to 24 hours), uses `irilab2026.load_atgenexpress()` to pull the data, and ends with the data in the shape that R1-Q1 picks up from. Reused across R1-Q1 through R1-Q4.
- **`r1-q1/`** — Common stress core. The methodological reproduction work.
- **`r1-q2/`** — Hub genes from co-expression analysis (WGCNA-style).
- **`r1-q3/`** — SHAP feature-attribution test for batch confound in the R1-Q4 cross-dataset classifier.
- **`r1-q4/`** — Cross-dataset stress classifier (AtGenExpress → Wang 2023).

## Status

Scaffolding in progress. The orientation notebook is the first thing to be drafted (and is explicitly provisional — expect one revision pass after the R1-Q1 analytical notebooks are written and reveal what the orientation actually needs to set up).