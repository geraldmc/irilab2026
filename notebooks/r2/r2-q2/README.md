# R2-Q2: Failure-mode distribution for PV→PD transfer

**When a PlantVillage-trained classifier misclassifies a PlantDoc image, what is it actually looking at?**

Categorizes 81 PD misclassifications into a five-category pre-committed taxonomy using Grad-CAM attention maps, SAM-based leaf segmentation, and numeric predicates on the attention pattern. The headline finding (69% background-attention) provides direct attention-map evidence for the PV shortcut-learning hypothesis that motivates R2 as a whole.

See the R2-Q2 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (in workflow order)

| # | File | Workflow row | Brief | Output |
|---|---|---|---|---|
| 01 | `01_orientation_and_precommit.ipynb` | Week 1 | Question-specific orientation. Orients on the failure-mode literature (Adebayo et al. 2018, Noyan 2022, Grad-CAM mechanics) and recaps the R2-Q1 outputs this question inherits. Locks the five-category taxonomy, the four predicates with their thresholds, the segmentation method (SAM with single point at image center), the predicate scheme (first-match-wins, multi-fires to other_ambiguous), and the aggregation level (overall_taxonomy_distribution). | `precommit.json` |
| 02 | `02_load_and_filter.ipynb` | Week 2 | Loads R2-Q1's outputs — the trained ResNet-18 classifier path, the PD prediction table, the R2-Q1 precommit for class-space mappings. Filters PD predictions to the 81 rows where the model misclassified at the category level. Annotates with `true_category` and `predicted_category`. Characterizes the misclassification set (count, host distribution, disease-category distribution, confidence distribution) as discussion-level hypotheses. | `working_set.parquet` (81 rows) |
| 03 | `03_sanity_checks_and_gradcam.ipynb` | Week 3 | Runs Adebayo et al. (2018)'s sanity checks (model-parameter randomization and data randomization) on the Grad-CAM method to confirm it tracks model behavior rather than producing spurious heatmaps. Then computes Grad-CAM attention heatmaps for each misclassification, target class = predicted class. Heatmaps are at the last conv block's spatial resolution (7×7) and are upsampled to native image resolution in N04 Section 6. | `heatmaps/*.npy` (81 files), `gradcam_metadata.parquet` |
| 04 | `04_categorization.ipynb` | Week 4 | Applies the taxonomy end-to-end. Segments leaves with SAM, validates segmentation quality, filters the working set, computes five derived quantities per image, applies the four predicates in the pre-committed order, produces the failure-mode distribution. | `categorizations.parquet`, `taxonomy_distribution.json`, `taxonomy_distribution.png` |

Week 5 has no new notebook — it's paper writing and revision against feedback.

The rationale-level orientation notebook (`../r2_orientation.ipynb`) introduces PlantVillage and PlantDoc and is reused across R2-Q1 through R2-Q4. The question-specific orientation (`01_orientation_and_precommit.ipynb` in this folder) picks up from there and commits the methodological choices that the rest of the question executes.

R2-Q2 takes the **Posture B (reuse)** approach to R2-Q1: rather than retraining a classifier or re-running PD inference, N02 inherits R2-Q1's classifier and PD prediction table as inputs. The pedagogical content of R2-Q2 is the failure-inspection workflow (Adebayo sanity checks, Grad-CAM, taxonomy categorization), not the classifier-training workflow R2-Q1 already covers.

## Data

PlantVillage (Mohanty et al. 2016) and PlantDoc (Singh et al. 2020), loaded via `iri.load_plantvillage()` and `iri.load_plantdoc()`. PV provides the training distribution (controlled lab conditions, single leaves on uniform backgrounds); PD provides the held-out evaluation distribution (field conditions, varied backgrounds, multi-leaf scenes). The working set consists of the 81 PD images that the PV-trained ResNet-18 from R2-Q1 misclassifies at the category level.

No external comparison anchor for R2-Q2. The interpretive frame is Noyan (2022)'s shortcut-learning result on PV: a model that has learned PV's background features will fail when those features change.

## Caveats carried into these notebooks

Three caveats apply to the analysis chain. They are documented in full on the R2-Q2 Notion question page and surfaced in N04's prose at the point they apply.

- **The working set was filtered.** 13 of 81 misclassifications were excluded because SAM produced a degenerate mask (`fg_fraction` outside `[0.05, 0.85]`). The excluded images were inspected and found to be ill-posed segmentation problems — wide field shots, multi-leaf compositions without a dominant foreground, low-contrast foliage-on-foliage scenes — rather than method failures. The analysis is therefore restricted to images where the segmentation problem was well-posed. The unfiltered 81-row table is preserved on disk as `working_set_unfiltered.parquet`.
- **The predicate scheme has known dependencies.** Under the precommit's first-match-wins ordering, 9 images that fired the `lighting_attended` predicate also fired `background_attended` and were routed to `other_ambiguous` as multi-fires. Under a different tie-break rule, `lighting_attended` could have been a substantively-populated category. The `multi_fire_patterns` field in `taxonomy_distribution.json` carries the raw evidence.
- **The methodology diverged from the precommit in two places.** N01 committed to IoU-based validation against a hand-segmented reference set and a color-thresholding fallback. N04 executed validation as a qualitative visual inspection and the "fallback" as the working-set filter described above. Both deviations are defensible (see N04 Section 4 opener and Section 5 opener) but are real deviations from a locked plan and need to be reflected back into N01 before the program ships.

## Findings worth carrying forward

These surfaced during the R2-Q2 analysis and feed directly into the Week-5 paper.

**Headline result.** 69% of PV→PD misclassifications (47 of 68 analyzed) show the model attending to non-leaf content (`background_attended`). Attention to a small in-leaf region with the wrong class label (`symptom_attended_but_wrong_class`) is rare (6%, 4 images). Attention to leaf edges (`leaf_shape_attended`) is 3%. The combination of high background-attention and low right-place-wrong-label provides direct attention-map evidence for Noyan (2022)'s PV shortcut-learning hypothesis: the model is not even looking at the leaf when it fails.

**fg_fraction is a single-signal diagnostic for SAM reliability.** Values of SAM's foreground-fraction near 0 or 1 reliably indicate that the segmentation problem was ill-posed (no dominant leaf foreground); values in the middle of the distribution reliably indicate that SAM produced a usable mask. A 10-image stratified visual check surfaced the pattern; a 9-image targeted check on the borderline band (`0.05 ≤ fg < 0.10`) tuned the lower bound. Both inspections stay in the notebook as the methods-section evidence. This pattern is transferable to any future question that uses prompt-driven segmentation on heterogeneous imagery.

**Visual inspection beats IoU when boundary precision is asymmetric.** Hand-traced reference boundaries are systematically less tight than SAM's, which makes IoU values hard to interpret as pass/fail thresholds — typical agreement-with-SAM lands in the 0.85–0.92 range. A qualitative visual check on a small stratified sample gives the same kind of evidence (does the method reliably find the leaf?) without the precision-asymmetry problem.

## Library and infrastructure notes

`irilab2026` provides `iri.setup()`, `iri.output_dir()`, `iri.load_plantvillage()`, `iri.load_plantdoc()`, and `iri.build_baseline_model()`. N03 installs `pytorch-grad-cam` at point of use; N04 Section 2 installs `segment-anything` at point of use and downloads the SAM checkpoint to a Drive-cached location to avoid re-downloading across sessions. Both are single-notebook dependencies and are not bundled into `irilab2026`.

The trained classifier `baseline_resnet18.pt` lives in **R2-Q1's** output directory (`iri.output_dir("r2_q1")`), not R2-Q2's. N02 reads it by path; N03 actually loads it into memory and runs inference for the sanity checks and Grad-CAM passes.

R2-Q2 notebook outputs and inputs share a folder at `/content/drive/MyDrive/irilab2026_outputs/r2_q2/`. Inter-notebook artifacts:

| File | Producer | Consumer |
|---|---|---|
| `precommit.json` | N01 | N02, N03, N04 |
| `working_set.parquet` | N02 | N03, N04 |
| `heatmaps/*.npy` | N03 | N04 |
| `gradcam_metadata.parquet` | N03 | N04 |
| `categorizations.parquet` | N04 | (paper / presentation) |
| `taxonomy_distribution.json` | N04 | (paper / presentation) |
| `taxonomy_distribution.png` | N04 | (paper / presentation) |

N04 additionally produces seven intra-notebook intermediate artifacts (SAM masks, mask metadata, visual-check figures, filtered and unfiltered working sets, derived quantities, predicate results) that document the methodology trail. They are not consumed by any later notebook but are present in the output directory for audit.

The N04 SAM run is the runtime bottleneck — roughly 50 seconds on a T4 for the 81 working-set images, and an additional minute or so for the 68-image derived-quantities loop. N03's Adebayo sanity checks add a few minutes on top of the Grad-CAM passes. Everything else runs in seconds.

## Status

All four notebooks complete and verified to run on Colab with a T4 GPU. The three Week-5 deliverables exist on disk. The Section 9 forward-pointer to paper writing is in place.

Remaining R2-Q2 work is external to the notebook chain:

- N01 precommit cleanup — three field updates to bring the precommit into agreement with the executed methodology (validation approach, validation sample size, fallback definition)
- EQ#2 (per-question essential question; due Week 2 of program — not yet drafted)
- Draft presentation (Week 3)
- Final paper and presentation (Week 4)
- Revisions against feedback (Week 5)

R2-Q2 and R2-Q1 are complementary by design: R2-Q1 asks where transfer breaks down, R2-Q2 asks why. Both findings can be read against the same shortcut-learning hypothesis. The Week-5 paper synthesizes both questions into a unified argument about how a PV-trained ResNet-18 generalizes (or fails to) on PlantDoc.