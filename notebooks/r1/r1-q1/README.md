# R1-Q1: Common stress core

**Which genes form a "common stress core" that responds across many different kinds of stress?**

Reproduces a published finding — framed as methodological practice rather than novel discovery. The answer is known well enough that your result can be checked against it (Hakkak & Tohidfar, 2026 consensus DEGs are the comparison anchor).

See the R1-Q1 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (in workflow order)

| # | File | Workflow row | Brief | Output |
|---|---|---|---|---|
| 01 | `01_deg_analysis.ipynb` | Week 2 | Differential expression per (stress × tissue) using InMoose's port of limma. Sixteen (stress × tissue) pairs, 22,810 genes per pair. | `de_results.parquet` (long-format DE table, 364,960 rows) |
| 02 | `02_core_overlap.ipynb` | Week 3 | Set-intersection across the per-stress DEG lists to identify the common stress core; functional enrichment on the core. | `core_genes.parquet` (9,067-gene core), `bp_enrichment.parquet` (144 BP terms) |
| 03 | `03_consensus_compare.ipynb` | Week 4 | Compare the recovered core against Hakkak & Tohidfar (2026)'s published consensus. | `comparison_summary.json`, `comparison_genes.parquet` (21,249 rows) |

Week 5 has no new notebook — it's revision against feedback on the paper and presentation.

The rationale-level orientation notebook (`../r1_orientation.ipynb`) loads AtGenExpress and is reused across R1-Q1 through R1-Q4. R1-Q1 has no question-specific orientation notebook — Notebook 01 picks up directly from the rationale-level orientation.

## Data

AtGenExpress abiotic stress series (Kilian et al., 2007), GEO accessions GSE5620–GSE5628. Loaded via `irilab2026.load_atgenexpress()`. Eight stresses plus control: cold, osmotic, salt, drought, genotoxic, UV-B, wounding, heat. Oxidative is at TAIR/NASCArrays only and is not part of the GEO download path.

Comparison anchor: Hakkak & Tohidfar (2026) consensus DEG meta-analysis. Their supplementary files are student-uploaded to the same Drive folder as notebook outputs:

- `hakkak_2026_supp1.csv` — consensus DEG list
- `hakkak_2026_supp3.csv` — transcription factor table (note: AGI column is `ORF`, not `agi`)

## Caveats carried into these notebooks

Three caveats apply to every notebook in this folder. They come from the AtGenExpress reality-check and are documented in full on the R1-Q1 Notion question page; brief versions:

- **Compute cross-stress overlap within tissue, not pooled across.** Whole-plant stresses (cold, drought, heat) directly stress both shoot and root; locally applied stresses (e.g., wounding) directly stress one tissue and produce a systemic response in the other. Pooling shoot and root samples mixes direct and systemic responses.
- **Don't generalize this dataset's drought genes to field drought.** AtGenExpress drought is fast hydroponic-raft desiccation to ~10% fresh-weight loss, not gradual soil drying.
- **State the stress coverage you actually have.** Eight stresses from GEO, not nine. Don't claim "all AtGenExpress abiotic stresses" without the qualifier.

## Files

All notebook outputs and student-uploaded supplementary files share a Drive folder at `/content/drive/MyDrive/irilab2026_outputs/r1_q1/`:

| File | Producer | Consumer |
|---|---|---|
| `de_results.parquet` | Notebook 01 | Notebook 02 |
| `core_genes.parquet` | Notebook 02 | Notebook 03 |
| `bp_enrichment.parquet` | Notebook 02 | (paper / presentation) |
| `comparison_summary.json` | Notebook 03 | (paper / presentation) |
| `comparison_genes.parquet` | Notebook 03 | (paper / presentation) |
| `hakkak_2026_supp1.csv` | (student upload) | Notebook 03 |
| `hakkak_2026_supp3.csv` | (student upload) | Notebook 03 |
