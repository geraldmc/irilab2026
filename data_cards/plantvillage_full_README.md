---
license: cc0-1.0
task_categories:
  - image-classification
language:
  - en
size_categories:
  - 10K<n<100K
pretty_name: PlantVillage (full)
tags:
  - plants
  - agriculture
  - plant-disease
  - biology
---

# PlantVillage (full)

A curated re-release of the PlantVillage plant-disease image dataset
(Mohanty, Hughes, Salathé 2016), with structured per-image metadata and
a leaf-grouped train/test split. Built for the iResearch Institute 2026
Virtual Lab mentorship's Rationale 2 track. The companion debug-grade
subset is at
[`geraldmc/plantvillage-tiny`](https://huggingface.co/datasets/geraldmc/plantvillage-tiny).

## What's in this dataset

54,304 images of plant leaves, photographed against plain backgrounds
under controlled lighting, across 38 classes — each class is a unique
combination of a host plant species and a disease (or "healthy"). The
image set is identical to the `raw/color/` directory of the upstream
PlantVillage repository at the commit this release was built from. The
contribution of this release is the metadata layer (host/disease
parsing, leaf-of-origin grouping, the deterministic train/test split)
and the packaging as Parquet shards for fast streaming access.

## How to use it

```python
from datasets import load_dataset

ds = load_dataset("geraldmc/plantvillage-full", revision="v0.1.0", split="train")
example = ds[0]
example["image"]         # PIL Image, 256x256 RGB
example["class_label"]   # "Apple___Apple_scab"
```

The dataset has a single underlying `"train"` HF split. The "train"
name is HF's default wrapping; the train-vs-held-out split for analysis
lives in the `split` metadata column (see Data fields below).

For users of the [`irilab2026`](https://github.com/geraldmc/irilab2026)
library, the wrapper function `iri.load_plantvillage()` returns a
`(metadata_df, hf_dataset)` tuple and provides a PyTorch `Dataset`
wrapper. See the library's documentation.

## Data fields

| Field | Type | Description |
|---|---|---|
| `image` | Image | The PV image. 256×256 pixel JPEG, RGB, uniformly sized across the dataset. |
| `class_label` | string | Combined host + disease folder name from upstream, e.g. `Tomato___Tomato_mosaic_virus`. |
| `class_idx` | int | Integer 0–37 assigned by alphabetical sort over `class_label`. The integer form a classifier predicts. |
| `host` | string | Host plant species, e.g. `Tomato`. Parsed from the left side of `class_label` split on `___`. |
| `disease` | string | Disease name, e.g. `Tomato mosaic virus` or `healthy`. Parsed from the right side; underscores replaced with spaces. |
| `split` | string | `"train"` (43,356 rows) or `"test"` (10,948 rows). Leaf-grouped 80/20 split — see Build provenance below. |
| `leaf_id` | string | Identifier for the physical leaf the image was taken from. Globally unique across classes. |
| `leaf_grouped` | bool | `True` if `leaf_id` reflects upstream grouping (from `filtered_leafmaps/`); `False` if synthetic (one per image). |

## Build provenance

Built from `spMohanty/PlantVillage-Dataset` at commit `<UPSTREAM_SHA>`
by `scripts/build_pv_full_hf.py` in the `irilab2026` repository. The
build steps:

1. Shallow-clones the upstream repository.
2. Walks `raw/color/` to enumerate images and parse class labels.
3. For each of the 30 classes that have a `filtered_leafmaps/` CSV,
   attaches the leaf-of-origin metadata as `leaf_id` and sets
   `leaf_grouped = True`.
4. For the remaining 8 classes, assigns each image its own synthetic
   `leaf_id` and sets `leaf_grouped = False`.
5. Shuffles `leaf_id` values with a fixed seed and produces a leaf-
   grouped 80/20 train/test split. Leaf-grouped means all images of a
   single physical leaf go to either train or test, never both — a
   classifier evaluated on the test set has not seen any image of any
   leaf it's being tested on.
6. Packages the result as Parquet shards and pushes to this repo.

The split ratio is 79.84% / 20.16% (43,356 / 10,948) rather than
exactly 80/20 because leaf-grouped rounding can't always hit the
nominal target.

## Known caveats

**Image count discrepancy.** Mohanty et al. (2016) reports 54,303
images. The current upstream `raw/color/` contains 54,304 images. The
provenance of the one-image difference has not been traced; if it
matters for your analysis, audit your loaded dataset directly rather
than citing the paper's count.

**`Tomato___Target_Spot` is effectively ungrouped despite having a
leafmap CSV.** The class's filtered leafmap was generated from a
different upstream snapshot than the current `raw/color/`, so every
filename lookup against it fails (1,404 entries, 1,404 misses). The
build script falls through to the synthetic-leaf-ID path for this
class, but `leaf_grouped` is set per the existence of the leafmap
file, not per whether the lookups succeeded. If your analysis depends
on `leaf_grouped` reflecting actual upstream grouping rather than
"a leafmap CSV exists upstream," filter out this class explicitly or
check whether the column's value matches your analytical intent.

In practice this means net leaf-grouping coverage is 29 classes
(grouped, lookups work) plus 9 classes (synthetic), rather than the
headline 30 + 8 from the class-name count.

## License

CC0 1.0 (Public Domain Dedication), inherited from the upstream
PlantVillage release.

## Citation

If you use this dataset in published work, cite the original
PlantVillage paper:

```bibtex
@article{mohanty2016using,
  title={Using deep learning for image-based plant disease detection},
  author={Mohanty, Sharada P and Hughes, David P and Salath{\'e}, Marcel},
  journal={Frontiers in Plant Science},
  volume={7},
  pages={1419},
  year={2016},
  publisher={Frontiers Media SA},
  doi={10.3389/fpls.2016.01419}
}
```

Curated and packaged by Gerald McCullagh for the iResearch Institute
2026 Virtual Lab.