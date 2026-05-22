"""Training helpers.

Currently exposes one function — `train_baseline` — which implements the
ResNet-18 training recipe R2-Q1 N03 used inline. R2-Q2 N03's
data-randomization sanity check is the first caller; the function is general
enough to be reused for any baseline retrain on PV or PD data.
"""

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from sklearn.model_selection import train_test_split

from .environment import seed_all
from .vision import (
    build_baseline_model,
    imagenet_train_transform,
    imagenet_eval_transform,
)


def train_baseline(
    metadata,
    hf_dataset,
    dataset_class,
    *,
    num_classes,
    shuffle_labels=False,
    seed=42,
    epoch_cap=None,
    verbose=True,
):
    """Train a ResNet-18 baseline classifier using R2-Q1's recipe.

    Implements the recipe R2-Q1 N03 used inline:

    - Architecture: ResNet-18, ImageNet-pretrained, classifier head replaced.
    - Optimizer: SGD, momentum 0.9, lr 0.01 → 0.001 (step at epoch 7).
    - Batch size 32, 10 epochs (or `epoch_cap` if smaller).
    - Loss: cross-entropy.
    - 10% stratified val carve from the train split.
    - Best-val checkpointing — the returned state_dict is the epoch with
      the highest val accuracy, not the final epoch's.

    The function handles its own data wrangling (split filtering, label
    shuffle if requested, stratified val carve, dataset/loader construction).
    Callers pass raw metadata and the HF Dataset, plus the dataset class to
    wrap them in.

    Parameters
    ----------
    metadata : pandas.DataFrame
        Full metadata DataFrame from `iri.load_plantvillage()` or
        `iri.load_plantdoc()`. Must have `split` and `class_idx` columns.
        Filtered internally to `split == "train"`; other rows are ignored.
    hf_dataset : datasets.Dataset
        The Hugging Face Dataset object paired with `metadata`. The dataset
        class wraps this for image loading.
    dataset_class : type
        PyTorch Dataset class — `iri.PlantVillageDataset` or
        `iri.PlantDocDataset`. Must accept
        `(metadata_df, hf_dataset, transform=)` as its constructor.
    num_classes : int
        Number of output classes. Required; passed to
        `iri.build_baseline_model`.
    shuffle_labels : bool, default False
        If True, shuffle `class_idx` values across the train split with a
        fixed seed *before* the val carve, so both train and val carry
        shuffled labels. Used for Adebayo et al. (2018)'s data-randomization
        sanity check.
    seed : int, default 42
        Seeds the label shuffle (if any), the stratified val carve, and
        `iri.seed_all()` at function entry. Determines reproducibility.
    epoch_cap : int, optional
        If set, train for `min(10, epoch_cap)` epochs. For dev iteration
        on the tiny PV variant — pass 2 to get a ~3-minute run, leave as
        None for the full 10-epoch production recipe.
    verbose : bool, default True
        If True, prints per-epoch loss/accuracy summary and shows tqdm
        progress bars (which auto-clear, leaving only the per-epoch lines).
        If False, runs silently.

    Returns
    -------
    state_dict : dict
        Best-val-accuracy epoch's state_dict, moved to CPU. Ready to
        torch.save or load into a fresh ResNet-18 built with
        `iri.build_baseline_model(num_classes, pretrained=False)`.
    history : dict
        Per-epoch training history with keys:

        - `train_loss` : list of floats (mean batch loss per epoch)
        - `val_loss`   : list of floats (mean batch loss per epoch)
        - `val_acc`    : list of floats (val accuracy per epoch)
        - `best_val_epoch` : int (zero-indexed)
        - `best_val_acc`   : float

    Examples
    --------
    Standard retrain (whatever the caller's dataset is):

    >>> metadata, hf_dataset = iri.load_plantvillage()
    >>> state_dict, history = iri.train_baseline(
    ...     metadata, hf_dataset,
    ...     dataset_class=iri.PlantVillageDataset,
    ...     num_classes=38,
    ... )
    >>> torch.save(state_dict, "baseline_resnet18.pt")

    Label-shuffled retrain for Adebayo's data-randomization check:

    >>> state_dict, history = iri.train_baseline(
    ...     metadata, hf_dataset,
    ...     dataset_class=iri.PlantVillageDataset,
    ...     num_classes=38,
    ...     shuffle_labels=True,
    ... )

    Dev mode (2 epochs on tiny variant):

    >>> metadata_tiny, hf_tiny = iri.load_plantvillage(variant="tiny")
    >>> state_dict, history = iri.train_baseline(
    ...     metadata_tiny, hf_tiny,
    ...     dataset_class=iri.PlantVillageDataset,
    ...     num_classes=38,
    ...     epoch_cap=2,
    ... )

    Notes
    -----
    Implements the same recipe R2-Q1 N03 uses inline; minor implementation
    differences (logging format, manual LR step vs scheduler object) don't
    affect the trained model. The function does not save to disk — callers
    that want a checkpoint do so via `torch.save(state_dict, path)`.
    """
    # Recipe constants — locked to match R2-Q1 N03's inline loop.
    EPOCHS = 10
    BATCH_SIZE = 32
    LR = 0.01
    LR_DECAY_EPOCH = 7
    LR_DECAY_FACTOR = 0.1
    VAL_FRACTION = 0.1
    MOMENTUM = 0.9
    NUM_WORKERS = 2

    seed_all(seed)
    epochs = min(EPOCHS, epoch_cap) if epoch_cap is not None else EPOCHS

    # --- Data preparation -------------------------------------------------

    train_metadata = metadata[metadata["split"] == "train"].copy()

    if shuffle_labels:
        # Shuffle BEFORE the val carve so both train and val have shuffled
        # labels — a model "best val" against unshuffled labels would be
        # meaningless when training is on shuffled.
        train_metadata["class_idx"] = (
            train_metadata["class_idx"]
            .sample(frac=1.0, random_state=seed)
            .values
        )

    # Stratified val carve from train. Preserve the original pandas
    # index (no reset_index) so dataset_class can look up images in
    # hf_dataset via row.name — the PlantVillage/PlantDoc Dataset
    # wrappers both depend on this.
    train_idx, val_idx = train_test_split(
        train_metadata.index,
        test_size=VAL_FRACTION,
        stratify=train_metadata["class_idx"],
        random_state=seed,
    )
    train_set_meta = train_metadata.loc[train_idx]
    val_set_meta = train_metadata.loc[val_idx]

    train_dataset = dataset_class(
        train_set_meta, hf_dataset, transform=imagenet_train_transform()
    )
    val_dataset = dataset_class(
        val_set_meta, hf_dataset, transform=imagenet_eval_transform()
    )

    train_loader = DataLoader(
        train_dataset, batch_size=BATCH_SIZE,
        shuffle=True, num_workers=NUM_WORKERS,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=BATCH_SIZE,
        shuffle=False, num_workers=NUM_WORKERS,
    )

    # --- Model, optimizer, criterion --------------------------------------

    model = build_baseline_model(num_classes, pretrained=True).cuda()
    optimizer = torch.optim.SGD(model.parameters(), lr=LR, momentum=MOMENTUM)
    criterion = nn.CrossEntropyLoss()

    # --- Training loop with best-val checkpointing ------------------------

    history = {"train_loss": [], "val_loss": [], "val_acc": []}
    best_val_acc = -1.0
    best_val_epoch = -1
    best_state_dict = None

    # tqdm is optional — only imported if verbose to avoid the dep when
    # callers want silent runs.
    if verbose:
        from tqdm.auto import tqdm

    for epoch in range(epochs):
        # Manual LR step — matches R2-Q1's "step from 0.01 to 0.001 at
        # epoch 7" without depending on torch.optim.lr_scheduler.
        current_lr = LR if epoch < LR_DECAY_EPOCH else LR * LR_DECAY_FACTOR
        for g in optimizer.param_groups:
            g["lr"] = current_lr

        # Train pass.
        model.train()
        train_losses = []
        train_iter = (
            tqdm(train_loader, leave=False, desc=f"E{epoch + 1} train")
            if verbose else train_loader
        )
        for x, y in train_iter:
            x, y = x.cuda(), y.cuda()
            optimizer.zero_grad()
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()
            train_losses.append(loss.item())

        # Val pass.
        model.eval()
        val_losses = []
        val_correct = 0
        val_total = 0
        val_iter = (
            tqdm(val_loader, leave=False, desc=f"E{epoch + 1} val")
            if verbose else val_loader
        )
        with torch.no_grad():
            for x, y in val_iter:
                x, y = x.cuda(), y.cuda()
                logits = model(x)
                loss = criterion(logits, y)
                val_losses.append(loss.item())
                val_correct += (logits.argmax(dim=1) == y).sum().item()
                val_total += y.size(0)

        train_loss = float(np.mean(train_losses))
        val_loss = float(np.mean(val_losses))
        val_acc = val_correct / val_total

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)

        # Best-val checkpointing — snapshot the state_dict on CPU so the
        # snapshot is independent of the GPU model's params.
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_val_epoch = epoch
            best_state_dict = {
                k: v.detach().cpu().clone()
                for k, v in model.state_dict().items()
            }

        if verbose:
            print(
                f"Epoch {epoch + 1}/{epochs}: "
                f"train_loss={train_loss:.4f} "
                f"val_loss={val_loss:.4f} "
                f"val_acc={val_acc:.4f} "
                f"lr={current_lr:.4f}"
            )

    history["best_val_epoch"] = best_val_epoch
    history["best_val_acc"] = best_val_acc

    return best_state_dict, history