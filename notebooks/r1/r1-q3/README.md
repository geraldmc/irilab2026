# R1-Q3: When a stress classifier makes its predictions, is it relying on known stress-responsive genes or on patterns that look more like dataset artifacts?

R1-Q4 asks whether a classifier trained on AtGenExpress transfers to Wang 2023 cold-stress RNA-seq. R1-Q3 asks an adjacent question: when such a classifier achieves high test accuracy, what features is it actually using? A classifier trained on pooled-across-studies data can hit high accuracy by learning real stress biology or by latching onto technical patterns — tissue dominance, batch structure, processing date — and accuracy alone can't tell them apart. R1-Q3 trains its own multi-class stress classifier on AtGenExpress, applies SHAP attribution to its predictions on a held-out test set, and compares the top-attributed genes against curated stress-responsive gene sets (Hakkak & Tohidfar 2026 and others) to assign one of three diagnostic verdicts: Strong, Mixed, or Low Overlap.

See the R1-Q3 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks

| # | File | Brief |
|---|---|---|
| 00 | `00_orient_and_precommit.ipynb` | Week 1. Restate the question; precommit attribution method, reference gene set, operational definition of "artifact-like," and data-source/stress-class scope. Produces `precommit.json` and EQ#1 input. |
| 01 | `01_classifier.ipynb` | Week 2. Train a multi-class stress classifier on AtGenExpress per the precommitted scope. Evaluate on a held-out test split; apply the accuracy gate before proceeding. Produces `classifier.pkl`, `classifier_metrics.parquet`, `classifier_summary.json`, and EQ#2 input. |
| 02 | `02_shap.ipynb` | Week 3. Apply the precommitted attribution method to the trained classifier on the test split. Produces `attribution_scores.parquet`, `top_attributed_genes.json`, `attribution_summary.json`, and Week 3 draft-presentation input. |
| 03 | `03_compare_and_interpret.ipynb` | Week 4. Compare top-attributed genes against the precommitted reference set; test for technical-metadata correlation; apply the "artifact-like" rule; assign the Strong / Mixed / Low Overlap verdict. Produces `attribution_overlap.parquet`, `overlap_genes.parquet`, and `attribution_comparison.json` — the headline finding for the final paper and presentation. |

## Data

AtGenExpress (GEO GSE5620–GSE5628; the training and test source). Curated stress-responsive gene sets from Hakkak & Tohidfar 2026.

## Status

Notebook scaffolding (opener + preamble + body section headers) drafted for all four notebooks. Body section content (given cells and practice cells) still to fill.