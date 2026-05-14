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
import re
import tarfile
import urllib.request
from importlib import resources
from pathlib import Path

import GEOparse           # <-- new
import pandas as pd

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

# ---------------------------------------------------------------------------
# Public — sample metadata
# ---------------------------------------------------------------------------

def atgenexpress_metadata(
    stresses: Iterable[str] | None = None,
    force_download: bool = False,
) -> pd.DataFrame:
    """
    Load sample-level metadata for the AtGenExpress abiotic stress series.

    Parses tissue, time point, and replicate number from GEO sample titles
    for the AtGenExpress accessions (GSE5620–GSE5628). Stress is assigned
    from the GSE the sample belongs to. The parsed metadata is cached as a
    parquet file after the first build; subsequent calls read from cache.

    On a cache miss, this function uses the SOFT files that
    ``load_atgenexpress`` has already downloaded. If a SOFT file is not yet
    on disk for a requested stress, ``load_atgenexpress`` is called first
    to fetch it.

    Parameters
    ----------
    stresses : iterable of str, optional
        Subset of stress names to include. Default: all nine conditions.
    force_download : bool, default False
        If True, force-re-download the SOFT files and re-parse from
        scratch, overwriting any cached metadata.

    Returns
    -------
    pandas.DataFrame
        Indexed by GSM ID. Columns:

        - ``stress`` (str): one of the AtGenExpress condition names.
        - ``tissue`` (str): ``'shoot'`` or ``'root'``.
        - ``time_h`` (float): time point in hours.
        - ``replicate`` (int): replicate number.
        - ``gse`` (str): the GEO accession the sample came from.

    Raises
    ------
    ValueError
        If any requested stress name is unknown.
    RuntimeError
        If the parsed per-stress chip counts do not match the canonical
        values from the AtGenExpress design (Hahn 2013 §4.1). A mismatch
        signals either drift in GEO content or a regex regression; both
        are conditions in which silent continuation is unsafe.

    Notes
    -----
    AtGenExpress sample titles follow the convention
    ``AtGen_6-NNNN_Stress-Tissue-TimePoint_RepN``, e.g.
    ``AtGen_6-0011_Control-Shoots-0h_Rep1``. The parser is the title-only
    parser verified in the R1-Q1 Week 2 walkthrough.

    Examples
    --------
    >>> from irilab2026 import atgenexpress_metadata
    >>> meta = atgenexpress_metadata(stresses=['cold'])
    >>> meta.shape
    (24, 5)
    >>> sorted(meta.columns.tolist())
    ['gse', 'replicate', 'stress', 'time_h', 'tissue']
    """
    if stresses is None:
        stresses = ALL_STRESSES

    requested = list(stresses)
    _validate_stress_names(requested)

    cache_file = cache_dir() / "atgenexpress_metadata.parquet"

    # Cache hit only counts if every requested stress is already in the
    # cached frame. A prior call with a smaller subset is not a hit for a
    # larger request.
    if cache_file.exists() and not force_download:
        cached = pd.read_parquet(cache_file)
        if set(requested).issubset(set(cached["stress"].unique())):
            return cached[cached["stress"].isin(requested)].copy()

    metadata = _build_atgenexpress_metadata(requested, force_download=force_download)
    _validate_chip_counts(metadata, requested)
    metadata.to_parquet(cache_file)
    return metadata

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
        # The tarball's internal layout is plantvillage_orientation/...,
        # so we extract to the cache root and let the prefix create the
        # extracted/ directory itself.
        print(f"Extracting to {extracted} ...")
        with tarfile.open(tarball, "r:gz") as tf:
            tf.extractall(cache, filter="data")

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

    return {
        "manifest": manifest,
        "sample_paths": sample_paths,
        "sample_dir": extracted,
    }


from importlib import resources
from pathlib import Path


def tair_gaf_path() -> Path:
    """Return the filesystem path to the bundled TAIR GAF file.

    The TAIR GAF (Gene Association File) maps *Arabidopsis thaliana* AGI gene
    identifiers to GO terms — the gene-to-GO mapping that `goatools` consumes
    for functional enrichment. The file is gzipped (tair.gaf.gz).

    The file is bundled with the library rather than downloaded at runtime
    because the GO Consortium's distribution server (current.geneontology.org)
    returns HTTP 403 for programmatic access from some networks, including
    Colab in some sessions. Bundling guarantees reproducibility and avoids
    a runtime failure mode.

    See `irilab2026/resources/README.md` for the source URL and release date of
    the bundled version.

    Returns
    -------
    Path
        Filesystem path to `irilab2026/resources/tair.gaf.gz`. The returned path
        is suitable for passing to `gzip.open()` or any code expecting a
        readable file path.

    Examples
    --------
    >>> import gzip
    >>> from irilab2026 import tair_gaf_path
    >>> with gzip.open(tair_gaf_path(), 'rt') as f:
    ...     first_line = f.readline()
    """
    return Path(str(resources.files("irilab2026") / "resources" / "tair.gaf.gz"))

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

# ---------------------------------------------------------------------------
# Internal — sample-metadata parsing
# ---------------------------------------------------------------------------


# AtGenExpress canonical per-stress chip counts. Sourced from Hahn 2013 §4.1
# and verified against the Pass 1 reality-check.
_EXPECTED_CHIP_COUNTS: dict[str, int] = {
    "control": 36,
    "cold": 24,
    "osmotic": 24,
    "salt": 24,
    "drought": 28,
    "genotoxic": 24,
    "uv_b": 28,
    "wounding": 28,
    "heat": 32,
}


# Time point: matches '0h', '0.25h', '0.5 h', '30 min', etc.
#
# Python's \b does not trigger before an underscore (underscore is a word
# character in Python regex), so a naive \b after the unit fails on
# AtGenExpress titles like '0.25h_Rep1'. The explicit lookahead handles
# end-of-string, whitespace, underscore, and common delimiters.
_TIME_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*"
    r"(hours?|hrs?|h|minutes?|mins?|m)"
    r"(?=$|[\s_\-,;|/])",
    re.IGNORECASE,
)


# Replicate: matches 'Rep1', 'replicate 2', '_R1', etc.
_REP_RE = re.compile(
    r"(?:replicate|rep|biological\s*replicate)\D*?(\d+)"
    r"|_R(\d+)\b",
    re.IGNORECASE,
)


def _extract_tissue(title: str) -> str | None:
    """Return 'shoot' or 'root', or None if the title is unclear."""
    t = title.lower()
    if "root" in t:
        return "root"
    if any(w in t for w in ("shoot", "leaf", "leaves", "rosette", "aerial")):
        return "shoot"
    return None


def _extract_time(title: str) -> float | None:
    """Return the time point in hours (minutes converted), or None."""
    m = _TIME_RE.search(title)
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2).lower()
    return value / 60.0 if unit.startswith("m") else value


def _extract_rep(title: str) -> int | None:
    """Return the replicate number as an int, or None."""
    m = _REP_RE.search(title)
    if not m:
        return None
    for group in m.groups():
        if group:
            return int(group)
    return None


def _build_atgenexpress_metadata(
    stresses: list[str],
    force_download: bool = False,
) -> pd.DataFrame:
    """
    Parse sample metadata from the cached SOFT files.

    For each requested stress, ensure the corresponding SOFT file is on
    disk (via ``_load_one_gse``, which is a no-op when the GSE is already
    cached), then read the SOFT file locally with GEOparse and parse each
    GSM's title into structured fields.
    """

    rows = []
    soft_dir = cache_dir() / "_soft"

    for stress in stresses:
        gse_id = STRESS_TO_GSE[stress]

        # Side-effect call: ensures the SOFT file is in soft_dir. The
        # returned expression DataFrame is unused here.
        _load_one_gse(gse_id, force_download=force_download)

        # GEOparse names SOFT files <GSE>_family.soft.gz, but glob to be
        # robust to any future naming change.
        soft_candidates = list(soft_dir.glob(f"{gse_id}*.soft.gz"))
        if not soft_candidates:
            raise RuntimeError(
                f"Expected a SOFT file for {gse_id} in {soft_dir} after "
                f"_load_one_gse, but found none. Cache may be in a bad state; "
                f"try force_download=True."
            )

        gse = GEOparse.get_GEO(filepath=str(soft_candidates[0]), silent=True)

        for gsm_id, gsm in gse.gsms.items():
            title = " ".join(gsm.metadata.get("title", []))
            rows.append({
                "GSM": gsm_id,
                "stress": stress,
                "tissue": _extract_tissue(title),
                "time_h": _extract_time(title),
                "replicate": _extract_rep(title),
                "gse": gse_id,
            })

    return pd.DataFrame(rows).set_index("GSM")


def _validate_chip_counts(metadata: pd.DataFrame, requested: list[str]) -> None:
    """
    Verify that per-stress chip counts match the canonical values.

    A mismatch means either GEO has drifted from what was deposited in
    2007, or the regex parser has regressed. Both are conditions where
    silent continuation produces analyses on the wrong data.
    """
    observed = metadata.groupby("stress").size().to_dict()
    mismatches = []
    for stress in requested:
        expected = _EXPECTED_CHIP_COUNTS[stress]
        actual = observed.get(stress, 0)
        if actual != expected:
            mismatches.append((stress, expected, actual))

    if mismatches:
        lines = ["Chip count mismatch against AtGenExpress canonical values:"]
        for stress, expected, actual in mismatches:
            lines.append(f"  {stress}: expected {expected}, got {actual}")
        lines.append(
            "This suggests either GEO content has changed, or the title "
            "parser has regressed."
        )
        raise RuntimeError("\n".join(lines))