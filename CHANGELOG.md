# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0] — 2026-05-29

The library grew from setup-and-load-only into a full support layer for both rationales. R1 added co-expression and feature-attribution work; R2 brought the plant-image classification track end-to-end. All eight question chains are now drafted; four are through paper / presentation and four are recently finalized.

### Added

**New library modules**

- `irilab2026/vision.py` — ResNet-18 baseline classifier and image transforms for the R2 image-classification work (`build_baseline_model`, `imagenet_train_transform`, `imagenet_eval_transform`, `randaugment_train_transform`). Train and eval transforms share ImageNet normalization constants by construction so they cannot drift out of sync.
- `irilab2026/training.py` — `train_baseline`, a reusable training helper implementing R2-Q1 NB03's canonical recipe (SGD momentum 0.9, lr 0.01 → 0.001 step at epoch 7, batch 32, 10 epochs, 10% stratified val carve, best-val checkpointing).
- `irilab2026/evaluation.py` — `build_idx_to_cat` and `evaluate_in_categories` for category-space scoring of PV-trained classifiers against either PV-internal or PD test sets. Implements the asymmetric mapping (predictions in the training-dataset class space, labels in the eval-dataset class space) that makes the PV → PD comparison correct.

**New environment helpers**

- `seed_all(seed=42)` — seeds Python, NumPy, and PyTorch (CPU + CUDA) and flips cuDNN into deterministic mode for reproducible training.
- `output_dir(question_slug)` — returns the per-question Drive output directory, creating it if missing.
- `cache_dir()` promoted from internal to public API.
- The unwrapped Colab helpers (`is_colab`, `mount_google_drive`, `has_gpu`) are now formally exported for use in the rationale-level orientation notebooks (the unwrapped-then-wrapped pedagogy pattern).

**New data loaders and helpers**

- `load_plantvillage_orientation()` — orientation slice (~190 sample images, manifest of all 38 classes, ~3 MB) for the R2 rationale orientation notebook. Backed by a SHA256-verified GitHub release tarball.
- `load_plantvillage(variant)` — full (~54k images, ~1.5 GB) and tiny (~1.9k images, debug-grade) variants of the curated PlantVillage dataset, served from Hugging Face Hub. Returns `(metadata, images)`.
- `load_plantdoc(variant)` — full (~2.5k images) and tiny (~164 images, smoke-test) variants of PlantDoc, served from Hugging Face Hub.
- `PlantVillageDataset`, `PlantDocDataset` — PyTorch `Dataset` wrappers around the (metadata, HF Dataset) pairs.
- `atgenexpress_metadata()` — sample-level metadata parser for the AtGenExpress series. Parses tissue, time, replicate from GSM titles; cached as parquet after first build; validates per-stress chip counts against Hahn 2013 §4.1.
- `probe_to_agi()` — Affymetrix ATH1 probe → AGI gene identifier mapping built from the GPL198 annotation table. Returns a `dict` (not a `Series`; deliberate, for parity with the original R1-Q1 inline pattern).
- `tair_gaf_path()` — accessor for the bundled `tair.gaf.gz` GO annotation file.

**Bundled resources**

- `irilab2026/resources/tair.gaf.gz` — *Arabidopsis thaliana* Gene Ontology Annotation file from the GO Consortium, bundled because the upstream distribution server returns HTTP 403 from some networks including Colab. Used by R1-Q1 Notebook 02 for functional enrichment.

**Notebooks**

- All eight question chains drafted (`r1-q1/` through `r1-q4/`, `r2-q1/` through `r2-q4/`).
- R1-Q1, R1-Q2, R2-Q1, R2-Q2 are reference chains — analytically closed and through the paper / presentation cycle.
- R1-Q3, R1-Q4, R2-Q3, R2-Q4 are recently finalized with full body content; their paper / presentation cycles are in progress.
- `notebooks/r2/r2_orientation.ipynb` — R2 rationale orientation, walking the PlantVillage on-ramp through the unwrapped-then-wrapped helpers pattern.

**Data products**

- PlantVillage `full` and `tiny` variants on Hugging Face Hub (`geraldmc/plantvillage-full`, `geraldmc/plantvillage-tiny`, both at revision `v0.1.0`).
- PlantDoc `full` and `tiny` variants on Hugging Face Hub (`geraldmc/plantdoc-full`, `geraldmc/plantdoc-tiny`, both at revision `v0.1.0`).
- PlantVillage orientation sample as GitHub release (`data-orientation-v0.1.0`, SHA256-pinned).

**Tests**

- Test suite grew from initial smoke set to 86 tests across 7 files (`test_smoke`, `test_atgenexpress_metadata`, `test_loaders`, `test_probe_to_agi`, `test_seed`, `test_vision`, `test_training`, `test_evaluation`) covering all five library modules. Network-free discipline maintained throughout — no test hits GEO or Hugging Face.

### Changed

- `train_baseline` gained two backward-compatible keyword-only parameters: `train_transform=None` (defaults to `imagenet_train_transform()`; lets R2-Q3 vary the train pipeline across no-aug / kitchen-sink / targeted conditions) and `val_dataset_class=None` (defaults to `dataset_class`; lets a training dataset that mutates images inside `__getitem__` use a plain validation dataset).
- `atgenexpress_metadata` schema gained a `last_update_date` column, used as a per-sample processing-date proxy for batch-confound tests. Cached frames built before this column existed are detected and rebuilt on next call.

### Removed

- Project-level numpy upper bound in `pyproject.toml`. pyWGCNA 2.2.1 (used by R1-Q2) requires `numpy >= 2.1.0`, which made a project-wide ceiling untenable; the numpy ABI footgun is mitigated through install-line patterns documented in CLAUDE.md instead.

### Notes

- `__version__` in `irilab2026/__init__.py` and `version` in `pyproject.toml` were bumped from 0.1.0 → 0.2.0 → 0.3.0 in step with code additions, but no matching git tags were cut. The notebook install line continues to use `@main`; the switch to a pinned tag (`@vX.Y.Z`) is deferred to the first milestone release. Treat the in-tree version markers as documentation, not as released versions.

## [0.1.0] — 2026-05-08

Initial release. Establishes the package skeleton and the first two public functions.

### Added

- `setup()` — single entry point called at the top of every notebook. Detects whether the notebook is running in Google Colab, mounts Google Drive when it is, checks the runtime against the notebook's declared GPU requirement, and prints a one-line summary.
- `load_atgenexpress()` — downloads (or loads from cache) the AtGenExpress abiotic stress microarray dataset from GEO accessions GSE5620–GSE5628. Returns a dict keyed by stress name, with one pandas DataFrame per stress (probes × samples).
- Cache directory at `My Drive/irilab2026_cache/` in Colab; `~/.irilab2026_cache/` locally.
- `notebooks/` directory tree: `r1/` and `r2/` rationale folders, each with per-question subfolders (`r1-q1/` through `r1-q4/`, `r2-q1/` through `r2-q4/`). Each folder has a README describing what notebooks will live there. No notebooks drafted yet — this is the scaffolding pass.
