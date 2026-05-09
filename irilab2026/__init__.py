"""
irilab2026 — shared infrastructure for the iResearch Institute 2026
Virtual Lab notebooks.

Public API:
    setup              — prepare the environment for a notebook
    load_atgenexpress  — load the AtGenExpress abiotic stress dataset
"""

from .environment import setup, is_colab, mount_google_drive, has_gpu
from .data import load_atgenexpress

__version__ = "0.1.0"

__all__ = [
    "setup",
    "is_colab",
    "mount_google_drive",
    "has_gpu",
    "load_atgenexpress",
    "__version__",
]