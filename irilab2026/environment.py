"""
Environment setup: Colab detection, Google Drive mounting, runtime checks,
and cache-path resolution.

The single public function exposed by this module is `setup()`, which is the
first thing every Virtual Lab notebook calls. The helpers it relies on are
also available for direct use in the orientation notebook, which walks
through them individually before introducing the wrapped form.
"""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def setup(gpu_required: bool = False, mount_drive: bool = True) -> None:
    """
    Prepare the environment for a Virtual Lab notebook.

    This function is the single first-cell call in every notebook. It does
    three things:

    1. Detects whether the notebook is running in Google Colab.
    2. If running in Colab and ``mount_drive`` is True, mounts Google Drive
       so the cache directory persists across sessions.
    3. Checks the runtime against the notebook's declared GPU requirement.
       Raises ``RuntimeError`` if the notebook needs a GPU and none is
       available.

    Parameters
    ----------
    gpu_required : bool, default False
        If True, require a GPU runtime and raise ``RuntimeError`` if none is
        detected. If False, run on whatever runtime is available; if a GPU is
        present, the summary line will note it but execution continues.
    mount_drive : bool, default True
        If True (and running in Colab), mount Google Drive at
        ``/content/drive``. Has no effect outside Colab.

    Returns
    -------
    None
        Prints a one-line summary of what was done.

    Raises
    ------
    RuntimeError
        If ``gpu_required=True`` and no GPU is available.
    """
    in_colab = is_colab()
    drive_mounted = False
    if in_colab and mount_drive:
        drive_mounted = mount_google_drive()

    gpu_available = has_gpu()
    if gpu_required and not gpu_available:
        raise RuntimeError(
            "This notebook requires a GPU runtime, but none is available. "
            "In Colab: Runtime → Change runtime type → Hardware accelerator → GPU."
        )

    _print_summary(
        in_colab=in_colab,
        drive_mounted=drive_mounted,
        gpu_available=gpu_available,
        gpu_required=gpu_required,
    )


def seed_all(seed: int = 42) -> None:
    """Seed Python, NumPy, and PyTorch (CPU + CUDA) for reproducibility.

    Also flips cuDNN into deterministic mode and disables the
    benchmark autotuner. Together these make training runs
    reproducible across re-executions of the same notebook on the
    same hardware.

    Idempotent: calling it twice with the same seed is the same as
    calling it once.

    Parameters
    ----------
    seed : int, default 42
        The seed value to use for every RNG.

    Notes
    -----
    PYTHONHASHSEED is deliberately not set here. By the time this
    function runs, Python's startup hashing has already happened —
    setting the env var at this point would have no effect. To make
    PYTHONHASHSEED reproducible you'd need to set it before the
    Python process starts, which is not in this function's scope.
    """
    import random
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
# ---------------------------------------------------------------------------
# Helpers — exposed for the orientation notebook
# ---------------------------------------------------------------------------


def is_colab() -> bool:
    """
    Return True if the current Python session is running in Google Colab.

    Detection is by import: ``google.colab`` is a Colab-only package, so
    its presence is a reliable signal.
    """
    try:
        import google.colab  # noqa: F401
        return True
    except ImportError:
        return False


def mount_google_drive(mount_point: str = "/content/drive") -> bool:
    """
    Mount Google Drive at ``mount_point``.

    Only meaningful in Colab. Outside Colab, returns False without doing
    anything. Inside Colab, the first call per session prompts the user to
    authorize Drive access; subsequent calls return immediately.
    """
    if not is_colab():
        return False
    from google.colab import drive  # type: ignore[import-not-found]
    drive.mount(mount_point)
    return True


def has_gpu() -> bool:
    """
    Return True if a CUDA GPU is available to PyTorch in the current session.

    This is the operationally relevant check: "can I actually use a GPU
    here." A machine with a GPU but a CPU-only PyTorch build will return
    False, which is correct — the GPU is unreachable from this Python
    session.

    Returns False (without raising) if PyTorch is not installed.
    """
    try:
        import torch
    except ImportError:
        return False
    return bool(torch.cuda.is_available())


def _colab_drive_root() -> Path | None:
    """Return the mounted Google Drive root in Colab, or None if unavailable.

    Colab mounts Drive at ``/content/drive/MyDrive`` (the canonical path).
    Older mounts also exposed ``/content/drive/My Drive`` (with a space) as a
    symlink; we accept that spelling only if the canonical one is absent.
    Returns None outside Colab or when Drive is not mounted, which lets callers
    fall back to ephemeral storage instead of silently creating a stray
    ``/content/drive/MyDrive`` directory on an unmounted runtime.
    """
    if not is_colab():
        return None
    canonical = Path("/content/drive/MyDrive")
    if canonical.exists():
        return canonical
    legacy = Path("/content/drive/My Drive")
    if legacy.exists():
        return legacy
    return None


def cache_dir() -> Path:
    """
    Return the directory where datasets should be cached.

    In Colab with Drive mounted: ``/content/drive/MyDrive/irilab2026_cache/``.
    In Colab without Drive: ``/content/irilab2026_cache/`` (lost on session
    reset; only used as a fallback).
    Outside Colab: ``~/.irilab2026_cache/``.

    The directory is created if it doesn't exist.
    """
    drive_root = _colab_drive_root()
    if drive_root is not None:
        path = drive_root / "irilab2026_cache"
    elif is_colab():
        path = Path("/content/irilab2026_cache")
    else:
        path = Path.home() / ".irilab2026_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path

def output_dir(question_slug: str) -> Path:
    """Return the output directory for a given question, creating it if missing.

    The path is environment-dependent:
        Colab with Drive mounted: /content/drive/MyDrive/irilab2026_outputs/<question_slug>/
        Colab without Drive: /content/irilab2026_outputs/<question_slug>/ (ephemeral)
        Local: ~/.irilab2026_outputs/<question_slug>/

    Use this to read or write per-question artifacts produced by one notebook
    and consumed by another. For example:

        de_path = output_dir("r1_q1") / "de_results.parquet"
        de_results.to_parquet(de_path)

    Parameters
    ----------
    question_slug : str
        Identifier for the question, e.g. "r1_q1", "r2_q3".

    Returns
    -------
    Path
        The per-question output directory. The directory is created if it
        does not already exist.
    """
    drive_root = _colab_drive_root()
    if drive_root is not None:
        root = drive_root / "irilab2026_outputs"
    elif is_colab():
        root = Path("/content/irilab2026_outputs")
    else:
        root = Path.home() / ".irilab2026_outputs"
    path = root / question_slug
    path.mkdir(parents=True, exist_ok=True)
    return path

# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _print_summary(
    *,
    in_colab: bool,
    drive_mounted: bool,
    gpu_available: bool,
    gpu_required: bool,
) -> None:
    """Print a one-line summary of the setup state."""
    parts = []
    parts.append("Colab" if in_colab else "local")
    if in_colab:
        parts.append("Drive mounted" if drive_mounted else "Drive not mounted")
    if gpu_required:
        parts.append("GPU OK" if gpu_available else "GPU MISSING")
    else:
        parts.append("GPU available" if gpu_available else "CPU only")
    print("[irilab2026] " + " | ".join(parts))
