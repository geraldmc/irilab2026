"""Smoke tests for irilab2026.vision helpers.

These tests use `pretrained=False` for the model factory so they
don't require network access — pretrained weights would otherwise
need to be downloaded from PyTorch's CDN.
"""

import pytest
import torch
import torch.nn as nn
import torchvision.transforms as T
from PIL import Image

import irilab2026


# ---------------------------------------------------------------------------
# build_baseline_model
# ---------------------------------------------------------------------------


def test_build_baseline_model_returns_nn_module():
    model = irilab2026.build_baseline_model(num_classes=38, pretrained=False)
    assert isinstance(model, nn.Module)


def test_build_baseline_model_fc_replaced_to_num_classes():
    """The final fc layer should be Linear(512, num_classes)."""
    model = irilab2026.build_baseline_model(num_classes=38, pretrained=False)
    assert isinstance(model.fc, nn.Linear)
    assert model.fc.in_features == 512
    assert model.fc.out_features == 38


def test_build_baseline_model_handles_different_num_classes():
    """num_classes should drive the output dimension. Test with R2-Q1's 38
    and PlantDoc's 27."""
    for n in (27, 38, 1000):
        model = irilab2026.build_baseline_model(num_classes=n, pretrained=False)
        assert model.fc.out_features == n, (
            f"Expected {n} output features, got {model.fc.out_features}"
        )


def test_build_baseline_model_forward_pass_shape():
    """A (batch, 3, 224, 224) input should produce (batch, num_classes) output."""
    model = irilab2026.build_baseline_model(num_classes=38, pretrained=False)
    model.eval()
    fake_batch = torch.randn(2, 3, 224, 224)
    with torch.no_grad():
        output = model(fake_batch)
    assert output.shape == (2, 38), (
        f"Expected (2, 38), got {tuple(output.shape)}"
    )


def test_build_baseline_model_pretrained_keyword_only():
    """pretrained must be a keyword arg — positional is not allowed.
    This protects against accidental misuse like
    `build_baseline_model(38, False)`."""
    with pytest.raises(TypeError):
        irilab2026.build_baseline_model(38, False)  # positional pretrained


# ---------------------------------------------------------------------------
# imagenet_train_transform
# ---------------------------------------------------------------------------


def test_imagenet_train_transform_returns_compose():
    t = irilab2026.imagenet_train_transform()
    assert isinstance(t, T.Compose)


def test_imagenet_train_transform_has_expected_sequence():
    """The train transform should be exactly:
    RandomResizedCrop → RandomHorizontalFlip → ToTensor → Normalize."""
    t = irilab2026.imagenet_train_transform()
    transform_types = [type(x).__name__ for x in t.transforms]
    assert transform_types == [
        "RandomResizedCrop",
        "RandomHorizontalFlip",
        "ToTensor",
        "Normalize",
    ]


def test_imagenet_train_transform_produces_correct_tensor_shape():
    """Applied to a PIL image of any size, output is (3, 224, 224)."""
    t = irilab2026.imagenet_train_transform()
    img = Image.new("RGB", (300, 400), color="red")
    result = t(img)
    assert isinstance(result, torch.Tensor)
    assert result.shape == (3, 224, 224)


def test_imagenet_train_transform_returns_fresh_compose():
    """Two calls return separate Compose instances. Important so independent
    callers can't accidentally share state."""
    a = irilab2026.imagenet_train_transform()
    b = irilab2026.imagenet_train_transform()
    assert a is not b


# ---------------------------------------------------------------------------
# imagenet_eval_transform
# ---------------------------------------------------------------------------


def test_imagenet_eval_transform_returns_compose():
    t = irilab2026.imagenet_eval_transform()
    assert isinstance(t, T.Compose)


def test_imagenet_eval_transform_has_expected_sequence():
    """The eval transform should be exactly:
    Resize → CenterCrop → ToTensor → Normalize."""
    t = irilab2026.imagenet_eval_transform()
    transform_types = [type(x).__name__ for x in t.transforms]
    assert transform_types == [
        "Resize",
        "CenterCrop",
        "ToTensor",
        "Normalize",
    ]


def test_imagenet_eval_transform_produces_correct_tensor_shape():
    t = irilab2026.imagenet_eval_transform()
    img = Image.new("RGB", (300, 400), color="red")
    result = t(img)
    assert isinstance(result, torch.Tensor)
    assert result.shape == (3, 224, 224)


def test_imagenet_eval_transform_is_deterministic():
    """Two passes over the same image produce identical tensors.
    This is the eval transform's contract — no randomness."""
    t = irilab2026.imagenet_eval_transform()
    img = Image.new("RGB", (300, 400), color="red")
    a = t(img)
    b = t(img)
    assert torch.equal(a, b), "Eval transform is not deterministic"


# ---------------------------------------------------------------------------
# train vs eval transform separation
# ---------------------------------------------------------------------------


def test_train_and_eval_transforms_use_same_normalization():
    """Train and eval must use identical normalization. If they drift, the
    eval transform feeds the model a differently-distributed tensor and
    accuracy will silently drop."""
    train_t = irilab2026.imagenet_train_transform()
    eval_t = irilab2026.imagenet_eval_transform()

    # Last transform in both should be Normalize with identical mean/std.
    train_norm = train_t.transforms[-1]
    eval_norm = eval_t.transforms[-1]

    assert train_norm.mean == eval_norm.mean, "Normalize mean differs between train and eval"
    assert train_norm.std == eval_norm.std, "Normalize std differs between train and eval"


# ---------------------------------------------------------------------------
# randaugment_train_transform
# ---------------------------------------------------------------------------


def test_randaugment_train_transform_returns_compose():
    t = irilab2026.randaugment_train_transform(num_ops=2, magnitude=9)
    assert isinstance(t, T.Compose)


def test_randaugment_train_transform_expected_sequence():
    """RandAugment must sit between the crop and ToTensor."""
    t = irilab2026.randaugment_train_transform(num_ops=2, magnitude=9)
    names = [type(x).__name__ for x in t.transforms]
    assert names == [
        "RandomResizedCrop",
        "RandAugment",
        "RandomHorizontalFlip",
        "ToTensor",
        "Normalize",
    ]


def test_randaugment_train_transform_randaugment_before_totensor():
    """The load-bearing ordering: RandAugment operates on PIL images, so it
    must precede ToTensor or it fails at runtime."""
    t = irilab2026.randaugment_train_transform()
    names = [type(x).__name__ for x in t.transforms]
    assert names.index("RandAugment") < names.index("ToTensor")


def test_randaugment_train_transform_produces_correct_tensor_shape():
    t = irilab2026.randaugment_train_transform(num_ops=2, magnitude=9)
    img = Image.new("RGB", (300, 400), color="red")
    result = t(img)
    assert isinstance(result, torch.Tensor)
    assert result.shape == (3, 224, 224)


def test_randaugment_train_transform_returns_fresh_compose():
    a = irilab2026.randaugment_train_transform()
    b = irilab2026.randaugment_train_transform()
    assert a is not b


def test_randaugment_train_transform_params_keyword_only():
    """num_ops and magnitude are keyword-only — guards against the
    (magnitude, num_ops) ordering mistake."""
    with pytest.raises(TypeError):
        irilab2026.randaugment_train_transform(2, 9)  # positional


def test_randaugment_train_transform_uses_imagenet_normalization():
    """Normalization must match the eval transform so augmented images stay in
    the model's expected distribution."""
    rand_t = irilab2026.randaugment_train_transform()
    eval_t = irilab2026.imagenet_eval_transform()
    assert rand_t.transforms[-1].mean == eval_t.transforms[-1].mean
    assert rand_t.transforms[-1].std == eval_t.transforms[-1].std


def test_randaugment_train_transform_rejects_bad_magnitude():
    with pytest.raises(ValueError, match="magnitude"):
        irilab2026.randaugment_train_transform(magnitude=99)


def test_randaugment_train_transform_rejects_bad_num_ops():
    with pytest.raises(ValueError, match="num_ops"):
        irilab2026.randaugment_train_transform(num_ops=0)