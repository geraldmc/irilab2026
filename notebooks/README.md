# Notebooks

This directory holds every Jupyter notebook in the Virtual Lab program. The structure mirrors the program's organization: two rationales, four questions per rationale, with a rationale-level orientation notebook that the question notebooks build on.

## Layout

```
notebooks/
├── r1/                       # Rationale 1: gene expression / ML on omics data
│   ├── r1_orientation.ipynb  # AtGenExpress on-ramp
│   ├── r1-q1/                # Common stress core
│   ├── r1-q2/                # Hub genes from co-expression
│   ├── r1-q3/                # SHAP feature-attribution batch-confound test
│   └── r1-q4/                # Cross-dataset stress classifier
└── r2/                       # Rationale 2: computer vision / plant disease
    ├── r2_orientation.ipynb  # PlantVillage / PlantDoc on-ramp
    ├── r2-q1/                # PV → PD transferability
    ├── r2-q2/                # Grad-CAM failure-mode taxonomy
    ├── r2-q3/                # Targeted vs kitchen-sink augmentation
    └── r2-q4/                # Cross-host transfer within PV
```

## Where to start

Pick your rationale, run its orientation notebook first, then open the README in your question folder.

- **Rationale 1 students** — open `r1/r1_orientation.ipynb`. It walks through the AtGenExpress dataset structure and ends with the data loaded into a known-good shape that the R1-Q1 through R1-Q4 notebooks pick up from.
- **Rationale 2 students** — open `r2/r2_orientation.ipynb`. It does the same job for the PlantVillage and PlantDoc image datasets used across R2-Q1 through R2-Q4.

Each question folder has its own README that names the notebooks in that folder, the data they use, what they produce, and any caveats specific to that question. That's where you'll spend most of your time — this top-level README is just the map.

## Conventions

**Folder names.** Lowercase with hyphens: `r1-q1`, `r2-q3`.

**Notebook filenames.** A two-digit numeric prefix in workflow order, then a short descriptive name — for example, `01_deg_analysis.ipynb`, `02_core_overlap.ipynb`. The prefix makes file listings sort in run order, so you can read the folder top-to-bottom and follow the workflow.

## Running the notebooks

For install and runtime instructions (Colab is the supported path; local Jupyter works too), see the repository's top-level [README](../README.md).