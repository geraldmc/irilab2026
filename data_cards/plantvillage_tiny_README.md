---
license: cc0-1.0
task_categories:
  - image-classification
language:
  - en
size_categories:
  - 1K<n<10K
pretty_name: PlantVillage (tiny)
tags:
  - plants
  - agriculture
  - plant-disease
  - biology
  - debug
---

# PlantVillage (tiny)

**This is a debug-grade subset, not a faithful subsample for analysis.**
50 images per class drawn from the full PlantVillage dataset is too few
to represent class-level visual diversity. Use it for iterating on
training-loop code, smoke-testing pipelines, or any situation where you
want the data structure but not the data scale. For actual classifier
training or evaluation, use
[`geraldmc/plantvillage-full`](https://huggingface.co/datasets/geraldmc/plantvillage-full).

## What's in this dataset

A stratified subsample of `geraldmc/plantvillage-full` — 50 images per
class × 38 classes = approximately 1,900 images total. The schema is
identical to the full variant; only the row count differs. Built so
that pipelines depending on the full dataset's structure (column layout,
image format, train/test split shape) can be developed and tested
without the ~855 MB download every iteration.

## How to use it

```python
from datasets import load_dataset

ds = load_dataset("geraldmc/plantvillage-tiny", revision="v0.1.0", split="train")
```

For users of the [`irilab2026`](https://github.com/geraldmc/irilab2026)
library:

```python
import irilab2026 as iri
metadata, images = iri.load_plantvillage(variant="tiny")
```

## Data fields

Identical to `geraldmc/plantvillage-full`. See that dataset's card for
the field-by-field schema.

## Build provenance

Built by the same script (`scripts/build_pv_full_hf.py`) and from the
same upstream commit as `plantvillage-full`. The additional step is
stratified subsampling:

- Random seed: `<SUBSAMPLE_SEED>` (fixed for reproducibility).
- 50 images per class, sampled without replacement, per class
  independently.
- The train/test `split` column is inherited from the full variant's
  pre-split assignment, not re-shuffled. This preserves leaf-grouping
  within the subsample, but means the train/test ratio in the tiny
  variant may drift slightly from 80/20.

## Known caveats

**Sample size is too small for analytical claims.** Per-class accuracy
on ~10 held-out test images per class is noisy enough that any reported
number swings with the seed. Use the full variant for any result you
intend to report.

**Same upstream caveats apply.** The image count discrepancy and the
`Tomato___Target_Spot` leafmap issue documented for the full variant
also apply here, in subsampled form. See the
[full variant's dataset card](https://huggingface.co/datasets/geraldmc/plantvillage-full)
for details.

## License

CC0 1.0 (Public Domain Dedication), inherited from the upstream
PlantVillage release.

## Citation

Same as the full variant. See
[`geraldmc/plantvillage-full`](https://huggingface.co/datasets/geraldmc/plantvillage-full)'s
dataset card for the BibTeX entry.