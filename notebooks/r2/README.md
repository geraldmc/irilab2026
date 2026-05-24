# Rationale 2

*Decoding Plant Health: Computer Vision Approaches to Disease Detection and Model Robustness.*

Rationale 2's four questions all use the **PlantVillage** (PV) dataset (Mohanty et al., 2016) — about 54,000 leaf images across 38 classes spanning 14 plant species and their diseases. R2-Q1 additionally evaluates against **PlantDoc** (PD; Singh et al., 2020), a smaller dataset of field photographs. A finding by Noyan (2022) — that PV class labels can be predicted from just eight background pixels at about 49% accuracy — shapes how all four questions probe what a classifier trained on PV is actually learning.

## Notebooks in this rationale

- **`r2_orientation.ipynb`** — PlantVillage on-ramp. Introduces the dataset, shows you what lab-condition disease photographs look like, walks through the 38-class structure and its imbalance, and ends with a sample of the data cached locally. Run this first, regardless of which question you're working on.
- **`r2-q1/`** — PV → PD transferability: does a classifier trained on lab-condition images transfer to field photographs?
- **`r2-q2/`** — Grad-CAM failure modes: when a classifier's attention is in the wrong place, what categories of failure show up?
- **`r2-q3/`** — Targeted vs kitchen-sink augmentation: is targeted augmentation actually better than throwing everything at the model?
- **`r2-q4/`** — Cross-host transfer within PV: when the same disease appears on different host plants, does the model learn the disease or the host?

Each question folder has its own README — that's where you'll find the weekly workflow, the data each notebook uses, what each notebook produces, and any caveats specific to that question.