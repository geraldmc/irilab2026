# R1-Q1: Common stress core

What stress-responsive genes are shared across the abiotic stresses in AtGenExpress, and do those shared genes define a meaningful "common stress core"? Reproduces published findings; framed as methodological practice rather than novel discovery.

See the R1-Q1 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (in workflow order)

| # | File | Workflow row | Brief |
|---|---|---|---|
| 01 | `01_deg_analysis.ipynb` | Week 2 | Differential expression analysis per stress. Identifies stress-responsive gene sets relative to the matched control, per stress, within tissue. |
| 02 | `02_core_overlap.ipynb` | Week 3a | Set-intersection across the per-stress DEG lists to identify the common stress core. Produces a Venn diagram and the core gene set. |
| 03 | `03_enrichment.ipynb` | Week 3b | Functional enrichment on the common stress core. GO terms, pathway annotations, etc. |
| 04 | `04_comparison.ipynb` | Week 4 | Comparison of the recovered core against Hakkak & Tohidfar 2026's published consensus DEG list. |

The orientation notebook (`../orientation.ipynb`) loads the AtGenExpress data; these four notebooks pick up from there.

## Data

AtGenExpress (GEO accessions GSE5620–GSE5628). Loaded via `irilab2026.load_atgenexpress()`. Eight stresses plus control: cold, osmotic, salt, drought, genotoxic, UV-B, wounding, heat. Oxidative is at TAIR/NASCArrays only and is not part of the GEO download path.

## Caveats carried into these notebooks

Three caveats apply to every notebook in this folder. They come from the AtGenExpress reality-check and are documented in full on the R1-Q1 Notion question page; brief versions:

- **Compute cross-stress overlap within tissue, not pooled across.** Whole-plant stresses (cold, drought, heat) directly stress both shoot and root; locally applied stresses (e.g., wounding) directly stress one tissue and produce a systemic response in the other. Pooling shoot and root samples mixes direct and systemic responses.
- **Don't generalize this dataset's drought genes to field drought.** AtGenExpress drought is fast hydroponic-raft desiccation to ~10% fresh-weight loss, not gradual soil drying.
- **State the stress coverage you actually have.** Eight stresses from GEO, not nine. Don't claim "all AtGenExpress abiotic stresses" without the qualifier.

## Status

Scaffolding only. No notebooks drafted yet.
