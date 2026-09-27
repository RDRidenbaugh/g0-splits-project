"""Calibrate every saw raw image and every lance image from its own scale bar -> analysis/data/calibration.csv.

Policy (user, 2026-09-27): every image is calibrated from its OWN scale bar. Images without a usable bar
(no_bar, bar_truncated, bar_far_from_nominal) get no px_per_mm here; they are listed for re-export or
re-imaging. `px_per_mm_session` (median of the same imager/session's bars) is given only so interim
analyses can run, and cal_source says which one a row uses.
"""
import csv, glob, os, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image
import tifffile
sys.path.insert(0, os.path.dirname(__file__))
from scalebar import calibrate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOMINAL = {'saw': 2141.4, 'lance': 927.0}


def load(f):
    if f.lower().endswith('.jpg'):
        return np.array(Image.open(f).convert('RGB'))
    t = tifffile.TiffFile(f); a = t.series[0].asarray(); ax = t.series[0].axes
    if a.ndim == 3 and ax.startswith('C'):
        a = np.moveaxis(a, 0, -1)
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
    return np.ascontiguousarray(a[..., :3]).astype(np.uint8)


def one(args):
    f, kind = args
    rel = os.path.relpath(f, ROOT)
    try:
        ppm, mm, b, flags = calibrate(load(f), NOMINAL[kind])
    except Exception as e:  # unreadable file
        return dict(image=rel, kind=kind, px_per_mm='', bar_mm='', bar_px='', bar_colour='', ticks='', flags='error:' + str(e)[:40])
    return dict(image=rel, kind=kind, session=rel.split(os.sep)[-2] if kind == 'lance' else rel.split(os.sep)[2], px_per_mm=round(ppm, 2) if ppm else '',
                bar_mm=mm or '', bar_px=round(b['length_px'], 1) if b else '', bar_colour=b['colour'] if b else '',
                ticks=b['ticks'] if b else '', flags=';'.join(flags))


def main():
    jobs = []
    for f in glob.glob(os.path.join(ROOT, '*/raw_images/**/*'), recursive=True):
        if f.lower().endswith(('.tif', '.jpg')):
            jobs.append((f, 'saw'))
    for f in glob.glob(os.path.join(ROOT, '*/raw_corresponding_lances/**/*'), recursive=True):
        if f.lower().endswith('.tif'):
            jobs.append((f, 'lance'))
    with Pool(6) as p:
        rows = p.map(one, sorted(jobs))
    groups = {}
    for r in rows:
        r['imager'] = r['image'].split(os.sep)[2] if r['kind'] == 'lance' else 'zeiss'
        if r['px_per_mm']:
            groups.setdefault((r['kind'], r['imager'], r['session']), []).append(float(r['px_per_mm']))
    for r in rows:
        g = groups.get((r['kind'], r['imager'], r['session']))
        r['px_per_mm_session'] = round(float(np.median(g)), 2) if g else ''
        r['cal_source'] = 'own_bar' if r['px_per_mm'] else ('session_median' if g else 'none')
    out = os.path.join(ROOT, 'analysis/data/calibration.csv')
    cols = ['image', 'kind', 'imager', 'session', 'px_per_mm', 'cal_source', 'px_per_mm_session',
            'bar_mm', 'bar_px', 'bar_colour', 'ticks', 'flags']
    with open(out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    bad = [r for r in rows if not r['px_per_mm']]
    with open(os.path.join(ROOT, 'analysis/data/calibration_problems.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore'); w.writeheader(); w.writerows(bad)
    print(f'{len(rows) - len(bad)}/{len(rows)} calibrated from their own bar; {len(bad)} listed in calibration_problems.csv')
    print('wrote', out, len(rows))


if __name__ == '__main__':
    main()
