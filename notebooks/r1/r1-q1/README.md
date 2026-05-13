# R1-Q1: Common stress core

**Which genes form a "common stress core" that responds across many different kinds of stress?**

Reproduces a published finding — framed as methodological practice rather than novel discovery. The answer is known well enough that a student's result can be checked against it (Hakkak & Tohidfar 2026 consensus DEGs are the comparison anchor).

See the R1-Q1 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (in workflow order)

| # | File | Workflow row | Brief | Output |
|---|---|---|---|---|
| 00 | `00_question_orientation.ipynb` | Week 1 | Question-specific orientation. Picks up from the rationale-level orientation and ends with the per-stress, per-tissue data shape that Notebook 01 consumes. | — |
| 01 | `01_deg_analysis.ipynb` | Week 2 | Differential expression per (stress × tissue) using InMoose's port of limma. Sixteen (stress × tissue) pairs, 22,810 genes per pair. | `de_results.parquet` (long-format DE table, 364,960 rows) |
| 02 | `02_core_overlap.ipynb` | Week 3 | Set-intersection across the per-stress DEG lists to identify the common stress core; functional enrichment on the core. | `core_genes.parquet` (9,067-gene core), `bp_enrichment.parquet` (144 BP terms) |
| 03 | `03_consensus_compare.ipynb` | Week 4 | Compare the recovered core against Hakkak & Tohidfar 2026's published consensus. | `comparison_summary.json`, `comparison_genes.parquet` (21,249 rows) |

Week 5 has no new notebook — it's revision against feedback on the paper and presentation.

The rationale-level orientation notebook (`../r1_orientation.ipynb`) loads AtGenExpress and is reused across R1-Q1 through R1-Q4. The question-specific orientation (`00_question_orientation.ipynb` in this folder) picks up from there and prepares the data shape used by `01_deg_analysis.ipynb`.

## Data

AtGenExpress abiotic stress series (Kilian et al. 2007), GEO accessions GSE5620–GSE5628. Loaded via `irilab2026.load_atgenexpress()`. Eight stresses plus control: cold, osmotic, salt, drought, genotoxic, UV-B, wounding, heat. Oxidative is at TAIR/NASCArrays only and is not part of the GEO download path.

Comparison anchor: Hakkak & Tohidfar (2026) consensus DEG meta-analysis. Their supplementary files are student-uploaded to the same Drive folder as notebook outputs:

- `hakkak_2026_supp1.csv` — consensus DEG list
- `hakkak_2026_supp3.csv` — transcription factor table (note: AGI column is `ORF`, not `agi`)

## Caveats carried into these notebooks

Three caveats apply to every notebook in this folder. They come from the AtGenExpress reality-check and are documented in full on the R1-Q1 Notion question page; brief versions:

- **Compute cross-stress overlap within tissue, not pooled across.** Whole-plant stresses (cold, drought, heat) directly stress both shoot and root; locally applied stresses (e.g., wounding) directly stress one tissue and produce a systemic response in the other. Pooling shoot and root samples mixes direct and systemic responses.
- **Don't generalize this dataset's drought genes to field drought.** AtGenExpress drought is fast hydroponic-raft desiccation to ~10% fresh-weight loss, not gradual soil drying.
- **State the stress coverage you actually have.** Eight stresses from GEO, not nine. Don't claim "all AtGenExpress abiotic stresses" without the qualifier.

## Findings worth carrying forward

These surfaced during R1-Q1 drafting and propagate to other R1 questions and (in one case) to EQ#2.

**Degenerate p-value distribution; effect size carries the load.** On AtGenExpress, the moderated-t p-value distribution shows a single spike near zero with no flat tail — about 99.9% of genes clear `p_adj < 0.05`. This is a property of moderated tests on small experiments with strong consistent signals (12 residual degrees of freedom plus 22,810 genes feeding the empirical Bayes prior produces extraordinarily sensitive variance estimates). The practical consequence: the effect-size threshold (`|logFC| ≥ 1`) is what actually decides what counts as differentially expressed. The p-value filter at `< 0.05` is essentially redundant on this dataset. This is the foundational interpretive move for EQ#2 and shapes how thresholds are framed in Notebook 01, Section 6.

**F-statistic ranks reliability; |logFC| ranks effect size.** Sorting `results` by F-statistic puts canonical cold markers at ranks 3,000–14,000 out of 22,810; sorting by `max_abs_logfc` puts the same markers in the top 100. The F-statistic asks "is this gene affected at all?"; |logFC| asks "of the genes that are affected, which had the biggest response?" Both questions matter; the answers are not the same gene list. Cell 5.13 of Notebook 01 documents this.

**Headline result.** 82% recovery of Hakkak & Tohidfar 2026's consensus stress-responsive set in the 9,067-gene single-dataset core. Regulatory components (transcription factors across DREB, MYB, NAC, WRKY families) transfer well; effector-level components transfer less reliably. The transfer/no-transfer split is the substantive finding for the paper, not the recovery rate itself.

## Library and infrastructure notes

`irilab2026` is at v0.2.0 for R1-Q1, providing `iri.setup()`, `iri.output_dir()`, `iri.cache_dir()`, and `iri.tair_gaf_path()`. The install line uses a four-variant pattern (active line: `--upgrade --force-reinstall --no-deps` with no version tag); see Notebook 02's Setup section for the canonical form. `matplotlib_venn` is installed at point of use in Notebook 02 rather than bundled — it's a single-notebook dependency.

Notebook outputs and inputs share a folder at `/content/drive/MyDrive/irilab2026_outputs/r1_q1/`:

| File | Producer | Consumer |
|---|---|---|
| `de_results.parquet` | Notebook 01 | Notebook 02 |
| `core_genes.parquet` | Notebook 02 | Notebook 03 |
| `bp_enrichment.parquet` | Notebook 02 | (paper / presentation) |
| `comparison_summary.json` | Notebook 03 | (paper / presentation) |
| `comparison_genes.parquet` | Notebook 03 | (paper / presentation) |
| `hakkak_2026_supp1.csv` | (student upload) | Notebook 03 |
| `hakkak_2026_supp3.csv` | (student upload) | Notebook 03 |

The first notebook to produce a persistent output for a later notebook to consume was Notebook 01, which is why the Drive-vs-local-filesystem convention is set there: relative paths in Colab live in a filesystem that is wiped when the runtime is recycled, so anything a downstream notebook needs gets written to the mounted Drive path.

## Status

All four notebooks complete and verified to run on real AtGenExpress data. Remaining R1-Q1 deliverables are external to the notebook chain:

- EQ#2 (per-question essential question; due Week 2 of program — not yet drafted)
- Draft presentation (Week 3)
- Final paper and presentation (Week 4)
- Revisions against feedback (Week 5)

R1-Q1 served as the template-setter for the other three Rationale 1 questions. The four-notebook structure (orientation + three working-week notebooks), the section numbering convention (`## N)` for top-level and `### N.k)` for subsections), and the Drive output convention all originate here and carry forward to R1-Q2, R1-Q3, and R1-Q4.