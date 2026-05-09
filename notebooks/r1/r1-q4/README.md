# R1-Q4: Cross-dataset stress classifier

Does a multi-class stress classifier trained on AtGenExpress generalize to Wang 2023 cold-stress RNA-seq with above-chance accuracy? Cross-platform integration via VST + ComBat.

See the R1-Q4 question page on Notion for the full Background, Prediction, Workflow, Considerations, and References.

## Notebooks (provisional, from scoping handoff)

| # | File | Brief |
|---|---|---|
| 01 | `01_integration.ipynb` | Cross-dataset integration. VST on Wang 2023 RNA-seq counts; ComBat for batch correction; alignment to ATH1 microarray space. |
| 02 | `02_classifier.ipynb` | Train the multi-class stress classifier on AtGenExpress. May share infrastructure with R1-Q3. |
| 03 | `03_wang_evaluation.ipynb` | Evaluate on Wang 2023. Direct timepoint overlap at 24h; soft overlap at 0h and 2h; 168h handled as out-of-distribution probe or excluded. |

This list is provisional and will be refined when R1-Q4 is worked through.

## Data

AtGenExpress (training; GEO GSE5620–GSE5628) and Wang 2023 cold (test; PRJNA767196 / SRP339213).

## Caveats carried into these notebooks

- **The 168h Wang 2023 timepoint is well outside AtGenExpress's 24h max.** Handling decision (exclude vs out-of-distribution probe) is part of R1-Q4's analysis design.
- **Two Python ports stack here.** pyDESeq2 for VST and a Python ComBat (pycombat / InMoose / neuroCombat) for batch correction. A spot-check against an R reference is worth doing before trusting the integrated output.

## Status

Not yet scaffolded. The integration notebook is likely the largest engineering risk in Rationale 1.
