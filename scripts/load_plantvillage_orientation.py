import hashlib
import tarfile
import urllib.request
from pathlib import Path
import pandas as pd

# Pinned release artifact. The data version tag is separate from the library
# version on purpose — tarball updates shouldn't force library releases,
# and library patches shouldn't invalidate cached tarballs.
_PV_ORIENTATION_URL = (
    "https://github.com/geraldmc/irilab2026/releases/download/"
    "data-v0.1.0/plantvillage_orientation.tar.gz"
)
_PV_ORIENTATION_SHA256 = "TODO_FILL_IN_AFTER_BUILD"


def _get_cache_dir():
    """Resolve the irilab2026 cache directory.

    On Colab with Drive mounted, uses My Drive/irilab2026_cache/.
    Otherwise falls back to ~/.cache/irilab2026/.
    """
    drive_root = Path("/content/drive/My Drive")
    if drive_root.exists():
        cache = drive_root / "irilab2026_cache"
    else:
        cache = Path.home() / ".cache" / "irilab2026"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


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
    deterministic sample of ~5 images per class (~190 images, ~6-10 MB)
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
    cache = _get_cache_dir()
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