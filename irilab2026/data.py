"""
Dataset loaders for the irilab2026 library.

The module hosts loaders for two data domains:

- **AtGenExpress (Arabidopsis microarray).** ``load_atgenexpress``,
  ``atgenexpress_metadata``, ``probe_to_agi``. All fetch from GEO on
  first call and cache locally.

- **PlantVillage (plant disease images).**
  ``load_plantvillage_orientation`` ships a small ~190-image structural
  preview as a GitHub release tarball. ``load_plantvillage`` ships the
  full ~54k-image dataset from Hugging Face Hub.

A note on AtGenExpress scope: GEO hosts eight stress conditions plus the
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

from torch.utils.data import Dataset
from datasets import load_dataset

import GEOparse
import pandas as pd

from typing import Iterable

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
        - ``last_update_date`` (str): the GSM's ``last_update_date`` field
          from the SOFT file, formatted as ``YYYY-MM-DD``. Used downstream
          as a per-sample processing-date proxy for batch-confound tests.

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
    (24, 6)
    >>> sorted(meta.columns.tolist())
    ['gse', 'last_update_date', 'replicate', 'stress', 'time_h', 'tissue']
    """
    if stresses is None:
        stresses = ALL_STRESSES

    requested = list(stresses)
    _validate_stress_names(requested)

    cache_file = cache_dir() / "atgenexpress_metadata.parquet"

    # Cache hit only counts if every requested stress is already in the
    # cached frame AND the cached frame has the current schema. A prior
    # call with a smaller subset is not a hit for a larger request; an
    # older cache built before last_update_date was added (pre-v0.3.0)
    # is also not a hit and will be rebuilt.
    if cache_file.exists() and not force_download:
        cached = pd.read_parquet(cache_file)
        has_stresses = set(requested).issubset(set(cached["stress"].unique()))
        has_schema = "last_update_date" in cached.columns
        if has_stresses and has_schema:
            return cached[cached["stress"].isin(requested)].copy()

    metadata = _build_atgenexpress_metadata(requested, force_download=force_download)
    _validate_chip_counts(metadata, requested)
    metadata.to_parquet(cache_file)
    return metadata

# ---------------------------------------------------------------------------
# Public — probe-to-AGI mapping (2026-05-16 addition)
# ---------------------------------------------------------------------------

def probe_to_agi(force_download: bool = False) -> dict[str, str]:
    """
    Build a mapping from Affymetrix ATH1 probe IDs to AGI gene identifiers.

    The mapping comes from the GPL198 annotation table, which GEOparse
    fetches from GEO on first call and caches locally afterward. AGI
    (Arabidopsis Genome Initiative) codes are the standard locus
    identifiers in TAIR and other Arabidopsis resources; the form is
    ``AT`` followed by a chromosome number and a five-digit locus number,
    for example ``AT5G42570``.

    The returned dict has roughly 21,000 entries out of the 22,810 probes
    on the ATH1 array. Two groups are not included:

    1. **Probes targeting more than one locus.** The annotation lists the
       targets separated by ``' /// '`` (for example,
       ``'AT4G25490 /// AT4G25470'``). The first locus is taken as the
       probe's primary target. Multi-locus probes are a small fraction of
       the array, but they exist and need a deterministic rule.
    2. **Probes with no AGI annotation.** This category includes the
       Affymetrix control probes (the ``AFFX-`` prefixed set) and a small
       number of design-stage probes that were never matched to a locus.
       Both groups are dropped.

    Parameters
    ----------
    force_download : bool, default False
        If True, delete any cached GPL198 file and re-fetch from GEO.
        Useful if the cached file is suspected to be corrupted.

    Returns
    -------
    dict[str, str]
        Keys are probe IDs (for example, ``'249264_s_at'``); values are
        AGI codes in upper case (for example, ``'AT5G42570'``).

    Notes
    -----
    The GPL198 SOFT file is roughly 7 MB. The first call downloads it
    (a few seconds on a typical connection); subsequent calls read from
    the local cache directory ``iri.cache_dir()``.

    Examples
    --------
    >>> probe_to_agi = iri.probe_to_agi()
    >>> probe_to_agi['249264_s_at']
    'AT5G42570'

    Translating a column of probe IDs in a DataFrame indexed by probe:

    >>> hubs['agi_id'] = hubs.index.map(probe_to_agi)
    """
    destdir = cache_dir()

    if force_download:
        # GEOparse names GPL annotation files like ``GPL198.annot.gz`` or
        # ``GPL198_family.soft.gz`` depending on which path it took. Glob
        # to be robust to either.
        for soft_path in Path(destdir).glob("GPL198*"):
            soft_path.unlink()

    gpl = GEOparse.get_GEO(geo='GPL198', destdir=str(destdir), silent=True)
    return _build_probe_to_agi_dict(gpl.table)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _build_probe_to_agi_dict(gpl_table: pd.DataFrame) -> dict[str, str]:
    """
    Build the probe-to-AGI dict from a GPL198 annotation table.

    Separated from ``probe_to_agi`` so the parsing logic can be tested
    against a synthetic table without a network fetch. Expects the input
    to have ``'ID'`` and ``'AGI'`` columns.

    Multi-locus probes get their first locus; probes with empty or NaN
    AGI annotations are dropped.
    """
    table = gpl_table[['ID', 'AGI']].dropna()

    first_locus = (
        table['AGI']
        .astype(str)
        .str.split(' /// ')
        .str[0]
        .str.strip()
        .str.upper()
    )

    mask = first_locus != ''
    return dict(zip(table.loc[mask, 'ID'].astype(str), first_locus[mask]))


# --- PlantVillage loaders ---

# Pinned release artifact. The data version tag is separate from the library
# version on purpose — tarball updates shouldn't force library releases,
# and library patches shouldn't invalidate cached tarballs.
_PV_ORIENTATION_URL = (
    "https://github.com/geraldmc/irilab2026/releases/download/"
    "data-orientation-v0.1.0/plantvillage_orientation.tar.gz"
)
_PV_ORIENTATION_SHA256 = (
    "7cc593e009d3ae45ffc3928eb0fea1929b1c6f5220a9c62bd02ac5ccc5b360c7"
)

# Hugging Face Hub coordinates for the curated PlantVillage variants.
# The revision is pinned to a tag rather than a commit SHA — namespace
# discipline (single-author ``geraldmc/``) is what makes the tag effectively
# immutable in practice. Reproducibility-critical pinning would be a SHA.
_PV_HF_REPO_FULL = "geraldmc/plantvillage-full"
_PV_HF_REPO_TINY = "geraldmc/plantvillage-tiny"
_PV_HF_REVISION  = "v0.1.0"

# --- PlantDoc HF Hub flow ---

# Tag-pinned for reproducibility. Single-author namespace discipline
# (geraldmc/) is what makes the tag effectively immutable in practice.
_PD_HF_REPO_FULL = "geraldmc/plantdoc-full"
_PD_HF_REPO_TINY = "geraldmc/plantdoc-tiny"
_PD_HF_REVISION = "v0.1.0"

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


def load_plantvillage(
    variant: str = "full",
    force_download: bool = False,
):
    """Load a curated PlantVillage dataset from Hugging Face Hub.

    Returns a ``(metadata, images)`` tuple. The first element is a pandas
    DataFrame with one row per image and seven metadata columns; the
    second is a Hugging Face Dataset of the same length, holding the
    image bytes inline. Pair them through :class:`PlantVillageDataset`
    to feed a PyTorch ``DataLoader``.

    For a small structural overview of PlantVillage (38 classes,
    ~190 sample images), use :func:`load_plantvillage_orientation`
    instead.

    Parameters
    ----------
    variant : {"full", "tiny"}, default "full"
        Which curated variant to load.

        - ``"full"`` — ~54,000 images, the real training data (~1.5 GB
          download on first call).
        - ``"tiny"`` — ~1,900 images (50 per class), a debug-grade
          subset for training-loop development. Iterates in minutes
          instead of hours. **Not** for analysis; the per-class
          subsample is too small to be a faithful representative.

    force_download : bool, default False
        If True, bypass the local HF cache and re-fetch from the Hub.
        Useful if the cache is suspected to be corrupted.

    Returns
    -------
    tuple of (pandas.DataFrame, datasets.Dataset)
        First element: DataFrame with seven columns:

        - ``class_label``  (str)  — e.g. ``"Apple___Apple_scab"``
        - ``class_idx``    (int)  — 0-indexed, alphabetical over
          ``class_label``
        - ``host``         (str)  — e.g. ``"Apple"``
        - ``disease``      (str)  — e.g. ``"Apple_scab"`` or ``"healthy"``
        - ``split``        (str)  — ``"train"`` or ``"test"``
        - ``leaf_id``      (str)  — groups images from the same physical
          leaf
        - ``leaf_grouped`` (bool) — True if ``leaf_id`` reflects upstream
          grouping, False if it's synthetic (one per image)

        Second element: HF Dataset of the same length, where
        ``ds[i]["image"]`` returns a PIL Image for the i-th row of the
        metadata DataFrame.

    Notes
    -----
    **First call.** Downloads ~1.5 GB (full) or ~60 MB (tiny) of Parquet
    shards from the Hub. Requires network access. Subsequent calls in the
    same Python session read from memory; calls across sessions read from
    the on-disk cache under :func:`cache_dir`.

    **Filtering preserves the index.** This means filtered metadata
    DataFrames still align with the underlying HF Dataset by row number,
    which is what :class:`PlantVillageDataset` relies on. Don't
    ``reset_index()`` after filtering:

        >>> df, ds = iri.load_plantvillage()
        >>> train_df = df[df.split == "train"]
        >>> train_set = iri.PlantVillageDataset(train_df, ds, transform=tx)

    **Train/test lives in metadata, not HF splits.** The HF dataset has
    a single underlying "train" split; the train/test partition for
    analysis is the ``split`` metadata column. This loader assumes the
    HF layout has exactly one split named ``"train"``; an explicit error
    is raised if that assumption breaks.

    Examples
    --------
    >>> from irilab2026 import load_plantvillage, PlantVillageDataset
    >>> df, ds = load_plantvillage(variant="tiny")
    >>> df.shape
    (1900, 7)
    >>> sorted(df.columns.tolist())
    ['class_idx', 'class_label', 'disease', 'host', 'leaf_grouped',
     'leaf_id', 'split']
    """
    valid_variants = {"full", "tiny"}
    if variant not in valid_variants:
        raise ValueError(
            f"Unknown variant: {variant!r}. "
            f"Valid variants: {sorted(valid_variants)}."
        )

    repo_id = _PV_HF_REPO_FULL if variant == "full" else _PV_HF_REPO_TINY
    download_mode = (
        "force_redownload" if force_download else "reuse_dataset_if_exists"
    )

    # ``cache_dir`` is forwarded so that on Colab, HF's Parquet shards land
    # on Drive (persistent across sessions) rather than the ephemeral
    # ``/root/.cache/huggingface`` default. The HF library creates its own
    # subdirectory structure under the path we pass.
    ds = load_dataset(
        repo_id,
        revision=_PV_HF_REVISION,
        cache_dir=str(cache_dir()),
        download_mode=download_mode,
    )

    # The build pipeline pushed a single Dataset via ``push_to_hub``, which
    # HF wraps as ``DatasetDict({"train": <ds>})`` on the hub. Our train/
    # test logic uses the ``split`` metadata column, not HF's split
    # mechanism. Confirm the assumption explicitly so a future change to
    # the build script doesn't silently break the loader.
    if list(ds.keys()) != ["train"]:
        raise RuntimeError(
            f"Expected {repo_id}@{_PV_HF_REVISION} to have a single 'train' "
            f"split, but found splits: {list(ds.keys())}. The dataset's "
            f"split structure may have changed; the loader assumes train/test "
            f"live in the `split` metadata column."
        )
    images = ds["train"]

    # The metadata DataFrame is everything except the image column.
    metadata_columns = [c for c in images.column_names if c != "image"]
    metadata = images.select_columns(metadata_columns).to_pandas()

    return metadata, images


def load_plantdoc(variant: str = "full", force_download: bool = False):
    """Load the PlantDoc dataset from Hugging Face Hub.

    PlantDoc (Singh et al. 2020) is a field-condition plant disease
    dataset built from web-scraped images across 13 host species. Unlike
    PlantVillage's controlled lab images, PlantDoc images are
    heterogeneous in resolution, lighting, and background — which is
    why it's the canonical test bed for measuring whether a PV-trained
    classifier transfers to real-world conditions.

    Parameters
    ----------
    variant : {"full", "tiny"}, default "full"
        Which HF Dataset to fetch. The "full" variant has 2,578 images
        across 28 classes; "tiny" has ~164 images stratified across the
        same classes, intended for fast test-suite use.
    force_download : bool, default False
        If True, bypass the local cache and re-fetch from HF Hub.

    Returns
    -------
    metadata : pandas.DataFrame
        One row per image, seven columns (no image column — images
        live in the HF Dataset object):
            class_label   str   — upstream folder name, verbatim
            class_idx     int   — 0–27, case-sensitive alphabetical sort
            host          str   — normalized host name (see dataset card)
            disease       str   — lowercased disease name, "healthy" for healthy leaves
            is_healthy    bool  — True if disease == "healthy"
            split         str   — "train" or "test", from the upstream partition
            filename      str   — original filename, verbatim
    hf_dataset : datasets.Dataset
        The HF Dataset object. Each row has the seven metadata columns
        above plus an `image` column carrying a PIL Image.

    Notes
    -----
    First call on a fresh Colab session downloads ~950 MB (full) or
    ~50 MB (tiny) and caches to Drive if mounted (via the same
    cache_dir resolver used by load_plantvillage). Subsequent calls
    hit the cache. The tiny variant exists for test-suite and
    smoke-test use, not analysis — see its dataset card on HF.

    The upstream PlantDoc dataset has 28 classes, but one class
    (Tomato two spotted spider mites leaf) has only 2 training images
    and 0 test images. Singh et al. 2020 and downstream benchmark
    papers report 27 classes; this loader preserves all 28 for
    upstream fidelity. The orphan class shows up in both train and
    metadata; filter on `df["split"] == "test"` for evaluation use.

    Examples
    --------
    >>> df, ds = iri.load_plantdoc()
    >>> train = df[df["split"] == "train"]
    >>> dataset = iri.PlantDocDataset(train, ds, transform=my_transform)
    """
    if variant not in {"full", "tiny"}:
        raise ValueError(
            f"Unknown variant {variant!r}. Expected 'full' or 'tiny'."
        )

    repo_id = _PD_HF_REPO_FULL if variant == "full" else _PD_HF_REPO_TINY

    hf_dataset = load_dataset(
        repo_id,
        revision=_PD_HF_REVISION,
        split="train",
        cache_dir=str(cache_dir()),
        download_mode="force_redownload" if force_download else "reuse_dataset_if_exists",
    )

    metadata = hf_dataset.remove_columns(["image"]).to_pandas()
    return metadata, hf_dataset


class PlantVillageDataset(Dataset):
    """PyTorch Dataset wrapper around the PlantVillage (metadata, images) pair.

    Pass the metadata DataFrame and HF Dataset returned by
    :func:`load_plantvillage`. The metadata DataFrame can be filtered
    first (for example, by ``split`` or ``host``) — its original index
    is preserved through filtering, which is what ``__getitem__`` uses
    to look up the image in the HF Dataset.

    Each ``__getitem__`` call reads the image from the HF Dataset,
    converts it to RGB, applies an optional transform, and returns an
    ``(image, class_idx)`` tuple.

    Parameters
    ----------
    metadata : pandas.DataFrame
        Returned (or filtered) from :func:`load_plantvillage`. Must
        contain at least a ``class_idx`` (int) column. The DataFrame's
        index is used as the positional lookup into ``hf_dataset``, so
        do not call ``reset_index()`` after filtering.
    hf_dataset : datasets.Dataset
        The image-bearing Dataset returned by :func:`load_plantvillage`.
        Must contain an ``"image"`` column whose elements are PIL Images.
    transform : callable, optional
        torchvision-style transform applied to the loaded PIL Image.
        Default ``None`` returns the (RGB-converted) PIL Image as-is.
        For a ResNet50 baseline, pass the standard ImageNet
        preprocessing pipeline.

    Notes
    -----
    Indexing uses ``.iloc`` (positional) on ``metadata`` to retrieve the
    row, then ``row.name`` (the DataFrame index value) to look up the
    image in ``hf_dataset``. This is why filtered DataFrames with
    non-contiguous indices — for example, the result of
    ``df[df["split"] == "train"]`` — work without
    ``reset_index()``.

    Examples
    --------
    >>> df, ds = iri.load_plantvillage(variant="tiny")
    >>> train_df = df[df.split == "train"]
    >>> train_set = PlantVillageDataset(train_df, ds)
    >>> image, label = train_set[0]
    """

    def __init__(self, metadata, hf_dataset, transform=None):
        self.metadata = metadata
        self.hf_dataset = hf_dataset
        self.transform = transform

    def __len__(self):
        return len(self.metadata)

    def __getitem__(self, idx):
        row = self.metadata.iloc[idx]
        image = self.hf_dataset[int(row.name)]["image"].convert("RGB")
        if self.transform is not None:
            image = self.transform(image)
        return image, int(row["class_idx"])


class PlantDocDataset(Dataset):
    """PyTorch Dataset wrapping a PlantDoc metadata slice and HF Dataset.

    Parameters
    ----------
    metadata_df : pandas.DataFrame
        Metadata for the slice you want to iterate over. Typically a
        filter of the full metadata DataFrame returned by
        `load_plantdoc()` — for example, `df[df["split"] == "train"]`.
        Pandas index values are preserved through filtering and used to
        look up images in `hf_dataset`, so do NOT call `.reset_index()`
        on the filtered DataFrame before passing it in.
    hf_dataset : datasets.Dataset
        The HF Dataset object also returned by `load_plantdoc()`.
        Contains image bytes and metadata columns; this wrapper reads
        only the image column.
    transform : callable, optional
        Applied to each PIL Image before it's returned. Standard
        torchvision transforms work. If None, a PIL Image is returned
        unchanged (after the .convert("RGB") defensive call).

    Returns from __getitem__
    -----------------------
    (image, class_idx) : (PIL.Image | torch.Tensor, int)
        `image` is the transformed image. `class_idx` is the integer
        class label from the metadata.

    Notes
    -----
    The .convert("RGB") call is essential here: PlantDoc images
    include at least one CMYK image, and silent tensor-conversion
    failure downstream would be hard to debug. PV images are uniformly
    RGB, so the same call there is defensive hygiene; here it is
    structural.
    """

    def __init__(self, metadata_df, hf_dataset, transform=None):
        self.metadata = metadata_df
        self.hf_dataset = hf_dataset
        self.transform = transform

    def __len__(self):
        return len(self.metadata)

    def __getitem__(self, idx):
        row = self.metadata.iloc[idx]
        image = self.hf_dataset[int(row.name)]["image"]
        image = image.convert("RGB")
        if self.transform is not None:
            image = self.transform(image)
        return image, int(row["class_idx"])


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
                "last_update_date": gsm.metadata.get("last_update_date", [None])[0],
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