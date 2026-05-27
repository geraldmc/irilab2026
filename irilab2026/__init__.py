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
    output_dir,
    seed_all,

)

from .vision import (
    build_baseline_model,
    imagenet_train_transform,
    imagenet_eval_transform,
)

from .data import (
    load_atgenexpress,
    atgenexpress_metadata,
    probe_to_agi,
    load_plantvillage,
    PlantVillageDataset,
    load_plantdoc,
    PlantDocDataset,
    load_plantvillage_orientation,
    tair_gaf_path,
)

from .training import train_baseline           # <-- new

__version__ = "0.3.0"

__all__ = [
    "setup",
    "is_colab",
    "mount_google_drive",
    "has_gpu",
    "output_dir",
    "seed_all",
    "load_atgenexpress",
    "atgenexpress_metadata",
    "probe_to_agi",
    "load_plantvillage",
    "PlantVillageDataset",
    "load_plantdoc",
    "PlantDocDataset",
    "load_plantvillage_orientation",
    "tair_gaf_path",
    "build_baseline_model",
    "imagenet_train_transform",
    "imagenet_eval_transform",
    "train_baseline",                          # <-- new
]
