"""Smoke tests for dataset loaders.

These tests exercise the real download path against the pinned GitHub
release. They require network access and will fetch the tarball into the
local cache on first run. Subsequent runs are fast (cache hit, no download).

Run from the repo root:
    pytest tests/test_loaders.py -v
"""

import irilab2026


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