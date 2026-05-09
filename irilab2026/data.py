"""
Dataset loaders.

For v0.1.0, the only loader is ``load_atgenexpress``, which fetches the
AtGenExpress abiotic stress microarray series from GEO (accessions
GSE5620–GSE5628) and returns one DataFrame per stress.

A note on what's included: GEO hosts the eight stress conditions plus the
control. The ninth AtGenExpress condition, oxidative stress, lives at
TAIR/NASCArrays only and is not reachable from the GEO download path. The
loader is honest about this — it loads what GEO has, and downstream code
should not assume "all nine AtGenExpress stresses" are present.
"""

from __future__ import annotations
import hashlib
import tarfile
import urllib.request

from pathlib import Path
from typing import Iterable

import pandas as pd

from irilab2026.environment import cache_dir


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


# AtGenExpress abiotic stress series. Mapping verified against GEO accession
# titles during the Phase 1 Pass 1 reality-check (see project documentation).
GSE_TO_STRESS: dict[str, str] = {
    "GSE5620": "control",
    "GSE5621": "cold",
    "GSE5622": "osmotic",
    "GSE5623": "salt",
    "GSE5624": "drought",
    "GSE5625": "genotoxic",
    "GSE5626": "uv_b",
    "GSE5627": "wounding",
    "GSE5628": "heat",
}

STRESS_TO_GSE: dict[str, str] = {v: k for k, v in GSE_TO_STRESS.items()}

ALL_STRESSES: tuple[str, ...] = tuple(GSE_TO_STRESS.values())


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def load_atgenexpress(
    stresses: Iterable[str] | None = None,
    force_download: bool = False,
) -> dict[str, pd.DataFrame]:
    """
    Load the AtGenExpress abiotic stress microarray dataset from GEO.

    Each requested stress condition is downloaded from its GEO accession (or
    loaded from the local cache, if a previous call already downloaded it),
    and returned as a pandas DataFrame with probe IDs as the row index and
    GEO sample IDs (GSMxxxxx) as columns.

    Parameters
    ----------
    stresses : iterable of str, optional
        Subset of stress names to load. Default: all nine conditions
        (``'control'``, ``'cold'``, ``'osmotic'``, ``'salt'``, ``'drought'``,
        ``'genotoxic'``, ``'uv_b'``, ``'wounding'``, ``'heat'``).
    force_download : bool, default False
        If True, re-download from GEO and overwrite the cache. Useful if the
        cached file is suspected to be corrupted.

    Returns
    -------
    dict[str, pandas.DataFrame]
        Keys are stress names. Values are DataFrames of shape
        ``(n_probes, n_samples)``, where ``n_probes`` is roughly 22,000 (the
        ATH1 array) and ``n_samples`` varies by stress (typically 24–36).
        Cell values are the normalized expression values from GEO.

    Notes
    -----
    Sample-level metadata (tissue, time point, replicate) is encoded in the
    GSM titles, which are accessible via GEOparse if needed. A future
    version of this loader may parse these into a separate metadata
    DataFrame.

    Examples
    --------
    >>> from irilab2026 import load_atgenexpress
    >>> data = load_atgenexpress(stresses=['cold', 'control'])
    >>> data['cold'].shape
    (22810, 24)
    """
    if stresses is None:
        stresses = ALL_STRESSES

    requested = list(stresses)
    _validate_stress_names(requested)

    out: dict[str, pd.DataFrame] = {}
    for stress in requested:
        gse_id = STRESS_TO_GSE[stress]
        out[stress] = _load_one_gse(gse_id, force_download=force_download)
    return out

# --- PlantVillage orientation loader ---

# Pinned release artifact. The data version tag is separate from the library
# version on purpose — tarball updates shouldn't force library releases,
# and library patches shouldn't invalidate cached tarballs.
_PV_ORIENTATION_URL = (
    "https://github.com/geraldmc/irilab2026/releases/download/"
    "data-v0.1.0/plantvillage_orientation.tar.gz"
)
_PV_ORIENTATION_SHA256 = (
    "7cc593e009d3ae45ffc3928eb0fea1929b1c6f5220a9c62bd02ac5ccc5b360c7"
)


def _sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_and_verify(url, expected_sha256, dest):
    """Download url to dest and verify its SHA256. Raises on mismatch."""
    print(f"Downloading {url} ...")
    urllib.request.urlretrieve(url, dest)
    actual = _sha256_of_file(dest)
    if actual != expected_sha256:
        dest.unlink()  # remove the bad file so the next try starts clean
        raise RuntimeError(
            f"SHA256 mismatch for {dest.name}\n"
            f"  expected: {expected_sha256}\n"
            f"  got:      {actual}\n"
            f"The download may be corrupt. Try again or report this issue."
        )


def load_plantvillage_orientation():
    """Load the PlantVillage orientation slice.

    Returns the full structural picture of PlantVillage (a manifest of all
    38 classes with their *total* image counts in the full dataset) plus a
    deterministic sample of ~5 images per class (~190 images, ~3 MB)
    for visual inspection.

    For the full ~54k-image dataset used in R2-Q1 onward, use
    load_plantvillage_full() instead.

    Returns
    -------
    dict
        'manifest'     : pd.DataFrame, 38 rows
                         (class, host, disease, is_healthy, n_total)
        'sample_paths' : pd.DataFrame, ~190 rows
                         (path, class, host, disease)
        'sample_dir'   : pathlib.Path, root of extracted samples
    """
    cache = cache_dir()
    extracted = cache / "plantvillage_orientation"
    tarball = cache / "plantvillage_orientation.tar.gz"
    manifest_path = extracted / "manifest.csv"

    # If the cache already has the manifest, skip download + extract.
    if not manifest_path.exists():
        need_download = (
            not tarball.exists()
            or _sha256_of_file(tarball) != _PV_ORIENTATION_SHA256
        )
        if need_download:
            _download_and_verify(
                _PV_ORIENTATION_URL,
                _PV_ORIENTATION_SHA256,
                tarball,
            )
        print(f"Extracting to {extracted} ...")
        extracted.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tarball, "r:gz") as tf:
            tf.extractall(extracted, filter="data")

    if not manifest_path.exists():
        raise RuntimeError(
            f"Expected manifest at {manifest_path} after extraction. "
            f"The tarball may be malformed."
        )

    manifest = pd.read_csv(manifest_path)

    # Walk the extracted class directories to build the sample-paths table.
    # We don't re-parse host/disease from directory names — the manifest is
    # the authority on class structure, we just join against it.
    sample_rows = []
    for class_dir in sorted(extracted.iterdir()):
        if not class_dir.is_dir():
            continue
        for img_path in sorted(class_dir.glob("*.jpg")):
            sample_rows.append({
                "path": str(img_path),
                "class": class_dir.name,
            })
    sample_paths = pd.DataFrame(sample_rows).merge(
        manifest[["class", "host", "disease"]],
        on="class",
        how="left",
    )

    return {
        "manifest": manifest,
        "sample_paths": sample_paths,
        "sample_dir": extracted,
    }

# ---------------------------------------------------------------------------
# Internal — single-GSE handling
# ---------------------------------------------------------------------------


def _load_one_gse(gse_id: str, force_download: bool = False) -> pd.DataFrame:
    """
    Load one GEO series, using a parquet cache.

    On first call: download via GEOparse, build the probe-by-sample matrix,
    write to cache. On subsequent calls: read from cache directly.
    """
    cache_file = cache_dir() / f"{gse_id}.parquet"
    if cache_file.exists() and not force_download:
        return pd.read_parquet(cache_file)

    expression_df = _download_and_build(gse_id)
    expression_df.to_parquet(cache_file)
    return expression_df


def _download_and_build(gse_id: str) -> pd.DataFrame:
    """
    Download a GSE from GEO via GEOparse and build a probes-by-samples
    expression matrix from its constituent samples.
    """
    import GEOparse

    # GEOparse downloads the SOFT file to a temp dir and parses it.
    # The destdir argument keeps downloads in our cache so subsequent
    # GEOparse calls (e.g., during force_download) reuse the SOFT file.
    soft_dir = cache_dir() / "_soft"
    soft_dir.mkdir(parents=True, exist_ok=True)
    gse = GEOparse.get_GEO(geo=gse_id, destdir=str(soft_dir), silent=True)

    # Each GSM has a `.table` DataFrame with at least ID_REF and VALUE columns.
    columns: dict[str, pd.Series] = {}
    for gsm_id, gsm in gse.gsms.items():
        table = gsm.table
        if "ID_REF" not in table.columns or "VALUE" not in table.columns:
            raise ValueError(
                f"Sample {gsm_id} in {gse_id} is missing ID_REF or VALUE columns; "
                "GEO data shape may have changed."
            )
        columns[gsm_id] = pd.Series(
            data=table["VALUE"].values,
            index=table["ID_REF"].values,
            name=gsm_id,
        )

    # Concatenate sample columns; align on probe index.
    expression_df = pd.concat(columns, axis=1)
    expression_df.index.name = "probe_id"
    expression_df.columns.name = "sample_id"
    return expression_df


# ---------------------------------------------------------------------------
# Internal — validation
# ---------------------------------------------------------------------------


def _validate_stress_names(stresses: list[str]) -> None:
    """Raise a clear error if any stress name is unknown."""
    unknown = [s for s in stresses if s not in STRESS_TO_GSE]
    if unknown:
        raise ValueError(
            f"Unknown stress name(s): {unknown}. "
            f"Valid names: {list(ALL_STRESSES)}."
        )
