"""
Smoke tests for atgenexpress_metadata.

Network-free. Tests the title-parsing logic against hardcoded
representative strings, and tests _validate_chip_counts against a
hand-built DataFrame. Importing private symbols is intentional —
the public function requires GEO, and tests must stay network-free.
"""
import pytest
import pandas as pd


def test_extract_tissue_shoot():
    from irilab2026.data import _extract_tissue
    assert _extract_tissue("AtGen_6-0011_Control-Shoots-0h_Rep1") == "shoot"


def test_extract_tissue_root():
    from irilab2026.data import _extract_tissue
    assert _extract_tissue("AtGen_6-0712_Cold-Roots-1h_Rep2") == "root"


def test_extract_tissue_unparseable():
    from irilab2026.data import _extract_tissue
    assert _extract_tissue("some random title") is None


def test_extract_time_integer_hours():
    from irilab2026.data import _extract_time
    assert _extract_time("AtGen_6-0011_Control-Shoots-0h_Rep1") == 0.0
    assert _extract_time("AtGen_6-9999_Heat-Shoots-12h_Rep1") == 12.0


def test_extract_time_fractional_hours():
    """The underscore-after-unit case that motivated the explicit lookahead."""
    from irilab2026.data import _extract_time
    assert _extract_time("AtGen_6-9999_Drought-Roots-0.25h_Rep2") == 0.25


def test_extract_time_minutes_converted_to_hours():
    from irilab2026.data import _extract_time
    assert _extract_time("some-title-30min_Rep1") == 0.5


def test_extract_rep():
    from irilab2026.data import _extract_rep
    assert _extract_rep("AtGen_6-0011_Control-Shoots-0h_Rep1") == 1
    assert _extract_rep("AtGen_6-0712_Cold-Roots-1h_Rep2") == 2


def test_validate_chip_counts_passes_on_correct_counts():
    from irilab2026.data import _validate_chip_counts, _EXPECTED_CHIP_COUNTS

    rows = [{"stress": "cold"} for _ in range(_EXPECTED_CHIP_COUNTS["cold"])]
    df = pd.DataFrame(rows)
    _validate_chip_counts(df, requested=["cold"])  # should not raise


def test_validate_chip_counts_raises_on_mismatch():
    from irilab2026.data import _validate_chip_counts

    rows = [{"stress": "cold"} for _ in range(5)]
    df = pd.DataFrame(rows)
    with pytest.raises(RuntimeError, match="cold: expected 24, got 5"):
        _validate_chip_counts(df, requested=["cold"])

def test_parquet_roundtrip_is_available(tmp_path):
    """
    The project's data loaders cache via pandas parquet I/O. Pandas
    doesn't bundle a parquet engine, so a missing pyarrow (or
    fastparquet) dependency would surface as an ImportError on first
    cache write in any environment that doesn't already have one
    installed — Colab masks the issue, fresh venvs do not.
    """
    import pandas as pd

    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    cache_file = tmp_path / "smoke.parquet"
    df.to_parquet(cache_file)
    roundtripped = pd.read_parquet(cache_file)
    pd.testing.assert_frame_equal(df, roundtripped)