"""Build the PlantDoc Hugging Face datasets (full and tiny variants).

One-time authoring script. Clones the upstream pratikkayal/PlantDoc-Dataset
repo, walks its canonical train/test directory partition, applies a
hand-curated class-normalization lookup, and produces two HF Datasets:

    huggingface.co/datasets/geraldmc/plantdoc-full   (~2,578 images)
    huggingface.co/datasets/geraldmc/plantdoc-tiny   (~165 images)

Both are tagged v0.1.0 by default.

The tiny variant takes min(3, available) stratified samples per class
per split with a fixed seed, so every non-orphan class appears in both
splits. The orphan class (Tomato two spotted spider mites leaf, 2 train
+ 0 test in upstream) appears with 2 train + 0 test in tiny too.

Authentication:
    Run `huggingface-cli login` once with a write-scoped token before
    invoking with --push.

Usage:
    # Build local artifacts only (no push):
    python scripts/build_pd_full_hf.py

    # Build and push both variants to HF:
    python scripts/build_pd_full_hf.py --push

    # Build only the tiny variant:
    python scripts/build_pd_full_hf.py --variant tiny --push

    # Use an existing clone instead of cloning into a temp dir:
    python scripts/build_pd_full_hf.py --upstream-dir ~/pd_clone --push
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
from datasets import Dataset, Features, Image as HFImage, Value


# -- Constants ---------------------------------------------------------------

UPSTREAM_REPO = "https://github.com/pratikkayal/PlantDoc-Dataset.git"

HF_REPO_FULL = "geraldmc/plantdoc-full"
HF_REPO_TINY = "geraldmc/plantdoc-tiny"
HF_REVISION = "v0.1.0"

SUBSAMPLE_PER_CLASS_PER_SPLIT = 3
SUBSAMPLE_SEED = 42

# Hand-curated class-normalization lookup. Maps the upstream folder name
# (left side, verbatim) to (host, disease, is_healthy). Diseases are
# lowercased; hosts preserve upstream case ("grape" lowercase, "Soyabean"
# misspelled). See r2q1_pd_recon.md for the full rationale.
CLASS_LOOKUP: dict[str, tuple[str, str, bool]] = {
    "Apple Scab Leaf":                        ("Apple",       "scab",                     False),
    "Apple leaf":                             ("Apple",       "healthy",                  True),
    "Apple rust leaf":                        ("Apple",       "rust",                     False),
    "Bell_pepper leaf":                       ("Bell pepper", "healthy",                  True),
    "Bell_pepper leaf spot":                  ("Bell pepper", "leaf spot",                False),
    "Blueberry leaf":                         ("Blueberry",   "healthy",                  True),
    "Cherry leaf":                            ("Cherry",      "healthy",                  True),
    "Corn Gray leaf spot":                    ("Corn",        "gray leaf spot",           False),
    "Corn leaf blight":                       ("Corn",        "leaf blight",              False),
    "Corn rust leaf":                         ("Corn",        "rust",                     False),
    "Peach leaf":                             ("Peach",       "healthy",                  True),
    "Potato leaf early blight":               ("Potato",      "early blight",             False),
    "Potato leaf late blight":                ("Potato",      "late blight",              False),
    "Raspberry leaf":                         ("Raspberry",   "healthy",                  True),
    "Soyabean leaf":                          ("Soyabean",    "healthy",                  True),
    "Squash Powdery mildew leaf":             ("Squash",      "powdery mildew",           False),
    "Strawberry leaf":                        ("Strawberry",  "healthy",                  True),
    "Tomato Early blight leaf":               ("Tomato",      "early blight",             False),
    "Tomato Septoria leaf spot":              ("Tomato",      "septoria leaf spot",       False),
    "Tomato leaf":                            ("Tomato",      "healthy",                  True),
    "Tomato leaf bacterial spot":             ("Tomato",      "bacterial spot",           False),
    "Tomato leaf late blight":                ("Tomato",      "late blight",              False),
    "Tomato leaf mosaic virus":               ("Tomato",      "mosaic virus",             False),
    "Tomato leaf yellow virus":               ("Tomato",      "yellow virus",             False),
    "Tomato mold leaf":                       ("Tomato",      "mold",                     False),
    "Tomato two spotted spider mites leaf":   ("Tomato",      "two spotted spider mites", False),
    "grape leaf":                             ("grape",       "healthy",                  True),
    "grape leaf black rot":                   ("grape",       "black rot",                False),
}


# -- Upstream acquisition ----------------------------------------------------

def clone_upstream(target_dir: Path) -> Path:
    """Shallow-clone the PlantDoc-Dataset repo into target_dir."""
    print(f"Cloning {UPSTREAM_REPO} (shallow) to {target_dir} ...")
    subprocess.run(
        ["git", "clone", "--depth", "1", UPSTREAM_REPO, str(target_dir)],
        check=True,
    )
    if not (target_dir / "train").is_dir() or not (target_dir / "test").is_dir():
        raise RuntimeError(
            f"Expected train/ and test/ under {target_dir} after clone — "
            f"upstream layout may have changed."
        )
    return target_dir


def get_upstream_commit_sha(repo_dir: Path) -> str:
    """Return the upstream commit SHA the clone points at."""
    return subprocess.check_output(
        ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
        text=True,
    ).strip()


# -- Metadata construction ---------------------------------------------------

def build_metadata(repo_root: Path) -> pd.DataFrame:
    """Walk train/ and test/, build the full metadata DataFrame.

    Columns produced (seven, in this order):
        class_label, class_idx, host, disease, is_healthy, split, filename

    class_idx is assigned by case-sensitive alphabetical sort over the
    distinct class_label values. Every class in upstream must be present
    in CLASS_LOOKUP — unknown classes raise.
    """
    rows = []
    expected = set(CLASS_LOOKUP.keys())

    for split in ("train", "test"):
        split_dir = repo_root / split
        if not split_dir.is_dir():
            raise RuntimeError(f"Missing {split_dir}")
        for class_dir in sorted(split_dir.iterdir()):
            if not class_dir.is_dir():
                continue
            cls = class_dir.name
            if cls not in expected:
                raise RuntimeError(
                    f"Class {cls!r} in {split}/ is not in CLASS_LOOKUP. "
                    f"Update CLASS_LOOKUP or investigate the upstream repo."
                )
            host, disease, is_healthy = CLASS_LOOKUP[cls]
            for img_path in sorted(class_dir.iterdir()):
                if not img_path.is_file():
                    continue
                rows.append({
                    "class_label": cls,
                    "host": host,
                    "disease": disease,
                    "is_healthy": is_healthy,
                    "split": split,
                    "filename": img_path.name,
                })

    df = pd.DataFrame(rows)

    # Warn about lookup entries that don't appear in upstream
    observed = set(df["class_label"].unique())
    missing = expected - observed
    if missing:
        print(
            f"Warning: CLASS_LOOKUP has {len(missing)} entries not seen in "
            f"upstream: {sorted(missing)}",
            file=sys.stderr,
        )

    # class_idx by case-sensitive alphabetical sort over class_label
    sorted_classes = sorted(observed)
    class_to_idx = {cls: i for i, cls in enumerate(sorted_classes)}
    df["class_idx"] = df["class_label"].map(class_to_idx)

    # Canonical column order
    df = df[
        ["class_label", "class_idx", "host", "disease",
         "is_healthy", "split", "filename"]
    ].reset_index(drop=True)

    # Print train-only and test-only class summaries
    train_classes = set(df[df["split"] == "train"]["class_label"].unique())
    test_classes = set(df[df["split"] == "test"]["class_label"].unique())
    train_only = train_classes - test_classes
    test_only = test_classes - train_classes
    if train_only:
        print(f"\nClasses present only in train (no test images):")
        for cls in sorted(train_only):
            n = int((df["class_label"] == cls).sum())
            print(f"  - {cls}: {n} train images, 0 test images")
    if test_only:
        print(f"\nClasses present only in test (no train images):")
        for cls in sorted(test_only):
            n = int((df["class_label"] == cls).sum())
            print(f"  - {cls}: 0 train images, {n} test images")

    return df


def stratified_subsample(
    df: pd.DataFrame,
    per_class_per_split: int,
    seed: int,
) -> pd.DataFrame:
    """Take min(per_class_per_split, available) samples per (class, split).

    Deterministic given (df, per_class_per_split, seed). Groups are
    iterated in sorted order so the same inputs produce identical output
    across runs.
    """
    pieces = []
    for (cls, split), group in df.groupby(["class_label", "split"], sort=True):
        n = min(per_class_per_split, len(group))
        pieces.append(group.sample(n=n, random_state=seed))
    return (
        pd.concat(pieces)
        .sort_values(["class_label", "split", "filename"])
        .reset_index(drop=True)
    )


# -- HF Dataset construction and push ---------------------------------------

def build_hf_dataset(
    metadata_df: pd.DataFrame,
    repo_root: Path,
) -> Dataset:
    """Construct an HF Dataset with an image field plus the 7 metadata columns.

    Image paths are passed to the HF Image() feature; bytes get embedded
    when push_to_hub runs (embed_external_files=True is the default).
    """
    image_paths = [
        str(repo_root / row["split"] / row["class_label"] / row["filename"])
        for _, row in metadata_df.iterrows()
    ]

    data = {
        "image": image_paths,
        "class_label": metadata_df["class_label"].tolist(),
        "class_idx": metadata_df["class_idx"].astype(int).tolist(),
        "host": metadata_df["host"].tolist(),
        "disease": metadata_df["disease"].tolist(),
        "is_healthy": metadata_df["is_healthy"].astype(bool).tolist(),
        "split": metadata_df["split"].tolist(),
        "filename": metadata_df["filename"].tolist(),
    }

    features = Features({
        "image": HFImage(),
        "class_label": Value("string"),
        "class_idx": Value("int64"),
        "host": Value("string"),
        "disease": Value("string"),
        "is_healthy": Value("bool"),
        "split": Value("string"),
        "filename": Value("string"),
    })

    return Dataset.from_dict(data, features=features)


def check_hf_auth() -> str:
    """Verify the user is logged into HF Hub. Returns the username."""
    from huggingface_hub import HfApi
    try:
        info = HfApi().whoami()
    except Exception:
        raise SystemExit(
            "Not logged in to Hugging Face Hub. Run "
            "`huggingface-cli login` with a write-scoped token, "
            "then re-run this script."
        )
    return info.get("name", "?")


def push_dataset(ds: Dataset, repo_id: str, tag: str) -> None:
    """Push the dataset to HF Hub and tag the resulting commit."""
    from huggingface_hub import HfApi

    print(f"Pushing to {repo_id} ...")
    ds.push_to_hub(repo_id, commit_message=f"Release {tag}")

    api = HfApi()
    try:
        api.create_tag(
            repo_id=repo_id,
            repo_type="dataset",
            tag=tag,
            tag_message=f"Release {tag}",
        )
        print(f"Tagged: {repo_id} @ {tag}")
    except Exception as exc:
        print(
            f"Warning: could not create tag {tag} on {repo_id}: {exc}\n"
            f"  If the tag already exists, delete it manually before "
            f"re-running.",
            file=sys.stderr,
        )


# -- Debug artifacts ---------------------------------------------------------

def write_metadata_csv(df: pd.DataFrame, path: Path) -> None:
    """Write the metadata DataFrame to CSV for local diff-checking."""
    df.to_csv(path, index=False)
    print(f"Wrote {path} ({len(df)} rows)")


def write_provenance_json(
    path: Path,
    *,
    variant: str,
    repo_id: str,
    revision: str,
    metadata_df: pd.DataFrame,
    upstream_commit_sha: str,
    subsample_info: dict | None = None,
) -> None:
    """Write a build-provenance JSON describing what would be (or was) pushed."""
    n_train = int((metadata_df["split"] == "train").sum())
    n_test = int((metadata_df["split"] == "test").sum())
    payload = {
        "dataset": f"plantdoc-{variant}",
        "hf_repo": repo_id,
        "hf_revision": revision,
        "upstream_repo": UPSTREAM_REPO,
        "upstream_commit_sha": upstream_commit_sha,
        "total_images": len(metadata_df),
        "train_images": n_train,
        "test_images": n_test,
        "class_count": int(metadata_df["class_label"].nunique()),
        "build_script": "scripts/build_pd_full_hf.py",
    }
    if subsample_info is not None:
        payload.update(subsample_info)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    print(f"Wrote {path}")


# -- Main --------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build"),
        help="Where to write metadata_*.csv and provenance_*.json. Default: build/",
    )
    parser.add_argument(
        "--upstream-dir",
        type=Path,
        default=None,
        help="Use an existing clone of pratikkayal/PlantDoc-Dataset. "
             "If omitted, the script clones into a temp directory.",
    )
    parser.add_argument(
        "--variant",
        choices=["full", "tiny", "both"],
        default="both",
        help="Which variant(s) to build. Default: both.",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push the built dataset(s) to Hugging Face Hub. "
             "Without --push, the script writes local artifacts only.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=SUBSAMPLE_SEED,
        help=f"Random seed for tiny variant stratified subsample. "
             f"Default: {SUBSAMPLE_SEED}",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.push:
        username = check_hf_auth()
        print(f"Authenticated as Hugging Face user: {username}")

    # Acquire the upstream clone (existing dir or fresh tempdir).
    cleanup_tmpdir: tempfile.TemporaryDirectory | None = None
    if args.upstream_dir is not None:
        if not (args.upstream_dir / "train").is_dir():
            raise SystemExit(f"Expected train/ under {args.upstream_dir}")
        repo_root = args.upstream_dir
        print(f"Using existing clone at {repo_root}")
    else:
        cleanup_tmpdir = tempfile.TemporaryDirectory()
        repo_root = clone_upstream(Path(cleanup_tmpdir.name) / "pd")

    try:
        upstream_sha = get_upstream_commit_sha(repo_root)
        print(f"Upstream commit: {upstream_sha[:12]}")

        # Full metadata is always built (tiny derives from it).
        print("\n=== Building metadata (full) ===")
        full_md = build_metadata(repo_root)
        print(
            f"\nFull metadata: {len(full_md)} images, "
            f"{full_md['class_label'].nunique()} classes, "
            f"{(full_md['split'] == 'train').sum()} train / "
            f"{(full_md['split'] == 'test').sum()} test"
        )

        if args.variant in ("full", "both"):
            write_metadata_csv(full_md, args.output_dir / "metadata_full.csv")
            write_provenance_json(
                args.output_dir / "provenance_full.json",
                variant="full",
                repo_id=HF_REPO_FULL,
                revision=HF_REVISION,
                metadata_df=full_md,
                upstream_commit_sha=upstream_sha,
            )

        if args.variant in ("tiny", "both"):
            print("\n=== Building metadata (tiny) ===")
            tiny_md = stratified_subsample(
                full_md,
                per_class_per_split=SUBSAMPLE_PER_CLASS_PER_SPLIT,
                seed=args.seed,
            )
            print(
                f"Tiny metadata: {len(tiny_md)} images, "
                f"{tiny_md['class_label'].nunique()} classes, "
                f"{(tiny_md['split'] == 'train').sum()} train / "
                f"{(tiny_md['split'] == 'test').sum()} test"
            )
            write_metadata_csv(tiny_md, args.output_dir / "metadata_tiny.csv")
            write_provenance_json(
                args.output_dir / "provenance_tiny.json",
                variant="tiny",
                repo_id=HF_REPO_TINY,
                revision=HF_REVISION,
                metadata_df=tiny_md,
                upstream_commit_sha=upstream_sha,
                subsample_info={
                    "subsample_rule": (
                        f"min({SUBSAMPLE_PER_CLASS_PER_SPLIT}, available) "
                        f"per class per split"
                    ),
                    "subsample_seed": args.seed,
                },
            )

        if args.push:
            if args.variant in ("full", "both"):
                print("\n=== Pushing full variant ===")
                full_ds = build_hf_dataset(full_md, repo_root)
                push_dataset(full_ds, HF_REPO_FULL, HF_REVISION)

            if args.variant in ("tiny", "both"):
                print("\n=== Pushing tiny variant ===")
                tiny_ds = build_hf_dataset(tiny_md, repo_root)
                push_dataset(tiny_ds, HF_REPO_TINY, HF_REVISION)
        else:
            print("\n--push not set; skipping HF push.")
            print("Re-run with --push to publish to Hugging Face Hub.")

    finally:
        if cleanup_tmpdir is not None:
            cleanup_tmpdir.cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())