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


def randaugment_train_transform(
    *,
    num_ops: int = 2,
    magnitude: int = 9,
) -> T.Compose:
    """Train-time transform with a RandAugment policy layered in.

    This is the "kitchen-sink" augmentation used as R2-Q3's strong baseline:
    a broad, general-purpose augmentation policy applied without reference to
    any specific failure mode. It is the same geometric pipeline as
    `imagenet_train_transform()` with one extra stage — a `RandAugment`
    operation inserted at the PIL-image stage, before the image becomes a
    tensor.

    What RandAugment does
    ---------------------
    RandAugment (Cubuk et al., 2020) applies a small number of randomly chosen
    image operations — rotate, shear, color, contrast, posterize, and so on —
    drawn from a fixed menu, each at a shared strength. You do not pick the
    operations; that is the point. It trades the work of hand-designing
    augmentations for two knobs:

    - `num_ops`   : how many operations are applied per image, in sequence.
                    More operations means a more heavily transformed image.
    - `magnitude` : how strong each operation is, on a 0-30 scale (0 is a
                    no-op, 30 is the strongest).

    Why it is composed here and not appended
    ----------------------------------------
    RandAugment operates on a PIL image, so it must run BEFORE `ToTensor()`
    converts the image to a normalized float tensor. You cannot simply append
    it to `imagenet_train_transform()` — that would hand RandAugment a
    normalized tensor and fail at runtime. This helper rebuilds the pipeline
    with RandAugment in the correct slot so you do not have to reason about
    ordering.

    The pipeline returned is:
        RandomResizedCrop(224) -> RandAugment(num_ops, magnitude)
        -> RandomHorizontalFlip() -> ToTensor() -> Normalize(ImageNet stats)

    The normalization matches the ImageNet pretrained weights — identical to
    `imagenet_train_transform()` and `imagenet_eval_transform()` — so the
    augmented images stay in the distribution the model was pretrained on.

    Parameters
    ----------
    num_ops : int, keyword-only, default 2
        Number of randomly chosen operations applied per image. Must be at
        least 1.
    magnitude : int, keyword-only, default 9
        Strength of each operation, 0-30. torchvision enforces
        `magnitude < num_magnitude_bins` (31 by default); this helper checks
        the 0-30 range up front with a clearer message.

    Returns
    -------
    torchvision.transforms.Compose
        A fresh Compose on each call — no state shared between callers.

    Examples
    --------
    >>> t = iri.randaugment_train_transform(num_ops=2, magnitude=9)
    >>> state_dict, history = iri.train_baseline(
    ...     metadata, hf_dataset,
    ...     dataset_class=iri.PlantVillageDataset,
    ...     num_classes=38,
    ...     train_transform=t,
    ... )

    Notes
    -----
    The defaults `num_ops=2`, `magnitude=9` match R2-Q3 NB00's precommit
    defaults. In NB01 you pass the values you committed in `precommit.json`
    rather than re-typing them, so the augmentation you train with is the one
    you locked in Week 1.
    """
    if num_ops < 1:
        raise ValueError(
            f"num_ops must be at least 1, got {num_ops}. "
            f"num_ops is how many operations RandAugment applies per image."
        )
    if not 0 <= magnitude <= 30:
        raise ValueError(
            f"magnitude must be in 0-30, got {magnitude}. "
            f"It is a strength on a fixed 0-30 scale, not a percentage."
        )

    return T.Compose([
        T.RandomResizedCrop(224),
        T.RandAugment(num_ops=num_ops, magnitude=magnitude),
        T.RandomHorizontalFlip(),
        T.ToTensor(),
        T.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
    ])