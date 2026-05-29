"""Category-space evaluation for the R2 image-classification notebooks.

Two functions for scoring a PlantVillage-trained classifier in the shared
disease-category space that the lab-to-field (PlantVillage-to-PlantDoc)
comparison runs in:

- `build_idx_to_cat(meta, class_to_cat, name)` — turn a dataset's integer
  `class_idx` into a disease category, via `class_idx -> class_label ->
  category`, using that dataset's committed class-to-category map.
- `evaluate_in_categories(state_dict, ...)` — rebuild a model from its saved
  weights, run it over an eval set, map predictions and labels into
  categories, and return overall and per-category accuracy.

The asymmetry that makes the comparison correct: a model always predicts its
*training* dataset's class space (PlantVillage), so predictions are mapped with
PlantVillage's lookup no matter what they are evaluated on, while ground-truth
labels are mapped with whichever dataset is being scored. R2-Q1 established this
category space; R2-Q3 reuses it across three classifiers; the maps themselves
are committed per question in `precommit.json` (`class_space_remapping`).
"""

from __future__ import annotations

import torch
from torch.utils.data import DataLoader

from .vision import build_baseline_model, imagenet_eval_transform


def build_idx_to_cat(meta, class_to_cat, name):
    """Map a dataset's `class_idx` to a disease category.

    Builds the lookup from the dataset's own metadata, going
    `class_idx -> class_label -> category`, so the integer index a model
    emits (or a label carries) can be scored in the shared category space.

    Parameters
    ----------
    meta : pandas.DataFrame
        Metadata with `class_idx` (int) and `class_label` (str) columns, as
        returned by `load_plantvillage()` / `load_plantdoc()`.
    class_to_cat : dict
        The committed `class_label -> category` map for this dataset (from
        `precommit.json`'s `class_space_remapping`).
    name : str
        Human-readable dataset name, used only in the error message.

    Returns
    -------
    dict
        `class_idx (int) -> category (str)`.

    Raises
    ------
    AssertionError
        If any class the dataset actually contains is missing from
        `class_to_cat`. Failing loud here — and naming the gap — is deliberate:
        a silently dropped class would corrupt the accuracy it is left out of.
    """
    idx_to_label = (
        meta[["class_idx", "class_label"]]
        .drop_duplicates()
        .set_index("class_idx")["class_label"]
        .to_dict()
    )
    unmapped = set(idx_to_label.values()) - set(class_to_cat)
    assert not unmapped, (
        f"{name} has classes missing from the committed map: {sorted(unmapped)}. "
        "Fix the class_space_remapping in NB00 so every class maps to a category."
    )
    return {idx: class_to_cat[label] for idx, label in idx_to_label.items()}


def evaluate_in_categories(
    state_dict,
    eval_metadata,
    eval_hf_dataset,
    dataset_class,
    *,
    num_classes: int,
    pred_idx_to_cat,
    true_idx_to_cat,
    categories,
    batch_size: int = 32,
    return_per_item: bool = False,
):
    """Score a PlantVillage-trained classifier in the shared category space.

    Rebuilds the model from its saved weights, runs it over `eval_metadata`
    under the deterministic eval transform, maps both predictions and
    ground-truth labels into categories, and returns overall and per-category
    accuracy.

    Parameters
    ----------
    state_dict : dict
        Trained weights, as returned by `train_baseline`.
    eval_metadata : pandas.DataFrame
        Metadata for the split to score (e.g. the test rows).
    eval_hf_dataset : datasets.Dataset
        The Hugging Face dataset paired with `eval_metadata`.
    dataset_class : type
        `PlantVillageDataset` or `PlantDocDataset` — wraps the metadata and
        dataset for image loading.
    num_classes : int
        Number of output classes the model was trained with. Used to rebuild
        the architecture before loading the weights.
    pred_idx_to_cat : dict
        Maps the MODEL's output index (always PlantVillage's class space) to a
        category. The same map is used regardless of the eval dataset.
    true_idx_to_cat : dict
        Maps the EVAL dataset's `class_idx` to a category — PlantVillage's map
        for PV-internal eval, PlantDoc's for PD.
    categories : list of str
        The shared category space, in the order to report.
    batch_size : int, default 32
        Evaluation batch size.
    return_per_item : bool, default False
        If True, also return a list of per-item predictions and true labels.
    Returns
    -------
    dict
        - `overall` : float, accuracy in category space across all images.
        - `per_category` : dict, `category -> accuracy`, with `None` where a
          category has no examples in this eval set (PlantDoc's test split has
          no `pest` images, for instance).
        - `n` : int, number of images scored.
        - `per_item` : dict, present only when `return_per_item=True`, with
          `pred_cats` and `true_cats` — the predicted and true category of
          each image, as lists in `eval_metadata` order (the loader runs
          `shuffle=False`). Two conditions scored on the same `eval_metadata`
          line up position-for-position, which is what lets a paired bootstrap
          resample image positions and read each condition's correctness at
          those positions.

    Notes
    -----
    Rebuilds the model with `pretrained=False` (no weight download) and calls
    `.cuda()` directly — a GPU is required, matching `train_baseline`.
    """
    # Rebuild a fresh ResNet-18 and load the trained weights into it.
    # train_baseline returned weights, not a model.
    model = build_baseline_model(num_classes, pretrained=False).cuda()
    model.load_state_dict(state_dict)
    model.eval()

    ds = dataset_class(
        eval_metadata, eval_hf_dataset, transform=imagenet_eval_transform()
    )
    loader = DataLoader(ds, batch_size=batch_size, shuffle=False, num_workers=2)

    pred_cats, true_cats = [], []
    with torch.no_grad():
        for x, y in loader:
            x = x.cuda()
            pred_idx = model(x).argmax(dim=1).cpu().tolist()
            pred_cats.extend(pred_idx_to_cat[i] for i in pred_idx)
            true_cats.extend(true_idx_to_cat[i] for i in y.tolist())

    # Overall accuracy in category space.
    overall = sum(p == t for p, t in zip(pred_cats, true_cats)) / len(true_cats)

    # Per-category accuracy: of the images whose TRUE category is c, the
    # fraction the model also called c. None if the category has no examples
    # in this eval set.
    per_category = {}
    for c in categories:
        rows = [i for i, t in enumerate(true_cats) if t == c]
        per_category[c] = (
            sum(pred_cats[i] == c for i in rows) / len(rows) if rows else None
        )

    result = {"overall": overall, "per_category": per_category, "n": len(true_cats)}
    if return_per_item:
        # The per-image category assignments this call already computed, in
        # eval_metadata order. Returned only on request so the default return
        # contract is unchanged. NB03's bootstrap reads these: same eval set,
        # same order across conditions -> positional pairing.
        result["per_item"] = {"pred_cats": pred_cats, "true_cats": true_cats}
    return result