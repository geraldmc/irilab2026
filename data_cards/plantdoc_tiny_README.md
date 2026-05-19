---
license: cc-by-4.0
task_categories:
  - image-classification
language:
  - en
tags:
  - plant-disease
  - test-fixture
  - debug-grade
size_categories:
  - n<1K
pretty_name: PlantDoc (tiny)
---

# PlantDoc — tiny variant

> **Warning: this is a debug-grade subset, not a faithful subsample for analysis.** Use it for test suites, smoke tests, and notebook iteration. For substantive work, use [`geraldmc/plantdoc-full`](https://huggingface.co/datasets/geraldmc/plantdoc-full).

A 164-image stratified subsample of [`geraldmc/plantdoc-full`](https://huggingface.co/datasets/geraldmc/plantdoc-full), built to support fast iteration. Loading is roughly a 50 MB download instead of ~950 MB, and a pass over the dataset takes seconds rather than minutes.

## Quick start

```python
from datasets import load_dataset

ds = load_dataset("geraldmc/plantdoc-tiny", revision="v0.1.0", split="train")
print(len(ds))    # 164
```

Inside the iResearch Institute 2026 Virtual Lab:

```python
import irilab2026 as iri

metadata_df, hf_dataset = iri.load_plantdoc(variant="tiny")
```

## What's in this dataset

- **164 images** stratified across 28 classes, 83 train + 81 test
- **Schema identical to `plantdoc-full`** — same 8 columns (image + 7 metadata), same values for any image that appears in both
- **Subsample rule:** `min(3, available)` per class per split, with a fixed seed

For every non-orphan class, this means 3 train + 3 test = 6 images. The orphan class (`Tomato two spotted spider mites leaf`) appears with its 2 train images and 0 test images, exactly as in the full variant.

## Schema, normalization, caveats

See the **[full variant's dataset card](https://huggingface.co/datasets/geraldmc/plantdoc-full)** for:

- Column descriptions and types
- Normalization rules for `host` and `disease`
- The orphan-class caveat
- Filename quirks
- Citation and license details

The schema is identical between the two variants; duplicating it here invites drift.

## Subsample parameters

- **Per-class budget:** `min(3, available)` per (class, split)
- **Seed:** `42` (passed as `random_state` to pandas `.sample()`)
- **Source:** `geraldmc/plantdoc-full` at revision `v0.1.0`

The subsample is fully deterministic given these three parameters. Re-running the build script with the same source and seed produces byte-identical metadata. Image bytes also match exactly because the same upstream files are referenced.

## What this dataset is NOT for

- **Training a classifier.** 3 training images per class is far too few to learn anything; this isn't a "small training set" — it's a fixture for code paths.
- **Measuring per-class accuracy.** Per-class test set sizes here are 1–3 images; any "accuracy" you compute is dominated by sampling noise.
- **Comparing model architectures.** Any signal would be noise at this scale.
- **Reporting results in a paper.** Whatever you find on the tiny variant is not a finding about PlantDoc — it's a finding about 164 images that happen to live under this repo ID.

## What this dataset IS for

- **Test suite use.** Fast assertion that loader code, Dataset wrappers, and training pipelines run end-to-end without surprise.
- **Notebook iteration.** Debugging a preprocessing pipeline or augmentation strategy without paying for the full dataset's load time.
- **CI runs.** Tests that exercise loader behavior can use this variant on every push without burning minutes on downloads.

## License

CC BY 4.0, matching the full variant and the upstream dataset.

## Citation

Cite the upstream dataset (Singh et al. 2020) and reference this tiny variant as `geraldmc/plantdoc-tiny @ v0.1.0`. Full BibTeX in the full variant's dataset card.