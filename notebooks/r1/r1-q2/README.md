# R1-Q2: Hub genes from co-expression

Are hub genes identified through WGCNA-style co-expression analysis on AtGenExpress enriched for known stress regulators relative to non-hub genes?

See the R1-Q2 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (provisional, from scoping handoff)

| # | File | Brief |
|---|---|---|
| 01 | `01_wgcna.ipynb` | Weighted co-expression network analysis on AtGenExpress. Module identification. |
| 02 | `02_hub_identification.ipynb` | Hub-gene identification within modules. |
| 03 | `03_comparison.ipynb` | Comparison against published hub-gene findings (anchor: Singhal et al. 2025). |

This list is from the first-pass notebook scoping and will be refined when R1-Q2 is worked through. Concrete notebook count and order are subject to change.

## Data

AtGenExpress (GEO accessions GSE5620–GSE5628). Loaded via `irilab2026.load_atgenexpress()`.

## Status

Not yet scaffolded. Will be picked up after R1-Q1 is complete.
