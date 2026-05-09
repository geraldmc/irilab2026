# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-05-08

Initial release. Establishes the package skeleton and the first two public functions.

### Added

- `setup()` — single entry point called at the top of every notebook. Detects whether the notebook is running in Google Colab, mounts Google Drive when it is, checks the runtime against the notebook's declared GPU requirement, and prints a one-line summary.
- `load_atgenexpress()` — downloads (or loads from cache) the AtGenExpress abiotic stress microarray dataset from GEO accessions GSE5620–GSE5628. Returns a dict keyed by stress name, with one pandas DataFrame per stress (probes × samples).
- Cache directory at `My Drive/irilab2026_cache/` in Colab; `~/.irilab2026_cache/` locally.
- `notebooks/` directory tree: `r1/` and `r2/` rationale folders, each with per-question subfolders (`r1-q1/` through `r1-q4/`, `r2-q1/` through `r2-q4/`). Each folder has a README describing what notebooks will live there. No notebooks drafted yet — this is the scaffolding pass.
