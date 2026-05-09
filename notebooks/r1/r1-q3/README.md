# R1-Q3: SHAP feature-attribution batch-confound test

When the R1-Q4 cross-dataset classifier transfers, is it transferring biological signal or cross-study technical variation? SHAP / integrated-gradients attribution on the held-out test set, compared against curated stress-responsive gene sets (Hakkak & Tohidfar 2026 consensus DEGs and other published lists).

See the R1-Q3 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (provisional, from scoping handoff)

| # | File | Brief |
|---|---|---|
| 01 | `01_classifier.ipynb` | The R1-Q4 cross-dataset classifier (used here as input to attribution analysis). May be shared with R1-Q4. |
| 02 | `02_shap.ipynb` | SHAP / integrated-gradients attribution on the test set. |
| 03 | `03_batch_confound.ipynb` | Compare top-attributed genes against curated stress-responsive sets. Diagnostic for biological-signal vs batch-structure transfer. |

This list is provisional and will be refined when R1-Q3 is worked through.

## Data

AtGenExpress (training side; GEO GSE5620–GSE5628) and Wang 2023 (test side; PRJNA767196). Curated gene sets from Hakkak & Tohidfar 2026.

## Status

Not yet scaffolded. Will follow R1-Q1 and R1-Q2.
