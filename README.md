# irilab2026

The Virtual Lab repository for the *Decoding Plant Biology* portion of iResearch Institute's 2026 program. One repo, cloned by every student, holding everything needed to work through one of eight research questions: shared library code, all notebooks across both rationales, and supporting documentation.

## What's here

```
irilab2026/
├── irilab2026/                       # Python library (plumbing only)
│   ├── environment.py                # Colab setup, Drive mounting, runtime checks
│   ├── data.py                       # dataset loaders (gene expression and plant images)
│   ├── vision.py                     # image-classifier helpers
│   └── training.py                   # training loop helpers
│
├── notebooks/                        # Jupyter notebooks for every question
│   │
│   ├── r1/                           # Rationale 1: Gene Expression
│   │   ├── r1_orientation.ipynb
│   │   ├── r1-q1/                    # Common stress core
│   │   ├── r1-q2/                    # Hub genes from co-expression
│   │   ├── r1-q3/                    # Feature attribution under batch effects
│   │   └── r1-q4/                    # Cross-dataset stress classifier
│   │   
│   └── r2/                           # Rationale 2: Plant Disease Imaging
│       ├── r2_orientation.ipynb
│       ├── r2-q1/                    # PV → PD transferability
│       ├── r2-q2/                    # Grad-CAM failure modes
│       ├── r2-q3/                    # Targeted vs kitchen-sink augmentation
│       └── r2-q4/                    # Cross-host transfer within PV
│  
├── tests/                            # smoke tests for the library
├── scripts/                          # ad-hoc scripts (data release tooling)
├── pyproject.toml
├── CHANGELOG.md
├── CLAUDE.md
├── LICENSE
└── README.md
```

The library code (under `irilab2026/`) is plumbing: it sets up the Colab environment, loads datasets, and provides shared modeling helpers, so the notebooks themselves can stay focused on the science. The analytical and pedagogical content lives in `notebooks/`, organized by rationale and question. Each question folder has its own README that explains the workflow, the data, the files each notebook produces, and any caveats specific to that question.

## Running a notebook

**The Colab path (default).** Each notebook in `notebooks/` opens in Google Colab from a badge at the top. The first cell installs the library and runs `setup()`:

```python
!pip install git+https://github.com/geraldmc/irilab2026.git@main
import irilab2026 as iri
iri.setup()
```

Colab handles the environment. You don't need to clone the repo.

**The clone path (optional).** Students who want everything locally can clone the repo and install the library in editable mode:

```bash
git clone https://github.com/geraldmc/irilab2026.git
cd irilab2026
pip install -e .
jupyter lab notebooks/
```

Local execution is documented but not the supported primary path. "Works on my machine" issues for local installs are the student's problem — or to sidestep by running the notebook in Colab instead.

## Where to start

Pick your rationale and open its orientation notebook first:

- **Rationale 1** (gene expression / machine learning on omics data) — open `notebooks/r1/r1_orientation.ipynb`. It walks through the AtGenExpress abiotic stress dataset and leaves the data in the shape the R1-Q1 through R1-Q4 notebooks pick up from.
- **Rationale 2** (computer vision / plant disease imagery) — open `notebooks/r2/r2_orientation.ipynb`. It does the same job for the PlantVillage and PlantDoc image datasets used across R2-Q1 through R2-Q4.

Then open the README in your question folder (for example, `notebooks/r1/r1-q1/README.md`) for the weekly workflow, data, and file conventions specific to that question.

For a map of the whole notebook tree, see `notebooks/README.md`.

## The library

`irilab2026` (currently v0.2.0) provides:

- **Environment** — `setup()`, Drive mounting, runtime and GPU checks, output and cache directory helpers, deterministic seeding.
- **Data** — loaders for the AtGenExpress abiotic stress series, PlantVillage, and PlantDoc; an AtGenExpress sample-metadata helper; a probe → AGI mapping for Arabidopsis microarray work.
- **Vision** — a ResNet-18 baseline classifier and the ImageNet-style training and evaluation transforms the R2 notebooks use.
- **Training** — a reusable training helper that implements the project's canonical training recipe (used by R2-Q1's baseline classifier and by R2-Q2's data-randomization sanity check).

See the docstrings in each module for the full API. Public API is what's exported from `irilab2026/__init__.py`; anything else is internal.

## Status

`irilab2026` is at v0.2.0. The R1-Q1, R1-Q2, R2-Q1, and R2-Q2 notebook chains are complete and verified to run end-to-end on Colab. R1-Q3, R1-Q4, R2-Q3, and R2-Q4 are at earlier stages of buildout. Each question folder's README is the source of truth for that question's current state.

## Development

```bash
git clone https://github.com/geraldmc/irilab2026.git
cd irilab2026
pip install -e ".[dev]"
pytest
```

Tests are smoke-only and stay network-free — no test should hit GEO, Hugging Face, or any external dataset host. CI cannot depend on those services' uptime. If you need to test the network paths, do it in a separate, opt-in integration suite.

## License

MIT. See `LICENSE`.