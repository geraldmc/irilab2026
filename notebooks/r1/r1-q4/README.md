# R1-Q4: Cross-dataset stress classifier

Does a multi-class stress classifier trained on AtGenExpress generalize to Wang 2023 cold-stress RNA-seq with above-chance accuracy? Cross-platform integration via VST + ComBat.

See the R1-Q4 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (in workflow order)

| # | File | Workflow row | Brief | Output |
|---|---|---|---|---|
| 00 | `00_orient_and_precommit.ipynb` | Week 1 | Question-specific orientation. Inspect AtGenExpress and Wang 2023; lock three precommit decisions in writing. | `precommit.json` (data source plus stress-class scope, Wang 2023 168 h timepoint handling, "above-chance" null) |
| 01 | `01_integration.ipynb` | Week 2 | Cross-platform integration. VST on Wang 2023 RNA-seq counts; align to ATH1 microarray probe space; ComBat across both datasets. | `wang_aligned.parquet`, `integrated_matrix.parquet`, `integration_summary.json` |
| 02 | `02_classifier.ipynb` | Week 3 | Train the multi-class stress classifier on the integrated AtGenExpress training set; evaluate on a held-out AtGenExpress split. | `classifier.pkl`, `classifier_summary.json`, `classifier_metrics.parquet`, `classifier_confusion.parquet`, `atgenexpress_test_split.parquet` |
| 03 | `03_wang_evaluation.ipynb` | Week 4 | Apply the trained classifier to integrated Wang 2023; per-timepoint accuracy; compare against the precommitted "above-chance" null. | `transfer_metrics.parquet`, `transfer_confusion.parquet`, `transfer_predictions.parquet`, `transfer_vs_within_comparison.parquet`, `transfer_summary.json` |

Week 5 has no new notebook — it's revision against feedback on the paper and presentation.

The rationale-level orientation notebook (`../r1_orientation.ipynb`) loads AtGenExpress and is reused across R1-Q1 through R1-Q4. The question-specific orientation (`00_orient_and_precommit.ipynb` in this folder) adds Wang 2023 orientation, locks the three precommit decisions, and produces the `precommit.json` file that Notebooks 01–03 read from.

Each notebook ends in a structured pass / partial / fail gate. A `fail` upstream blocks the chain: Notebook 02 refuses to train on a failed integration gate, and Notebook 03 refuses to evaluate on a failed integration or accuracy gate.

## Data

**Training side:** AtGenExpress abiotic stress series (Kilian et al., 2007), GEO accessions GSE5620–GSE5628. Loaded via `irilab2026.load_atgenexpress()`. Eight stresses plus control: cold, osmotic, salt, drought, genotoxic, UV-B, wounding, heat. Oxidative is at TAIR/NASCArrays only and is not part of the GEO download path — this is the GEO 8-class vs TAIR/NASCArrays 9-class scope decision in Notebook 00.

**Test side:** Wang et al. (2023) cold-stress RNA-seq, loaded via the mentor-provided loader (see the Wang 2023 data descriptor for accession details). Rosette tissue (shoot-equivalent); cold timepoints at 0 h, 2 h, 24 h, and 168 h. The Wang side is class-imbalanced: 3 control samples (0 h) versus 9 cold samples (2 h, 24 h, 168 h).

## Caveats carried into these notebooks

- **Filter the AtGenExpress training set to shoot samples only.** Wang 2023 sequenced rosette tissue, which is shoot-equivalent. AtGenExpress carries both shoot and root; training on the pooled set would inject tissue-vs-tissue variance into a comparison meant to test cold response. NB01 Section 2.2 does this filter before any integration.
- **VST first, then ComBat — the order matters.** VST (via `pyDESeq2`) stabilizes the count-scale variance of the Wang RNA-seq data before ComBat (via `inmoose.pycombat_norm`) removes the platform-level batch effect between RNA-seq and the ATH1 microarray. Run the wrong way around and both steps are undermined. NB01 Section 6 enforces the order.
- **The integration rests on two Python ports of R tools.** VST through `pyDESeq2`, ComBat through `inmoose.pycombat_norm`. NB01 Section 7's diagnostics — PCA before/after correction, per-gene stress-signal preservation, and a six-gene CBF cold-marker spot check — plus the Section 8 integration gate exist to certify the joint matrix before any training happens.
- **The 168 h Wang 2023 timepoint is well outside AtGenExpress's 24 h maximum.** The handling decision (exclude vs include as an out-of-distribution probe) is the Precommit 2 entry in Notebook 00, read by NB01 (timepoint filter on load) and NB03 (per-timepoint breakout).
- **Ecotype provenance is inferred, not stated.** The Wang 2023 data descriptor does not name the ecotype; Col-0 is confirmed indirectly through Guo et al. 2023 from the same research group. Unlikely to affect transfer (both studies are Col-0), but the methods should say what is confirmed directly versus inferred.
- **The Wang test side is small and imbalanced (3 control / 9 cold).** This is why Precommit 3's "above-chance" null is framed as binary cold-vs-control balanced accuracy (50% null) or multi-class per-class recall rather than raw accuracy, and why NB03's transfer gate includes a sample-size sufficiency check.

## Files

All notebook outputs share a Drive folder at `/content/drive/MyDrive/irilab2026_outputs/r1_q4/`:

| File | Producer | Consumer |
|---|---|---|
| `precommit.json` | Notebook 00 | Notebooks 01, 02, 03 |
| `wang_aligned.parquet` | Notebook 01 | (paper / diagnostic; not reloaded downstream) |
| `integrated_matrix.parquet` | Notebook 01 | Notebooks 02, 03 |
| `integration_summary.json` | Notebook 01 | Notebooks 02, 03 (refuse-on-fail gate) |
| `classifier.pkl` | Notebook 02 | Notebook 03 |
| `classifier_summary.json` | Notebook 02 | Notebook 03 (refuse-on-fail gate) |
| `classifier_metrics.parquet` | Notebook 02 | Notebook 03 |
| `classifier_confusion.parquet` | Notebook 02 | Notebook 03 (loaded for completeness; not computed on) |
| `atgenexpress_test_split.parquet` | Notebook 02 | (paper / reproducibility) |
| `transfer_metrics.parquet` | Notebook 03 | (paper / presentation) |
| `transfer_confusion.parquet` | Notebook 03 | (paper / presentation) |
| `transfer_predictions.parquet` | Notebook 03 | (paper / presentation) |
| `transfer_vs_within_comparison.parquet` | Notebook 03 | (paper / presentation) |
| `transfer_summary.json` | Notebook 03 | (paper / presentation) |

`classifier.pkl` is a joblib-pickled `{"scaler": ..., "classifier": ...}` bundle (a scikit-learn logistic regression), so `.pkl` is correct here — unlike the Rationale 2 chains, which save PyTorch state dicts as `.pt`.

## Status

All four notebooks have full body content. Notebook 01 (VST, ATH1 alignment, ComBat) was the largest engineering risk in Rationale 1 and landed. R1-Q4 has not yet gone through the program's paper / presentation cycle.
