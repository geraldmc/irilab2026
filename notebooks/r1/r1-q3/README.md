# R1-Q3: Feature attribution under batch effects

**When a stress classifier makes its predictions, is it relying on known stress-responsive genes or on patterns that look more like dataset artifacts?**

R1-Q4 asks whether a classifier trained on AtGenExpress transfers to Wang 2023 cold-stress RNA-seq. R1-Q3 asks an adjacent question: when such a classifier achieves high test accuracy, what features is it actually using? A classifier trained on pooled-across-studies data can hit high accuracy by learning real stress biology or by latching onto technical patterns — tissue dominance, batch structure, processing date — and accuracy alone can't tell them apart. R1-Q3 trains its own multi-class stress classifier on AtGenExpress, applies SHAP attribution to its predictions on a held-out test set, and compares the top-attributed genes against the Hakkak & Tohidfar 2026 consensus DEGs to assign one of three diagnostic verdicts: Strong, Mixed, or Low Overlap.

See the R1-Q3 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (in workflow order)

| # | File | Workflow row | Brief | Output |
|---|---|---|---|---|
| 00 | `00_orient_and_precommit.ipynb` | Week 1 | Restate the question; precommit attribution method, reference gene set, operational definition of "artifact-like," and data-source/stress-class scope. | `precommit.json` |
| 01 | `01_classifier.ipynb` | Week 2 | Train a multi-class stress classifier on AtGenExpress per the precommitted scope. Evaluate on a held-out test split; apply the accuracy gate before proceeding. | `classifier.pkl`, `classifier_metrics.parquet`, `classifier_summary.json` |
| 02 | `02_shap.ipynb` | Week 3 | Apply the precommitted attribution method to the trained classifier on the test split. Per-class top-attributed gene lists. | `attribution_scores.parquet`, `top_attributed_genes.json`, `attribution_summary.json` |
| 03 | `03_compare_and_interpret.ipynb` | Week 4 | Compare top-attributed genes against the precommitted reference set; test for technical-metadata correlation; apply the "artifact-like" rule; assign the Strong / Mixed / Low Overlap verdict. | `attribution_overlap.parquet`, `overlap_genes.parquet`, `attribution_comparison.json` |

Week 5 has no new notebook — it's revision against feedback on the paper and presentation.

The rationale-level orientation notebook (`../r1_orientation.ipynb`) loads AtGenExpress and is reused across R1-Q1 through R1-Q4. The question-specific orientation (`00_orient_and_precommit.ipynb` in this folder) picks up from there, locks the four precommit decisions, and produces the `precommit.json` file that Notebooks 01–03 read from.

## Data

AtGenExpress abiotic stress series (Kilian et al., 2007), GEO accessions GSE5620–GSE5628. Loaded via `irilab2026.load_atgenexpress()`. Eight stresses plus control: cold, osmotic, salt, drought, genotoxic, UV-B, wounding, heat. Oxidative is at TAIR/NASCArrays only and is not part of the GEO download path.

Reference set for the verdict in Notebook 03: Hakkak & Tohidfar (2026) consensus DEGs — Supplementary Table 1, the same anchor used by R1-Q1. Student-uploaded to the question's output folder as `hakkak_2026_supp1.csv`.

## Caveats carried into these notebooks

These come from the R1-Q3 considerations on the Notion question page; brief versions:

- **Train per-tissue or include tissue as an explicit covariate.** Tissue identity accounts for a larger share of expression variance in AtGenExpress than any single stress treatment. A classifier trained on pooled samples can hit high accuracy by recognizing tissue and exploiting tissue-stress correlations in the experimental design — a tissue classifier that happens to do okay on stress, not the other way around. Either split your training by tissue or model tissue explicitly so it can't act as a hidden shortcut.
- **Lock the attribution method and the reference set in writing before running.** SHAP, integrated gradients, and permutation importance produce different per-class rankings; the curated reference set you compare against also shapes the verdict. Swapping either after seeing attributions is fitting the method to the conclusion. Both choices are committed in Notebook 00 and read by Notebooks 02 and 03.
- **Define "artifact-like" operationally before you run, not after.** A defensible rule: top-attributed genes are artifact-like if their overlap with the reference set is no greater than chance *and* their attribution scores correlate with technical metadata (batch, processing date, tissue identity) at a pre-specified threshold. Deciding what "artifact-like" means after seeing the results means you can no longer answer the question honestly.

## Files

All notebook outputs and the precommit file share a Drive folder at `/content/drive/MyDrive/irilab2026_outputs/r1_q3/`:

| File | Producer | Consumer |
|---|---|---|
| `precommit.json` | Notebook 00 | Notebooks 01, 02, 03 |
| `classifier.pkl` | Notebook 01 | Notebooks 02, 03 |
| `classifier_metrics.parquet` | Notebook 01 | (paper / presentation) |
| `classifier_summary.json` | Notebook 01 | (paper / presentation) |
| `attribution_scores.parquet` | Notebook 02 | Notebook 03 |
| `top_attributed_genes.json` | Notebook 02 | Notebook 03 |
| `attribution_summary.json` | Notebook 02 | Notebook 03 |
| `attribution_overlap.parquet` | Notebook 03 | (paper / presentation) |
| `overlap_genes.parquet` | Notebook 03 | (paper / presentation) |
| `attribution_comparison.json` | Notebook 03 | (paper / presentation) |
| `hakkak_2026_supp1.csv` | (student upload) | Notebook 03 |

## Status

All four notebooks have full body content. R1-Q3 has not yet gone through the program's paper / presentation cycle.
