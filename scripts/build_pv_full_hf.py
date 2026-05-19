#!/usr/bin/env python3
"""Build and publish the PlantVillage HF dataset.

Authoring script. Mirrors the upstream PlantVillage color image dataset,
attaches leaf-grouping metadata from filtered_leafmaps/, produces a
deterministic leaf-grouped 80/20 train/test split, and publishes the
result to Hugging Face Hub as a versioned dataset.

Port of scripts/build_pv_full_tarball.py. The metadata-construction
logic (clone, walk, leafmap join, split assignment) is unchanged. What's
different: instead of building a .tar.gz and uploading to a GitHub
release, the script constructs an HF Dataset with image bytes inline
and calls push_to_hub. The HF commit hash plays the role the SHA256
played for the tarball.

Two variants are produced from one script, selected by --variant:

  full  — all ~54k images. Pushed to <namespace>/plantvillage-full.
  tiny  — 50 images per class (~1,900 total). Pushed to
          <namespace>/plantvillage-tiny. Same metadata schema. Intended
          for debugging training loops, not for serious analysis.

Usage:
    # Full variant against a local clone
    python scripts/build_pv_full_hf.py \\
        --repo geraldmc/plantvillage-full \\
        --tag v0.1.0 \\
        --upstream-dir /path/to/PlantVillage-Dataset

    # Tiny variant
    python scripts/build_pv_full_hf.py \\
        --repo geraldmc/plantvillage-tiny \\
        --tag v0.1.0 \\
        --variant tiny \\
        --upstream-dir /path/to/PlantVillage-Dataset

    # Dry run — build everything but skip the push
    python scripts/build_pv_full_hf.py \\
        --repo geraldmc/plantvillage-full \\
        --tag v0.1.0 \\
        --upstream-dir /path/to/PlantVillage-Dataset \\
        --dry-run

Requirements:
    Python 3.9+
    pip install datasets huggingface_hub
    git on PATH
    huggingface-cli login (one-time, before first non-dry-run)

Determinism:
    For the full variant, the published dataset is reproducible given the
    same upstream commit and the same SPLIT_SEED. For the tiny variant,
    SUBSAMPLE_SEED additionally fixes which images are selected. The HF
    commit hash itself includes upload-time metadata, but the row content
    inside the shards is byte-identical across runs.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

# Reproducibility seed for the leaf-grouped 80/20 split. Changing this
# changes which leaves go to train vs test. Don't change casually — if
# you do, bump the data release version too.
SPLIT_SEED = 20260518
TRAIN_RATIO = 0.8

# Reproducibility seed for the tiny variant's per-class subsample.
# Independent of SPLIT_SEED so that the tiny subsample can be regenerated
# without forcing a re-shuffle of the train/test split.
SUBSAMPLE_SEED = 20260519
TINY_IMAGES_PER_CLASS = 50

# Bump when the script's output format changes meaningfully (new column,
# different split logic, different schema). Recorded in the local
# provenance.json so downstream code can detect mismatches.
BUILD_SCRIPT_VERSION = "0.1.0"

UPSTREAM_REPO = "https://github.com/spMohanty/PlantVillage-Dataset.git"
UPSTREAM_COLOR_SUBDIR = "raw/color"
UPSTREAM_LEAFMAPS_SUBDIR = "leaf_grouping/filtered_leafmaps"

# Sanity-check expectation: how many classes lack leafmap metadata.
# Per upstream as of 2026-05-18, eight classes are ungrouped. Detected
# dynamically; this is just a warning threshold in case upstream changes.
EXPECTED_UNGROUPED_COUNT = 8


# ==========================================================================
# Helpers — unchanged from build_pv_full_tarball.py
# ==========================================================================

def parse_class_name(class_dir_name: str) -> tuple[str, str]:
    """Parse a PV class directory name into (host, disease).

    PV class directories follow the convention ``Host___Disease``. The
    triple-underscore is the separator; single underscores within host
    or disease become spaces. Trailing commas and whitespace are stripped
    so that ``Corn_(maize)___Common_rust_`` parses cleanly.
    """
    if "___" not in class_dir_name:
        raise ValueError(f"Unexpected class name format: {class_dir_name}")
    host_raw, disease_raw = class_dir_name.split("___", 1)
    host = host_raw.replace("_", " ").rstrip(", ")
    disease = disease_raw.replace("_", " ").rstrip(", ")
    return host, disease


def lab_original_filename(image_filename: str) -> str:
    """Strip the Mohanty-applied UUID prefix from a raw/color/ filename.

    Files in raw/color/ are named ``{UUID}___{lab_original_filename}``.
    The filtered_leafmaps/ CSVs key on the lab-original filename, so
    joining requires stripping the UUID prefix.
    """
    if "___" in image_filename:
        return image_filename.split("___", 1)[1]
    return image_filename


def clone_upstream(target_dir: Path) -> Path:
    """Shallow-clone the upstream PV repo. Returns path to the repo root."""
    print(f"Cloning {UPSTREAM_REPO} (shallow) to {target_dir} ...")
    subprocess.run(
        ["git", "clone", "--depth", "1", UPSTREAM_REPO, str(target_dir)],
        check=True,
    )
    color_dir = target_dir / UPSTREAM_COLOR_SUBDIR
    leafmaps_dir = target_dir / UPSTREAM_LEAFMAPS_SUBDIR
    if not color_dir.is_dir():
        raise RuntimeError(
            f"Expected {color_dir} after clone — upstream layout may have changed."
        )
    if not leafmaps_dir.is_dir():
        raise RuntimeError(
            f"Expected {leafmaps_dir} after clone — upstream layout may have changed."
        )
    return target_dir


def get_upstream_commit_sha(upstream_dir: Path) -> str:
    """Return the HEAD commit SHA of the upstream clone."""
    result = subprocess.run(
        ["git", "-C", str(upstream_dir), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def load_leafmap(leafmap_csv: Path) -> dict[str, int]:
    """Read a filtered_leafmaps CSV and return a dict of filename to Leaf #.

    The CSV has two columns: 'File Name' and 'Leaf #'. Rows with non-numeric
    'Leaf #' values (e.g. 'n/a', empty) are skipped — those images fall
    through to the synthetic-leaf_id path in build_metadata, the same way
    images that aren't in the leafmap at all do.
    """
    mapping: dict[str, int] = {}
    with open(leafmap_csv, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row["File Name"].strip()
            raw_leaf = row["Leaf #"].strip()
            try:
                leaf_num = int(float(raw_leaf))
            except ValueError:
                # 'n/a', empty, or other non-numeric. Skip — the image
                # will be reported by build_metadata's "missing entries"
                # warning, treated as ungrouped within this class.
                continue
            mapping[filename] = leaf_num
    return mapping


def list_images_in_class(class_dir: Path) -> list[Path]:
    """Return sorted, case-insensitive list of JPG files in a class directory.

    Filters by suffix rather than glob pattern to avoid double-counting on
    case-insensitive filesystems (where glob('*.JPG') and glob('*.jpg')
    return the same files).
    """
    images = [
        p for p in class_dir.iterdir()
        if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg")
    ]
    return sorted(images)


def build_metadata(
    upstream_color_dir: Path,
    upstream_leafmaps_dir: Path,
) -> tuple[list[dict], dict]:
    """Walk upstream classes, build per-image metadata rows + aggregate stats.

    Returns
    -------
    metadata_rows : list of dicts
        One dict per image. Two path keys are populated:
            image_path_abs — absolute path on disk (for HF Image() feature)
            image_path_rel — relative path (for local CSV / display)
        Plus the seven schema columns: class_label, class_idx, host,
        disease, split (None at this stage), leaf_id, leaf_grouped.
    stats : dict
        Aggregate statistics used for provenance recording.
    """
    class_dirs = sorted(p for p in upstream_color_dir.iterdir() if p.is_dir())
    if len(class_dirs) != 38:
        print(
            f"Warning: expected 38 PV classes, found {len(class_dirs)}. "
            f"Continuing — verify this is intentional before publishing."
        )

    # First pass: alphabetical class_label -> class_idx mapping.
    class_labels = sorted(p.name for p in class_dirs)
    class_idx_map = {label: idx for idx, label in enumerate(class_labels)}

    rows: list[dict] = []
    image_counts: dict[str, int] = {}
    ungrouped_classes: list[str] = []

    for class_dir in class_dirs:
        class_label = class_dir.name
        host, disease = parse_class_name(class_label)
        class_idx = class_idx_map[class_label]

        images = list_images_in_class(class_dir)
        if not images:
            print(f"Warning: no JPGs in {class_label}, skipping.")
            continue

        image_counts[class_label] = len(images)

        leafmap_path = upstream_leafmaps_dir / f"{class_label}.csv"
        class_has_leafmap = leafmap_path.exists()
        leafmap = load_leafmap(leafmap_path) if class_has_leafmap else {}

        if not class_has_leafmap:
            ungrouped_classes.append(class_label)
        else:
            image_lookup_keys = {lab_original_filename(img.name) for img in images}
            mapped_names = set(leafmap.keys())
            missing = image_lookup_keys - mapped_names
            extra = mapped_names - image_lookup_keys
            if missing:
                print(
                    f"Warning: {class_label} has {len(missing)} image(s) "
                    f"without leafmap entries. Treating those as ungrouped "
                    f"within an otherwise grouped class."
                )
            if extra:
                print(
                    f"Note: {class_label}'s leafmap references "
                    f"{len(extra)} filename(s) not present in raw/color/. "
                    f"Ignored."
                )

        for img in images:
            lookup_key = lab_original_filename(img.name)
            if class_has_leafmap and lookup_key in leafmap:
                leaf_id = f"{class_label}::leaf_{leafmap[lookup_key]}"
                row_leaf_grouped = True
            else:
                leaf_id = f"{class_label}::{img.name}"
                row_leaf_grouped = False

            rows.append({
                # Path keys — only image_path_abs goes into the HF Dataset
                "image_path_abs": str(img),
                "image_path_rel": f"color/{class_label}/{img.name}",
                # Schema columns (matching legacy metadata.csv)
                "class_label":  class_label,
                "class_idx":    class_idx,
                "host":         host,
                "disease":      disease,
                "split":        None,  # filled in by assign_splits()
                "leaf_id":      leaf_id,
                "leaf_grouped": row_leaf_grouped,
            })

    if len(ungrouped_classes) != EXPECTED_UNGROUPED_COUNT:
        print(
            f"Warning: expected {EXPECTED_UNGROUPED_COUNT} ungrouped classes, "
            f"found {len(ungrouped_classes)}: {sorted(ungrouped_classes)}. "
            f"Upstream may have changed; verify before publishing."
        )

    stats = {
        "n_images_total":         len(rows),
        "n_classes":              len(image_counts),
        "image_counts_per_class": dict(sorted(image_counts.items())),
        "n_grouped_classes":      len(image_counts) - len(ungrouped_classes),
        "n_ungrouped_classes":    len(ungrouped_classes),
        "ungrouped_classes":      sorted(ungrouped_classes),
    }

    return rows, stats


def assign_splits(rows: list[dict], seed: int, train_ratio: float) -> None:
    """In-place assign 'split' = 'train' or 'test' to each row.

    Stratified by class, grouped by leaf_id: within each class, the unique
    leaf_ids are shuffled with `seed` and split train_ratio / (1 - train_ratio).
    Every image inherits its leaf's split assignment.

    This is the standard leak-free split for image classification: the same
    leaf never appears in both train and test, and every class is represented
    at roughly the chosen ratio.
    """
    rng = random.Random(seed)
    rows_by_class: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        rows_by_class[row["class_label"]].append(row)

    # Sorted iteration keeps the rng draws deterministic regardless of
    # dict insertion order.
    for class_label in sorted(rows_by_class.keys()):
        class_rows = rows_by_class[class_label]
        unique_leaves = sorted({r["leaf_id"] for r in class_rows})
        shuffled = unique_leaves[:]
        rng.shuffle(shuffled)
        n_train = int(round(len(shuffled) * train_ratio))
        train_leaves = set(shuffled[:n_train])
        for row in class_rows:
            row["split"] = "train" if row["leaf_id"] in train_leaves else "test"


# ==========================================================================
# Tiny variant
# ==========================================================================

def stratified_subsample(
    rows: list[dict],
    n_per_class: int,
    seed: int,
) -> list[dict]:
    """Return a subsample of rows with at most n_per_class per class.

    Sampling happens at the image level, after splits are assigned. The
    resulting subsample has both train and test rows in proportions
    roughly matching the full dataset (within sampling noise). Leaf
    metadata is preserved on each row, but the tiny variant does not
    try to be a faithful leaf-grouped subsample — at 50 images per class,
    sampling whole leaves would leave too many leaves with one image.
    """
    rng = random.Random(seed)
    rows_by_class: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        rows_by_class[row["class_label"]].append(row)

    out: list[dict] = []
    for class_label in sorted(rows_by_class.keys()):
        class_rows = rows_by_class[class_label]
        k = min(n_per_class, len(class_rows))
        sampled = rng.sample(class_rows, k)
        out.extend(sampled)
    return sorted(out, key=lambda r: r["image_path_rel"])


# ==========================================================================
# HF Dataset construction and push
# ==========================================================================

def build_hf_dataset(rows: list[dict]):
    """Construct an HF Dataset from the metadata rows.

    The Image() feature on the 'image' column tells the datasets library
    to treat the values as file paths and read their bytes when the
    dataset is serialized. After push_to_hub, those bytes live inline
    in Parquet shards and the local paths are no longer referenced.
    """
    # Local import keeps the module importable without datasets installed
    # (useful for testing the metadata-construction logic in isolation).
    from datasets import Dataset, Features, Image, Value

    data = {
        "image":        [r["image_path_abs"] for r in rows],
        "class_label":  [r["class_label"]    for r in rows],
        "class_idx":    [r["class_idx"]      for r in rows],
        "host":         [r["host"]           for r in rows],
        "disease":      [r["disease"]        for r in rows],
        "split":        [r["split"]          for r in rows],
        "leaf_id":      [r["leaf_id"]        for r in rows],
        "leaf_grouped": [r["leaf_grouped"]   for r in rows],
    }

    features = Features({
        "image":        Image(),
        "class_label":  Value("string"),
        "class_idx":    Value("int32"),
        "host":         Value("string"),
        "disease":      Value("string"),
        "split":        Value("string"),
        "leaf_id":      Value("string"),
        "leaf_grouped": Value("bool"),
    })

    return Dataset.from_dict(data, features=features)


def push_dataset(ds, repo: str, tag: str, commit_message: str):
    """Push the dataset to HF Hub and create a version tag.

    The push creates a commit on the dataset repo's main branch. The
    tag is then attached to that specific commit, so revision=tag is
    pinnable for the lifetime of the repo.
    """
    from huggingface_hub import HfApi

    print(f"Pushing {len(ds)} rows to {repo} ...")
    commit_info = ds.push_to_hub(repo, commit_message=commit_message)
    print(f"  pushed, commit oid={commit_info.oid}")

    print(f"Tagging commit as {tag} ...")
    HfApi().create_tag(
        repo_id=repo,
        repo_type="dataset",
        tag=tag,
        revision=commit_info.oid,
    )
    print(f"  tagged.")
    return commit_info


# ==========================================================================
# Local debug artifacts (not pushed)
# ==========================================================================

def write_metadata_csv(rows: list[dict], dest: Path) -> None:
    """Write a local metadata.csv for inspection.

    Same 8 columns as the legacy tarball schema, with 'image_path' being
    the relative path under 'color/'. The HF dataset itself uses image
    bytes inline rather than paths; this CSV is only for local diffing
    and sanity-checking before push.
    """
    columns = [
        "image_path", "class_label", "class_idx", "host", "disease",
        "split", "leaf_id", "leaf_grouped",
    ]
    csv_rows = [{**r, "image_path": r["image_path_rel"]} for r in rows]
    sorted_rows = sorted(csv_rows, key=lambda r: r["image_path"])
    with open(dest, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted_rows)


def write_provenance_json(
    rows: list[dict],
    stats: dict,
    upstream_commit_sha: str,
    variant: str,
    dest: Path,
) -> None:
    """Write a local provenance.json for diff-checking across builds.

    Records the upstream commit, seeds, and counts that should also
    appear in the dataset card README. Not pushed to HF directly — the
    dataset card carries the same info in narrative form.
    """
    n_train = sum(1 for r in rows if r["split"] == "train")
    n_test = sum(1 for r in rows if r["split"] == "test")

    # Recompute per-class image counts from the (possibly subsampled) rows
    # so the provenance matches what's actually being pushed.
    image_counts = dict(sorted(Counter(r["class_label"] for r in rows).items()))

    provenance = {
        "build_script_version":   BUILD_SCRIPT_VERSION,
        "variant":                variant,
        "upstream_repo":          UPSTREAM_REPO,
        "upstream_commit_sha":    upstream_commit_sha,
        "n_images_total":         len(rows),
        "n_classes":              stats["n_classes"],
        "image_counts_per_class": image_counts,
        "split_seed":             SPLIT_SEED,
        "split_ratio":            [TRAIN_RATIO, round(1.0 - TRAIN_RATIO, 4)],
        "n_train_images":         n_train,
        "n_test_images":          n_test,
        "n_grouped_classes":      stats["n_grouped_classes"],
        "n_ungrouped_classes":    stats["n_ungrouped_classes"],
        "ungrouped_classes":      stats["ungrouped_classes"],
    }
    if variant == "tiny":
        provenance["subsample_seed"] = SUBSAMPLE_SEED
        provenance["tiny_images_per_class"] = TINY_IMAGES_PER_CLASS

    with open(dest, "w") as f:
        json.dump(provenance, f, indent=2, sort_keys=True)
        f.write("\n")


# ==========================================================================
# Orchestrator
# ==========================================================================

def run_build(
    upstream_root: Path,
    output_dir: Path,
    variant: str,
) -> tuple[object, dict]:
    """Build the HF Dataset object plus a small provenance summary.

    Returns
    -------
    ds : datasets.Dataset
        Ready to be pushed (or inspected, in --dry-run mode).
    provenance : dict
        Minimal summary printed at end-of-run.
    """
    upstream_color = upstream_root / UPSTREAM_COLOR_SUBDIR
    upstream_leafmaps = upstream_root / UPSTREAM_LEAFMAPS_SUBDIR
    if not upstream_color.is_dir():
        print(f"Error: {upstream_color} doesn't exist.", file=sys.stderr)
        sys.exit(1)
    if not upstream_leafmaps.is_dir():
        print(f"Error: {upstream_leafmaps} doesn't exist.", file=sys.stderr)
        sys.exit(1)

    commit_sha = get_upstream_commit_sha(upstream_root)
    print(f"Upstream commit: {commit_sha}")

    print("Building metadata ...")
    rows, stats = build_metadata(upstream_color, upstream_leafmaps)
    print(
        f"  {stats['n_images_total']} images across {stats['n_classes']} classes "
        f"({stats['n_grouped_classes']} grouped, "
        f"{stats['n_ungrouped_classes']} ungrouped)"
    )

    print(f"Assigning leaf-grouped train/test split (seed={SPLIT_SEED}) ...")
    assign_splits(rows, seed=SPLIT_SEED, train_ratio=TRAIN_RATIO)

    if variant == "tiny":
        print(
            f"Subsampling to {TINY_IMAGES_PER_CLASS} images per class "
            f"(seed={SUBSAMPLE_SEED}) ..."
        )
        rows = stratified_subsample(
            rows,
            n_per_class=TINY_IMAGES_PER_CLASS,
            seed=SUBSAMPLE_SEED,
        )

    n_train = sum(1 for r in rows if r["split"] == "train")
    n_test = sum(1 for r in rows if r["split"] == "test")
    print(f"  Final row count: {len(rows)} ({n_train} train, {n_test} test)")

    # Local debug artifacts. Not pushed; useful for diffing builds.
    metadata_csv = output_dir / f"metadata_{variant}.csv"
    provenance_json = output_dir / f"provenance_{variant}.json"
    print(f"Writing {metadata_csv} (local, not pushed) ...")
    write_metadata_csv(rows, metadata_csv)
    print(f"Writing {provenance_json} (local, not pushed) ...")
    write_provenance_json(rows, stats, commit_sha, variant, provenance_json)

    print("Constructing HF Dataset ...")
    ds = build_hf_dataset(rows)

    provenance = {
        "upstream_commit_sha": commit_sha,
        "n_rows":              len(rows),
        "n_train":             n_train,
        "n_test":              n_test,
        "variant":             variant,
    }
    return ds, provenance


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="HF dataset repo (e.g. geraldmc/plantvillage-full)",
    )
    parser.add_argument(
        "--tag",
        required=True,
        help="Version tag (e.g. v0.1.0)",
    )
    parser.add_argument(
        "--variant",
        choices=["full", "tiny"],
        default="full",
        help="Which variant to build (default: full)",
    )
    parser.add_argument(
        "--upstream-dir",
        type=Path,
        default=None,
        help=(
            "Path to an existing local clone of spMohanty/PlantVillage-Dataset. "
            "If omitted, the script clones into a temp directory."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build"),
        help="Where to write local debug artifacts (default: ./build/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build everything but skip the push to HF Hub.",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.upstream_dir is not None:
        ds, provenance = run_build(args.upstream_dir, args.output_dir, args.variant)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            upstream_root = clone_upstream(Path(tmp) / "pv")
            ds, provenance = run_build(upstream_root, args.output_dir, args.variant)

    print()
    print("=" * 60)
    print(f"Variant:           {args.variant}")
    print(f"Repo:              {args.repo}")
    print(f"Tag:               {args.tag}")
    print(f"Rows:              {provenance['n_rows']}")
    print(f"Train / test:      {provenance['n_train']} / {provenance['n_test']}")
    print(f"Upstream commit:   {provenance['upstream_commit_sha']}")
    print("=" * 60)
    print()

    if args.dry_run:
        print("Dry run — skipping push to HF Hub.")
        print(f"Local debug artifacts written to: {args.output_dir}")
        return

    commit_message = (
        f"Release {args.tag} (variant={args.variant}, "
        f"upstream={provenance['upstream_commit_sha'][:8]})"
    )
    push_dataset(ds, args.repo, args.tag, commit_message)

    print()
    print("Done. Verify with:")
    print("  from datasets import load_dataset")
    print(f"  ds = load_dataset('{args.repo}', revision='{args.tag}')")


if __name__ == "__main__":
    main()
