"""
irilab2026 — shared infrastructure for the iResearch Institute 2026
Virtual Lab notebooks.

Public API (18 symbols, grouped by module):

  environment — setup, is_colab, mount_google_drive, has_gpu,
                cache_dir, output_dir, seed_all
  data        — load_atgenexpress, atgenexpress_metadata, probe_to_agi,
                load_plantvillage, PlantVillageDataset,
                load_plantdoc, PlantDocDataset,
                load_plantvillage_orientation, tair_gaf_path
  vision      — build_baseline_model, imagenet_train_transform,
                imagenet_eval_transform, randaugment_train_transform
  training    — train_baseline
  evaluation  — build_idx_to_cat, evaluate_in_categories

See each module's docstring for details on individual functions.
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
    randaugment_train_transform,
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

from .training import train_baseline

from .evaluation import (
    build_idx_to_cat,
    evaluate_in_categories,
)

__version__ = "0.3.0"

__all__ = [
    "setup",
    "is_colab",
    "mount_google_drive",
    "has_gpu",
    "cache_dir",
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
    "randaugment_train_transform",
    "train_baseline",
    "build_idx_to_cat",
    "evaluate_in_categories",
]
