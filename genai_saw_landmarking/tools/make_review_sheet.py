"""Review sheet for the saw labels that need a person (review/label_review.csv + review/overlays/).

Rows:
  qc_fail        the v1.1 automatic label failed QC (tools/autolabel.py): the overlay shows the v1.1
                 points; the flags say which part is off (gap_<point> = that outline point is > 25 px
                 from the traced outline; detour_<a>-<b> = the traced segment wanders)
  not_digitized  a raw saw image with no human configuration (no training label yet)
  33_points      the old txt has 33 points instead of 32 (an extra click at the tip)
  annulus_shift  the image was digitized twice (BH and GK) and the two disagree on which band is
                 which annulus (old points 18-21 ~290 px apart): one of them skipped an annulus
Columns to fill in: decision (fix | ok | drop), note.

usage: python tools/make_review_sheet.py [--no-overlays]
"""
import argparse, csv, glob, os, re, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from draw_protocol import load_rgb, new_config, draw, CAL  # noqa: E402

REASON = {
    'gap_S01': 'apex off the traced outline (blurred or faint tip)',
    'gap_V': 'a ventral annulus end off the outline (faint teeth, or the old point is off)',
    'gap_T': 'a serrula tip off the outline',
    'detour': 'traced outline segment wanders (flap/debris attached, or a tooth merged)',
}


def explain(flags):
    out = []
    for f in flags.split(';'):
        if not f:
            continue
        key = 'gap_S01' if f == 'gap_S01' else f[:5] if f.startswith(('gap_V', 'gap_T')) else 'detour' if f.startswith('detour') else f
        out.append(REASON.get(key, f))
    return '; '.join(dict.fromkeys(out))


def marked_for(txt):
    stem = os.path.basename(txt).rsplit('_', 2)[0]
    for f in glob.glob(os.path.join(ROOT, os.path.dirname(os.path.dirname(txt)), 'marked', '*.tif')):
        if os.path.basename(f).rsplit('_', 2)[0] == stem:
            return f
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-overlays', action='store_true')
    a = ap.parse_args()
    od = os.path.join(ROOT, 'review', 'overlays'); os.makedirs(od, exist_ok=True)
    rows = []
    for r in csv.DictReader(open(os.path.join(ROOT, 'autolabels/qc_v12.csv'))):
        if r['pass'] == '1':
            continue
        tif = marked_for(r['txt'])
        ov = ''
        if tif and not a.no_overlays and os.path.exists(os.path.join(ROOT, r['txt'])):
            img = load_rgb(tif)
            old = np.loadtxt(os.path.join(ROOT, r['txt']))[:32] * CAL
            anc, semis, paths, mask = new_config(img, old)
            stem = os.path.splitext(os.path.basename(r['txt']))[0]
            ov = os.path.join('review', 'overlays', stem + '.jpg')
            draw(img, anc, semis, paths, os.path.join(ROOT, ov), mask, title=f'{stem}: {r["flags"]}')
        rows.append(dict(kind='qc_fail', image=os.path.relpath(tif, ROOT) if tif else '', txt=r['txt'],
                         flags=r['flags'], why=explain(r['flags']), overlay=ov, decision='', note=''))

    digitized = {re.sub(r'_(MARK|XY)_[A-Z]+$', '', os.path.splitext(os.path.basename(t))[0]).upper()
                 for t in glob.glob(os.path.join(ROOT, '*/marked_images/*/txt/*.txt'))}
    for f in sorted(glob.glob(os.path.join(ROOT, '*/raw_images/**/*'), recursive=True)):
        if f.lower().endswith(('.tif', '.jpg')):
            stem = os.path.splitext(os.path.basename(f))[0].upper()
            if stem not in digitized:
                rows.append(dict(kind='not_digitized', image=os.path.relpath(f, ROOT), txt='', flags='',
                                 why='no human configuration: digitize with the v1.1 protocol', overlay='', decision='', note=''))

    for t in sorted(glob.glob(os.path.join(ROOT, '*/marked_images/*/txt/*.txt'))):
        if len(np.loadtxt(t)) == 33:
            rows.append(dict(kind='33_points', image='', txt=os.path.relpath(t, ROOT), flags='',
                             why='33 points: the last two are both at the tip; the first 32 were used', overlay='', decision='', note=''))
    for t in sorted(glob.glob(os.path.join(ROOT, 'splits/marked_images/*/txt/*X012_A27_L*.txt'))):
        rows.append(dict(kind='annulus_shift', image=os.path.relpath(marked_for(os.path.relpath(t, ROOT)) or '', ROOT), txt=os.path.relpath(t, ROOT),
                         flags='', why='BH and GK disagree on annulus identity for old points 18-21: check which counted annulus 1 correctly',
                         overlay='', decision='', note=''))

    with open(os.path.join(ROOT, 'review', 'label_review.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    from collections import Counter
    print('review/label_review.csv:', dict(Counter(r['kind'] for r in rows)))


if __name__ == '__main__':
    main()
