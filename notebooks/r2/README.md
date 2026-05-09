# Rationale 2

*Plant disease recognition: convolutional neural networks, transferability, and interpretability.*

Rationale 2's four questions all draw on PlantVillage (PV) and PlantDoc (PD) image datasets. Different combinations of those datasets and different methodological postures across the four questions.

## Notebooks in this rationale

- **`r2-q1/`** — PV → PD transferability: does a classifier trained on lab-condition images transfer to field images?
- **`r2-q2/`** — Grad-CAM failure-mode taxonomy: when CNN saliency methods fail, what does the failure look like?
- **`r2-q3/`** — Targeted vs kitchen-sink augmentation: is targeted augmentation actually better than throwing everything at the model?
- **`r2-q4/`** — Cross-host transfer within PV: does a classifier learn a disease, or just a disease-on-a-host?

Whether Rationale 2 needs its own orientation notebook (analogous to `r1/orientation.ipynb`) is still being scoped. PV is well-documented and has straightforward loading; PD is a smaller dataset with its own quirks. An R2 orientation notebook may make sense, or per-question setup may be enough.

## Status

Not yet scaffolded. R2 work is downstream of completing R1-Q1 as the prototype.
