# R2-Q2: Failure-mode distribution for PV → PD transfer

**When a PlantVillage-trained classifier misclassifies a PlantDoc image, what is it actually looking at?**

Categorizes the PlantDoc images a PV-trained classifier got wrong into a five-category pre-committed taxonomy: background-attended, leaf-shape-attended, lighting-attended, symptom-attended-but-wrong-class, plus an "other / ambiguous" bucket. Grad-CAM provides the attention maps; SAM provides leaf segmentation; numeric predicates on the attention pattern decide which category each failure lands in. Where R2-Q1 measured *where* PV → PD transfer breaks down, R2-Q2 asks *why*.

See the R2-Q2 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (in workflow order)

| # | File | Workflow row | Brief | Output |
|---|---|---|---|---|
| 01 | `01_orientation_and_precommit.ipynb` | Week 1 | Orients on the failure-mode literature (Adebayo et al. 2018, Noyan 2022, Grad-CAM mechanics) and on what R2-Q2 inherits from R2-Q1. Pre-commits the taxonomy, the categorization procedure (SAM-based leaf segmentation, four numeric predicates, first-match-wins ordering with multi-fires routing to `other_ambiguous`), and the aggregation level. | `precommit.json` |
| 02 | `02_load_and_filter.ipynb` | Week 2 | Loads R2-Q1's outputs (classifier path, PD predictions, class-space mappings), filters PD predictions to the rows where the model misclassified at the category level, annotates with true and predicted category, and characterizes the resulting misclassification set as hypotheses to revisit. | `working_set.parquet` (81 rows) |
| 03 | `03_sanity_checks_and_gradcam.ipynb` | Week 3 | Runs Adebayo et al. (2018)'s two sanity checks (model-parameter randomization and data randomization) on the Grad-CAM method to confirm it tracks model behavior rather than producing spurious heatmaps. Computes Grad-CAM heatmaps for each misclassification, with target class set to the model's predicted class. Heatmaps are saved at the last conv block's spatial resolution (7×7); N04 upsamples them at use time. | `sanity_check_trajectory.png`, `shuffled_resnet18.pt`, `heatmaps/*.npy` (81 files), `gradcam_metadata.parquet`, `sanity_check_results.json` |
| 04 | `04_categorization.ipynb` | Week 4 | Applies the taxonomy end-to-end. Segments leaves with SAM, validates segmentation quality, computes derived quantities per image, applies the four pre-committed predicates in order, produces the failure-mode distribution. | `sam_masks.parquet`, `categorizations.parquet`, `taxonomy_distribution.json`, `taxonomy_distribution.png` |

Week 5 has no new notebook — it's paper writing and revision against feedback.

The rationale-level orientation notebook (`../r2_orientation.ipynb`) introduces PlantVillage and PlantDoc and is reused across R2-Q1 through R2-Q4. **R2-Q2 also requires R2-Q1's outputs**: Notebook 02 in this folder reads R2-Q1's trained classifier, PlantDoc prediction table, and pre-commit file. Run R2-Q1 to completion before starting R2-Q2.

## Data

R2-Q2's primary inputs are not raw datasets but artifacts produced by R2-Q1's pipeline. Three live in `/content/drive/MyDrive/irilab2026_outputs/r2_q1/`:

- `baseline_resnet18.pt` — the PV-trained classifier; loaded by N03 for Grad-CAM passes and for the model-parameter randomization sanity check.
- `pd_predictions.parquet` — R2-Q1's 236-row PlantDoc prediction table; N02 filters this to the misclassification rows that become R2-Q2's working set.
- `precommit.json` from R2-Q1 — class-space mappings (PV ↔ PD); read by N02 for class-name lookups.

For the Grad-CAM and SAM passes, N03 and N04 also load PlantDoc images directly via `irilab2026.load_plantdoc()` from a curated Hugging Face Hub release.

## Caveats carried into these notebooks

These come from the R2-Q2 reality-check and are documented in full on the R2-Q2 Notion question page. Brief versions:

- **Run Adebayo's sanity checks before you interpret any Grad-CAM output.** Vanilla Grad-CAM passes the model-parameter and data-randomization sanity checks; Guided Backpropagation and Guided Grad-CAM do not. If you skip the checks and your method silently fails them, every "the model attended to X" claim afterward is undermined. Treat the sanity checks as a hard methodological requirement, not an optional refinement.
- **Pre-commit your taxonomy, decision rules, categorization procedure, and aggregation level — and include the "other / ambiguous" bucket.** A taxonomy chosen after seeing Grad-CAM heatmaps is a taxonomy fit to the data. The "other" bucket protects against forcing failures into prepared boxes; a non-trivial share landing there is itself a finding worth reporting. N01 writes the pre-commit file; Notebooks 02 through 04 read from it.
- **Aggregate to overall taxonomy distribution, not per-class.** PlantDoc has roughly 2,500 images across 27 classes; only a fraction will be misclassified, spread thinly across classes. Per-class counts within the taxonomy will be too small for fine-grained claims. Report the overall distribution; treat any per-class pattern as a hypothesis for follow-up, not a finding.

## Files

All notebook outputs share a Drive folder at `/content/drive/MyDrive/irilab2026_outputs/r2_q2/`:

| File | Producer | Consumer |
|---|---|---|
| `precommit.json` | Notebook 01 | Notebooks 02, 03, 04 |
| `working_set.parquet` | Notebook 02 | Notebooks 03, 04 |
| `sanity_check_trajectory.png` | Notebook 03 | (paper / presentation) |
| `shuffled_resnet18.pt` | Notebook 03 | Notebook 03 (cached so re-runs skip the 30-minute retrain) |
| `heatmaps/*.npy` (81 files) | Notebook 03 | Notebook 04 |
| `gradcam_metadata.parquet` | Notebook 03 | Notebook 04 |
| `sanity_check_results.json` | Notebook 03 | (paper / presentation) |
| `sam_masks.parquet` | Notebook 04 | (paper / presentation) |
| `categorizations.parquet` | Notebook 04 | (paper / presentation) |
| `taxonomy_distribution.json` | Notebook 04 | (paper / presentation) |
| `taxonomy_distribution.png` | Notebook 04 | (paper / presentation) |