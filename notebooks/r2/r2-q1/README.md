# R2-Q1: PV → PD transferability

Does a CNN classifier trained on PlantVillage (lab-condition images) transfer to PlantDoc (field-condition images)?

See the R2-Q1 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (provisional, from scoping handoff)

| # | File | Brief |
|---|---|---|
| 01 | `01_pv_orientation.ipynb` | PlantVillage data loading, structure, basic statistics. |
| 02 | `02_pd_orientation.ipynb` | PlantDoc data loading, structure, basic statistics. |
| 03 | `03_baseline_classifier.ipynb` | Train a baseline CNN classifier on PV. |
| 04 | `04_transfer_evaluation.ipynb` | Evaluate the PV-trained classifier on PD. |

This list is provisional. The two orientation notebooks may collapse into per-dataset sections within a single setup notebook, depending on how much each dataset needs.

## Data

PlantVillage (Mohanty et al. 2016, GitHub repo). PlantDoc (Singh et al. 2020, GitHub repo).

## Status

Not yet scaffolded.
