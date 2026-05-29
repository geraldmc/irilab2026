# R1-Q4: Cross-dataset stress classifier

Does a multi-class stress classifier trained on AtGenExpress generalize to Wang 2023 cold-stress RNA-seq with above-chance accuracy? Cross-platform integration via VST + ComBat.

See the R1-Q4 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (in workflow order)

| # | File | Workflow row | Brief | Output |
|---|---|---|---|---|
| 00 | `00_orient_and_precommit.ipynb` | Week 1 | Question-specific orientation. Inspect AtGenExpress and Wang 2023; lock three precommit decisions in writing. | `precommit.json` (data source plus stress-class scope, Wang 2023 168 h timepoint handling, "above-chance" null) |
| 01 | `01_integration.ipynb` | Week 2 | Cross-platform integration. VST on Wang 2023 RNA-seq counts; align to ATH1 microarray probe space; ComBat across both datasets. | `wang_aligned.parquet`, `integrated_matrix.parquet`, `integration_summary.json` |
| 02 | `02_classifier.ipynb` | Week 3 | Train the multi-class stress classifier on the integrated AtGenExpress training set; evaluate on a held-out AtGenExpress split. | `classifier.pkl`, `classifier_metrics.parquet`, `classifier_summary.json` |
| 03 | `03_wang_evaluation.ipynb` | Week 4 | Apply the trained classifier to integrated Wang 2023; per-timepoint accuracy; compare against the precommitted "above-chance" null. | `wang_transfer_accuracy.parquet`, `wang_predictions.parquet`, `transfer_summary.json` |

Week 5 has no new notebook — it's revision against feedback on the paper and presentation.

The rationale-level orientation notebook (`../r1_orientation.ipynb`) loads AtGenExpress and is reused across R1-Q1 through R1-Q4. The question-specific orientation (`00_orient_and_precommit.ipynb` in this folder) adds Wang 2023 orientation, locks the three precommit decisions, and produces the `precommit.json` file that Notebooks 01–03 read from.

## Data

**Training side:** AtGenExpress abiotic stress series (Kilian et al., 2007), GEO accessions GSE5620–GSE5628. Loaded via `irilab2026.load_atgenexpress()`. Eight stresses plus control: cold, osmotic, salt, drought, genotoxic, UV-B, wounding, heat. Oxidative is at TAIR/NASCArrays only and is not part of the GEO download path — this is the GEO 8-class vs TAIR/NASCArrays 9-class scope decision in Notebook 00.

**Test side:** Wang et al. (2023) cold-stress RNA-seq. PRJNA767196 / SRP339213. Rosette tissue (shoot-equivalent); cold timepoints at 0 h, 2 h, 24 h, and 168 h.

## Caveats carried into these notebooks

- **The 168 h Wang 2023 timepoint is well outside AtGenExpress's 24 h max.** Handling decision (exclude vs out-of-distribution probe) is the Precommit 2 entry in Notebook 00.
- **Two Python ports stack in the integration step.** pyDESeq2 for VST and a Python ComBat (pycombat / InMoose / neuroCombat) for batch correction. A spot-check against an R reference is worth doing before trusting the integrated output.

## Status

All four notebooks have full body content. Notebook 01 (VST, ATH1 alignment, ComBat) was the largest engineering risk in Rationale 1 and landed. R1-Q4 has not yet gone through the program's paper / presentation cycle.
