"""Tests for irilab2026.evaluation.

`build_idx_to_cat` is pure DataFrame/dict logic and is tested fully without a
GPU or network. `evaluate_in_categories` runs a model forward pass on real
data and needs both, so its end-to-end test is marked `@pytest.mark.slow`.
"""

import inspect

import pandas as pd
import pytest

import irilab2026


# ---------------------------------------------------------------------------
# exports and signatures (network-free)
# ---------------------------------------------------------------------------


def test_evaluation_top_level_exports():
    """Both helpers are exposed at the top level of the package."""
    for name in ("build_idx_to_cat", "evaluate_in_categories"):
        assert hasattr(irilab2026, name), (
            f"{name} is not exported from irilab2026. "
            "Check irilab2026/__init__.py."
        )


def test_evaluate_in_categories_signature_keyword_only():
    """num_classes, the two index maps, categories, and batch_size are
    keyword-only — everything after the eval inputs comes after the `*`."""
    sig = inspect.signature(irilab2026.evaluate_in_categories)
    keyword_only = [
        name for name, p in sig.parameters.items()
        if p.kind == inspect.Parameter.KEYWORD_ONLY
    ]
    for name in ("num_classes", "pred_idx_to_cat", "true_idx_to_cat",
                 "categories", "batch_size"):
        assert name in keyword_only, (
            f"{name} should be keyword-only. Check the * separator in "
            "evaluate_in_categories's signature."
        )


# ---------------------------------------------------------------------------
# build_idx_to_cat (network-free)
# ---------------------------------------------------------------------------


def test_build_idx_to_cat_maps_indices_through_labels():
    """class_idx -> class_label -> category, deduplicated across rows."""
    meta = pd.DataFrame({
        "class_idx":   [0, 0, 1, 2],
        "class_label": ["Apple___healthy", "Apple___healthy",
                        "Apple___Apple_scab", "Tomato___Bacterial_spot"],
    })
    class_to_cat = {
        "Apple___healthy": "healthy",
        "Apple___Apple_scab": "fungal",
        "Tomato___Bacterial_spot": "bacterial",
    }
    result = irilab2026.build_idx_to_cat(meta, class_to_cat, "test")
    assert result == {0: "healthy", 1: "fungal", 2: "bacterial"}


def test_build_idx_to_cat_fails_loud_on_unmapped_class():
    """A class present in the data but absent from the map must raise,
    naming the missing class rather than silently dropping it."""
    meta = pd.DataFrame({
        "class_idx":   [0, 1],
        "class_label": ["Apple___healthy", "Grape___Black_rot"],
    })
    class_to_cat = {"Apple___healthy": "healthy"}  # Grape___Black_rot missing
    with pytest.raises(AssertionError, match="Grape___Black_rot"):
        irilab2026.build_idx_to_cat(meta, class_to_cat, "test")


# ---------------------------------------------------------------------------
# evaluate_in_categories (needs GPU + data download)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_evaluate_in_categories_returns_expected_shape():
    """End-to-end on the tiny PV variant: train one quick epoch, score the
    test split in category space, and check the return contract."""
    metadata, hf_dataset = irilab2026.load_plantvillage(variant="tiny")
    num_classes = metadata["class_idx"].nunique()

    state_dict, _ = irilab2026.train_baseline(
        metadata, hf_dataset,
        dataset_class=irilab2026.PlantVillageDataset,
        num_classes=num_classes,
        epoch_cap=1,
        verbose=False,
    )

    # A trivial category map: send every class to the same category, so the
    # test exercises the scoring path without depending on a committed map.
    categories = ["all"]
    class_to_cat = {label: "all" for label in metadata["class_label"].unique()}
    idx_to_cat = irilab2026.build_idx_to_cat(metadata, class_to_cat, "PV")

    test_meta = metadata[metadata["split"] == "test"]
    res = irilab2026.evaluate_in_categories(
        state_dict, test_meta, hf_dataset, irilab2026.PlantVillageDataset,
        num_classes=num_classes,
        pred_idx_to_cat=idx_to_cat,
        true_idx_to_cat=idx_to_cat,
        categories=categories,
    )

    assert set(res) == {"overall", "per_category", "n"}
    assert 0.0 <= res["overall"] <= 1.0
    assert set(res["per_category"]) == set(categories)
    # Every image's true category is "all", so accuracy there equals overall.
    assert res["per_category"]["all"] == pytest.approx(res["overall"])
    assert res["n"] == len(test_meta)
