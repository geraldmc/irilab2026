#!/usr/bin/env python3
"""Build the PlantVillage full tarball.

One-time authoring script. Mirrors the upstream PlantVillage color image
dataset, attaches leaf-grouping metadata from filtered_leafmaps/, produces
a deterministic leaf-grouped 80/20 train/test split, and tars everything
plus a manifest.

The output tarball is uploaded as a release asset on the irilab2026 repo
(release tag: data-pv-full-vX.Y.Z) and its SHA256 is pinned in
irilab2026/data.py as _PV_FULL_SHA256.

Usage:
    # Clone upstream into a temp dir (slower but self-contained)
    python scripts/build_pv_full_tarball.py --output-dir build/

    # Or use an existing local clone (faster)
    python scripts/build_pv_full_tarball.py \\
        --output-dir build/ --upstream-dir /path/to/PlantVillage-Dataset

Requirements:
    Python 3.9+ (no third-party packages — uses only the standard library)
    git on PATH

The upstream PlantVillage repo (spMohanty/PlantVillage-Dataset) ships
roughly 2 GB on disk across three image variants; this script uses only
the color variant (~1.5 GB). If --upstream-dir is omitted, the script
clones shallowly into a temp directory and cleans up afterward.

Determinism:
    The tarball is byte-stable given the same upstream commit. Image
    bytes are streamed directly from the upstream clone (no copy step).
    Member order is sorted by arcname; mtimes, uids, gids, and names
    are zeroed. The leaf-grouped train/test split is seeded by
    SPLIT_SEED below. Running the script twice on the same upstream
    commit yields the same SHA256.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import subprocess
import sys
import tarfile
import tempfile
from collections import defaultdict
from pathlib import Path

# Reproducibility seed for the leaf-grouped 80/20 split. Changing this
# changes which leaves go to train vs test, which changes the tarball
# bytes and the SHA256 every student's loader checks. Don't change
# casually — if you do, bump the data release version too.
SPLIT_SEED = 20260518
TRAIN_RATIO = 0.8

# Bump when the script's output format changes meaningfully (new column,
# different split logic, different layout). Recorded in manifest.json
# so downstream code can detect mismatches.
BUILD_SCRIPT_VERSION = "0.1.0"

UPSTREAM_REPO = "https://github.com/spMohanty/PlantVillage-Dataset.git"
UPSTREAM_COLOR_SUBDIR = "raw/color"
UPSTREAM_LEAFMAPS_SUBDIR = "leaf_grouping/filtered_leafmaps"

# Top-level directory inside the tarball. The loader extracts to its
# cache root and this prefix creates the wrapper dir automatically,
# so extraction can't pollute the parent directory.
WRAPPER_DIR = "plantvillage_full"

# Sanity-check expectation: how many classes lack leafmap metadata.
# Per upstream as of 2026-05-18, eight classes are ungrouped. The
# script detects ungrouped classes dynamically; this is just a
# warning threshold in case upstream changes.
EXPECTED_UNGROUPED_COUNT = 8


def parse_class_name(class_dir_name: str) -> tuple[str, str]:
    """Parse a PV class directory name into (host, disease).

    PV class directories follow the convention ``Host___Disease``, e.g.
    ``Apple___Apple_scab`` or ``Tomato___healthy``. The triple-underscore
    is the separator; single underscores within host or disease become
    spaces. Trailing commas and whitespace are stripped so that
    ``Corn_(maize)___Common_rust_`` parses cleanly.
    """
    if "___" not in class_dir_name:
        raise ValueError(f"Unexpected class name format: {class_dir_name}")
    host_raw, disease_raw = class_dir_name.split("___", 1)
    host = host_raw.replace("_", " ").rstrip(", ")
    disease = disease_raw.replace("_", " ").rstrip(", ")
    return host, disease

def lab_original_filename(image_filename: str) -> str:
    """Strip the Mohanty-applied UUID prefix from a raw/color/ filename.

    Files in raw/color/ are named ``{UUID}___{lab_original_filename}``
    where the UUID was applied by Mohanty when staging the dataset and
    the lab-original filename is what the source labs (FREC, Rutgers,
    etc.) used. The filtered_leafmaps/ CSVs key on the lab-original
    filename, so joining requires stripping the UUID prefix.
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
    """Read a filtered_leafmaps CSV and return a dict mapping filename to Leaf #.

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
        One dict per image. Keys are the 8 metadata.csv columns. The
        'split' value is None at this point; assign_splits() fills it in.
    stats : dict
        Aggregate statistics for the manifest.
    """
    class_dirs = sorted(p for p in upstream_color_dir.iterdir() if p.is_dir())
    if len(class_dirs) != 38:
        print(
            f"Warning: expected 38 PV classes, found {len(class_dirs)}. "
            f"Continuing — verify this is intentional before publishing."
        )

    # First pass: build class_label -> class_idx mapping. Alphabetical sort
    # over the canonical folder names, indexed 0..N-1. Per pre-commit 2,
    # this mapping is baked into the CSV; the loader does not recompute it.
    class_labels = sorted(p.name for p in class_dirs)
    class_idx_map = {label: idx for idx, label in enumerate(class_labels)}

    # Second pass: walk each class, build rows.
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

        # Try to load a leafmap for this class. Eight classes (per upstream
        # as of build time) have no leafmap CSV; for those, each image
        # gets a synthetic per-image leaf_id and leaf_grouped=False.
        leafmap_path = upstream_leafmaps_dir / f"{class_label}.csv"
        class_has_leafmap = leafmap_path.exists()
        leafmap = load_leafmap(leafmap_path) if class_has_leafmap else {}

        if not class_has_leafmap:
            ungrouped_classes.append(class_label)
        else:
            # Sanity-check coverage. A grouped class with images missing
            # from its leafmap is not catastrophic — those rows fall through
            # to the synthetic-leaf_id path below — but it's worth a note.
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
                # Either an ungrouped class, or a grouped class with this
                # specific image missing from its leafmap. Synthesize a
                # per-image leaf_id so the split logic still works.
                leaf_id = f"{class_label}::{img.name}"
                row_leaf_grouped = False

            rows.append({
                "image_path": f"color/{class_label}/{img.name}",
                "class_label": class_label,
                "class_idx": class_idx,
                "host": host,
                "disease": disease,
                "split": None,  # filled in by assign_splits()
                "leaf_id": leaf_id,
                "leaf_grouped": row_leaf_grouped,
            })

    # Soft sanity check on ungrouped class count.
    if len(ungrouped_classes) != EXPECTED_UNGROUPED_COUNT:
        print(
            f"Warning: expected {EXPECTED_UNGROUPED_COUNT} ungrouped classes "
            f"(per upstream as of build time), found {len(ungrouped_classes)}: "
            f"{sorted(ungrouped_classes)}. Upstream may have changed; verify "
            f"before publishing."
        )

    stats = {
        "n_images_total": len(rows),
        "n_classes": len(image_counts),
        "image_counts_per_class": dict(sorted(image_counts.items())),
        "n_grouped_classes": len(image_counts) - len(ungrouped_classes),
        "n_ungrouped_classes": len(ungrouped_classes),
        "ungrouped_classes": sorted(ungrouped_classes),
    }

    return rows, stats


def assign_splits(rows: list[dict], seed: int, train_ratio: float) -> None:
    """In-place assign 'split' = 'train' or 'test' to each row.

    Stratified by class, grouped by leaf_id: within each class, the unique
    leaf_ids in that class are shuffled with `seed` and split train_ratio /
    (1 - train_ratio). Every image inherits its leaf's split assignment.

    This is the standard leak-free split for image classification: the
    same leaf never appears in both train and test, and every class is
    represented at roughly the chosen ratio (no class can collapse to
    0 train or 0 test by chance).
    """
    rng = random.Random(seed)

    # Group rows by class_label so we can stratify.
    rows_by_class: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        rows_by_class[row["class_label"]].append(row)

    # Iterate classes in sorted order so the rng draws are deterministic
    # regardless of dict insertion order.
    for class_label in sorted(rows_by_class.keys()):
        class_rows = rows_by_class[class_label]
        unique_leaves = sorted({r["leaf_id"] for r in class_rows})

        shuffled = unique_leaves[:]
        rng.shuffle(shuffled)

        n_train = int(round(len(shuffled) * train_ratio))
        train_leaves = set(shuffled[:n_train])

        for row in class_rows:
            row["split"] = "train" if row["leaf_id"] in train_leaves else "test"


def write_metadata_csv(rows: list[dict], dest: Path) -> None:
    """Write metadata.csv with the 8 settled columns in fixed order.

    Rows are sorted by image_path for byte-stable output.
    """
    columns = [
        "image_path",
        "class_label",
        "class_idx",
        "host",
        "disease",
        "split",
        "leaf_id",
        "leaf_grouped",
    ]
    sorted_rows = sorted(rows, key=lambda r: r["image_path"])
    with open(dest, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(sorted_rows)


def write_manifest(
    rows: list[dict],
    stats: dict,
    upstream_commit_sha: str,
    dest: Path,
) -> None:
    """Write manifest.json with provenance and reproducibility info.

    Deliberately omits build date: including it would defeat byte
    stability (same upstream commit + same script + same seed must
    produce the same SHA256). The GitHub release's creation date
    serves as the "when" record instead.
    """
    n_train = sum(1 for r in rows if r["split"] == "train")
    n_test = sum(1 for r in rows if r["split"] == "test")

    manifest = {
        "build_script_version": BUILD_SCRIPT_VERSION,
        "upstream_repo": UPSTREAM_REPO,
        "upstream_commit_sha": upstream_commit_sha,
        "n_images_total": stats["n_images_total"],
        "n_classes": stats["n_classes"],
        "image_counts_per_class": stats["image_counts_per_class"],
        "split_seed": SPLIT_SEED,
        "split_ratio": [TRAIN_RATIO, round(1.0 - TRAIN_RATIO, 4)],
        "n_train_images": n_train,
        "n_test_images": n_test,
        "n_grouped_classes": stats["n_grouped_classes"],
        "n_ungrouped_classes": stats["n_ungrouped_classes"],
        "ungrouped_classes": stats["ungrouped_classes"],
    }

    with open(dest, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")  # trailing newline for clean POSIX text


def make_tarball(
    upstream_color_dir: Path,
    aux_files: dict[str, Path],
    output_path: Path,
) -> None:
    """Create a deterministic gzipped tarball.

    Image bytes are streamed directly from upstream_color_dir — no
    intermediate copy step. aux_files maps arcname suffix (under the
    wrapper dir) to source path for metadata.csv and manifest.json.

    Members are sorted by arcname; mtimes, uids, gids, and ownership
    names are zeroed for byte-stable output across runs and machines.
    """
    print(f"Writing tarball to {output_path} ...")

    # Build the full (arcname, source_path) list. Aux files first
    # (logically), then images. Final order is determined by sorting.
    members: list[tuple[str, Path]] = []

    for arcname_suffix, src in aux_files.items():
        arcname = f"{WRAPPER_DIR}/{arcname_suffix}"
        members.append((arcname, src))

    for class_dir in sorted(upstream_color_dir.iterdir()):
        if not class_dir.is_dir():
            continue
        for img in list_images_in_class(class_dir):
            arcname = f"{WRAPPER_DIR}/color/{class_dir.name}/{img.name}"
            members.append((arcname, img))

    # Sort by arcname for byte-stable order across runs.
    members.sort(key=lambda pair: pair[0])

    with tarfile.open(output_path, "w:gz") as tf:
        for arcname, src in members:
            ti = tf.gettarinfo(str(src), arcname=arcname)
            # Zero out variable metadata for byte-stable output.
            ti.mtime = 0
            ti.uid = 0
            ti.gid = 0
            ti.uname = ""
            ti.gname = ""
            if ti.isfile():
                with open(src, "rb") as f:
                    tf.addfile(ti, f)
            else:
                tf.addfile(ti)


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_build(upstream_root: Path, output_dir: Path) -> Path:
    """Execute the full build against a given upstream clone root.

    Returns the path to the built tarball.
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
    n_train = sum(1 for r in rows if r["split"] == "train")
    n_test = sum(1 for r in rows if r["split"] == "test")
    print(f"  {n_train} train, {n_test} test")

    metadata_csv = output_dir / "metadata.csv"
    manifest_json = output_dir / "manifest.json"
    print(f"Writing {metadata_csv} ...")
    write_metadata_csv(rows, metadata_csv)
    print(f"Writing {manifest_json} ...")
    write_manifest(rows, stats, commit_sha, manifest_json)

    tarball_path = output_dir / "plantvillage_full.tar.gz"
    make_tarball(
        upstream_color,
        aux_files={
            "metadata.csv": metadata_csv,
            "manifest.json": manifest_json,
        },
        output_path=tarball_path,
    )
    return tarball_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build"),
        help="Where to stage aux files and write the tarball (default: ./build/)",
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
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.upstream_dir is not None:
        tarball_path = run_build(args.upstream_dir, args.output_dir)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            upstream_root = clone_upstream(Path(tmp) / "pv")
            tarball_path = run_build(upstream_root, args.output_dir)

    digest = sha256_of_file(tarball_path)
    size_mb = tarball_path.stat().st_size / (1024 * 1024)

    print()
    print("=" * 60)
    print(f"Tarball:    {tarball_path}")
    print(f"Size:       {size_mb:.2f} MB")
    print(f"SHA256:     {digest}")
    print("=" * 60)
    print()
    print("Next steps:")
    print(f"  1. Add _PV_FULL_URL and _PV_FULL_SHA256 to irilab2026/data.py.")
    print(f"     SHA256: {digest}")
    print(f"  2. Cut a release tagged 'data-pv-full-vX.Y.Z' on the irilab2026 repo.")
    print(f"  3. Attach {tarball_path.name} as a release asset.")
    print(f"  4. Update _PV_FULL_URL in data.py to the new asset URL.")
    print(f"  5. Verify with: curl -L -s -o /dev/null -w '%{{http_code}}\\n' <URL>")


if __name__ == "__main__":
    main()