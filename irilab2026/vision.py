"""Vision helpers for the R2 image-classification notebooks.

Three functions:

- `build_baseline_model(num_classes)` — ResNet-18 + ImageNet
  weights + replaced classification head. The standard baseline
  used by R2-Q1's N03, N04, and (in extended form) R2-Q3.
- `imagenet_train_transform()` — the train-time transform pipeline.
- `imagenet_eval_transform()` — the eval-time transform pipeline.

The ImageNet normalization constants live here as module-level
constants so train and eval transforms cannot drift out of sync.
"""

from __future__ import annotations

import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as T


# ImageNet pretrained weights expect this normalization.
# Source: https://pytorch.org/vision/stable/models.html
_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD = [0.229, 0.224, 0.225]


def build_baseline_model(
    num_classes: int,
    *,
    pretrained: bool = True,
) -> nn.Module:
    """Return a ResNet-18 with the classification head replaced.

    Parameters
    ----------
    num_classes : int
        Number of output classes. The default ResNet-18's final
        layer is a Linear(512, 1000) — this is replaced by
        Linear(512, num_classes).
    pretrained : bool, keyword-only, default True
        If True, load IMAGENET1K_V1 pretrained weights. If False,
        random-initialize. The False path exists so tests can run
        without pulling weights over the network; notebooks should
        always use True.

    Returns
    -------
    nn.Module
        A ResNet-18 ready to train. Move it to a device with `.to(device)`.

    Notes
    -----
    The first time `pretrained=True` is used on a given Colab
    runtime, torchvision downloads ~45 MB of weights to
    `~/.cache/torch/hub/checkpoints/`. Subsequent calls within the
    same session are instant.
    """
    weights = models.ResNet18_Weights.IMAGENET1K_V1 if pretrained else None
    model = models.resnet18(weights=weights)
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model


def imagenet_train_transform() -> T.Compose:
    """Train-time transform pipeline matching ImageNet pretrained weights.

    Returns a fresh `Compose` of:
        RandomResizedCrop(224) → RandomHorizontalFlip()
        → ToTensor() → Normalize(IMAGENET stats)

    The random crop and flip provide light augmentation; the
    output tensor matches the input expectations of the ResNet-18
    pretrained weights.

    Returns
    -------
    torchvision.transforms.Compose
    """
    return T.Compose([
        T.RandomResizedCrop(224),
        T.RandomHorizontalFlip(),
        T.ToTensor(),
        T.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
    ])


def imagenet_eval_transform() -> T.Compose:
    """Eval-time transform pipeline matching ImageNet pretrained weights.

    Returns a fresh `Compose` of:
        Resize(256) → CenterCrop(224)
        → ToTensor() → Normalize(IMAGENET stats)

    Deterministic — no randomness. Two passes over the same image
    produce identical tensors.

    Returns
    -------
    torchvision.transforms.Compose
    """
    return T.Compose([
        T.Resize(256),
        T.CenterCrop(224),
        T.ToTensor(),
        T.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
    ])