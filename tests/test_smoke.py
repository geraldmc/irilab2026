"""
Smoke tests.

These are deliberately minimal: they confirm that imports work and that the
package's own constants are internally consistent. Tests that hit the
network (i.e., actual GEO downloads) live elsewhere; we don't want CI to
depend on GEO's uptime.
"""

from __future__ import annotations


def test_top_level_imports():
    """The two public functions are importable from the package root."""
    from irilab2026 import setup, load_atgenexpress  # noqa: F401


def test_version_is_set():
    """__version__ is exported and looks like a version string."""
    from irilab2026 import __version__
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_stress_mapping_round_trips():
    """STRESS_TO_GSE is the inverse of GSE_TO_STRESS."""
    from irilab2026.data import GSE_TO_STRESS, STRESS_TO_GSE
    for gse, stress in GSE_TO_STRESS.items():
        assert STRESS_TO_GSE[stress] == gse
    assert len(GSE_TO_STRESS) == len(STRESS_TO_GSE) == 9


def test_all_stresses_covers_mapping():
    """ALL_STRESSES contains every stress name in the GSE mapping."""
    from irilab2026.data import ALL_STRESSES, GSE_TO_STRESS
    assert set(ALL_STRESSES) == set(GSE_TO_STRESS.values())


def test_unknown_stress_raises():
    """load_atgenexpress raises a clear error on an unknown stress name."""
    import pytest
    from irilab2026 import load_atgenexpress

    with pytest.raises(ValueError, match="Unknown stress name"):
        load_atgenexpress(stresses=["not_a_real_stress"])


def test_setup_runs_outside_colab():
    """setup() runs without error in a local environment when no GPU is required."""
    from irilab2026 import setup
    setup(gpu_required=False, mount_drive=False)


def test_setup_raises_when_gpu_required_and_missing():
    """setup() raises RuntimeError if a GPU is required but unavailable."""
    import pytest
    from irilab2026 import setup
    from irilab2026.environment import has_gpu

    if has_gpu():
        pytest.skip("This test only runs on CPU-only environments.")

    with pytest.raises(RuntimeError, match="requires a GPU"):
        setup(gpu_required=True, mount_drive=False)

def test_output_dir_creates_local_path(tmp_path, monkeypatch):
    """output_dir() returns a usable per-question path when not in Colab."""
    # Point ~/.irilab2026_outputs/ at a temp directory for this test.
    monkeypatch.setenv("HOME", str(tmp_path))

    from irilab2026 import output_dir

    path = output_dir("r1_q1")

    assert path.exists()
    assert path.is_dir()
    assert path.name == "r1_q1"
    assert path.parent.name == ".irilab2026_outputs"
