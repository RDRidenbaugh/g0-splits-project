"""Autolabels (px) -> saw XY table in mm (ID, side, qc_pass, px_per_mm, cal_source, X1..Y52), the layout the production CNN export will use.
Until the saw CNN exists this lets the saw x lance analysis run on the human-derived v1.1 labels."""
import csv, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import scheme
from calib import saw_px_per_mm_for_label
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
order = [p for p, _ in scheme.point_order()]
qc = {r['txt']: r for r in csv.DictReader(open(os.path.join(ROOT, 'autolabels/qc_v12.csv')))}
out = os.path.join(ROOT, 'analysis/output/saw_v12_XY.csv')
with open(out, 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['ID', 'side', 'source', 'qc_pass', 'px_per_mm', 'cal_source'] + [f'{c}{i}' for i in range(1, len(order) + 1) for c in 'XY'])
    for r in csv.DictReader(open(os.path.join(ROOT, 'autolabels/labels_v12.csv'))):
        stem = re.sub(r'_(MARK|XY)_[A-Z]+$', '', os.path.splitext(os.path.basename(r['txt']))[0])
        m = re.match(r'(.+?)_(L|R)(?:_[vV]\d+)?$', stem)
        ID, side = (m.group(1), m.group(2)) if m else (stem, '')
        ppm, src = saw_px_per_mm_for_label(r['txt'])  # the image's own scale bar
        if ppm is None:
            print('no calibration, skipped:', stem); continue
        vals = [round(float(r[f'{p}_{c}']) / ppm, 5) for p in order for c in 'xy']
        w.writerow([ID, side, r['txt'], qc[r['txt']]['pass'], ppm, src] + vals)
print('wrote', out)
