"""Training data for the saw (protocol v1.1) landmark models (step 2 of the saw production pipeline).

Reads image_table.csv (prep_images.py) and ../autolabels/labels_v12.csv + qc_v12.csv, and writes here:
  manifest_saw_v12.csv  one row per prepared image whose v1.1 label passed QC, in the layout the
                        shared CNN code (lance_landmarking/cnn) reads: angle = "Saw", raw_image =
                        images/<key>.tif (mirrored apex-left, colour-normalized; same pixel grid as
                        the marked TIFF the label was made on), landmarks_px_json = the 52 points.
                        marked_tiff is left empty on purpose: evaluate.py would take mm from the
                        ImageJ calibration in the marked TIFF (the old global 2160.7 px/mm), which is
                        wrong for most sessions. Errors are reported in px; mm come from each image's
                        own scale bar in the landmarking step.
  folds_saw_v12.json    {family: fold 0..K-1}. Folds are assigned per COLONY (siblings), balanced
                        within each group (cohort x species), then written for every image's family
                        as the shared code computes it (splits.family_of(key)), so siblings never sit
                        on both sides of a train/test boundary. Covers all prepared images, so
                        unlabelled ones are defined too.
Images digitized twice (the BH/GK pairs) keep one label: the first that passed QC.
Exact duplicate raw files (same bytes: archive copies) get duplicate_of = the first copy's key in
image_table.csv and are neither trained on nor predicted.

usage: python make_production_data.py [--folds 5] [--seed 42]
"""
import argparse, csv, json, os, random, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CNN = os.path.abspath(os.path.join(ROOT, '..', 'lance_landmarking', 'cnn'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, CNN)
import scheme  # noqa: E402
from pairing import norm_id  # noqa: E402
from splits import family_of  # noqa: E402

ORDER = [p for p, _ in scheme.point_order()]


def prime():
    meta = {}
    for f, cohort in [('prime_g0_v6.csv', 'g0'), ('prime_splits_v8.csv', 'splits')]:
        for r in csv.DictReader(open(os.path.join(ROOT, 'analysis/data', f))):
            meta[norm_id(r['ID'])] = dict(species=r['Species'].upper(), colony=r.get('Colony') or '', cohort=cohort)
    return meta


def canon(ID):
    """One spelling per splits specimen: NE_X002_A15 / NEX002_A15 -> NL22NE_X002_A15; NP23KYX035 -> NP23KY_X035."""
    s = norm_id(ID)
    s = re.sub(r'^NE_?X', 'NL22NE_X', s)
    s = re.sub(r'^(N[LP]\d\d(?:NE|KY))_?X0*(\d+)', lambda m: f'{m.group(1)}_X{int(m.group(2)):03d}', s)
    return s


def colony_of(ID, cohort, meta):
    ID = canon(ID)
    m = meta.get(norm_id(ID))
    if m and m['colony']:
        return norm_id(m['colony'])
    s = norm_id(ID)
    if cohort == 'splits':
        x = re.search(r'X0*(\d+)', s)
        pop = re.match(r'(N[LP]\d\d(?:NE|KY))', s)
        return f"{pop.group(1) if pop else '?'}_X{int(x.group(1)):03d}" if x else s
    return re.split(r'_F\d*$|_F_', s)[0]  # g0: collection lot before _F<n>


def species_of(ID, cohort, meta, colony_species):
    m = meta.get(norm_id(canon(ID)))
    if m:
        return m['species']
    s = canon(ID)
    if s.startswith(('NL', 'NP')) and cohort == 'splits':
        return 'LECONTEI' if s.startswith('NL') else 'PINETUM'
    return colony_species.get(colony_of(ID, cohort, meta), 'UNKNOWN')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--folds', type=int, default=5)
    ap.add_argument('--seed', type=int, default=42)
    a = ap.parse_args()
    meta = prime()
    imgs = list(csv.DictReader(open(os.path.join(HERE, 'image_table.csv'))))
    # stem -> image; when a stem occurs more than once (re-shoots, archive copies) take the copy that
    # is pixel-identical to the marked TIFF (smallest marked_diff): that is the one that was digitized
    by_stem = {}
    for r in imgs:
        st = os.path.splitext(os.path.basename(r['raw_image']))[0].upper()
        d = float(r['marked_diff']) if r['marked_diff'] != '' else 1e9
        if st not in by_stem or d < by_stem[st][0]:  # ties keep the first copy
            by_stem[st] = (d, r)
    by_stem = {k: v[1] for k, v in by_stem.items()}

    qc = {r['txt']: r['pass'] == '1' for r in csv.DictReader(open(os.path.join(ROOT, 'autolabels/qc_v12.csv')))}
    labels, no_image = {}, []
    for r in csv.DictReader(open(os.path.join(ROOT, 'autolabels/labels_v12.csv'))):
        if not qc.get(r['txt']):
            continue
        stem = re.sub(r'_(MARK|XY)_[A-Z]+$', '', os.path.splitext(os.path.basename(r['txt']))[0]).upper()
        im = by_stem.get(stem)
        if im is None:
            no_image.append(r['txt']); continue
        if im['key'] in labels:  # digitized twice: keep the first
            continue
        labels[im['key']] = ([[round(float(r[f'{p}_x']), 2), round(float(r[f'{p}_y']), 2)] for p in ORDER], r['txt'])

    # exact duplicate files (archive copies, re-exports) point at the first copy
    import hashlib
    first = {}
    for r in imgs:
        h = hashlib.md5(open(os.path.join(HERE, r['raw_image']), 'rb').read()).hexdigest()
        r['duplicate_of'] = first.get(h, '')
        first.setdefault(h, r['key'])
    colony_species = {}
    for pid, m in meta.items():  # a colony's species, from its PRIME members
        colony_species.setdefault(colony_of(pid, m['cohort'], meta), m['species'])
    for r in imgs:
        r['species'] = species_of(r['id'], r['cohort'], meta, colony_species)
        r['group'] = f"{r['cohort']}_{r['species'][:3]}"
        r['colony'] = colony_of(r['id'], r['cohort'], meta)

    out = []
    for r in imgs:
        if r['key'] not in labels or r['duplicate_of']:
            continue
        pts, txt = labels[r['key']]
        w, h = 2560, 1920
        out.append(dict(group=r['group'], angle='Saw', key=r['key'], marked_tiff='', txt=os.path.relpath(os.path.join(ROOT, txt), HERE),
                        raw_image=r['image'], raw_group=r['group'], n_expected=len(pts), n_found=len(pts),
                        landmark_source='autolabel_v1.2', image_width=w, image_height=h,
                        landmarks_px_json=json.dumps(pts), flags=''))
    with open(os.path.join(HERE, 'manifest_saw_v12.csv'), 'w', newline='') as fh:
        w_ = csv.DictWriter(fh, fieldnames=list(out[0])); w_.writeheader(); w_.writerows(out)

    # colonies -> folds, balanced within group by image count (largest colonies first)
    col_n = defaultdict(lambda: defaultdict(int))
    for r in imgs:
        col_n[r['group']][r['colony']] += 1
    rng = random.Random(a.seed)
    cfold, total = {}, [0] * a.folds
    for g in sorted(col_n):
        cols = sorted(col_n[g]); rng.shuffle(cols); cols.sort(key=lambda c: -col_n[g][c])
        in_g = [0] * a.folds
        for c in cols:
            if c in cfold:
                continue
            k = min(range(a.folds), key=lambda i: (in_g[i], total[i], rng.random()))
            cfold[c] = k; in_g[k] += col_n[g][c]; total[k] += col_n[g][c]
    folds = {}
    for r in imgs:
        fam = family_of(r['key'])
        if fam in folds and folds[fam] != cfold[r['colony']]:
            raise SystemExit(f'family {fam} spans two colonies')
        folds[fam] = cfold[r['colony']]
    json.dump(folds, open(os.path.join(HERE, 'folds_saw_v12.json'), 'w'), indent=0, sort_keys=True)
    with open(os.path.join(HERE, 'image_table.csv'), 'w', newline='') as fh:  # add group/colony/fold
        for r in imgs:
            r['fold'] = folds[family_of(r['key'])]
            r['labelled'] = int(r['key'] in labels)
        w_ = csv.DictWriter(fh, fieldnames=list(imgs[0])); w_.writeheader(); w_.writerows(imgs)

    n = defaultdict(lambda: [0] * a.folds)
    for r in out:
        n[r['group']][folds[family_of(r['key'])]] += 1
    print(f'manifest_saw_v12.csv: {len(out)} labelled images; labels without a raw image: {no_image}')
    print(f'folds_saw_v12.json: {len(cfold)} colonies, {len(folds)} families; labelled images per fold by group:')
    for g, c in sorted(n.items()):
        print(f'  {g:12s} {c}')
    print('  total       ', [sum(c[i] for c in n.values()) for i in range(a.folds)])


if __name__ == '__main__':
    main()
