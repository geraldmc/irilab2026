# R1-Q3: Feature attribution under batch effects

**When a stress classifier makes its predictions, is it relying on known stress-responsive genes or on patterns that look more like dataset artifacts?**

R1-Q4 asks whether a classifier trained on AtGenExpress transfers to Wang 2023 cold-stress RNA-seq. R1-Q3 asks an adjacent question: when such a classifier achieves high test accuracy, what features is it actually using? A classifier trained on pooled-across-studies data can hit high accuracy by learning real stress biology or by latching onto technical patterns — tissue dominance, batch structure, processing date — and accuracy alone can't tell them apart. R1-Q3 trains its own multi-class stress classifier on AtGenExpress, applies SHAP attribution to its predictions on a held-out test set, and compares the top-attributed genes against the Hakkak & Tohidfar 2026 consensus DEGs to assign one of three diagnostic verdicts: Strong, Mixed, or Low Overlap.

See the R1-Q3 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (in workflow order)

| # | File | Workflow row | Brief | Output |
|---|---|---|---|---|
| 00 | `00_orient_and_precommit.ipynb` | Week 1 | Restate the question; precommit attribution method, reference gene set, operational definition of "artifact-like," and data-source/stress-class scope. | `precommit.json` |
| 01 | `01_classifier.ipynb` | Week 2 | Apply your tissue-handling decision, then train a multi-class stress classifier on AtGenExpress per the precommitted scope. Evaluate on a held-out test split; the accuracy gate decides whether the model is worth interpreting. | `classifier.pkl`, `classifier_summary.json`, `test_splits.parquet`, `controls_background.parquet` |
| 02 | `02_shap.ipynb` | Week 3 | Apply the precommitted attribution method to the trained classifier on the test split, using the control samples as the SHAP background. Per-class top-attributed gene lists. | `attribution_scores.parquet`, `top_attributed_genes.json`, `attribution_summary.json` |
| 03 | `03_compare_and_interpret.ipynb` | Week 4 | Compare top-attributed genes against the precommitted reference set; test for technical-metadata correlation; apply the "artifact-like" rule; assign the Strong / Mixed / Low Overlap verdict. | `verdicts.parquet`, `comparison_summary.json` |

Week 5 has no new notebook — it's revision against feedback on the paper and presentation.

The rationale-level orientation notebook (`../r1_orientation.ipynb`) loads AtGenExpress and is reused across R1-Q1 through R1-Q4. The question-specific orientation (`00_orient_and_precommit.ipynb` in this folder) picks up from there, locks the four precommit decisions, and produces the `precommit.json` file that Notebooks 01–03 read from.

Notebook 01 ends in an explicit accuracy gate: if the classifier isn't good enough to be worth interpreting, it stops there. The gate verdict is recorded in `classifier_summary.json`, which Notebooks 02 and 03 read before proceeding.

## Data

AtGenExpress abiotic stress series (Kilian et al., 2007), GEO accessions GSE5620–GSE5628. Loaded via `irilab2026.load_atgenexpress()`. Eight stresses plus control: cold, osmotic, salt, drought, genotoxic, UV-B, wounding, heat. Oxidative is at TAIR/NASCArrays only and is not part of the GEO download path.

Reference set for the verdict in Notebook 03: Hakkak & Tohidfar (2026) consensus DEGs — Supplementary Table 1, the same anchor used by R1-Q1. Student-uploaded to the question's output folder as `hakkak_2026_supp1.csv`.

## Caveats carried into these notebooks

- **Apply a tissue-handling decision before training.** Tissue identity accounts for more expression variance in AtGenExpress than any single stress treatment, so a classifier trained on pooled shoot+root can reach high accuracy by recognizing tissue and exploiting tissue-stress correlations in the experimental design — a tissue classifier that happens to do okay on stress, not the reverse. NB01 Section 3 makes you either split training by tissue or model tissue as an explicit covariate, so it can't act as a hidden shortcut.
- **Don't attribute a classifier that hasn't cleared the accuracy gate.** AtGenExpress is clean and well-separated, so a model can reach high test accuracy while keying on features that have nothing to do with stress biology. Attribution on an unchecked or weak classifier manufactures a story about features that don't actually drive predictions. NB01 Section 5 is an explicit stop-here gate; the SHAP work in NB02 is meant to run only on a model that cleared it.
- **Lock the attribution method and the reference set in writing before running.** SHAP, integrated gradients, and permutation importance produce different per-class rankings, and the curated reference set you compare against also shapes the verdict. Swapping either after seeing attributions is fitting the method to the conclusion. Both choices are committed in NB00 (`attribution_method`, `reference_gene_set`) and read by NB02 and NB03.
- **Define "artifact-like" operationally before you run, not after.** The committed rule (NB00's `artifact_like_definition`): top-attributed genes are artifact-like if their overlap with the reference set is no greater than chance *and* their attribution scores correlate with technical metadata (batch, processing date, tissue identity) above a pre-specified threshold. NB03 applies exactly this rule to assign the Strong / Mixed / Low Overlap verdict. Deciding what "artifact-like" means after seeing the results means you can no longer answer the question honestly.

## Files

All notebook outputs and the precommit file share a Drive folder at `/content/drive/MyDrive/irilab2026_outputs/r1_q3/`:

| File | Producer | Consumer |
|---|---|---|
| `precommit.json` | Notebook 00 | Notebooks 01, 02, 03 |
| `classifier.pkl` | Notebook 01 | Notebook 02 |
| `classifier_summary.json` | Notebook 01 | Notebooks 02, 03 (carries the accuracy-gate verdict) |
| `test_splits.parquet` | Notebook 01 | Notebook 02 |
| `controls_background.parquet` | Notebook 01 | Notebook 02 (SHAP background samples) |
| `attribution_scores.parquet` | Notebook 02 | Notebook 03 |
| `top_attributed_genes.json` | Notebook 02 | Notebook 03 |
| `attribution_summary.json` | Notebook 02 | Notebook 03 |
| `verdicts.parquet` | Notebook 03 | (paper / presentation) |
| `comparison_summary.json` | Notebook 03 | (paper / presentation) |
| `hakkak_2026_supp1.csv` | (student upload) | Notebook 03 |

`classifier.pkl` is a joblib-pickled scikit-learn classifier bundle, so `.pkl` is correct here (the same convention as R1-Q4; the Rationale 2 chains save PyTorch state dicts as `.pt`).

## Status

All four notebooks have full body content; the question chain was recently finalized. R1-Q3 has not yet gone through the program's paper / presentation cycle.
