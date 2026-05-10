"""
irilab2026 — shared infrastructure for the iResearch Institute 2026
Virtual Lab notebooks.

Public API:
    setup              — prepare the environment for a notebook
    load_atgenexpress  — load the AtGenExpress abiotic stress dataset
"""

from .environment import (
    setup,
    is_colab,
    mount_google_drive,
    has_gpu,
    cache_dir,
)

from .data import (
    load_atgenexpress,
    load_plantvillage_orientation,
)

__all__ = [
    "setup",
    "is_colab",
    "mount_google_drive",
    "has_gpu",
    "cache_dir",
    "load_atgenexpress",
    "load_plantvillage_orientation",
]