# CLAUDE.md Update — Data Release Sections

*Proposed replacement for the "Cutting a data release" section and a small
addition to "Open decisions," reflecting the PV-full migration to Hugging
Face Hub. Two changes total; both shown as full replacement blocks below.*

---

## Summary of changes

- **"Cutting a data release"** — rewrite the whole section. Two release
  flows now exist (GitHub tarball, HF Hub); the section presents both
  side by side under a lookup table that maps each product to its
  platform. The existing tarball steps are preserved nearly verbatim;
  the HF steps are new.
- **"Open decisions"** — add one bullet about PD's release platform,
  which becomes a real decision when PD curation starts.

No other section of CLAUDE.md needs to change. The package-status,
glossary, repository-conventions, and library-specifics blocks remain
correct.

---

## Change 1 — Replace the entire "Cutting a data release" section

Replace the existing section (everything from `## Cutting a data release`
through the end of step 5 of the current procedure) with:

```markdown
## Cutting a data release

Data products are hosted on one of two platforms — GitHub releases (a
versioned tarball with a SHA256 the loader verifies) or Hugging Face Hub
(versioned Parquet-shard datasets the `datasets` library fetches). The
choice is per-product, based on access pattern: tarballs work fine for
medium-sized, all-at-once releases; HF works better for image datasets
where many-small-file extraction on Drive would otherwise be the
bottleneck.

Existing products and their platforms:

| Product | Platform | Tag scheme |
|---|---|---|
| Orientation sample | GitHub release | `data-orientation-vX.Y.Z` |
| PlantVillage full image dataset | Hugging Face Hub | `vX.Y.Z` on `geraldmc/plantvillage-full` |
| PlantVillage tiny image dataset (debug-grade subset) | Hugging Face Hub | `vX.Y.Z` on `geraldmc/plantvillage-tiny` |
| PlantDoc image dataset (not yet built) | Undecided | — |
| PlantVillage pre-extracted features (deferred) | GitHub release | `data-pv-features-vX.Y.Z` |

The PlantDoc release platform is undecided — see Open decisions.

### GitHub release flow (tarball)

Used by the orientation sample and the deferred PV-features release.

1. Build the tarball: `python scripts/build_<product>_tarball.py`
2. Note the SHA256 from the script's output box
3. Cut the release on GitHub:
   - Tag: per-product, as in the table above (always with the `data-`
     prefix and a product qualifier)
   - Drag the tarball into Assets
   - **Click "Publish release," not "Save draft"** (drafts are not
     publicly downloadable)
4. Update the matching `_<PRODUCT>_URL` / `_<PRODUCT>_SHA256` constants
   in `irilab2026/data.py`
5. Commit, push, smoke-test on a fresh Colab runtime

### Hugging Face Hub flow

Used by `plantvillage-full` and `plantvillage-tiny`. Both variants are
built and pushed by a single script.

1. Build and push: `python scripts/build_pv_full_hf.py`
   - The script clones the upstream source, constructs the metadata and
     HF `Dataset` objects for both `full` and `tiny` variants, calls
     `push_to_hub` for each, and tags the revision.
   - Authentication: requires a one-time `huggingface-cli login`
     (write-scoped). The token persists in
     `~/.cache/huggingface/token`; students need no auth at all to
     read.
   - Local debug artifacts (`metadata_*.csv`, `provenance_*.json`) land
     in `build/` for diff-checking; these are not pushed to HF.
2. Verify the push: visit
   `https://huggingface.co/datasets/geraldmc/plantvillage-full` (and
   the `-tiny` repo); confirm the new tag is present in the file tree's
   revision dropdown.
3. Update `_PV_HF_REVISION` in `irilab2026/data.py` to the new tag.
4. Commit, push, smoke-test on a fresh Colab runtime by calling
   `iri.load_plantvillage(variant="tiny")` first (smaller download),
   then `iri.load_plantvillage()` (full variant).

The HF flow does not produce a SHA256 or a downloadable tarball asset.
Reproducibility lives in the Parquet shards on HF (immutable under
content-addressed storage) and in the revision tag pinned by
`_PV_HF_REVISION`. Tags are nominally mutable, so namespace discipline
(single-author `geraldmc/`) is what makes them effectively immutable
for this project; treat the act of retagging as you'd treat
force-pushing to a release branch.
```

---

## Change 2 — Add one bullet to "Open decisions"

Add this bullet to the existing "Open decisions" section, after the
existing jupytext and `r1_orientation.ipynb` bullets:

```markdown
- **PlantDoc release platform.** Whether to ship `plantdoc` via GitHub
  release (consistent with orientation) or Hugging Face Hub (consistent
  with `plantvillage-full`). PD has the same many-small-file property
  that drove the PV-full migration to HF, so HF is the structural fit.
  But PD is smaller (~2,500 images vs PV's 54k), so the Drive-extract
  pain may be tolerable. Decide when PD curation starts.
```

---

## Things I considered but did not change

- **The opening line about the eventual move to pinned tags** (in the
  "Working style" section). That paragraph references "pinned tags" for
  the library install line, which is still TBD. The data-release tag
  story is separate from the library-release tag story; nothing in the
  library install-line policy changed.

- **The "Library specifics worth knowing before editing" block.** None
  of the points there are affected by the HF migration — the cache
  directory rule still applies, the GSE→stress mapping is unchanged,
  `setup()`'s asymmetric GPU check is unchanged, and the
  `probe_to_agi()` return type is unchanged. The HF cache lives under
  `cache_dir()` (in a `datasets/` subdirectory HF creates), but that's
  a layout detail HF manages, not something the rule needs to call out.

- **The Project status block.** The current `v0.2.0` status text
  describes R1 progress and the Distribution policy. Neither needs an
  edit for the loader rewrite. A status bump (e.g. to `v0.3.0`) would
  happen when a library release is cut to pin this loader — that's a
  separate step deferred from this chat.

- **A "cleanup of orphan artifacts" subsection.** The cleanup we did
  today (orphan Drive directory, `data-pv-full-v0.1.0` release/tag,
  `data-v0.1.0` tag) was a one-time consequence of the migration, not
  a recurring procedure. Cleanup belongs in the chat closeout doc,
  not in CLAUDE.md.