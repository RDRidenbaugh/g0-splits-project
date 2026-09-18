"""Build a training manifest for the lance-landmarking CNN.

Walks Raw_Images/<group>/ and Landmarked_<group>/{marked_tiff,txt}/<angle>/
for every group and angle, matches raw <-> marked_tiff <-> txt by a
normalized filename stem, extracts pixel-space landmark ground truth
(preferring the ImageJ ROI embedded in the marked TIFF; falling back to the
mm .txt export converted via that image's own XResolution), and writes one
row per landmarked image to manifest.csv plus a manifest_issues.csv of
everything that needed a flag.

This does not guess past genuinely ambiguous cases -- unmatched or
inconsistent files are flagged, not silently dropped or silently paired.

Usage: source ../.venv/bin/activate && python3 build_manifest.py
(run from lance_landmarking/tools/, or pass --root explicitly)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from landmarks_io import read_image_meta, read_landmark_roi, read_txt_landmarks_mm

GROUPS = ["F1", "LBX", "Non_Laying_Parents", "PBX", "Parents"]
ANGLES = {"Bottom": "B", "Left": "L", "Right": "R"}
EXPECTED_N = {"Bottom": 17, "Left": 32, "Right": 36}
# (group, angle) pairs known to contain a base/base+"1" duplicate digitizing
# pass, per recon findings. Extend this if the generic scan below reports
# the same pattern elsewhere.
KNOWN_DUP_PASS_SCOPE = {("F1", "Right"), ("PBX", "Right")}

MARK_RE = re.compile(r"[\s._]*MARK", re.IGNORECASE)
DUP_COPY_RE = re.compile(r"\s*\(\d+\)\s*$")
MULTI_USCORE_RE = re.compile(r"_+")
PUNCT_AROUND_USCORE_RE = re.compile(r"[\s.]+(?=_)|(?<=_)[\s.]+")


def normalize_stem(stem: str) -> tuple[str, list[str]]:
    """Return (matching_key, flags) for a filename stem (no extension)."""
    flags = []
    s = stem
    if MARK_RE.search(s):
        s = MARK_RE.sub("", s)
    if DUP_COPY_RE.search(s):
        flags.append("dup_copy_suffix")
        s = DUP_COPY_RE.sub("", s)
    s = PUNCT_AROUND_USCORE_RE.sub("", s)
    s = MULTI_USCORE_RE.sub("_", s).strip("_ .")
    return s.lower(), flags


def angle_folder_name(landmarked_dir: Path, angle: str) -> Path | None:
    candidates = [angle, f"{angle} Side"]
    for c in candidates:
        p = landmarked_dir / c
        if p.is_dir():
            return p
    return None


def list_files(d: Path, exts: tuple[str, ...]) -> dict[str, list[Path]]:
    """normalized_key -> list of paths (usually length 1) within one folder."""
    out: dict[str, list[Path]] = defaultdict(list)
    if d is None or not d.is_dir():
        return out
    for p in d.iterdir():
        if p.name.endswith(":Zone.Identifier") or p.suffix.lower() not in exts:
            continue
        key, _flags = normalize_stem(p.stem)
        out[key].append(p)
    return out


def build_raw_maps(root: Path) -> dict[str, dict[str, list[Path]]]:
    maps = {}
    for group in GROUPS:
        d = root / "Raw_Images" / group
        maps[group] = list_files(d, (".tif", ".tiff"))
    return maps


def find_raw(raw_maps: dict[str, dict[str, list[Path]]], group: str, key: str):
    paths = raw_maps.get(group, {}).get(key)
    if paths:
        return group, paths, False
    for other_group, m in raw_maps.items():
        if other_group == group:
            continue
        paths = m.get(key)
        if paths:
            return other_group, paths, True
    return None, [], False


def pixel_landmarks_for(marked_path: Path | None, txt_path: Path | None, expected_n: int):
    """Return (points_px, n, source, flags) using ROI when available, else
    mm txt converted via that image's own resolution tag."""
    flags = []
    if marked_path is not None:
        roi = read_landmark_roi(str(marked_path))
        if roi is not None:
            if roi.n != expected_n:
                flags.append(f"n_mismatch_roi:{roi.n}")
            return roi.points, roi.n, "roi", flags
        flags.append("marked_tiff_missing_roi")
    if txt_path is not None:
        meta = read_image_meta(str(marked_path)) if marked_path else None
        pts_mm = read_txt_landmarks_mm(str(txt_path))
        if len(pts_mm) != expected_n:
            flags.append(f"n_mismatch_txt:{len(pts_mm)}")
        if meta is not None and meta.px_per_unit:
            scale = meta.px_per_unit
            pts_px = [(x * scale, y * scale) for x, y in pts_mm]
            return pts_px, len(pts_mm), "txt_mm_converted", flags
        flags.append("no_calibration_for_txt_fallback")
        return pts_mm, len(pts_mm), "txt_uncalibrated", flags
    flags.append("no_landmark_source")
    return [], 0, "none", flags


def average_points(list_of_pointsets: list[list[tuple[float, float]]]):
    n = len(list_of_pointsets[0])
    out = []
    for i in range(n):
        xs = [pts[i][0] for pts in list_of_pointsets]
        ys = [pts[i][1] for pts in list_of_pointsets]
        out.append((sum(xs) / len(xs), sum(ys) / len(ys)))
    return out


def max_displacement(list_of_pointsets: list[list[tuple[float, float]]]) -> float:
    a, b = list_of_pointsets[0], list_of_pointsets[1]
    return max(((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5 for (x1, y1), (x2, y2) in zip(a, b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).parent.parent), help="lance_landmarking/ directory")
    ap.add_argument("--out", default=str(Path(__file__).parent.parent / "manifest.csv"))
    args = ap.parse_args()
    root = Path(args.root)

    raw_maps = build_raw_maps(root)
    rows = []
    generic_dup_pass_hits = []

    for group in GROUPS:
        landmarked_dir = root / f"Landmarked_{group}"
        for angle in ANGLES:
            marked_dir = angle_folder_name(landmarked_dir / "marked_tiff", angle)
            txt_dir = landmarked_dir / "txt" / angle
            marked_map = list_files(marked_dir, (".tif", ".tiff"))
            txt_map = list_files(txt_dir, (".txt",))

            all_keys = set(marked_map) | set(txt_map)

            # generic scan (not auto-applied outside KNOWN_DUP_PASS_SCOPE):
            # flag any key `k` where `k+"1"` also exists in the same folder set.
            for k in list(all_keys):
                if (k + "1") in all_keys:
                    generic_dup_pass_hits.append((group, angle, k))

            consumed = set()
            for key in sorted(all_keys):
                if key in consumed:
                    continue
                flags = []
                marked_paths = list(marked_map.get(key, []))
                txt_paths = list(txt_map.get(key, []))

                dup_key = key + "1"
                is_dup_scope = (group, angle) in KNOWN_DUP_PASS_SCOPE
                has_dup_instance = is_dup_scope and dup_key in all_keys

                expected_n = EXPECTED_N[angle]

                if has_dup_instance:
                    consumed.add(dup_key)
                    base_marked = marked_map.get(key, [None])[0]
                    base_txt = txt_map.get(key, [None])[0]
                    dup_marked = marked_map.get(dup_key, [None])[0]
                    dup_txt = txt_map.get(dup_key, [None])[0]

                    if dup_marked is not None:
                        # a genuinely separate marked TIFF for the "1" variant:
                        # this is a real independent digitization, not a dupe
                        # export -- compare its own ROI to the base ROI.
                        base_pts_check, base_n, _s, _f = pixel_landmarks_for(base_marked, base_txt, expected_n)
                        dup_pts, dup_n, _s2, _f2 = pixel_landmarks_for(dup_marked, dup_txt, expected_n)
                        flags += _f + _f2
                        if base_n == expected_n and dup_n == expected_n:
                            disp = max_displacement([base_pts_check, dup_pts])
                            flags.append(f"duplicate_pass_averaged:disp={disp:.2f}px")
                            points = average_points([base_pts_check, dup_pts])
                            n_found = expected_n
                            landmark_source = "roi+roi_averaged"
                        else:
                            points, n_found, landmark_source = base_pts_check, base_n, _s
                        marked_path = base_marked
                    else:
                        # dup variant is txt-only with no marked TIFF of its
                        # own -- confirm it's a byte-identical duplicate
                        # export of the base txt, then ignore it (base ROI
                        # is the authoritative source; don't try to convert
                        # the dup txt with a calibration it doesn't carry).
                        if base_txt and dup_txt:
                            identical = Path(base_txt).read_bytes() == Path(dup_txt).read_bytes()
                            flags.append("duplicate_txt_identical" if identical else "duplicate_txt_DIFFERS_from_base_uninvestigated")
                        points, n_found, landmark_source, f2 = pixel_landmarks_for(base_marked, base_txt, expected_n)
                        flags += f2
                        marked_path = base_marked
                    txt_path = base_txt
                else:
                    if len(marked_paths) > 1:
                        flags.append(f"multiple_marked_tiff:{len(marked_paths)}")
                    if len(txt_paths) > 1:
                        flags.append(f"multiple_txt:{len(txt_paths)}")
                    marked_path = marked_paths[0] if marked_paths else None
                    txt_path = txt_paths[0] if txt_paths else None
                    points, n_found, landmark_source, f2 = pixel_landmarks_for(marked_path, txt_path, expected_n)
                    flags += f2

                raw_group, raw_paths, cross_group = find_raw(raw_maps, group, key)
                if raw_group is None:
                    flags.append("no_raw_match")
                else:
                    if cross_group:
                        flags.append(f"raw_found_in_group:{raw_group}")
                    if len(raw_paths) > 1:
                        flags.append(f"multiple_raw:{len(raw_paths)}")

                image_width = image_height = None
                if marked_path is not None:
                    try:
                        meta = read_image_meta(str(marked_path))
                        image_width, image_height = meta.width, meta.height
                    except Exception as e:
                        flags.append(f"meta_read_error:{e}")

                rows.append(
                    {
                        "group": group,
                        "angle": angle,
                        "key": key,
                        "marked_tiff": str(marked_path) if marked_path else "",
                        "txt": str(txt_path) if txt_path else "",
                        "raw_image": str(raw_paths[0]) if raw_paths else "",
                        "raw_group": raw_group or "",
                        "n_expected": expected_n,
                        "n_found": n_found,
                        "landmark_source": landmark_source,
                        "image_width": image_width,
                        "image_height": image_height,
                        "landmarks_px_json": json.dumps(points),
                        "flags": ";".join(flags),
                    }
                )

    out_path = Path(args.out)
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    issues = [r for r in rows if r["flags"]]
    issues_path = out_path.with_name("manifest_issues.csv")
    with open(issues_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(issues)

    print(f"Wrote {len(rows)} rows to {out_path}")
    print(f"  {len(issues)} rows have >=1 flag -> {issues_path}")
    clean = [r for r in rows if not r["flags"] and r["n_found"] == r["n_expected"]]
    print(f"  {len(clean)} rows are clean (no flags, correct landmark count) and training-ready")
    if generic_dup_pass_hits:
        outside_scope = [h for h in generic_dup_pass_hits if (h[0], h[1]) not in KNOWN_DUP_PASS_SCOPE]
        print(f"  generic base/base+'1' pattern found in {len(generic_dup_pass_hits)} (group,angle,key) triples;"
              f" {len(outside_scope)} outside KNOWN_DUP_PASS_SCOPE (not auto-merged, worth reviewing):")
        for g, a, k in outside_scope[:15]:
            print(f"    {g}/{a}/{k}")


if __name__ == "__main__":
    main()
