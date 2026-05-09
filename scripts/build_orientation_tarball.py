"""Build the PlantVillage orientation tarball.

One-time authoring script. Downloads the upstream PlantVillage dataset,
samples a small deterministic subset (~5 images per class), writes a
manifest with full-dataset class counts, and tars the result.

The output tarball is uploaded as a release asset on the irilab2026 repo
(release tag: data-vX.Y.Z) and its SHA256 is pinned in
irilab2026/data.py as _PV_ORIENTATION_SHA256.

Usage:
    python scripts/build_orientation_tarball.py --output-dir build/

Requirements:
    pip install pandas pillow tqdm
    git (for cloning the upstream PV repo)

The upstream PlantVillage repo (spMohanty/PlantVillage-Dataset) is large
(~2 GB). This script clones it shallowly into a temp directory by default;
pass --upstream-dir to point at an existing local clone instead.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import random
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

# Reproducibility: this seed determines which 5 images per class go in
# the tarball. Don't change it casually — changing the seed changes the
# tarball bytes, which changes the SHA256 every student's loader checks.
SAMPLE_SEED = 20260509
SAMPLES_PER_CLASS = 5

UPSTREAM_REPO = "https://github.com/spMohanty/PlantVillage-Dataset.git"
# The "color" subdirectory holds the standard 38-class RGB images.
# (The repo also ships grayscale and segmented variants we don't want here.)
UPSTREAM_SUBDIR = "raw/color"


def parse_class_name(class_dir_name: str) -> tuple[str, str, bool]:
    """Parse a PV class directory name into (host, disease, is_healthy).

    PV class directories follow the convention ``Host___Disease``, e.g.
    ``Apple___Apple_scab`` or ``Tomato___healthy``. The triple-underscore
    is the separator; underscores within host or disease are spaces.
    """
    if "___" not in class_dir_name:
        raise ValueError(f"Unexpected class name format: {class_dir_name}")
    host_raw, disease_raw = class_dir_name.split("___", 1)
    host = host_raw.replace("_", " ")
    disease = disease_raw.replace("_", " ")
    is_healthy = disease_raw.lower() == "healthy"
    return host, disease, is_healthy


def clone_upstream(target_dir: Path) -> Path:
    """Shallow-clone the upstream PV repo. Returns path to the color subdir."""
    print(f"Cloning {UPSTREAM_REPO} (shallow) to {target_dir} ...")
    subprocess.run(
        ["git", "clone", "--depth", "1", UPSTREAM_REPO, str(target_dir)],
        check=True,
    )
    color_dir = target_dir / UPSTREAM_SUBDIR
    if not color_dir.is_dir():
        raise RuntimeError(
            f"Expected {color_dir} after clone — upstream layout may have changed."
        )
    return color_dir


def build_manifest_and_sample(
    upstream_color_dir: Path,
    output_dir: Path,
) -> Path:
    """Walk upstream classes, build manifest, copy sampled images.

    Returns the path to the staged directory ready for tarring.
    """
    staged = output_dir / "plantvillage_orientation"
    if staged.exists():
        shutil.rmtree(staged)
    staged.mkdir(parents=True)

    rng = random.Random(SAMPLE_SEED)

    class_dirs = sorted(p for p in upstream_color_dir.iterdir() if p.is_dir())
    if len(class_dirs) != 38:
        print(
            f"Warning: expected 38 PV classes, found {len(class_dirs)}. "
            f"Continuing — verify this is intentional before publishing."
        )

    manifest_rows = []
    for class_dir in class_dirs:
        all_images = sorted(class_dir.glob("*.JPG")) + sorted(class_dir.glob("*.jpg"))
        if not all_images:
            print(f"Warning: no JPGs found in {class_dir.name}, skipping.")
            continue

        host, disease, is_healthy = parse_class_name(class_dir.name)
        manifest_rows.append({
            "class": class_dir.name,
            "host": host,
            "disease": disease,
            "is_healthy": is_healthy,
            "n_total": len(all_images),
        })

        # Deterministic sample. rng.sample is stateful — order of class_dirs
        # matters, which is why we sort above.
        n_to_sample = min(SAMPLES_PER_CLASS, len(all_images))
        sampled = rng.sample(all_images, n_to_sample)

        dest_class_dir = staged / class_dir.name
        dest_class_dir.mkdir()
        for i, src in enumerate(sorted(sampled)):  # sort for stable filenames
            dest = dest_class_dir / f"img_{i:03d}.jpg"
            shutil.copy2(src, dest)

    # Write manifest.csv (sorted by class for stable byte output)
    manifest_rows.sort(key=lambda r: r["class"])
    manifest_path = staged / "manifest.csv"
    with open(manifest_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["class", "host", "disease", "is_healthy", "n_total"],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"Staged {len(manifest_rows)} classes at {staged}")
    return staged


def make_tarball(staged: Path, output_path: Path) -> None:
    """Create a deterministic-ish gzipped tarball.

    Sorts members by name and zeroes mtimes so re-running the script on
    the same inputs yields the same bytes (and the same SHA256).
    """
    print(f"Writing tarball to {output_path} ...")
    members = sorted(
        staged.rglob("*"),
        key=lambda p: p.relative_to(staged.parent).as_posix(),
    )
    with tarfile.open(output_path, "w:gz") as tf:
        for member_path in members:
            arcname = member_path.relative_to(staged.parent).as_posix()
            ti = tf.gettarinfo(str(member_path), arcname=arcname)
            # Zero out variable metadata for byte-stable output
            ti.mtime = 0
            ti.uid = 0
            ti.gid = 0
            ti.uname = ""
            ti.gname = ""
            if ti.isfile():
                with open(member_path, "rb") as f:
                    tf.addfile(ti, f)
            else:
                tf.addfile(ti)


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build"),
        help="Where to stage files and write the tarball (default: ./build/)",
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
        upstream_color = args.upstream_dir / UPSTREAM_SUBDIR
        if not upstream_color.is_dir():
            print(f"Error: {upstream_color} doesn't exist.", file=sys.stderr)
            sys.exit(1)
        staged = build_manifest_and_sample(upstream_color, args.output_dir)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            upstream_color = clone_upstream(Path(tmp) / "pv")
            staged = build_manifest_and_sample(upstream_color, args.output_dir)

    tarball_path = args.output_dir / "plantvillage_orientation.tar.gz"
    make_tarball(staged, tarball_path)

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
    print(f"  1. Update _PV_ORIENTATION_SHA256 in irilab2026/data.py to:")
    print(f"     {digest}")
    print(f"  2. Cut a release tagged 'data-vX.Y.Z' on the irilab2026 repo")
    print(f"  3. Attach {tarball_path.name} as a release asset")
    print(f"  4. Update _PV_ORIENTATION_URL in irilab2026/data.py to match")


if __name__ == "__main__":
    main()