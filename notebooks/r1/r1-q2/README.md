# R1-Q2: Hub genes from co-expression

**Are the most-connected ("hub") genes in stress-relevant co-expression modules enriched for known stress regulators?**

Builds per-tissue co-expression networks on AtGenExpress, identifies hub genes in stress-relevant modules, and tests whether those hubs are enriched for known stress-responsive transcription factors (Hakkak & Tohidfar (2026) Supplementary 3 reference set). The analytical pipeline — network construction, hub identification, enrichment test — is the work you'll defend in your writeup.

See the R1-Q2 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (in workflow order)

| # | File | Workflow row | Brief | Output |
|---|---|---|---|---|
| 00 | `00_question_orientation.ipynb` | Week 1 | WGCNA-specific prep on top of the rationale-level orientation: MAD-filter to high-variance genes per tissue, then pre-commit your method choices (gene filtering, network construction, hub identification, reference set, statistical framework, background) in writing. | `shoot_filtered.parquet`, `root_filtered.parquet`, `precommit.json` |
| 00b | `00b_matrix_quality_check.ipynb` | Week 1 | Read-only diagnostics against N0's outputs. Sample-level structure (PCA, per-condition counts, pairwise correlation), gene-level structure (effectively-constant genes, surviving AFFX control probes), and the whole-matrix correlation distribution. The synthesis at the end is where you decide whether to proceed to N1 or revise N0 and re-run. | — |
| 01 | `01_wgcna.ipynb` | Week 2 | Per-tissue co-expression networks via PyWGCNA. Two parallel pipelines (shoot, root) using your committed network-construction parameters. | `shoot.p`, `root.p` (PyWGCNA pickles), `network_summary.json` |
| 02 | `02_hub_identification.ipynb` | Week 3 | Identify stress-relevant modules (`|r| ≥ 0.3` with a stress trait), compute kME within each, apply the kME ≥ 0.8 hub threshold, and assemble per-tissue hub tables. Cross-tissue overlap preview at the end. | `shoot_hubs.parquet` (212 hubs), `root_hubs.parquet` (467 hubs), `hub_summary.json` |
| 03 | `03_comparison.ipynb` | Week 4 | Probe → AGI mapping; hypergeometric enrichment test against Hakkak & Tohidfar (2026) Supplementary 3 with Bonferroni correction across tissues; cross-tissue convergence; paper-ready outputs. | `shoot_compare.parquet`, `root_compare.parquet`, `cross_tissue_compare.parquet`, `comparison_summary.json` |

Week 5 has no new notebook — it's revision against feedback on the paper and presentation.

The rationale-level orientation notebook (`../r1_orientation.ipynb`) loads AtGenExpress and is reused across R1-Q1 through R1-Q4. The question-specific orientation (`00_question_orientation.ipynb` in this folder) picks up from there and adds the WGCNA-specific prep — gene filtering and pre-commits — that Notebooks 00b, 01, 02, and 03 consume.

## Data

AtGenExpress abiotic stress series (Kilian et al., 2007), GEO accessions GSE5620–GSE5628. Loaded via `irilab2026.load_atgenexpress()`. Eight stresses plus control: cold, osmotic, salt, drought, genotoxic, UV-B, wounding, heat. Oxidative is at TAIR/NASCArrays only and is not part of the GEO download path.

Comparison anchor: Hakkak & Tohidfar (2026) Supplementary Table 3 — roughly 60 stress-responsive transcription factors across 15 TF families. The same file used by R1-Q1; student-uploaded to this folder as `hakkak_2026_supp3.csv` (note: the AGI column is named `ORF`, not `agi`).

## Caveats carried into these notebooks

These come from the AtGenExpress reality-check and the R1-Q2 method-choices surface area; they are documented in full on the R1-Q2 Notion question page. Brief versions:

- **Build per-tissue networks, not pooled across tissues.** Co-expression is sensitive to tissue identity. Pool shoot and root and the dominant signal will be the shoot-vs-root distinction, not stress response — your hubs will reflect tissue identity rather than what you're trying to study.
- **Pre-commit your method choices before you run anything.** Soft-thresholding power, module-detection parameters, hub-ness metric, hub threshold, statistical test, multiple-testing correction. If you tune these after seeing results, you're fitting your method to your conclusion. N0 writes the pre-commit file; every later notebook reads from it.
- **State the stress coverage you actually have.** Eight stresses from GEO, not nine. Don't claim "all AtGenExpress abiotic stresses" without the qualifier.

## Files

All notebook outputs and student-uploaded supplementary files share a Drive folder at `/content/drive/MyDrive/irilab2026_outputs/r1_q2/`:

| File | Producer | Consumer |
|---|---|---|
| `shoot_filtered.parquet` | Notebook 00 | Notebooks 00b, 01, 03 (as background) |
| `root_filtered.parquet` | Notebook 00 | Notebooks 00b, 01, 03 (as background) |
| `precommit.json` | Notebook 00 | Notebooks 00b, 01, 02, 03 |
| `shoot.p` | Notebook 01 | Notebook 02 |
| `root.p` | Notebook 01 | Notebook 02 |
| `network_summary.json` | Notebook 01 | (paper / presentation) |
| `shoot_hubs.parquet` | Notebook 02 | Notebook 03 |
| `root_hubs.parquet` | Notebook 02 | Notebook 03 |
| `hub_summary.json` | Notebook 02 | (paper / presentation) |
| `shoot_compare.parquet` | Notebook 03 | (paper / presentation) |
| `root_compare.parquet` | Notebook 03 | (paper / presentation) |
| `cross_tissue_compare.parquet` | Notebook 03 | (paper / presentation) |
| `comparison_summary.json` | Notebook 03 | (paper / presentation) |
| `hakkak_2026_supp3.csv` | (student upload) | Notebook 03 |