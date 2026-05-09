# R2-Q2: Grad-CAM failure-mode taxonomy

When CNN saliency methods (Grad-CAM, Guided Backpropagation, etc.) produce wrong or uninformative explanations, what categories of failure occur, and how often?

See the R2-Q2 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (provisional, from scoping handoff)

| # | File | Brief |
|---|---|---|
| 01 | `01_gradcam.ipynb` | Generate Grad-CAM saliency maps. Includes Adebayo-style sanity checks (which vanilla Grad-CAM passes; Guided variants do not). |
| 02 | `02_failure_coding.ipynb` | Manual taxonomy assignment over a sample of saliency maps. |
| 03 | `03_per_failure_summary.ipynb` | Summary statistics and visualization per failure mode. |

This list is provisional and will be refined when R2-Q2 is worked through.

## Data

PlantVillage (Mohanty et al. 2016). Possibly PlantDoc as a secondary set, depending on Adebayo-sanity-check results.

## Status

Not yet scaffolded.
