# irilab2026

The Virtual Lab repository for the `Decoding Plant Biology` portion of iResearch Institute's 2026 program. One repo, cloned by every student, holding everything needed to work through one of eight research questions: shared library code, all notebooks across both rationales, and supporting documentation.

## Layout

```
irilab2026/
├── irilab2026/             # Python library (plumbing only)
│   ├── environment.py      # setup(), Drive mounting, runtime checks
│   └── data.py             # dataset loaders (gene expression, plant images)
├── notebooks/              # Jupyter notebooks for every question
│   ├── r1/                 # Rationale 1: gene expression
│   │   ├── r1_orientation.ipynb
│   │   ├── r1-q1/
│   │   ├── r1-q2/
│   │   ├── r1-q3/
│   │   └── r1-q4/
│   └── r2/                 # Rationale 2: plant disease imaging
│   │   ├── r2_orientation.ipynb
│       ├── r2-q1/
│       ├── r2-q2/
│       ├── r2-q3/
│       └── r2-q4/
├── tests/                  # Smoke tests for the library
├── pyproject.toml
├── CHANGELOG.md
├── CLAUDE.md
├── LICENSE
└── README.md
```

The library code (under `irilab2026/irilab2026`) is for "plumbing only" - meaning it does an important job but you don't need to see it, it just works. The files `environment.py` and `data.py` configure the environment on Colab for the student. Under this configuration all notebooks will run without further adjustment. The analytical and pedagogical code lives in the notebooks (under `notebooks`) and this is where students should focus their time and attention.

## How a student should use this repo

**The Colab path (default).** Each notebook in `notebooks/` has an "Open in Colab" link at the top. Clicking it opens the notebook in a browser; the first cell installs the library from a tagged release and runs `setup()`:

```python
!pip install git+https://github.com/geraldmc/irilab2026.git -q
from irilab2026 import setup
setup()
```

The student never has to clone the repo to run a notebook. Colab handles everything.

**The clone path (optional).** students who want everything locally can clone the repo and either pip-install the library in editable mode or just open the notebooks in Jupyter:

```bash
git clone https://github.com/geraldmc/irilab2026.git
cd irilab2026
pip install -e .
jupyter lab notebooks/
```

Local execution is documented but not supported as a primary path. "Works on my machine" issues for local installs are the student's problem to debug, or to sidestep by running the notebook in Colab instead.

## The library

Two functions, both imported from the top of the package:

```python
from irilab2026 import setup, load_atgenexpress

setup(gpu_required=False)        # first cell of every notebook
data = load_atgenexpress()       # dict[stress_name, DataFrame]
```

`setup()` detects Colab, mounts Google Drive, checks the runtime against the notebook's declared GPU requirement, and prints a one-line summary. `load_atgenexpress()` downloads (or loads from cache) the AtGenExpress abiotic stress dataset from GEO and returns one DataFrame per stress.

See the docstrings in `irilab2026/environment.py` and `irilab2026/data.py` for the full API.

## The notebooks

Every notebook maps to a row in a question page's Workflow table on Notion. Notebooks are organized by rationale and question:

- `notebooks/r1/r1_orientation.ipynb` is the AtGenExpress on-ramp, reused across all four R1 questions.
- `notebooks/r1/r1-q1/01_deg_analysis.ipynb` (and 02, 03, 04) are R1-Q1's four analytical notebooks.
- `notebooks/r1/r1-q2/`, `r1-q3/`, `r1-q4/` follow the same convention.
- `notebooks/r2/r2-q1/` through `r2-q4/` likewise.

Each question folder has its own README listing the notebooks it contains, the data they use, and any caveats specific to that question.

## Status

This is the scaffolding pass. The library exists at v0.1.0 with `setup()` and `load_atgenexpress()`. Notebook directories exist with READMEs but no notebooks yet. The first notebook to be drafted is `r1/r1_orientation.ipynb`, followed by R1-Q1's four notebooks in workflow order.

## Development

```bash
git clone https://github.com/geraldmc/irilab2026.git
cd irilab2026
pip install -e ".[dev]"
pytest
```

## License

MIT. See `LICENSE`.
