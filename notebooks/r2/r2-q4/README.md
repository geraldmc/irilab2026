# R2-Q4: Cross-host transfer within PV

**Within PlantVillage, when a disease appears on multiple host species, does a classifier trained on the disease in one host transfer to the same disease in a different host? Or does it learn a host-specific template rather than the disease itself?**

Cross-host transfer within PlantVillage as a diagnostic for whether a disease classifier has learned generalizable disease features or host-specific templates. A small within-host vs cross-host accuracy gap supports the disease-features reading; a large gap supports the host-template reading. The interpretation is committed to per disease, not as a single sweeping claim.

See the R2-Q4 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (in workflow order)

| # | File | Workflow row | Brief | Output |
|---|---|---|---|---|
| 00 | `00_orient_and_precommit.ipynb` | Week 1 | Question-specific orientation. Inspects PlantVillage to identify multi-host diseases and per-host sample counts. Locks three decisions: disease list (which multi-host diseases qualify; which single-host diseases serve as controls), hold-out scheme (leave-one-host-out per disease vs fixed train/test host assignment), and cross-host accuracy aggregation (per-disease vs overall). | `precommit.json` |
| 01 | `01_within_host_classifier.ipynb` | Week 2 | Trains a disease classifier on PV following the precommitted disease list and hold-out scheme. Evaluates within-host: per-disease accuracy on held-out samples from the same hosts the classifier saw during training. Accuracy gate before transfer measurement. | `classifier.pkl`, `within_host_test.parquet`, `within_host_accuracy.parquet` |
| 02 | `02_cross_host_evaluation.ipynb` | Week 3 | Applies the within-host classifier to the same diseases on the held-out hosts. Computes the per-disease gap (within − cross), aggregated per Precommit 3. | `cross_host_accuracy.parquet`, `gap_table.parquet`, `comparison_summary.json` |
| 03 | `03_per_disease_interpretation.ipynb` | Week 4 | Per-disease interpretation against the page's 2×2 grid (transfer outcome × pathogen identity). Background-shortcut sanity check against Noyan (2022). Per-disease claims for the paper-level conclusion. | `interpretation_table.parquet` |

Week 5 has no new notebook — it's paper revision against feedback.

The rationale-level orientation notebook (`../r2_orientation.ipynb`) introduces PlantVillage and PlantDoc and is reused across R2-Q1 through R2-Q4. The question-specific orientation (`00_orient_and_precommit.ipynb` in this folder) picks up from there and commits the three experimental-design decisions that the rest of the question executes.

## Data

PlantVillage (Mohanty et al. 2016), loaded via `iri.load_plantvillage()`. The R2-Q4 working slice is the subset of PV where the same disease label appears on more than one host species — the page's "~4 diseases" guidance is the order-of-magnitude expectation; the exact list is Precommit 1.

No external comparison anchor for R2-Q4. The interpretive frame is the page's 2×2 grid combining transfer outcome (success/failure) with pathogen identity (same pathogen across hosts, or different pathogens reusing one disease name).

## Caveats carried into these notebooks

- **Background-shortcut contamination.** Noyan (2022) Table 6 shows that on PlantVillage, even *foreground-only* blurred imagery predicts class at roughly 10% (vs random-guess ~2.6%), meaning PV's capture bias has contaminated the foreground itself, not just the background. Removing the background does not fully isolate host-template effects. This is surfaced in N03's sanity-check section.
- **Per-disease claims, not sweeping ones.** Per Consideration 4 on the page: the gap is per-disease. Aggregating to one overall cross-host accuracy washes out the most important signal. Reporting must commit to which diseases transferred and which didn't, not just an average.
- **Low within-host accuracy is itself informative.** Per Consideration 3 on the page: if the within-host classifier underperforms, that doesn't mean the disease is hard to transfer — it could mean the disease is hard to classify in general. The gap is meaningful only relative to your actual within-host finding. This shapes how N01's accuracy-gate decision gets read in N02 and N03.

## Files

All notebook outputs share a Drive folder at `/content/drive/MyDrive/irilab2026_outputs/r2_q4/`:

| File | Producer | Consumer |
|---|---|---|
| `precommit.json` | Notebook 00 | Notebooks 01, 02, 03 |
| `classifier.pkl` | Notebook 01 | Notebooks 02, 03 |
| `within_host_test.parquet` | Notebook 01 | Notebook 02 |
| `within_host_accuracy.parquet` | Notebook 01 | Notebook 02 |
| `cross_host_accuracy.parquet` | Notebook 02 | Notebook 03 |
| `gap_table.parquet` | Notebook 02 | Notebook 03 |
| `comparison_summary.json` | Notebook 02 | Notebook 03 |
| `interpretation_table.parquet` | Notebook 03 | (paper / presentation) |


## Status

All four notebooks have full body content; the question chain was recently finalized. R2-Q4 has not yet gone through the program's paper / presentation cycle.
