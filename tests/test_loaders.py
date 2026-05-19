"""Smoke tests for dataset loaders.

These tests exercise the real download paths — orientation via the
pinned GitHub release, PlantVillage via Hugging Face Hub. They require
network access and will populate the local cache on first run.
Subsequent runs are fast (cache hits, no download).

Most PV tests use the `tiny` variant (~1,900 images, ~60 MB) to keep CI
runtime low. One test exercises the full variant (~855 MB) to verify
the default code path works at scale; it is marked `@pytest.mark.slow`
so CI can opt out via `pytest -m "not slow"`.

Run from the repo root:
    pytest tests/test_loaders.py -v
    pytest tests/test_loaders.py -v -m "not slow"   # skip the full-variant test
"""

import irilab2026
import pandas as pd
import pytest
from PIL import Image


# ---------------------------------------------------------------------------
# load_plantvillage_orientation (GitHub release flow — unchanged)
# ---------------------------------------------------------------------------


def test_load_plantvillage_orientation_top_level_export():
    """The loader is exposed at the top level of the package."""
    assert hasattr(irilab2026, "load_plantvillage_orientation"), (
        "load_plantvillage_orientation is not exported from irilab2026. "
        "Check irilab2026/__init__.py."
    )


def test_load_plantvillage_orientation_returns_expected_shape():
    """End-to-end: download, verify hash, extract, parse, return."""
    data = irilab2026.load_plantvillage_orientation()

    assert set(data.keys()) == {"manifest", "sample_paths", "sample_dir"}

    assert data["manifest"].shape == (38, 5), (
        f"Expected manifest shape (38, 5), got {data['manifest'].shape}"
    )

    expected_cols = {"class", "host", "disease", "is_healthy", "n_total"}
    assert set(data["manifest"].columns) == expected_cols

    assert data["sample_paths"].shape == (190, 4), (
        f"Expected sample_paths shape (190, 4), got {data['sample_paths'].shape}"
    )

    assert data["sample_dir"].exists()
    assert any(data["sample_dir"].iterdir())


def test_load_plantvillage_orientation_manifest_content():
    """The manifest's full-dataset counts match Mohanty 2016's published total."""
    data = irilab2026.load_plantvillage_orientation()

    total = data["manifest"]["n_total"].sum()
    assert 54_000 <= total <= 55_000, (
        f"Manifest n_total sum is {total}, outside the expected ~54,303 range. "
        "The upstream PlantVillage repo may have changed."
    )

    n_healthy = data["manifest"]["is_healthy"].sum()
    assert n_healthy >= 8, f"Expected at least 8 healthy classes, got {n_healthy}"


# ---------------------------------------------------------------------------
# load_plantvillage and PlantVillageDataset (HF Hub flow)
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


def test_load_plantvillage_unknown_variant_raises():
    """Bad variant names raise ValueError before any network call."""
    with pytest.raises(ValueError, match="Unknown variant"):
        irilab2026.load_plantvillage(variant="full_color")


def test_load_plantvillage_returns_expected_shape():
    """End-to-end (tiny variant): fetch from HF, return (metadata_df, hf_dataset).

    Uses the tiny variant to keep CI fast (~60 MB download on first run).
    The full-variant equivalent is test_load_plantvillage_default_variant_is_full.
    """
    result = irilab2026.load_plantvillage(variant="tiny")

    # Returns a 2-tuple
    assert isinstance(result, tuple) and len(result) == 2, (
        f"Expected a 2-tuple return, got {type(result).__name__} of length "
        f"{len(result) if hasattr(result, '__len__') else 'n/a'}."
    )
    metadata, hf_dataset = result

    # Metadata is a DataFrame with the seven non-image columns
    assert isinstance(metadata, pd.DataFrame)

    expected_cols = {
        "class_label", "class_idx",
        "host", "disease", "split",
        "leaf_id", "leaf_grouped",
    }
    assert set(metadata.columns) == expected_cols, (
        f"Column set mismatch. Got {set(metadata.columns)}, "
        f"expected {expected_cols}."
    )

    # Tiny variant is ~50 images per class × 38 classes ≈ 1,900 rows
    assert 1_800 <= len(metadata) <= 2_000, (
        f"Expected ~1,900 rows for tiny variant, got {len(metadata)}. "
        f"The HF dataset may have been re-built with a different subsample size."
    )

    # HF Dataset length matches metadata
    assert len(hf_dataset) == len(metadata), (
        f"hf_dataset length {len(hf_dataset)} does not match "
        f"metadata length {len(metadata)}."
    )


def test_load_plantvillage_content():
    """Spot-check column dtypes, class count, split values, and the HF Dataset's
    image column on the tiny variant."""
    metadata, hf_dataset = irilab2026.load_plantvillage(variant="tiny")

    # class_idx is integer-typed
    assert pd.api.types.is_integer_dtype(metadata["class_idx"]), (
        f"class_idx should be integer dtype, got {metadata['class_idx'].dtype}."
    )

    # leaf_grouped is boolean-typed
    assert pd.api.types.is_bool_dtype(metadata["leaf_grouped"]), (
        f"leaf_grouped should be bool dtype, got {metadata['leaf_grouped'].dtype}."
    )

    # 38 distinct classes per Mohanty 2016
    assert metadata["class_label"].nunique() == 38, (
        f"Expected 38 classes, got {metadata['class_label'].nunique()}."
    )

    # split takes only the two expected values
    assert set(metadata["split"].unique()) == {"train", "test"}, (
        f"split column has unexpected values: {set(metadata['split'].unique())}."
    )

    # The HF Dataset's image column returns PIL Images (not a bytes dict).
    # This is the assumption verified on Colab during the loader rewrite; the
    # test catches a regression if the build script ever changes how images
    # are pushed.
    first_image = hf_dataset[0]["image"]
    assert isinstance(first_image, Image.Image), (
        f"Expected hf_dataset[0]['image'] to be a PIL Image, "
        f"got {type(first_image)}."
    )


def test_plantvillage_dataset_smoke():
    """Instantiate the Dataset from a small slice and check that
    __len__ and __getitem__ behave as expected."""
    metadata, hf_dataset = irilab2026.load_plantvillage(variant="tiny")

    # Small slice to keep the test fast
    sample = metadata.head(3)
    ds = irilab2026.PlantVillageDataset(sample, hf_dataset)

    assert len(ds) == 3

    image, label = ds[0]
    # transform=None means PIL Image comes through unchanged
    # (post-.convert("RGB") in __getitem__)
    assert isinstance(image, Image.Image), (
        f"Expected PIL Image, got {type(image)}."
    )
    assert image.mode == "RGB", (
        f"Expected RGB mode after .convert('RGB'), got {image.mode}."
    )
    assert isinstance(label, int), (
        f"Expected plain Python int label, got {type(label)}."
    )


def test_plantvillage_dataset_handles_filtered_dataframe():
    """Dataset uses .iloc on metadata and int(row.name) on the HF Dataset, so
    a filtered DataFrame with non-contiguous pandas indices should still work
    without needing reset_index() upstream."""
    metadata, hf_dataset = irilab2026.load_plantvillage(variant="tiny")

    # Force a non-contiguous index regardless of how the metadata happens to
    # be sorted. .iloc[1::2] preserves the original index for every other
    # row, so filtered.index will be [1, 3, 5, ...] — deterministically
    # non-contiguous.
    filtered = metadata.iloc[1::2].head(3)
    assert list(filtered.index) == [1, 3, 5], (
        f"Test setup expected indices [1, 3, 5], got {list(filtered.index)}. "
        "If this fails, the test isn't actually exercising the "
        "non-contiguous-index path."
    )

    ds = irilab2026.PlantVillageDataset(filtered, hf_dataset)
    image, label = ds[0]
    assert isinstance(image, Image.Image)
    assert isinstance(label, int)


@pytest.mark.slow
def test_load_plantvillage_default_variant_is_full():
    """End-to-end (full variant): verify the default code path works at scale.

    This is the only PV test that exercises the full variant (~855 MB
    download on first run). Marked `slow` so CI can skip it via
    `pytest -m "not slow"`. All other PV tests use the tiny variant.
    """
    metadata, hf_dataset = irilab2026.load_plantvillage()  # variant default = "full"

    # Mohanty 2016 reports ~54,303 images; current build has 54,304.
    assert 54_000 <= len(metadata) <= 55_000, (
        f"Expected ~54,000 rows for full variant, got {len(metadata)}."
    )
    assert len(hf_dataset) == len(metadata)
    assert metadata["class_label"].nunique() == 38


def test_load_plantvillage_force_download():
    """force_download=True doesn't crash. Exercises the parameter wiring;
    the actual re-fetch behavior is HF's responsibility, not ours.

    Uses the tiny variant so the forced re-download is ~60 MB rather
    than ~855 MB.
    """
    metadata, _ = irilab2026.load_plantvillage(
        variant="tiny", force_download=True
    )
    assert isinstance(metadata, pd.DataFrame)
    assert len(metadata) > 0

# ---------------------------------------------------------------------------
# load_plantdoc and PlantDocDataset (HF Hub flow)
# ---------------------------------------------------------------------------


def test_load_plantdoc_top_level_export():
    """The loader is exposed at the top level of the package."""
    assert hasattr(irilab2026, "load_plantdoc"), (
        "load_plantdoc is not exported from irilab2026. "
        "Check irilab2026/__init__.py."
    )


def test_plantdoc_dataset_top_level_export():
    """The Dataset class is exposed at the top level of the package."""
    assert hasattr(irilab2026, "PlantDocDataset"), (
        "PlantDocDataset is not exported from irilab2026. "
        "Check irilab2026/__init__.py."
    )


def test_load_plantdoc_unknown_variant_raises():
    """Bad variant names raise ValueError before any network call."""
    with pytest.raises(ValueError, match="Unknown variant"):
        irilab2026.load_plantdoc(variant="cropped")


def test_load_plantdoc_returns_expected_shape():
    """End-to-end (tiny variant): fetch from HF, return (metadata_df, hf_dataset).

    Uses the tiny variant to keep CI fast (~50 MB download on first run).
    The full-variant equivalent is test_load_plantdoc_default_variant_is_full.
    """
    result = irilab2026.load_plantdoc(variant="tiny")

    # Returns a 2-tuple
    assert isinstance(result, tuple) and len(result) == 2
    metadata, hf_dataset = result

    # Metadata is a DataFrame with the seven non-image columns
    assert isinstance(metadata, pd.DataFrame)

    expected_cols = {
        "class_label", "class_idx",
        "host", "disease", "is_healthy",
        "split", "filename",
    }
    assert set(metadata.columns) == expected_cols, (
        f"Column set mismatch. Got {set(metadata.columns)}, "
        f"expected {expected_cols}."
    )

    # Tiny variant is min(3, available) per class per split.
    # 27 non-orphan classes × 3 × 2 splits = 162, + 2 orphan train = 164
    assert 150 <= len(metadata) <= 180, (
        f"Expected ~164 rows for tiny variant, got {len(metadata)}. "
        f"The HF dataset may have been re-built with a different subsample size."
    )

    # HF Dataset length matches metadata
    assert len(hf_dataset) == len(metadata)


def test_load_plantdoc_content():
    """Spot-check column dtypes, class count, split values, and the HF Dataset's
    image column on the tiny variant."""
    metadata, hf_dataset = irilab2026.load_plantdoc(variant="tiny")

    # class_idx is integer-typed
    assert pd.api.types.is_integer_dtype(metadata["class_idx"]), (
        f"class_idx should be integer dtype, got {metadata['class_idx'].dtype}."
    )

    # is_healthy is boolean-typed
    assert pd.api.types.is_bool_dtype(metadata["is_healthy"]), (
        f"is_healthy should be bool dtype, got {metadata['is_healthy'].dtype}."
    )

    # 28 distinct classes (preserves the orphan)
    assert metadata["class_label"].nunique() == 28, (
        f"Expected 28 classes, got {metadata['class_label'].nunique()}."
    )

    # split takes only the two expected values
    assert set(metadata["split"].unique()) == {"train", "test"}

    # The HF Dataset's image column returns PIL Images (not bytes).
    first_image = hf_dataset[0]["image"]
    assert isinstance(first_image, Image.Image), (
        f"Expected hf_dataset[0]['image'] to be a PIL Image, "
        f"got {type(first_image)}."
    )


def test_plantdoc_dataset_smoke():
    """Instantiate the Dataset from a small slice and check that
    __len__ and __getitem__ behave as expected. Verifies the
    .convert("RGB") call fires correctly on heterogeneous PD images."""
    metadata, hf_dataset = irilab2026.load_plantdoc(variant="tiny")

    sample = metadata.head(3)
    ds = irilab2026.PlantDocDataset(sample, hf_dataset)

    assert len(ds) == 3

    image, label = ds[0]
    assert isinstance(image, Image.Image)
    # The defensive .convert("RGB") guarantees this even though some
    # upstream PD images are CMYK.
    assert image.mode == "RGB", (
        f"Expected RGB mode after .convert('RGB'), got {image.mode}. "
        f"This catches a regression where the defensive convert was removed."
    )
    assert isinstance(label, int)


@pytest.mark.slow
def test_load_plantdoc_default_variant_is_full():
    """End-to-end (full variant): verify the default code path works at scale.

    Marked `slow` so CI can skip it via `pytest -m "not slow"`.
    All other PD tests use the tiny variant.
    """
    metadata, hf_dataset = irilab2026.load_plantdoc()  # variant default = "full"

    # 2,578 images, 28 classes, 2,342 train / 236 test
    assert 2_500 <= len(metadata) <= 2_700
    assert len(hf_dataset) == len(metadata)
    assert metadata["class_label"].nunique() == 28