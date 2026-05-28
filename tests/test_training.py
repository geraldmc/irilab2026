"""Tests for iri.train_baseline."""

import pytest

import irilab2026


def test_train_baseline_top_level_export():
    """The helper is exposed at the top level of the package."""
    assert hasattr(irilab2026, "train_baseline"), (
        "train_baseline is not exported from irilab2026. "
        "Check irilab2026/__init__.py."
    )


def test_train_baseline_signature_keyword_only():
    """num_classes, shuffle_labels, seed, epoch_cap, and verbose are
    keyword-only — calling with positional args past the first three
    should fail."""
    import inspect
    sig = inspect.signature(irilab2026.train_baseline)
    params = sig.parameters

    # First three are positional (or positional-or-keyword); the rest
    # come after a `*`.
    keyword_only = [
        name for name, p in params.items()
        if p.kind == inspect.Parameter.KEYWORD_ONLY
    ]
    for name in ("num_classes", "train_transform", "shuffle_labels",
                    "seed", "epoch_cap", "verbose"):
        assert name in keyword_only, (
            f"{name} should be keyword-only. Check the * separator in "
            f"train_baseline's signature."
        )


@pytest.mark.slow
def test_train_baseline_smoke_tiny_variant():
    """End-to-end smoke test on the tiny PV variant — verifies the helper
    runs, returns the expected shapes, and produces a state_dict that
    loads cleanly into a fresh ResNet-18."""
    import torch

    metadata, hf_dataset = irilab2026.load_plantvillage(variant="tiny")
    state_dict, history = irilab2026.train_baseline(
        metadata, hf_dataset,
        dataset_class=irilab2026.PlantVillageDataset,
        num_classes=38,
        epoch_cap=1,        # one epoch on tiny — completes in ~30 s
        verbose=False,
    )

    # Returned types and shapes.
    assert isinstance(state_dict, dict)
    assert "fc.weight" in state_dict
    assert state_dict["fc.weight"].shape == (38, 512)

    assert isinstance(history, dict)
    assert set(history) >= {
        "train_loss", "val_loss", "val_acc",
        "best_val_epoch", "best_val_acc",
    }
    assert len(history["train_loss"]) == 1
    assert len(history["val_loss"]) == 1
    assert len(history["val_acc"]) == 1

    # Loads into a fresh model without errors.
    fresh_model = irilab2026.build_baseline_model(38, pretrained=False)
    fresh_model.load_state_dict(state_dict)


@pytest.mark.slow
def test_train_baseline_shuffle_changes_state_dict():
    """Same seed, shuffle_labels=True vs False should produce different
    trained weights — confirms the shuffle flag actually shuffles."""
    import torch

    metadata, hf_dataset = irilab2026.load_plantvillage(variant="tiny")

    sd_normal, _ = irilab2026.train_baseline(
        metadata, hf_dataset,
        dataset_class=irilab2026.PlantVillageDataset,
        num_classes=38,
        epoch_cap=1,
        seed=42,
        shuffle_labels=False,
        verbose=False,
    )
    sd_shuffled, _ = irilab2026.train_baseline(
        metadata, hf_dataset,
        dataset_class=irilab2026.PlantVillageDataset,
        num_classes=38,
        epoch_cap=1,
        seed=42,
        shuffle_labels=True,
        verbose=False,
    )

    # At least one parameter tensor should differ between the two runs.
    # (We don't check exact-match-everywhere because the model's weights
    # under shuffled labels are essentially memorizing noise, so per-layer
    # similarity is undefined.)
    any_diff = any(
        not torch.allclose(sd_normal[k], sd_shuffled[k])
        for k in sd_normal
    )
    assert any_diff, (
        "Shuffled and unshuffled training produced identical state_dicts. "
        "The shuffle_labels flag may not be doing anything."
    )


def test_train_baseline_accepts_train_transform_keyword():
    """train_transform is a keyword-only parameter defaulting to None."""
    import inspect
    sig = inspect.signature(irilab2026.train_baseline)
    assert "train_transform" in sig.parameters
    p = sig.parameters["train_transform"]
    assert p.kind == inspect.Parameter.KEYWORD_ONLY
    assert p.default is None


@pytest.mark.slow
def test_train_baseline_runs_with_custom_train_transform():
    """Passing a custom train transform (here the deterministic eval
    transform — the no-augmentation condition) runs end to end and returns the
    expected shapes."""
    metadata, hf_dataset = irilab2026.load_plantvillage(variant="tiny")
    state_dict, history = irilab2026.train_baseline(
        metadata, hf_dataset,
        dataset_class=irilab2026.PlantVillageDataset,
        num_classes=38,
        train_transform=irilab2026.imagenet_eval_transform(),  # no-aug floor
        epoch_cap=1,
        verbose=False,
    )
    assert isinstance(state_dict, dict)
    assert state_dict["fc.weight"].shape == (38, 512)
    assert len(history["train_loss"]) == 1