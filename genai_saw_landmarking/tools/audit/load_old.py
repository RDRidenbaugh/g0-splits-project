"""Load the old 32-point human saw configurations and join them to the PRIME metadata."""
import csv, glob, os, re
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAL = 2160.7  # px/mm used by the digitizers (0.0004628 mm/px)


def _meta():
    rows = {}
    for f, cohort in [('prime_g0_v6.csv', 'g0'), ('prime_splits_v8.csv', 'splits')]:
        with open(os.path.join(ROOT, 'analysis/data', f)) as fh:
            for r in csv.DictReader(fh):
                r['cohort'] = cohort
                rows[r['ID']] = r
    return rows


def parse_name(path):
    b = os.path.basename(path)
    m = re.match(r'(.+?)_(L|R)(?:_[vV]\d+)?_(?:MARK|XY)_([A-Z]+)', b)
    if not m:
        return None
    return dict(stem=m.group(1), side=m.group(2), initials=m.group(3))


def load():
    meta = _meta()
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, '*/marked_images/*/txt/*.txt'))):
        p = parse_name(f)
        a = np.loadtxt(f)
        cohort = f.split(os.sep)[-5]
        folder = f.split(os.sep)[-3]
        rec = dict(file=os.path.relpath(f, ROOT), cohort=cohort, folder=folder,
                   xy_mm=a, n=len(a), **(p or {}))
        stem = rec.get('stem', '')
        m = meta.get(stem) or meta.get(re.sub(r'_G0', '', stem))
        rec['meta'] = m
        out.append(rec)
    return out, meta


if __name__ == '__main__':
    recs, meta = load()
    print(len(recs), 'configs;', sum(r['meta'] is not None for r in recs), 'matched to PRIME')
    print('unparsed', [r['file'] for r in recs if 'stem' not in r])
    un = [r['file'] for r in recs if r['meta'] is None]
    print('unmatched', len(un), un[:40])
    ids = {r.get('stem') for r in recs}
    print('PRIME rows without txt', [k for k in meta if k not in ids][:40])


def match_by_coords(recs, meta, tol=2e-3):
    """Map PRIME ID -> txt record by identical coordinates (PRIME XY were pasted from the txt files)."""
    keys = [f'X{i}' for i in range(1, 33)]
    out, unmatched = {}, []
    for pid, r in meta.items():
        try:
            v = np.array([[float(r[f'X{i}']), float(r[f'Y{i}'])] for i in range(1, 33)])
        except (ValueError, KeyError):
            unmatched.append((pid, 'noXY')); continue
        best, bd = None, 1e9
        for k, rec in enumerate(recs):
            if rec['n'] < 32:
                continue
            d = np.abs(rec['xy_mm'][:32] - v).max()
            if d < bd:
                best, bd = k, d
        if bd < tol:
            out[pid] = best
        else:
            unmatched.append((pid, round(bd, 4)))
    return out, unmatched


def specimen_key(rec):
    """Normalise the many spellings of one specimen (NE_X002_A15, NEX002_A15, NL22NE_X002_A15; RB017_G0_F1)."""
    s = rec.get('stem') or re.sub(r'_(MARK|XY)_.*', '', os.path.basename(rec['file']))
    s = s.upper()
    m = re.search(r'X0*(\d+)_([AB]F?\d+)', s)
    if rec['cohort'] == 'splits' and m:
        pop = re.match(r'(N[LP]\d\dNE|N[LP]\d\dKY|NE)', s)
        pop = pop.group(1) if pop else '?'
        pop = 'NL22NE' if pop == 'NE' else pop
        return f"{pop}_X{int(m.group(1)):03d}_{m.group(2)}"
    return s.replace('_G0', '')
