# Notebooks

This directory holds every Jupyter notebook used in the Virtual Lab program. The structure mirrors the project's conceptual organization: two rationales, four questions per rationale, with a rationale-level orientation notebook that the four question notebooks build on.

## Layout

```
notebooks/
├── r1/                    # Rationale 1: gene expression / ML on omics data
│   ├── r1_orientation.ipynb  # AtGenExpress on-ramp (rationale-level)
│   ├── r1-q1/             # Common stress core
│   ├── r1-q2/             # Hub genes from co-expression
│   ├── r1-q3/             # SHAP feature-attribution batch-confound test
│   └── r1-q4/             # Cross-dataset stress classifier
└── r2/                    # Rationale 2: computer vision / plant disease
    ├── r2-q1/             # PV → PD transferability
    ├── r2-q2/             # Grad-CAM failure-mode taxonomy
    ├── r2-q3/             # Targeted vs kitchen-sink augmentation
    └── r2-q4/             # Cross-host transfer within PV
```

## Conventions

**Folder names.** Lowercase with hyphens (`r1-q1`, not `R1Q1` or `r1_q1`). Matches the question-page naming used elsewhere in the project documentation.

**Notebook filenames.** Numeric prefix in workflow order, then a short descriptive name: `01_deg_analysis.ipynb`, `02_core_overlap.ipynb`, and so on. The prefix is mildly ugly but makes file listings sort correctly without anyone having to think about it.

**Helpers.** Code that's shared across the notebooks in a single question folder — but not yet shared widely enough to belong in the `irilab2026` library — lives in a `helpers.py` next to those notebooks. The promotion rule from the project handoff still holds: code moves into `irilab2026/` only after it has been duplicated across three or more notebooks.

## Orientation notebooks

Each rationale has an orientation notebook. For Rationale 1, that's `r1/r1_orientation.ipynb`, which walks through the AtGenExpress dataset structure and ends with the data loaded into a known-good shape that the R1-Q1 through R1-Q4 notebooks pick up from. Rationale 2's orientation needs are still being scoped.

## Status

This directory is scaffolding. Most folders contain a README that names the upcoming notebooks but no notebooks yet. Notebooks land as each question is worked through, starting with the R1-Q1 stack.
