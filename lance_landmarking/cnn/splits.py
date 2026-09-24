"""Load the manifest and build train/val/test splits.

Splits are stratified by (cross-type group, family) so that: (a) each split
gets a roughly proportional mix of F1/LBX/PBX/Parents/Non_Laying_Parents,
and (b) siblings from the same cross+replicate never straddle train/val/test
(which would leak information and inflate val/test accuracy).
"""
from __future__ import annotations

import csv
import json
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

INDIVIDUAL_RE = re.compile(r"^(?P<id>.+)_(?P<angle>[blr])(?P<frame>\d*)$")
VERSION_SUFFIX_RE = re.compile(r"-?v\d+$")


@dataclass
class Sample:
    group: str
    angle: str
    key: str
    family: str
    raw_image: str
    marked_tiff: str  # source of px_per_mm calibration for mm-space eval
    n_expected: int
    landmarks_px: list  # list of [x, y]
    image_width: int
    image_height: int


def family_of(key: str) -> str:
    m = INDIVIDUAL_RE.match(key)
    individual_id = m.group("id") if m else key
    return VERSION_SUFFIX_RE.sub("", individual_id)


def load_clean_samples(manifest_csv: str, angle: str) -> list[Sample]:
    samples = []
    root = Path(manifest_csv).resolve().parent  # manifest paths are relative to its directory
    with open(manifest_csv, newline="") as f:
        for row in csv.DictReader(f):
            if row["angle"] != angle:
                continue
            if row["flags"] and "duplicate_txt_identical" not in row["flags"].split(";"):
                # any flag other than the benign deduped-duplicate export
                # means this row's ground truth is incomplete/unreliable
                continue
            if int(row["n_found"]) != int(row["n_expected"]):
                continue
            if not row["raw_image"]:
                continue
            pts = json.loads(row["landmarks_px_json"])
            if len(pts) != int(row["n_expected"]):
                continue
            samples.append(
                Sample(
                    group=row["group"],
                    angle=row["angle"],
                    key=row["key"],
                    family=family_of(row["key"]),
                    raw_image=str(root / row["raw_image"]),
                    marked_tiff=str(root / row["marked_tiff"]) if row["marked_tiff"] else "",
                    n_expected=int(row["n_expected"]),
                    landmarks_px=pts,
                    image_width=int(row["image_width"]) if row["image_width"] else None,
                    image_height=int(row["image_height"]) if row["image_height"] else None,
                )
            )
    return samples


def split_samples(samples: list[Sample], val_frac=0.15, test_frac=0.15, seed=42):
    """Return (train, val, test) lists, split by family within each group."""
    rng = random.Random(seed)
    by_group_family = defaultdict(lambda: defaultdict(list))
    for s in samples:
        by_group_family[s.group][s.family].append(s)

    train, val, test = [], [], []
    for group, families in by_group_family.items():
        family_ids = list(families.keys())
        rng.shuffle(family_ids)
        n = len(family_ids)
        n_val = max(1, round(n * val_frac)) if n >= 3 else 0
        n_test = max(1, round(n * test_frac)) if n >= 3 else 0
        val_families = set(family_ids[:n_val])
        test_families = set(family_ids[n_val : n_val + n_test])
        for fam in family_ids:
            bucket = val if fam in val_families else test if fam in test_families else train
            bucket.extend(families[fam])
    return train, val, test
