# R2-Q4: Cross-host transfer within PV

Within PlantVillage, when a disease appears on multiple host species, does a classifier trained on the disease in one host transfer to the same disease in a different host? Or does it learn a host-specific template rather than the disease itself?

See the R2-Q4 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (provisional, from scoping handoff)

| # | File | Brief |
|---|---|---|
| 01 | `01_cross_host_slice.ipynb` | Identify the ~4 diseases in PV that appear on multiple hosts and their host distributions. |
| 02 | `02_holdout_classifier.ipynb` | Train classifiers with leave-one-host-out splits. |
| 03 | `03_cross_host_evaluation.ipynb` | Evaluate cross-host generalization, per disease. |
| 04 | `04_per_disease_interpretation.ipynb` | Per-disease analysis of where transfer succeeds and fails. |

This list is provisional and will be refined when R2-Q4 is worked through.

## Data

PlantVillage (Mohanty et al. 2016).

## Caveats carried into these notebooks

- **Background-shortcut contamination.** Noyan (2022) Table 6 shows foreground-only blur predicts class at ~10% (vs random-guess ~2.6%), meaning PV's capture-bias contaminates the foreground too — not just the background. Removing the background does not fully isolate host-template effects.

## Status

Not yet scaffolded.
