---
license: cc-by-4.0
task_categories:
  - image-classification
language:
  - en
tags:
  - plant-disease
  - agriculture
  - field-conditions
  - computer-vision
size_categories:
  - 1K<n<10K
pretty_name: PlantDoc (full)
---

# PlantDoc — full variant

A curated mirror of the PlantDoc plant disease classification dataset (Singh et al. 2020), with normalized class metadata and a stable schema, hosted as a Hugging Face Dataset for reproducible distribution. The companion **`plantdoc-tiny`** variant is a 164-image stratified subsample of this dataset for fast test-suite use.

PlantDoc was built to address a specific failure mode in earlier plant disease datasets like PlantVillage: lab-condition images don't predict field-condition performance. PlantDoc images are web-scraped photos of diseased and healthy leaves in real-world settings — heterogeneous in resolution, lighting, background, and capture device. That heterogeneity is the point.

## Quick start

```python
from datasets import load_dataset

ds = load_dataset("geraldmc/plantdoc-full", revision="v0.1.0", split="train")
print(len(ds))                # 2578
print(ds.features)            # image + 7 metadata columns
print(ds[0]["class_label"])   # 'Apple Scab Leaf'
```

Inside the iResearch Institute 2026 Virtual Lab, the typical entry point is:

```python
import irilab2026 as iri

metadata_df, hf_dataset = iri.load_plantdoc()
```

## What's in this dataset

- **2,578 images** across 28 classes covering 13 host plant species
- **Train/test split shipped intact** from the upstream repository — 2,342 train + 236 test
- **Heterogeneous resolution** (189–4,000 px width, 194–4,272 px height), heterogeneous lighting, heterogeneous backgrounds — by design
- **Mostly RGB, some CMYK** color modes — downstream loaders should `.convert("RGB")` defensively

## Schema

| Column | Type | Description | Example |
|---|---|---|---|
| `image` | image | PIL Image at original upstream resolution | (W, H) JPEG |
| `class_label` | string | Upstream folder name, verbatim | `"Apple Scab Leaf"` |
| `class_idx` | int64 | 0–27, case-sensitive alphabetical sort over `class_label` | `0` |
| `host` | string | Normalized host name | `"Apple"` |
| `disease` | string | Lowercased disease name, or `"healthy"` for healthy leaves | `"scab"` |
| `is_healthy` | bool | True iff the class is a healthy leaf | `False` |
| `split` | string | `"train"` or `"test"`, from the upstream partition | `"train"` |
| `filename` | string | Original filename, verbatim (URL-encoded chars and double extensions preserved) | `"052609%20Hartman%20Crabapple%20scab%20single%20leaf.JPG.jpg"` |

### About `host`

Hosts are normalized from upstream folder names with one transformation: underscores become spaces (`Bell_pepper` → `"Bell pepper"`). Capitalization and spelling are otherwise preserved as upstream had them. Notable inheritances from upstream:

- `Soyabean` retains the upstream misspelling (canonical is "Soybean") so the normalized name links unambiguously to the original folder.
- `grape` retains the upstream lowercase. Other hosts are Title Case.
- `Corn` retains the upstream naming (the more standard botanical name is "Maize") to match Singh et al. 2020 and downstream benchmark papers.

If your downstream code needs cross-dataset matching (e.g., aligning PlantDoc classes to PlantVillage classes), do that normalization explicitly in your code rather than relying on these column values to be canonical — that step is meaningful research methodology and should be visible in your work.

### About `disease`

Disease names are lowercased even when the upstream had Title Case (`Powdery mildew` → `"powdery mildew"`, `Septoria leaf spot` → `"septoria leaf spot"`). Two non-obvious mappings worth flagging:

- `Tomato mold leaf` → `"mold"` (the canonical disease is *leaf mold*, caused by *Passalora fulva*, but the upstream label format doesn't say "leaf mold" — the column stays close to upstream literal naming).
- `Tomato two spotted spider mites leaf` → `"two spotted spider mites"` (a pest, not strictly a plant disease, but it's a PlantDoc class).

### About `class_idx`

Class indices 0–27 are assigned by case-sensitive alphabetical sort over `class_label` values. With case-sensitive sort, lowercase `grape leaf` and `grape leaf black rot` land at indices 26 and 27, after the uppercase Title Case classes.

## Known caveats

### One class has 2 training images and 0 test images

`Tomato two spotted spider mites leaf` appears in `train/` with 2 images and is entirely absent from `test/` in the upstream repository. Singh et al. 2020 and downstream benchmark papers (e.g., Ahmad et al. 2023) report 27 classes — they implicitly drop this orphan. This dataset preserves all 28 classes for upstream fidelity. If you're benchmarking against the literature, drop the orphan explicitly:

```python
df = df[df["class_label"] != "Tomato two spotted spider mites leaf"]
```

### Class names are inconsistent in capitalization, word order, and the position of "leaf"

The upstream folder names are not internally consistent. Examples that all appear in this dataset: `Apple Scab Leaf` (Title Case, disease before "Leaf"), `Tomato Septoria leaf spot` (mixed case, "leaf spot" as a compound), `grape leaf` (all lowercase), `Tomato mold leaf` (disease before "leaf"), `Tomato leaf bacterial spot` (host "leaf" disease). The `host` and `disease` columns are the hand-curated normalization; the `class_label` column preserves the upstream string verbatim.

### Filenames have quirks worth knowing about

About 6% of filenames contain URL-encoded characters (`%20` for spaces, `%2C` for commas) — artifacts of however the upstream curators saved web-scraped images. Roughly 12% have double extensions like `.JPG.jpg` or `.jpeg.jpg`. The `filename` column preserves these exactly because they're identifiers — the link back to the upstream filename is exact and unambiguous.

### Per-class test set sizes are small

Test split sizes range from 4 (Corn Gray leaf spot) to 12 (Corn leaf blight, grape leaf), with a median around 9. Per-class accuracy estimates on this dataset will have wide confidence intervals — frame your conclusions accordingly. Aggregate metrics (averaged across classes or grouped by host family) are more reliable than per-class numbers.

### About `class_count = 28` but the README of upstream says 17

The upstream README at `pratikkayal/PlantDoc-Dataset` claims "13 plant species and up to 17 classes of diseases." That's 17 *disease* classes; the dataset includes healthy-leaf classes for many hosts, bringing the total to 28 (or 27 if the orphan is dropped — see above).

## Build provenance

This dataset was built by:

1. Cloning `pratikkayal/PlantDoc-Dataset` at commit `5467f6012d78` (on a case-sensitive Linux filesystem — see note below).
2. Walking `train/` and `test/` directory trees to enumerate all image files.
3. Applying a hand-curated 28-row class-normalization lookup to produce the `host`, `disease`, and `is_healthy` columns.
4. Assigning `class_idx` by case-sensitive alphabetical sort over distinct `class_label` values.
5. Constructing an HF `Dataset` with the `Image()` feature and pushing to `geraldmc/plantdoc-full` with revision tag `v0.1.0`.

Build script: [`scripts/build_pd_full_hf.py`](https://github.com/geraldmc/irilab2026/blob/main/scripts/build_pd_full_hf.py) in the `irilab2026` repository.

### A note about case-sensitive filesystems

The upstream repository contains 6 pairs of files whose names differ only in case (e.g., `CAR1.jpg` and `car1.jpg` in `Apple rust leaf/`). On case-insensitive filesystems (default macOS APFS/HFS+, default Windows NTFS) `git clone` silently drops one file per pair and produces a 2,572-image working tree instead of 2,578. This dataset was built on Colab's case-sensitive Linux filesystem to preserve all 2,578 upstream images. If you rebuild from `scripts/build_pd_full_hf.py`, do so on a case-sensitive filesystem.

## License

This curated mirror is released under **CC BY 4.0**, matching the license of the upstream `pratikkayal/PlantDoc-Dataset`.

Attribution must include both the upstream dataset (Singh et al. 2020) and this curated mirror. See *Citation* below.

## Citation

```bibtex
@inproceedings{singh2020plantdoc,
  title     = {{PlantDoc}: A Dataset for Visual Plant Disease Detection},
  author    = {Singh, Davinder and Jain, Naman and Jain, Pranjali and
               Kayal, Pratik and Kumawat, Sudhakar and Batra, Nipun},
  booktitle = {Proceedings of the 7th ACM IKDD CoDS and 25th COMAD},
  pages     = {249--253},
  year      = {2020}
}
```

When citing the curated mirror itself, additionally reference this Hugging Face Dataset by its repo ID and revision tag (`geraldmc/plantdoc-full @ v0.1.0`).

## Related resources

- **`geraldmc/plantdoc-tiny`** — 164-image stratified subsample for test-suite use
- **`geraldmc/plantvillage-full`** — the lab-condition counterpart dataset; PlantDoc is most commonly used as a transfer test for classifiers trained on this
- **`pratikkayal/PlantDoc-Dataset`** — the upstream GitHub repository