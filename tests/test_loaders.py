"""Smoke tests for dataset loaders.

These tests exercise the real download path against the pinned GitHub
release. They require network access and will fetch the tarball into the
local cache on first run. Subsequent runs are fast (cache hit, no download).

Run from the repo root:
    pytest tests/test_loaders.py -v
"""

import irilab2026
from pathlib import Path
import pandas as pd
from PIL import Image


def test_load_plantvillage_orientation_top_level_export():
    """The loader is exposed at the top level of the package."""
    assert hasattr(irilab2026, "load_plantvillage_orientation"), (
        "load_plantvillage_orientation is not exported from irilab2026. "
        "Check irilab2026/__init__.py."
    )


def test_load_plantvillage_orientation_returns_expected_shape():
    """End-to-end: download, verify hash, extract, parse, return."""
    data = irilab2026.load_plantvillage_orientation()

    # Three keys, all present
    assert set(data.keys()) == {"manifest", "sample_paths", "sample_dir"}

    # Manifest: 38 rows (PV class count), 5 columns
    assert data["manifest"].shape == (38, 5), (
        f"Expected manifest shape (38, 5), got {data['manifest'].shape}"
    )

    # Manifest carries the expected columns
    expected_cols = {"class", "host", "disease", "is_healthy", "n_total"}
    assert set(data["manifest"].columns) == expected_cols

    # Sample paths: 38 classes × 5 images = 190 rows, 4 columns
    assert data["sample_paths"].shape == (190, 4), (
        f"Expected sample_paths shape (190, 4), got {data['sample_paths'].shape}"
    )

    # The sample directory exists and is non-empty
    assert data["sample_dir"].exists()
    assert any(data["sample_dir"].iterdir())


def test_load_plantvillage_orientation_manifest_content():
    """The manifest's full-dataset counts match Mohanty 2016's published total."""
    data = irilab2026.load_plantvillage_orientation()

    # Mohanty 2016 reports ~54,303 images in PV; the manifest's n_total sum
    # should match the actual upstream count we sampled from.
    total = data["manifest"]["n_total"].sum()
    assert 54_000 <= total <= 55_000, (
        f"Manifest n_total sum is {total}, outside the expected ~54,303 range. "
        "The upstream PlantVillage repo may have changed."
    )

    # There should be at least a few healthy classes
    n_healthy = data["manifest"]["is_healthy"].sum()
    assert n_healthy >= 8, f"Expected at least 8 healthy classes, got {n_healthy}"


# ---------------------------------------------------------------------------
# load_plantvillage and PlantVillageDataset
# ---------------------------------------------------------------------------


def test_load_plantvillage_top_level_export():
    """The loader is exposed at the top level of the package."""
    assert hasattr(irilab2026, "load_plantvillage"), (
        "load_plantvillage is not exported from irilab2026. "
        "Check irilab2026/__init__.py."
    )


def test_plantvillage_dataset_top_level_export():
    """The Dataset class is exposed at the top level of the package."""
    assert hasattr(irilab2026, "PlantVillageDataset"), (
        "PlantVillageDataset is not exported from irilab2026. "
        "Check irilab2026/__init__.py."
    )


def test_load_plantvillage_returns_expected_shape():
    """End-to-end: download, verify hash, extract, parse, return a DataFrame
    of the expected shape."""
    df = irilab2026.load_plantvillage()

    assert isinstance(df, pd.DataFrame)

    expected_cols = {
        "image_path", "class_label", "class_idx",
        "host", "disease", "split",
        "leaf_id", "leaf_grouped",
    }
    assert set(df.columns) == expected_cols, (
        f"Column set mismatch. Got {set(df.columns)}, expected {expected_cols}."
    )

    # Mohanty 2016 reports ~54,303 images across 38 classes.
    assert 54_000 <= len(df) <= 55_000, (
        f"Expected ~54,000 rows, got {len(df)}. "
        f"The upstream PlantVillage repo may have changed."
    )


def test_load_plantvillage_content():
    """Spot-check column dtypes, class count, split values, and that
    image_path values resolve to files that actually exist on disk."""
    df = irilab2026.load_plantvillage()

    # class_idx is integer-typed
    assert pd.api.types.is_integer_dtype(df["class_idx"]), (
        f"class_idx should be integer dtype, got {df['class_idx'].dtype}."
    )

    # leaf_grouped is boolean-typed (verified earlier: pandas reads
    # Python True/False from CSV as numpy.bool_, which is bool-typed)
    assert pd.api.types.is_bool_dtype(df["leaf_grouped"]), (
        f"leaf_grouped should be bool dtype, got {df['leaf_grouped'].dtype}."
    )

    # 38 distinct classes per Mohanty 2016
    assert df["class_label"].nunique() == 38, (
        f"Expected 38 classes, got {df['class_label'].nunique()}."
    )

    # split takes only the two expected values
    assert set(df["split"].unique()) == {"train", "test"}, (
        f"split column has unexpected values: {set(df['split'].unique())}."
    )

    # image_path is resolved to absolute paths; the first one should
    # point at a file that actually exists
    first_path = Path(df["image_path"].iloc[0])
    assert first_path.exists(), (
        f"First image_path does not exist on disk: {first_path}. "
        "image_path may not be properly resolved to absolute paths, "
        "or the extracted tarball is missing the referenced file."
    )


def test_plantvillage_dataset_smoke():
    """Instantiate the Dataset from a small slice and check that
    __len__ and __getitem__ behave as expected."""
    df = irilab2026.load_plantvillage()

    # Small slice to keep the test fast
    sample = df.head(3)
    ds = irilab2026.PlantVillageDataset(sample)

    assert len(ds) == 3

    image, label = ds[0]
    # transform=None means PIL Image comes through unchanged
    assert isinstance(image, Image.Image), (
        f"Expected PIL Image, got {type(image)}."
    )
    assert isinstance(label, int), (
        f"Expected plain Python int label, got {type(label)}."
    )


def test_plantvillage_dataset_handles_filtered_dataframe():
    """Dataset uses .iloc (positional), so a filtered DataFrame with
    non-contiguous pandas indices should still work without needing
    reset_index() upstream."""
    df = irilab2026.load_plantvillage()

    # Filtering produces non-contiguous indices, which is the common
    # downstream pattern (train/test, per-host, per-class).
    first_class = df["class_label"].iloc[0]
    filtered = df[df["class_label"] == first_class].head(3)
    ds = irilab2026.PlantVillageDataset(filtered)

    image, label = ds[0]
    assert isinstance(image, Image.Image)
    assert isinstance(label, int)