# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`irilab2026` is the shared Python package + Jupyter notebook suite for the iResearch Institute 2026 Virtual Lab mentorship. Mentees open notebooks in Google Colab; the package gives them a one-line environment setup and tested data loaders so the lesson stays on the science, not Colab plumbing.

The package and the notebooks have different audiences and different rules:

- **`irilab2026/` is plumbing.** Library code, not pedagogy. Tested, terse, reusable across notebooks.
- **`notebooks/` is teaching material.** Audience-facing. Markdown explanations, stepwise reveals, and clarity-over-cleverness matter more than terseness.

Treat changes to the library as load-bearing for every notebook. Treat notebooks as student-facing — clarity beats elegance.

## What this repo is not

The repo holds the Python package and notebooks. It does not hold:

- Question pages (R1-Q1 through R2-Q4) — these live in Notion.
- The citation library and paper synopses — Notion.
- Hypothesis statements, reality-check documents, and program-level closeouts — Notion and prior chat outputs.
- The mentor SOP, program calendar, and deliverables structure — iRI Notion Wiki.

If asked to produce any of the above, ask before adding it to the repo. The default is they belong elsewhere.

## Working style

- Conversational dialogue. Talk through changes before making them, especially anything touching multiple files or affecting notebook structure.
- Work backwards from the desired outcome to the implementation, not the other way around. State the outcome first.
- Plain English. No private jargon. If a term needs defining, define it.
- Reproducibility matters. Pinned versions, deterministic seeds where relevant, cache paths over ad-hoc downloads. Notebooks currently install from `@main` because no milestone release is tagged yet — see **Distribution** under Project status for the policy and the eventual move to pinned tags.
- Python is the working language.

## Glossary

- **Rationale 1 (R1)** — the RNA-seq / gene-expression track of the Virtual Lab program. Four research questions, R1-Q1 through R1-Q4.
- **Rationale 2 (R2)** — the computer-vision / plant-disease track. Four questions, R2-Q1 through R2-Q4. R2-Q1 and R2-Q2 are reference chains (analytically closed); R2-Q3 and R2-Q4 are drafted as of 2026-05-29.
- **AtGenExpress** — Kilian et al. 2007 abiotic-stress microarray series on the ATH1 platform. GSE5620–GSE5628 on GEO. Eight stresses reachable via GEO; the ninth (oxidative) is TAIR/NASCArrays-only and deliberately excluded from `load_atgenexpress()`.
- **Wang 2023** — RNA-seq cold-stress dataset (PRJNA767196 / SRP339213). Test side for R1-Q4 cross-platform classifier; not in the loader yet.
- **EQ#1, EQ#2** — Essential Question reports. Mentee deliverables in weeks 1 and 2 of the program. Notebook prose may reference them; they are not produced by code.
- **Canonical hypothesis statement** — the agreed-upon wording of a hypothesis. (The phrase "lock language" was retired across the project; do not use it.)
- **Citation form** — papers are cited by author and year (e.g. "Hakkak & Tohidfar 2026"), never by position in any list.

## Repository conventions

These are decided, not aspirational. Don't deviate without a reason.

- **Notebook filenames:** numeric prefix in workflow order, then a short descriptive name — `01_deg_analysis.ipynb`, `02_core_overlap.ipynb`. Sorts correctly without thinking about it.
- **Question folder names:** lowercase, hyphenated — `r1-q1/`, not `R1Q1/` or `r1_q1/`.
- **Rationale orientation notebooks** sit as a sibling of the question folders (e.g. `notebooks/r1/r1_orientation.ipynb`), not nested in their own folder.
- **Install line every notebook currently uses** is `pip install git+https://github.com/geraldmc/irilab2026.git@main`. This pins to the latest commit on `main`; proper versioned tags are deferred until a milestone release. This is provisional — see **Distribution** under Project status for the full policy and what changes once a release is cut.

## Notebook pedagogy: unwrapped-then-wrapped

Each rationale's `orientation.ipynb` teaches setup in two passes:

1. **Unwrapped:** demoes `is_colab()`, `mount_google_drive()`, `has_gpu()` individually with markdown explaining each.
2. **Wrapped:** introduces `setup()` (or `setup(gpu_required=True)`) as the form every other notebook will use.

Analytical notebooks (`r1-q1/01_*.ipynb` etc.) use only the wrapped form — `setup()` first, no helper calls. The orientation is the only place students see the unwrapped helpers.

### Audience and tone

Mentees are high school and early college students. Assume no prior Python beyond basic syntax and no prior molecular biology beyond high-school level. Define terms before using them. Avoid idioms and metaphors that assume cultural context. Prefer literal descriptions in markdown — "the cell that loads the data," not "the engine of the notebook."

## Library specifics worth knowing before editing

- **`setup()`'s GPU check is intentionally asymmetric:** hard-error if `gpu_required=True` and no GPU is available; soft note ("GPU available") if a GPU is present but not required. Do not "fix" the asymmetry.
- **`load_atgenexpress()` deliberately excludes the ninth AtGenExpress condition (oxidative).** Oxidative is TAIR/NASCArrays-only and not on GEO. Don't add it. The docstring and `data.py` module docstring explain why.
- **The GSE→stress mapping in `data.py` was verified against GEO accession titles.** Don't change it without re-verifying against GEO directly — a wrong mapping silently produces analyses on the wrong stress.
- **Cache directory** is `My Drive/irilab2026_cache/` in Colab (Drive mounted), `/content/irilab2026_cache/` in Colab without Drive (fallback only), `~/.irilab2026_cache/` locally. The `_soft/` subdirectory inside it is GEOparse's SOFT-file cache.
- **`probe_to_agi()` returns a dict, not a Series.** Deliberate, for parity with the R1-Q1 inline pattern and to simplify testing. Don't switch return types without checking call sites; `df.index.map(probe_to_agi)` and `df['probe_col'].map(probe_to_agi)` both work with the dict form.
- **`vision.py`'s train and eval transforms share normalization constants by construction.** `_IMAGENET_MEAN` and `_IMAGENET_STD` are module-level so train, eval, and `randaugment_train_transform` cannot drift out of sync. Don't duplicate them inside individual transform functions.
- **`train_baseline()`'s recipe is locked to R2-Q1 N03's choices** — SGD 0.9, lr 0.01 → 0.001 step at epoch 7, batch 32, 10 epochs, 10% stratified val carve, best-val checkpointing. Changing any of these silently invalidates cross-condition comparability with R2-Q1's published baseline. Don't tune.
- **`train_baseline()` has two recent additive parameters.** `train_transform=None` (defaults to `imagenet_train_transform()`); `val_dataset_class=None` (defaults to `dataset_class`). Both are backward-compatible — `None` reproduces the pre-parameter behavior. The val transform is always `imagenet_eval_transform()` regardless of `train_transform`; validation augmentation is wrong by design, so there is no override knob for that.
- **`evaluate_in_categories()` uses an asymmetric mapping deliberately.** Predictions are always mapped with the *training dataset's* (PV's) class-to-category lookup, because the model emits indices in its training class space. Ground-truth labels are mapped with the *eval dataset's* lookup. This asymmetry is what makes the PV→PD comparison correct; do not "fix" it.
- **`train_baseline()` and `evaluate_in_categories()` both require a GPU.** They call `.cuda()` directly. Notebooks that train or evaluate should call `iri.setup(gpu_required=True)` so the absence of a GPU fails at setup rather than mid-recipe.

## Commands

```bash
# Install for development
pip install -e ".[dev]"

# Run all tests (smoke only — no network)
pytest

# Run a single test
pytest tests/test_smoke.py::test_unknown_stress_raises

# Quick local check that setup() works
python -c "from irilab2026 import setup; setup()"
```

**Tests are smoke only and must stay network-free.** No test should hit GEO. CI is not allowed to depend on GEO's uptime. If you need to test the loader's network path, do it in a separate, opt-in integration suite — not in `tests/`.

## Open decisions

These are pending choices. Don't silently default to one path; raise the question when it would first be needed.

- **Notebook source format.** Notebooks are currently authored as `.ipynb` directly. Whether to move to a jupytext-paired `.py` / `.ipynb` setup so source is reviewable in Git is undecided. Don't introduce jupytext unprompted.
- **`r1_orientation.ipynb` structural revision.** The v0.1.0 status note flagged that the orientation notebook would need one structural revision after R1-Q1's analytical notebooks landed and revealed what orientation actually needs to set up. R1-Q1 is now complete; the revision has not been done. Decide whether it is still needed and, if so, scope it.
- **Install line normalization.** Six distinct install patterns coexist across the 35 notebooks: `--force-reinstall --no-deps git+...@main` (R1-Q1 and parts of R1-Q2), plain `git+...@main` (most of R1-Q2 onward and all of R2-Q3/Q4), the commented two-line printed pattern (all of R2-Q1 and R2-Q2), and orientation-only one-offs. The repository-conventions section names `pip install -q git+...@main` as the canonical line; if that's still the intent, the 35 notebooks need rewriting for uniformity. If the two-mode pattern in R2-Q1/Q2 is the better answer because of the numpy footgun, propagate that pattern instead.
- **Precommit notebook naming.** The "Week 1 orient + write precommit.json" role uses three different filenames: `00_question_orientation` (R1-Q2), `00_orient_and_precommit` (R1-Q3, R1-Q4, R2-Q3, R2-Q4), and `01_orientation_and_precommit` (R2-Q2); R2-Q1 embeds it inside `02_pd_orientation`. Pick one.
- **Notebook numbering origin.** Some folders start at `01` (R1-Q1, R2-Q1, R2-Q2); others start at `00` (R1-Q2 onward in R1, R2-Q3 and R2-Q4 in R2). Either is fine; both is churn.
- **Classifier weight file extension.** R2-Q1 saves `baseline_resnet18.pt`; R2-Q3 N01 saves `*.pkl`; R2-Q4 N01 prose says `.pt` while the code path saves `.pkl`. PyTorch state_dicts are conventionally `.pt`. Pick one.

## Cutting a data release

Data products are hosted on one of two platforms — GitHub releases (a versioned tarball with a SHA256 the loader verifies) or Hugging Face Hub (versioned Parquet-shard datasets the `datasets` library fetches). The choice is per-product, based on access pattern: tarballs work fine for medium-sized, all-at-once releases; HF works better for image datasets where many-small-file extraction on Drive would otherwise be the bottleneck.

Existing products and their platforms:

| Product | Platform | Tag scheme |
|---|---|---|
| Orientation sample | GitHub release | `data-orientation-vX.Y.Z` |
| PlantVillage full image dataset | Hugging Face Hub | `vX.Y.Z` on `geraldmc/plantvillage-full` |
| PlantVillage tiny image dataset (debug-grade subset) | Hugging Face Hub | `vX.Y.Z` on `geraldmc/plantvillage-tiny` |
| PlantDoc full image dataset | Hugging Face Hub | `vX.Y.Z` on `geraldmc/plantdoc-full` |
| PlantDoc tiny image dataset (debug-grade subset) | Hugging Face Hub | `vX.Y.Z` on `geraldmc/plantdoc-tiny` |
| PlantVillage pre-extracted features (deferred) | GitHub release | `data-pv-features-vX.Y.Z` |

## Known footguns and how to handle them

A growing list of environmental gotchas that have bitten this project before and will again. Each entry describes the symptom first (what you'll see when it happens), then the cause, then the recovery procedure.

### The numpy ABI break after a fresh pip install in Colab

**Symptom.** A cell that should just be importing or calling library code raises an `ImportError` deep in numpy's internals — typically something like `cannot import name '_center' from 'numpy._core.umath'`. Stack trace often goes through `datasets`, `pyarrow`, or `pandas` rather than touching project code directly. The error doesn't reproduce on a fresh runtime — only after a pip install ran during the current session.

**Cause.** `pip install ... irilab2026` (or upgrading any package whose deps include numpy) pulled in a newer numpy version. Modules already imported into the running Python process — including pyarrow, numba, and `datasets`'s C extensions — were compiled against the older numpy ABI. Python now holds two incompatible numpy versions in memory at once. Colab usually prompts to restart but the prompt is not reliable; it sometimes silently skips. The first cell that imports anything depending on numpy after the install triggers the error.

**Recovery.** Runtime menu → Restart session. The pip-installed package stays on disk; only in-memory state is lost. You'll need to re-run authentication cells (e.g. `login(token=...)`) and `import irilab2026 as iri; iri.setup()`. After restart, numpy is at a single consistent version and imports resolve cleanly. **Do not** try to re-pip-install or use `--force-reinstall` — that just churns deps more and doesn't fix the in-memory state.

**Mitigation when writing new student-facing notebooks.** Three patterns reduce the frequency of this footgun:

1. Default install line uses `--no-deps`: `!pip install -q --upgrade --no-deps git+https://github.com/geraldmc/irilab2026.git@main`. The `--no-deps` flag tells pip not to touch the dep tree at all, avoiding any numpy upgrade. The trade-off: students need to install the deps separately on a fresh runtime, and a new dep added to `pyproject.toml` requires a one-time deps install. The two-mode pattern documented in `pip-install-reference.md` walks through this in detail.

2. Include a markdown cell in the install region acknowledging the restart prompt: "If Colab shows a yellow banner asking to restart the runtime after the install cell, click Restart Session and re-run from this cell forward. This is normal — pip upgraded numpy and Python needs a fresh process to use it cleanly." The PV Notebook 01 install region has this cell as of yesterday's loader-rewrite chat; copy the pattern.

3. Be aware of the numpy floor pyWGCNA forces. R1-Q2 uses pyWGCNA 2.2.1, which requires `numpy >= 2.1.0`. This means the project-wide `pyproject.toml` cannot pin a numpy ceiling below 2.1 without breaking R1-Q2. Restricting numpy at the project level was considered and rejected during the R2-Q1 PD packaging chat. The footgun remains; the install-time mitigations above are how we live with it.

**Why this entry exists.** First surfaced during R2-Q1 PD verification, and likely to recur on every fresh Colab session that pulls in a numpy upgrade through the package dep tree. The recovery is mechanical once you know what's happening; this entry exists so the recovery is the first thing you reach for rather than the third.

### GitHub release flow (tarball)

Used by the orientation sample and the deferred PV-features release.

1. Build the tarball: `python scripts/build_<product>_tarball.py`
2. Note the SHA256 from the script's output box
3. Cut the release on GitHub:
   - Tag: per-product, as in the table above (always with the `data-` prefix and a product qualifier)
   - Drag the tarball into Assets
   - **Click "Publish release," not "Save draft"** (drafts are not publicly downloadable)
4. Update the matching `_<PRODUCT>_URL` / `_<PRODUCT>_SHA256` constants in `irilab2026/data.py`
5. Commit, push, smoke-test on a fresh Colab runtime

### Hugging Face Hub flow

Used by `plantvillage-full` and `plantvillage-tiny`. Both variants are built and pushed by a single script.

1. Build and push: `python scripts/build_pv_full_hf.py`
   - The script clones the upstream source, constructs the metadata and HF `Dataset` objects for both `full` and `tiny` variants, calls `push_to_hub` for each, and tags the revision.
   - Authentication: requires a one-time `huggingface-cli login` (write-scoped). The token persists in `~/.cache/huggingface/token`; students need no auth at all to read.
   - Local debug artifacts (`metadata_*.csv`, `provenance_*.json`) land in `build/` for diff-checking; these are not pushed to HF.
2. Verify the push: visit `https://huggingface.co/datasets/geraldmc/plantvillage-full` (and the `-tiny` repo); confirm the new tag is present in the file tree's revision dropdown.
3. Update `_PV_HF_REVISION` in `irilab2026/data.py` to the new tag.
4. Commit, push, smoke-test on a fresh Colab runtime by calling `iri.load_plantvillage(variant="tiny")` first (smaller download), then `iri.load_plantvillage()` (full variant).

The HF flow does not produce a SHA256 or a downloadable tarball asset. Reproducibility lives in the Parquet shards on HF (immutable under content-addressed storage) and in the revision tag pinned by `_PV_HF_REVISION`. Tags are nominally mutable, so namespace discipline (single-author `geraldmc/`) is what makes them effectively immutable for this project; treat the act of retagging as you'd treat force-pushing to a release branch.

## Cutting a library release

No library release has been cut yet — versioning is deferred until a milestone (see **Distribution** below). When the first release is cut, this section should document the procedure. At minimum it needs to cover: choosing the version number, keeping `__version__` in `irilab2026/__init__.py` and `version` in `pyproject.toml` in sync, tagging the release, and updating the install line in notebooks from `@main` to the pinned tag. Until then, treat this as TBD and raise it when the milestone is reached.

## Project status (as of v0.3.0)

The library has grown beyond setup-and-load-only into a full support layer for both rationales. Public API now numbers 18 exported symbols across five modules:

- **`environment.py`** — `setup`, `is_colab`, `mount_google_drive`, `has_gpu`, `cache_dir`, `output_dir`, `seed_all`.
- **`data.py`** — `load_atgenexpress`, `atgenexpress_metadata`, `probe_to_agi`, `load_plantvillage`, `PlantVillageDataset`, `load_plantdoc`, `PlantDocDataset`, `load_plantvillage_orientation`, `tair_gaf_path`.
- **`vision.py`** — `build_baseline_model`, `imagenet_train_transform`, `imagenet_eval_transform`, `randaugment_train_transform`.
- **`training.py`** — `train_baseline`.
- **`evaluation.py`** — `build_idx_to_cat`, `evaluate_in_categories`.

Tests in `tests/` remain network-free and pass — 86 tests across 7 files covering all five modules, including the recent `train_transform=` and `val_dataset_class=` parameters on `train_baseline`.

**R1 notebooks.** All four question chains drafted. R1-Q1 and R1-Q2 are analytically closed and through paper / presentation. R1-Q3 and R1-Q4 have full notebook content but their per-question READMEs still carry the "scaffolding drafted, body to fill" footer from earlier in the cycle and need a status refresh.

- `r1_orientation.ipynb` — drafted; the post-R1-Q1 structural revision flagged in the v0.1.0 status note has still not been done (see Open decisions).
- `r1-q1/` — three analytical notebooks (`01_deg_analysis`, `02_core_overlap`, `03_consensus_compare`), all closed. Note: the per-question README still references a `00_question_orientation.ipynb` that was never created in this folder; the row should drop.
- `r1-q2/` — five notebooks (`00_question_orientation`, `00b_matrix_quality_check`, `01_wgcna`, `02_hub_identification`, `03_comparison`), all closed. The only folder with a `00b` notebook.
- `r1-q3/` — four notebooks (`00_orient_and_precommit` through `03_compare_and_interpret`), drafted with substantial body content.
- `r1-q4/` — four notebooks (`00_orient_and_precommit` through `03_wang_evaluation`), drafted. `01_integration.ipynb` (VST + ATH1 alignment + ComBat) was the largest engineering risk in R1 and landed.

**R2 notebooks.** All four question chains drafted. R2-Q1 and R2-Q2 are reference chains (analytically closed); R2-Q3 and R2-Q4 were finalized in the 2026-05-25 → 2026-05-29 window. Per-question READMEs for R2-Q3 and R2-Q4 still carry the "scaffolding drafted" footer and need a status refresh.

- `r2_orientation.ipynb` — drafted. PlantVillage on-ramp via `load_plantvillage_orientation`.
- `r2-q1/` — five notebooks (`01_pv_orientation` through `05_gap_characterization`), all closed.
- `r2-q2/` — four notebooks (`01_orientation_and_precommit` through `04_categorization`), all closed. Only R2 notebook with an active second pip install (`segment-anything` in NB04).
- `r2-q3/` — four notebooks (`00_orient_and_precommit` through `03_comparison`), drafted.
- `r2-q4/` — four notebooks (`00_orient_and_precommit` through `03_per_disease_interpretation`), drafted.

**Distribution.** Unchanged from prior status. The library is on GitHub but not yet published to PyPI. Eventual policy: once a milestone release is cut, student-facing notebooks install from a pinned tag, `pip install git+https://github.com/geraldmc/irilab2026.git@vX.Y.Z`, and `@main` is reserved for active development. **No milestone release has been tagged yet**, so for now every notebook — student-facing included — installs from `@main`. The switch to `@vX.Y.Z` happens when the first library release is cut (see **Cutting a library release**). The library `__version__` and `pyproject.toml` version have both been bumped to 0.3.0 in step with code additions, but no matching git tag exists; treat these as in-tree version markers, not releases.
