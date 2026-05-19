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
- **Rationale 2 (R2)** — the computer-vision / plant-disease track. Four questions, R2-Q1 through R2-Q4. **No R2 notebooks exist in this repo yet** — focus is R1 first.
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

**Why this entry exists.** This bit during R2-Q1 PD verification on 2026-05-19. Loss of an hour of debugging time on a non-substantive issue. Future occurrences should be a 30-second fix once this section exists.

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

## Project status (as of v0.2.0)

The library has grown from setup-and-load-only to actively supporting R1-Q2 notebook
drafting. Public API: `setup()`, `output_dir()`, `load_atgenexpress()`,
`atgenexpress_metadata()` (added during R1-Q2 N0 drafting; AtGenExpress sample-level
metadata parsed from cached SOFT files), and the unwrapped helpers
`is_colab()`, `mount_google_drive()`, `has_gpu()`. Tests in `tests/` remain
network-free and pass.

**R1 notebooks.**

- `r1_orientation.ipynb` — drafted, but the post-R1-Q1 structural revision flagged
  in the v0.1.0 status note has not been done (see Open decisions).
- `r1-q1/` — all four notebooks complete and analytically closed:
  `00_question_orientation.ipynb`, `01_deg_analysis.ipynb`, `02_core_overlap.ipynb`,
  `03_consensus_compare.ipynb`. Remaining R1-Q1 deliverables (final paper,
  presentation) live outside the notebook chain.
- `r1-q2/` — in progress. `00_question_orientation.ipynb` complete (produces
  filtered per-tissue matrices and `precommit.json`). `01_wgcna.ipynb` actively
  drafting. `02_hub_identification.ipynb` and `03_comparison.ipynb` scoped but
  not drafted.
- `r1-q3/`, `r1-q4/` — not drafted. The Workflow / Considerations / References
  pass applied to R1-Q1 and R1-Q2 question pages has not yet been applied to
  these.

**R2 notebooks.** None exist. Question pages live on Notion. R2 drafting is
deferred until R1 lands.

**Distribution.** The library is on GitHub but not yet published to PyPI. The
eventual policy: once a milestone release is cut, student-facing notebooks install
from a pinned tag, `pip install git+https://github.com/geraldmc/irilab2026.git@vX.Y.Z`,
and `@main` is reserved for active development (the iteration shape with
`--upgrade --force-reinstall`). **No milestone release has been tagged yet**,
however, so until one is, every notebook — student-facing included — installs from
`@main`. The switch to `@vX.Y.Z` happens when the first library release is cut
(see **Cutting a library release**).