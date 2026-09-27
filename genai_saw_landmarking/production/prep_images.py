"""Prepare every raw saw image for the CNN (step 1 of the saw production pipeline).

For each raw image (g0/ and splits/ raw_images, .tif or .jpg) writes images/<key>.tif:
  * in the PROTOCOL frame (tools/frame.py): apex LEFT, teeth UP. First mirrored left-right when needed
    so the apex points left (the marked-TIFF frame), then flipped top to bottom. When a marked
    TIFF exists, the orientation is taken from it (raw vs mirrored raw, whichever matches the
    marked image); otherwise from the filename side (_R -> mirrored).
  * colour-normalized: each channel divided by the image's own background colour (median of the
    border) and scaled to a neutral grey of 200, so the green / pink / grey / white session
    backgrounds all look the same to the network.
  * same pixel grid as the raw image (only mirrored and flipped), so label and prediction pixels map
    back to the raw image exactly: x_raw = W - x if mirrored, y_raw = H - y (vflipped).
and image_table.csv: key, id, side, cohort, session, raw_image, image, mirrored, orient_source,
px_per_mm, cal_source, has_marked, marked_diff (mean grey difference to the marked TIFF;
~0 = this raw file is the one that was digitized: used to pick among duplicate stems).

key = lower-case file stem, e.g. nl22ne_x002_a15_r (unique; duplicates across sessions get _2, _3).
usage: python prep_images.py [--workers 6] [--overwrite]
"""
import argparse, csv, glob, os, re, sys
from multiprocessing import Pool

import numpy as np
import tifffile
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from calib import px_per_mm  # noqa: E402
from frame import image_to_protocol  # noqa: E402

GREY = 200.0


def load_rgb(f):
    if f.lower().endswith('.jpg'):
        return np.array(Image.open(f).convert('RGB'))
    t = tifffile.TiffFile(f); a = t.series[0].asarray(); ax = t.series[0].axes
    if a.ndim == 3 and ax.startswith('C'):
        a = np.moveaxis(a, 0, -1)
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
    return np.ascontiguousarray(a[..., :3]).astype(np.uint8)


def normalize(a):
    f = a.astype(np.float32)
    border = np.concatenate([f[:40].reshape(-1, 3), f[-40:].reshape(-1, 3), f[:, :40].reshape(-1, 3), f[:, -40:].reshape(-1, 3)])
    bg = np.median(border, 0)
    return np.clip(f * (GREY / np.maximum(bg, 1)), 0, 255).astype(np.uint8)


def marked_index():
    idx = {}
    for f in glob.glob(os.path.join(ROOT, '*/marked_images/*/marked/*.tif')):
        stem = re.sub(r'_MARK_[A-Z]+$', '', os.path.splitext(os.path.basename(f))[0]).upper()
        idx.setdefault(stem, f)
    return idx


def orientation(raw, marked_path, side):
    if marked_path:
        m = load_rgb(marked_path)
        if m.shape == raw.shape:
            s = lambda x: x[::8, ::8].astype(np.float32).mean(2)
            d0 = np.abs(s(raw) - s(m)).mean(); d1 = np.abs(s(raw[:, ::-1]) - s(m)).mean()
            return (d1 < d0), 'marked_tiff', round(float(min(d0, d1)), 3)
    return side == 'R', 'filename', ''


def one(job):
    raw_path, key, out, overwrite, marked = job
    stem = os.path.splitext(os.path.basename(raw_path))[0]
    m = re.match(r'(.+?)_(L|R)(?:_[vV]\d+)?$', stem)
    ID, side = (m.group(1), m.group(2)) if m else (stem, '')
    a = load_rgb(raw_path)
    mirrored, src, mdiff = orientation(a, marked, side)
    if overwrite or not os.path.exists(out):
        b = normalize(image_to_protocol(a[:, ::-1] if mirrored else a))  # apex left, then teeth up
        tifffile.imwrite(out, b, compression='zlib')
    ppm, cal = px_per_mm('saw', stem)
    rel = os.path.relpath(raw_path, ROOT).split(os.sep)
    return dict(key=key, id=ID, side=side, cohort=rel[0], session=rel[2], raw_image=os.path.relpath(raw_path, HERE),
                image=os.path.relpath(out, HERE), mirrored=int(mirrored), vflipped=1, orient_source=src, marked_diff=mdiff,
                px_per_mm=ppm or '', cal_source=cal, has_marked=int(bool(marked)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--overwrite', action='store_true')
    a = ap.parse_args()
    os.makedirs(os.path.join(HERE, 'images'), exist_ok=True)
    mk = marked_index()
    raws = sorted(f for f in glob.glob(os.path.join(ROOT, '*/raw_images/**/*'), recursive=True)
                  if f.lower().endswith(('.tif', '.jpg')))
    jobs, seen = [], {}
    for f in raws:
        stem = os.path.splitext(os.path.basename(f))[0]
        key = stem.lower()
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            key = f'{key}_{seen[key]}'
        jobs.append((f, key, os.path.join(HERE, 'images', key + '.tif'), a.overwrite, mk.get(stem.upper())))
    with Pool(a.workers) as p:
        rows = p.map(one, jobs)
    with open(os.path.join(HERE, 'image_table.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    n_m = sum(r['mirrored'] for r in rows)
    dis = [r['key'] for r in rows if r['orient_source'] == 'marked_tiff' and r['mirrored'] != int(r['side'] == 'R')]
    print(f'{len(rows)} images -> images/; mirrored {n_m}; orientation from marked TIFF {sum(r["orient_source"] == "marked_tiff" for r in rows)}')
    print('marked orientation disagrees with filename side:', dis)
    print('duplicate stems renamed:', [r['key'] for r in rows if re.search(r'_\d$', r['key']) and seen.get(r['key'][:-2], 0) > 1])


if __name__ == '__main__':
    main()
