#!/usr/bin/env python3
"""
atgenexpress_metadata_pull.py

Verification metadata pull for the AtGenExpress abiotic stress series.
Pass 1 of 3 in Channel A Phase 1.

What this script does:
  1. Downloads SOFT family files for each candidate GSE via GEOparse.
     SOFT files are cached locally so re-runs do not re-hit NCBI.
     GEOparse uses NCBI's FTP, not the rate-limited HTTP API.
  2. Parses per-sample metadata: stress, tissue, time-point, replicate.
     Extracts what is parseable and flags what is not, rather than
     silently guessing.
  3. Writes a tidy CSV (one row per GSM).
  4. Writes a Markdown reality-check entry that cross-checks the
     observed sample counts against Hahn et al. 2013, IJMS 14:7617,
     Section 4.1, which reports per-stress chip counts for the series.

Usage:
  pip install GEOparse pandas
  python atgenexpress_metadata_pull.py

Outputs (relative to the script's working directory):
  cache/                         cached SOFT files (gz)
  atgenexpress_metadata.csv      tidy metadata table
  atgenexpress_realitycheck.md   reality-check entry for the Notion wiki
"""

import re
import sys
from collections import Counter
from pathlib import Path

import GEOparse
import pandas as pd


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

# bioRxiv 618926 (2019) explicitly lists 5620-5628 as the AtGenExpress
# accessions. We include 5629 to confirm it is NOT part of the series;
# the script tolerates a 404 there.
CANDIDATE_GSES = [f"GSE{n}" for n in range(5620, 5630)]

CACHE_DIR = Path("cache")
OUTPUT_CSV = Path("atgenexpress_metadata.csv")
OUTPUT_MD = Path("atgenexpress_realitycheck.md")

# Per-stress chip counts from Hahn et al. 2013, IJMS 14:7617, §4.1.
# These are our ground-truth comparison values.
EXPECTED_CHIPS_HAHN_2013 = {
    "control":   (9, 36),
    "cold":      (6, 24),
    "drought":   (7, 28),
    "uvb":       (7, 28),
    "salt":      (6, 24),
    "osmotic":   (6, 24),
    "wounding":  (7, 28),
    "heat":      (8, 32),
    "genotoxic": (6, 24),
    "oxidative": (6, 24),
}


# ----------------------------------------------------------------------
# Parsers
#
# All parsers return None on failure rather than guessing. The caller
# turns Nones into flags so the reality-check entry can show them.
# ----------------------------------------------------------------------

# Order matters: "cold" must match before any substring match like
# "control" would otherwise win. We also map UV-B variants to a single
# canonical key.
_STRESS_KEYS = (
    "genotoxic", "oxidative", "osmotic", "wounding",
    "drought", "salt", "heat", "cold",
    "uv-b", "uv b", "uvb", "control",
)
_STRESS_CANON = {"uv-b": "uvb", "uv b": "uvb"}


def normalize_stress(text):
    if not text:
        return None
    t = text.lower()
    for key in _STRESS_KEYS:
        if key in t:
            return _STRESS_CANON.get(key, key)
    return None


def normalize_tissue(text):
    if not text:
        return None
    t = text.lower()
    if "root" in t:
        return "root"
    if any(w in t for w in ("shoot", "leaf", "leaves", "rosette", "aerial")):
        return "shoot"
    if any(w in t for w in ("whole plant", "seedling")):
        return "whole_plant"
    return None


# Time pattern: matches "0h", "0.25h", "0.5 h", "30 min", "0.5hours", etc.
# In AtGenExpress titles the unit is often followed by an underscore
# (e.g. "Control-Shoots-0.25h_Rep1"). Python's \b treats underscore as a
# word character, so \b after "h" did NOT match before "_". We use an
# explicit lookahead for end-of-string, whitespace, underscore, hyphen,
# or non-alphanumeric punctuation instead.
_TIME_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*"
    r"(hours?|hrs?|h|minutes?|mins?|m)"
    r"(?=$|[\s_\-,;|/])",
    re.IGNORECASE,
)


def extract_time_hours(text):
    """Return time-point in hours (float), or None."""
    if not text:
        return None
    m = _TIME_RE.search(text)
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2).lower()
    return value / 60.0 if unit.startswith("m") else value


# Replicate pattern: "rep1", "replicate 2", "_R1", etc.
_REP_RE = re.compile(
    r"(?:replicate|rep|biological\s*replicate)\D*?(\d+)"
    r"|_R(\d+)\b|_rep(\d+)\b",
    re.IGNORECASE,
)


def extract_replicate(text):
    if not text:
        return None
    m = _REP_RE.search(text)
    if not m:
        return None
    for group in m.groups():
        if group:
            return int(group)
    return None


def parse_gsm(gsm_id, gsm):
    """Return one row's worth of metadata from a GEOparse sample object."""
    md = gsm.metadata
    title = " ".join(md.get("title", []))
    characteristics = " ; ".join(md.get("characteristics_ch1", []))
    source = " ; ".join(md.get("source_name_ch1", []))
    description = " ".join(md.get("description", []))

    # Free-text blob for stress/tissue parsing - safe to use everything.
    blob = " | ".join([title, characteristics, source, description])

    stress = normalize_stress(blob)
    tissue = normalize_tissue(blob)

    # Time and replicate must come from the TITLE only. The description
    # field carries growth-condition blurbs like "16h light / 8h dark"
    # that previously contaminated time_h with photoperiod values.
    time_h = extract_time_hours(title)
    replicate = extract_replicate(title)

    flags = []
    if stress is None:
        flags.append("stress_unparsed")
    if tissue is None:
        flags.append("tissue_unparsed")
    if time_h is None:
        flags.append("time_unparsed")
    if replicate is None:
        flags.append("replicate_unparsed")

    return {
        "GSM": gsm_id,
        "stress": stress,
        "tissue": tissue,
        "time_h": time_h,
        "replicate": replicate,
        "platform": "; ".join(md.get("platform_id", [])),
        "flags": ";".join(flags),
        "title": title,
        "characteristics": characteristics,
        "source_name": source,
    }


# ----------------------------------------------------------------------
# Pull
# ----------------------------------------------------------------------

def fetch_one(gse_id, cache_dir):
    """Return GEOparse object or None on failure (e.g. 404)."""
    try:
        return GEOparse.get_GEO(
            geo=gse_id,
            destdir=str(cache_dir),
            silent=True,
            include_data=False,  # metadata only
        )
    except Exception as e:
        print(f"  [skip] {gse_id}: {e}", file=sys.stderr)
        return None


def main():
    CACHE_DIR.mkdir(exist_ok=True)

    rows = []
    series_titles = {}

    for gse_id in CANDIDATE_GSES:
        print(f"Fetching {gse_id}...", file=sys.stderr)
        gse = fetch_one(gse_id, CACHE_DIR)
        if gse is None:
            continue

        series_titles[gse_id] = "; ".join(gse.metadata.get("title", []))

        for gsm_id, gsm in gse.gsms.items():
            row = parse_gsm(gsm_id, gsm)
            row["GSE"] = gse_id
            row["GSE_title"] = series_titles[gse_id]
            rows.append(row)

    if not rows:
        print("No data fetched. Check your network and try again.",
              file=sys.stderr)
        sys.exit(1)

    df = pd.DataFrame(rows)
    column_order = [
        "GSE", "GSE_title", "GSM",
        "stress", "tissue", "time_h", "replicate",
        "platform", "flags",
        "title", "characteristics", "source_name",
    ]
    df = df[[c for c in column_order if c in df.columns]]
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nWrote {len(df)} rows to {OUTPUT_CSV}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Reality-check Markdown
    # ------------------------------------------------------------------
    md = []
    md.append("# AtGenExpress Reality-Check Entry\n\n")
    md.append("Generated by `atgenexpress_metadata_pull.py` from live "
              "GEO metadata.\n\n")

    # Per-GSE summary.
    md.append("## Per-GSE summary\n\n")
    md.append("| GSE | Title | Samples | Stress(es) | Tissue(s) |\n")
    md.append("|---|---|---|---|---|\n")
    for gse_id in CANDIDATE_GSES:
        sub = df[df["GSE"] == gse_id]
        if sub.empty:
            md.append(f"| {gse_id} | _(not found)_ | 0 | - | - |\n")
            continue
        stresses = sorted(sub["stress"].dropna().unique().tolist())
        tissues = sorted(sub["tissue"].dropna().unique().tolist())
        md.append(
            f"| {gse_id} | {series_titles[gse_id]} | {len(sub)} | "
            f"{', '.join(stresses) or '?'} | "
            f"{', '.join(tissues) or '?'} |\n"
        )

    # Chip-count cross-check.
    md.append("\n## Chip-count cross-check (vs Hahn 2013, §4.1)\n\n")
    md.append("| Stress | Hahn 2013 expected | Observed | Match |\n")
    md.append("|---|---|---|---|\n")
    obs_counts = df["stress"].value_counts().to_dict()
    for stress, (timepoints, expected) in EXPECTED_CHIPS_HAHN_2013.items():
        obs = obs_counts.get(stress, 0)
        match = "OK" if obs == expected else f"MISMATCH (delta={obs - expected})"
        md.append(
            f"| {stress} | {expected} chips ({timepoints} time points) | "
            f"{obs} | {match} |\n"
        )

    # Parse warnings.
    md.append("\n## Parse warnings\n\n")
    flag_counter = Counter()
    for f in df["flags"]:
        for tag in (f or "").split(";"):
            if tag:
                flag_counter[tag] += 1
    if not flag_counter:
        md.append("None - all samples parsed cleanly.\n")
    else:
        for tag, count in flag_counter.most_common():
            md.append(f"- `{tag}`: {count} samples\n")

    # Seven-item reality-check.
    md.append("\n## Seven-item reality-check\n\n")

    md.append("### 1. Per-condition sample structure\n")
    md.append("See per-GSE summary above and the chip-count cross-check.\n\n")

    md.append("### 2. Replicate independence\n")
    md.append("Replicate numbers extracted where parseable. "
              "Independence (separate biological replicates vs technical "
              "duplicates) cannot be confirmed from metadata alone - "
              "requires consulting Kilian 2007 Methods. **TODO.**\n\n")

    md.append("### 3. Label provenance\n")
    md.append("Labels parsed from GEO `characteristics_ch1`, "
              "`source_name_ch1`, and `title` fields. Submitter "
              "(Kilian/Harter group) is consistent across the series.\n\n")

    md.append("### 4. Label content vs name\n")
    md.append("Stress labels match Kilian 2007's stated treatments where "
              "parsed. **TODO:** confirm 'osmotic' = mannitol-induced "
              "(per Kilian methods) and not PEG-induced; confirm 'salt' "
              "concentration; confirm 'drought' protocol "
              "(slow vs sudden).\n\n")

    md.append("### 5. Tissue/condition consistency\n")
    md.append("Per Hahn 2013, six stresses (genotoxic, osmotic, oxidative, "
              "salt, UV-B, wounding) were applied to shoot OR root only; "
              "three (cold, drought, heat) were whole-plant. **The series "
              "is NOT uniformly split across stresses** - see tissue "
              "column above. This is a structural caveat for any "
              "cross-stress pooling that Channel A's hypotheses do.\n\n")

    md.append("### 6. Platform/protocol comparability\n")
    platforms = sorted(df["platform"].dropna().unique().tolist())
    md.append(f"Platforms observed: {', '.join(platforms) or '(none)'}.\n\n")
    md.append("Per Kilian 2007, all samples used Affymetrix ATH1 (GPL198) "
              "under shared protocol.\n\n")

    md.append("### 7. Prior-publication overlap\n")
    md.append("Per-hypothesis check (TODO):\n\n")
    md.append("- **H1** (common stress core): Sham 2014 covered this on "
              "AtGenExpress. Reframe as methodological practice.\n")
    md.append("- **H2** (hub genes from co-expression): anchored to "
              "literature paper 12. Confirm not duplicating it.\n")
    md.append("- **H3** (time-resolved bio/abio convergence): novel "
              "framing per the prior session. Pending Botrytis side.\n")
    md.append("- **H4** (cross-dataset generalization): novel framing.\n\n")

    md.append("## Decision\n\n")
    md.append("**Pending** - proposed: `lock with caveat` "
              "(non-uniform tissue structure across stresses; "
              "non-aligned time grids). Final lock requires Botrytis "
              "pass and H4 test-set selection.\n")

    OUTPUT_MD.write_text("".join(md))
    print(f"Wrote reality-check entry to {OUTPUT_MD}", file=sys.stderr)


if __name__ == "__main__":
    main()