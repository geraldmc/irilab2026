# R2-Q3: Targeted vs kitchen-sink augmentation

Does targeted image augmentation (transformations chosen to address known failure modes) outperform kitchen-sink augmentation (RandAugment-style throw-everything-at-it) on plant disease classification?

See the R2-Q3 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (provisional, from scoping handoff)

| # | File | Brief |
|---|---|---|
| 01 | `01_baseline.ipynb` | Baseline classifier with no augmentation. May share infrastructure with R2-Q1. |
| 02 | `02_kitchen_sink.ipynb` | Classifier trained with RandAugment-style aggressive augmentation. |
| 03 | `03_targeted.ipynb` | Classifier trained with targeted augmentation chosen against known PV/PD failure modes. |
| 04 | `04_comparison.ipynb` | Statistical comparison across the three regimes. |

This list is provisional and will be refined when R2-Q3 is worked through.

## Data

PlantVillage (Mohanty et al. 2016). Possibly PlantDoc as a transfer evaluation.

## Status

Not yet scaffolded.
