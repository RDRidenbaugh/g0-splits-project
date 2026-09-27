"""Build v1.0 labels for every old-digitized image: anchors migrated from the human points, curve
semilandmarks traced on the automatic silhouette. Writes autolabels/labels_v12.csv (pixel coordinates
in the PROTOCOL frame: apex left, teeth up = the marked TIFF flipped top to bottom; tools/frame.py)
and autolabels/qc_v12.csv.

QC (a label fails if any is true):
  gap      an anchor on the outline (V2-V7, T2-T4, S01) is > 25 px from the traced silhouette
  detour   a traced segment is > 2.5x (+30 px) the straight-line distance between its anchors (serrula
           notches are deep, so a tighter ratio flags normal anatomy)
           (the path went round the wrong side, or through an attached flap)
  order    V1..V7 not in proximal -> distal order along the saw axis
"""
import csv, glob, os, sys
from multiprocessing import Pool
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from draw_protocol import load_rgb, new_config, CAL
from outline import contour
from frame import to_protocol
import scheme

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDER = [p for p, _ in scheme.point_order()]


def marked_for(txt):
    stem = os.path.basename(txt).rsplit('_', 2)[0]
    for f in glob.glob(os.path.join(os.path.dirname(os.path.dirname(txt)), 'marked', '*.tif')):
        if os.path.basename(f).rsplit('_', 2)[0] == stem:
            return f
    return None


def one(txt):
    tif = marked_for(txt)
    rel = os.path.relpath(txt, ROOT)
    if tif is None:
        return rel, None, ['no_marked_tif']
    old = np.loadtxt(txt)
    if len(old) < 32:
        return rel, None, ['old_points_%d' % len(old)]
    a = load_rgb(tif)
    anc, semis, paths, mask = new_config(a, old[:32] * CAL)
    flags = []
    c = contour(mask)
    for pid in ['V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'T2', 'T3', 'T4', 'S01']:
        if np.sqrt(((c - anc[pid]) ** 2).sum(1)).min() > 25:
            flags.append('gap_' + pid)
    for (p, q), path in paths.items():
        L = np.linalg.norm(np.diff(path, axis=0), axis=1).sum()
        if L > 2.5 * np.linalg.norm(anc[p] - anc[q]) + 30:
            flags.append(f'detour_{p}-{q}')
    ax = anc['V1'] - anc['S01']; ax /= np.linalg.norm(ax)
    proj = [float(anc[f'V{k}'] @ ax) for k in range(1, 8)]
    if not all(proj[i] > proj[i + 1] for i in range(6)):
        flags.append('order')
    allp = {**anc, **semis}
    # written in the PROTOCOL frame (apex left, teeth up); QC above was done in the marked frame
    return rel, to_protocol(np.array([allp[p] for p in ORDER]), a.shape[0]), flags


def main():
    txts = sorted(glob.glob(os.path.join(ROOT, '*/marked_images/*/txt/*.txt')))
    with Pool(6) as pool:
        res = pool.map(one, txts)
    os.makedirs(os.path.join(ROOT, 'autolabels'), exist_ok=True)
    with open(os.path.join(ROOT, 'autolabels/labels_v12.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['txt'] + [f'{p}_{c}' for p in ORDER for c in 'xy'])
        for rel, X, fl in res:
            if X is not None:
                w.writerow([rel] + [round(v, 1) for v in X.ravel()])
    with open(os.path.join(ROOT, 'autolabels/qc_v12.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['txt', 'pass', 'flags'])
        for rel, X, fl in res:
            w.writerow([rel, int(X is not None and not fl), ';'.join(fl)])
    n = len(res); ok = sum(1 for _, X, fl in res if X is not None and not fl)
    print(f'{ok}/{n} pass')
    import collections
    print(collections.Counter(x.split('_')[0] for _, _, fl in res for x in fl).most_common())


if __name__ == '__main__':
    main()
