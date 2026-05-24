# Rationale 1

*Decoding Plant Stress: Machine Learning Approaches to Gene Expression and Regulatory Networks.*

Rationale 1's four questions all draw on the **AtGenExpress** abiotic stress microarray dataset (Kilian et al., 2007). R1-Q4 additionally uses a cold-stress RNA-seq dataset (Wang et al., 2023) as a cross-platform test set.

## Notebooks in this rationale

- **`r1_orientation.ipynb`** — AtGenExpress on-ramp. Walks through the dataset structure (eight stresses plus control, shoot and root tissue, time courses up to 24 hours), uses `irilab2026.load_atgenexpress()` to pull the data, and ends with the data in the shape that the question notebooks pick up from. Run this first, regardless of which question you're working on.
- **`r1-q1/`** — Common stress core: which genes respond across many different kinds of stress?
- **`r1-q2/`** — Hub genes from co-expression: do hubs in stress-relevant co-expression modules correspond to known stress regulators?
- **`r1-q3/`** — Feature attribution under batch effects: when a classifier is trained on data pooled across studies, are the features it relies on biological signals or batch artifacts?
- **`r1-q4/`** — Cross-dataset stress classifier: do features learned on microarray data transfer to RNA-seq?

Each question folder has its own README — that's where you'll find the weekly workflow, the data each notebook uses, what each notebook produces, and any caveats specific to that question.