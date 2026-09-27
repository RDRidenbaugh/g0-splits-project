"""Does apparent saw size (px) jump between imaging sessions? Tests whether the ZEN scaling profile
(and hence the burned-in scale bar and the old mm coordinates) matches the real magnification."""
import collections, glob, os, re, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from load_old import load, match_by_coords, CAL, ROOT
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from czi_meta import czi_meta


def raw_index():
    idx = {}
    for f in glob.glob(os.path.join(ROOT, '*/raw_images/**/*'), recursive=True):
        if not f.lower().endswith(('.tif', '.jpg')):
            continue
        rel = os.path.relpath(f, ROOT)
        session = rel.split(os.sep)[2]
        stem = os.path.splitext(os.path.basename(f))[0]
        czi = glob.glob(os.path.join(os.path.dirname(os.path.dirname(f)), 'CZI', stem + '.czi')) + \
            glob.glob(os.path.join(os.path.dirname(f), stem + '.czi'))
        idx[stem.upper()] = dict(raw=rel, session=session, czi=czi[0] if czi else None)
    return idx


def main():
    recs, meta = load()
    idmap, _ = match_by_coords(recs, meta)
    rev = {recs[i]['file']: pid for pid, i in idmap.items()}
    idx = raw_index()
    rows = collections.defaultdict(list)
    for r in recs:
        stem = re.sub(r'_(MARK|XY)_[A-Z]+$', '', os.path.splitext(os.path.basename(r['file']))[0]).upper()
        e = idx.get(stem)
        if not e:
            continue
        pid = rev.get(r['file'])
        sp = meta[pid]['Species'][:3] if pid else ('PIN?' if stem.startswith('NP') else '?')
        mag = czi_meta(e['czi']).get('TotalMagnification') if e['czi'] else None
        L = np.linalg.norm(r['xy_mm'][0] - r['xy_mm'][14]) * CAL  # annulus-1 ventral -> apex, px
        rows[(e['session'], mag, sp)].append(L)
    print('session  TotalMag  species  n  median saw length px (LM1->LM15)')
    for k in sorted(rows, key=lambda k: (k[2], k[0])):
        print(*k, len(rows[k]), round(float(np.median(rows[k]))))


if __name__ == '__main__':
    main()
