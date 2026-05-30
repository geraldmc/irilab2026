# R2-Q3: Can targeted image augmentations close the lab→field gap?

**Can targeted image augmentations — designed against R2-Q2's failure-mode taxonomy — close the PV→PD gap better than a kitchen-sink baseline (RandAugment-style)?**

A three-condition comparison (no augmentation, kitchen-sink, targeted) measured by PV→PD gap reduction, with the prediction that targeted wins but only by a modest margin — and that a small margin is itself evidence that the kitchen-sink baseline picked up the same signal incidentally, by suppressing the same shortcuts less precisely.

See the R2-Q3 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (in workflow order)

| # | File | Workflow row | Brief | Output |
|---|---|---|---|---|
| 00 | `00_orient_and_precommit.ipynb` | Week 1 | Question-specific orientation. Locks six decisions: taxonomy source (R2-Q2 in parallel, R2-Q2's published version, or your own), experimental design (factorial vs hold-one-out), kitchen-sink composition (exact augmentation list), failure-mode-to-augmentation mapping (with the symptom-attended-but-wrong-class exclusion named explicitly), class-space remapping (per-dataset class → category lookup that anchors the PV → PD comparison), and statistical comparison (specific test, not just "compare"). | `precommit.json` |
| 01 | `01_baseline_and_kitchen_sink.ipynb` | Week 2 | Trains two PV classifiers under the same scaffold: one with no augmentation, one with the precommitted kitchen-sink list. Evaluates both on PV-internal and PD; computes the PV→PD gap for each. | `baseline_classifier.pt`, `kitchen_sink_classifier.pt`, `baseline_metrics.parquet`, `kitchen_sink_metrics.parquet` |
| 02 | `02_targeted_augmentation.ipynb` | Week 3 | Trains the targeted-augmentation classifier per the precommitted failure-mode-to-augmentation mapping. Evaluates on PV-internal and PD; computes the targeted PV→PD gap. | `targeted_classifier.pt`, `targeted_metrics.parquet` |
| 03 | `03_comparison.ipynb` | Week 4 | Three-way gap-reduction comparison (no-aug vs kitchen-sink vs targeted) plus the precommitted statistical test (a paired bootstrap by default). Per-category breakdown where the data supports it; overall otherwise. Conclusions framed per Consideration 5 — augmentation reduces the problem, doesn't solve it. | `comparison_table.parquet`, `comparison_summary.json` |

Week 5 has no new notebook — it's paper revision against feedback.

The rationale-level orientation notebook (`../r2_orientation.ipynb`) introduces PlantVillage and PlantDoc and is reused across R2-Q1 through R2-Q4. The question-specific orientation (`00_orient_and_precommit.ipynb` in this folder) picks up from there and commits the six experimental-design decisions that the rest of the question executes.

R2-Q3 builds on R2-Q2's failure-mode taxonomy. Per Precommit 1, the taxonomy can be inherited from R2-Q2 in parallel, used as published, or replaced with the student's own — but in all three options the question is the same: can those failure modes be operationalized into augmentations that beat a kitchen-sink baseline?

## Data

PlantVillage (Mohanty et al. 2016) and PlantDoc (Singh et al. 2020), loaded via `iri.load_plantvillage()` and `iri.load_plantdoc()`. PV is the training distribution (controlled lab conditions); PD is the held-out field evaluation distribution. Three classifiers train on PV and get evaluated against both PV-internal and PD; the PV→PD gap per condition is the headline measurement. Scoring runs in a shared five-category disease space (the class-space remapping of Precommit 5), since PlantDoc is too small to support per-class numbers.

Methodological precedent: the Targeted Data Augmentation (TDA) framework introduced by Mikołajczyk-Bareła et al. (2023). TDA identifies biases, designs augmentations targeting them, trains, evaluates, and quantifies the reduction in bias. R2-Q3 applies that loop to the PV→PD transfer problem.

## Caveats carried into these notebooks

- **One failure mode is intentionally unaddressed.** Per Consideration 2: symptom-attended-but-wrong-class failures (the model attends to a real symptom but assigns the wrong class) cannot be fixed by augmentation — they reflect genuine confusion between similar diseases. Precommit 4's mapping names this exclusion explicitly, alongside an "other / ambiguous" bucket that is likewise unaddressable, rather than quietly dropping the row.
- **Kitchen-sink may incidentally reduce the gap.** Per the page's Prediction: RandAugment-style kitchen-sink augmentation can pick up the same shortcut-suppression signal as a targeted set, just less precisely. A small targeted-vs-kitchen-sink margin is therefore not a null result — it is evidence that the kitchen-sink baseline reached the same fix. NB03's interpretation frames the comparison as "did targeted reduce the gap *more than kitchen-sink did*," not "did targeted reduce the gap."
- **Background-shortcut contamination is upstream of all three conditions.** Noyan (2022) showed PlantVillage's disease labels can be predicted from roughly eight background pixels at about 49% accuracy, against ~2.6% for guessing among the 38 classes — the dataset's uniform backdrops are tied to the labels. Background-targeted augmentation is the most direct response, but no augmentation pipeline tested here removes the structural confound at its source. Per Consideration 5: augmentation reduces the problem, it doesn't solve it.

## Files

All notebook outputs share a Drive folder at `/content/drive/MyDrive/irilab2026_outputs/r2_q3/`:

| File | Producer | Consumer |
|---|---|---|
| `precommit.json` | Notebook 00 | Notebooks 01, 02, 03 |
| `baseline_classifier.pt` | Notebook 01 | (paper / reproducibility; not reloaded for the bootstrap) |
| `kitchen_sink_classifier.pt` | Notebook 01 | Notebook 03 (paired bootstrap) |
| `baseline_metrics.parquet` | Notebook 01 | Notebooks 02, 03 |
| `kitchen_sink_metrics.parquet` | Notebook 01 | Notebooks 02, 03 |
| `targeted_classifier.pt` | Notebook 02 | Notebook 03 (paired bootstrap) |
| `targeted_metrics.parquet` | Notebook 02 | Notebooks 03 |
| `comparison_table.parquet` | Notebook 03 | (paper / presentation) |
| `comparison_summary.json` | Notebook 03 | (paper / presentation) |

Classifiers are saved with `torch.save` as PyTorch state dicts (`.pt`), not `.pkl`. The Week-4 paired bootstrap reloads the kitchen-sink and targeted classifiers to recover per-image correctness; the no-augmentation floor is read from its metrics file only.

## Status

All four notebooks have full body content; the question chain was recently finalized. R2-Q3 has not yet gone through the program's paper / presentation cycle.
