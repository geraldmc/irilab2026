# R2-Q1: PV → PD transferability

**How well does a classifier trained on PlantVillage's lab-condition images transfer to PlantDoc's field photographs?**

Train a CNN classifier on PlantVillage, evaluate it on PlantDoc, and measure the transfer gap with a defensible statistical test. The lab → field gap is well-established in the literature (Singh et al., 2020; Noyan, 2022); the work here is in measuring it on your own model and characterizing which host groups and disease categories transfer cleanly versus poorly.

See the R2-Q1 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (in workflow order)

| # | File | Workflow row | Brief | Output |
|---|---|---|---|---|
| 01 | `01_pv_orientation.ipynb` | Week 1 | PlantVillage walkthrough beyond the rationale-level orientation: the 38-class space, host-disease pairings, and the class imbalance you'll need to consider when designing the transfer evaluation. | — |
| 02 | `02_pd_orientation.ipynb` | Week 1 | PlantDoc walkthrough — the 27-class space, the field-photograph quirks — and the three Week-1 pre-commits: aggregation level, PV ↔ PD class-space remapping, and statistical test for the gap. | `precommit.json` |
| 03 | `03_baseline_classifier.ipynb` | Week 2 | Train a ResNet-18 on PlantVillage. Evaluate PV-internal accuracy on a held-out test split as a go/no-go check before transfer testing. | `baseline_resnet18.pt`, `eq2_results.json`, `training_curves.png` |
| 04 | `04_transfer_gap_measure.ipynb` | Week 3 | Apply the trained classifier to PlantDoc using your pre-committed class-space remapping. Bootstrap a confidence interval on the PV-internal vs PV → PD accuracy gap at your committed aggregation level. | `pv_predictions.parquet`, `pd_predictions.parquet`, `transfer_gap.parquet`, `gap_summary.json` |
| 05 | `05_gap_characterization.ipynb` | Week 4 | Decompose the gap by host and by disease category, with per-cut bootstrap confidence intervals. Cuts where per-group counts are too small to support a claim are suppressed rather than reported. | `gap_decomposition.parquet`, `characterization_summary.json`, host-cut and category-cut PNG figures |

Week 5 has no new notebook — it's revision against feedback on the paper and presentation.

The rationale-level orientation notebook (`../r2_orientation.ipynb`) introduces PlantVillage and the Noyan (2022) background-pixel finding that shapes how the R2 questions probe what a PV-trained classifier is actually learning. Notebook 01 in this folder picks up with PlantVillage's class structure in more detail; Notebook 02 introduces PlantDoc and produces the Week-1 pre-commit file that Notebooks 03, 04, and 05 read.

## Data

**PlantVillage** (Mohanty et al., 2016) — about 54,000 leaf images across 38 classes spanning 14 plant species and their diseases, photographed against uniform lab backgrounds. Loaded via `irilab2026.load_plantvillage()` from a curated Hugging Face Hub release.

**PlantDoc** (Singh et al., 2020) — about 2,598 field photographs across 27 classes. Loaded via `irilab2026.load_plantdoc()`, also from Hugging Face Hub.

PV and PD have different class spaces, so a direct evaluation is not possible without a remapping. Your Week-1 pre-commit captures that remapping along with your aggregation level (host group, disease category, or another defensible cut) and your statistical test.

## Caveats carried into these notebooks

These come from the R2-Q1 reality-check and are documented in full on the R2-Q1 Notion question page. Brief versions:

- **Measure the gap on your own model — don't assume the published numbers transfer.** PV → PD gaps have been reported in the literature, but their *size* depends on architecture, training choices, and augmentation. Cite published gaps for context; report your gap as your gap.
- **Pre-commit your aggregation level, class-space remapping, and statistical test before you measure.** Tune any of these after seeing results and you're choosing the verdict you want. N02 writes the pre-commit file; Notebooks 03 through 05 read from it.
- **Aggregate to coarser groupings before you compare.** PlantDoc has roughly 2,500 images across 27 classes — per-class counts are too small to support reliable per-class claims. Aggregate to host groups, to fungal/bacterial/viral disease categories, or to another grouping you can defend.

## Files

All notebook outputs share a Drive folder at `/content/drive/MyDrive/irilab2026_outputs/r2_q1/`:

| File | Producer | Consumer |
|---|---|---|
| `precommit.json` | Notebook 02 | Notebooks 03, 04, 05 |
| `baseline_resnet18.pt` | Notebook 03 | Notebook 04 |
| `eq2_results.json` | Notebook 03 | (paper / presentation) |
| `training_curves.png` | Notebook 03 | (paper / presentation) |
| `pv_predictions.parquet` | Notebook 04 | (paper / presentation) |
| `pd_predictions.parquet` | Notebook 04 | Notebook 05 |
| `transfer_gap.parquet` | Notebook 04 | (paper / presentation) |
| `gap_summary.json` | Notebook 04 | (paper / presentation) |
| `gap_decomposition.parquet` | Notebook 05 | (paper / presentation) |
| `characterization_summary.json` | Notebook 05 | (paper / presentation) |