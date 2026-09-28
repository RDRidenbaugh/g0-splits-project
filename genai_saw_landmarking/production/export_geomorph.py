"""Turn the saw predictions into geomorph-ready tables in mm (step 5 of the saw production pipeline).

Reads output/predictions_px_saw.csv (landmark_images.py) and writes to output/geomorph/:
  Saw_v12_XY.csv        one row per saw (female x side): ID (PRIME spelling), side, cohort, species,
                        host, treatment, colony, population, px_per_mm, cal_source, source, key,
                        qc_flags, qc_pass, then X1, Y1, ..., X52, Y52 in mm. Protocol frame, image
                        axes: x to the right, y DOWN, apex left, teeth up. Same layout as the PRIME saw
                        tables, so arrayspecs(df[, first_X:last_Y], 52, 2) works.
  Saw_v12_sliders.csv   before / slide / after (1-indexed) for gpagen(curves = ...)
  landmark_key_v12.csv  number (1..52), protocol ID, role, definition
  export_report.txt     counts, images not used (duplicates of a saw), IDs without PRIME metadata

mm: each image's own scale bar (image_table px_per_mm; cal_source says whether it is the image's own bar).
QC: qc_pass is TRUE when landmark_images.py raised no flag (no_scale alone does not fail an image when a
session median exists). After looking at the overlays, record decisions in qc_review.csv
(key, decision = keep | drop, note); they override the flags.
When a saw (same ID and side) has several images, the one kept is: passing QC, then out-of-fold over
ensemble, then smallest model disagreement.
Metadata: from the PRIME tables. metadata_overrides.csv (ID, species, host, treatment, colony, population, note)
supplies or corrects it by ID: every non-empty cell replaces the value from PRIME/the ID rules, for all saws
of that female. Use it (not hand edits of Saw_v12_XY.csv, which this script overwrites) for saws missing from
PRIME or for corrections.

usage: python export_geomorph.py [--out-dir output/geomorph]
"""
import csv, json, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import scheme  # noqa: E402
from make_production_data import canon, colony_of, prime, species_of  # noqa: E402
from pairing import norm_id  # noqa: E402

ORDER = scheme.point_order()


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', default=os.path.join(HERE, 'output', 'geomorph'))
    out = ap.parse_args().out_dir
    os.makedirs(out, exist_ok=True)
    rows = list(csv.DictReader(open(os.path.join(HERE, 'output', 'predictions_px_saw.csv'))))
    review = {}
    rp = os.path.join(HERE, 'qc_review.csv')
    if os.path.exists(rp):
        review = {r['key']: r['decision'].strip().lower() for r in csv.DictReader(open(rp))}
    meta = {}
    for f, cohort in [('prime_g0_v6.csv', 'g0'), ('prime_splits_v8.csv', 'splits')]:
        for r in csv.DictReader(open(os.path.join(ROOT, 'analysis/data', f))):
            meta[norm_id(r['ID'])] = dict(r, cohort=cohort)
    pm = prime()
    # PRIME ID by identical coordinates (digitized saws; exact whatever the spelling), else by name
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'audit'))
    from load_old import load, match_by_coords  # noqa: E402
    import re
    recs, pmeta = load()
    by_coord = {}
    for pid, i in match_by_coords(recs, pmeta)[0].items():
        stem = re.sub(r'_(MARK|XY)_[A-Z]+$', '', os.path.splitext(os.path.basename(recs[i]['file']))[0]).upper()
        by_coord[stem] = norm_id(pid)

    overrides = {}
    op = os.path.join(HERE, 'metadata_overrides.csv')
    if os.path.exists(op):
        for r in csv.DictReader(open(op)):
            overrides[norm_id(r['ID'])] = {c: r[c].strip() for c in ('species', 'host', 'treatment', 'colony', 'population')
                                           if r.get(c, '').strip()}
    used_overrides = set()
    col_sp = {}
    for pid, mm in pm.items():
        col_sp.setdefault(colony_of(pid, mm['cohort'], pm), mm['species'])
    groups = defaultdict(list)
    for r in rows:
        flags = [x for x in r['flags'].split(';') if x]
        hard = [x for x in flags if x != 'no_scale' or r['cal_source'] == 'none']
        r['qc_pass'] = (review.get(r['key']) == 'keep') or (not hard and review.get(r['key']) != 'drop')
        stem = os.path.splitext(os.path.basename(r['raw_image']))[0].upper()
        cid = by_coord.get(stem) or by_coord.get(re.sub(r'_[LR](_V\d+)?$', '', stem)) or norm_id(canon(r['id']))
        r['id_source'] = 'prime_coords' if stem in by_coord else 'name'
        groups[(cid, r['side'])].append(r)

    n = len(ORDER)
    report, missing, kept = [], [], []
    for (cid, side), rs in sorted(groups.items()):
        rs.sort(key=lambda r: (not r['qc_pass'], not r['source'].startswith('oof'), float(r['spread_px'])))
        r = rs[0]
        if len(rs) > 1:
            report.append(f"{cid} {side}: kept {r['key']}; not used {[x['key'] for x in rs[1:]]}")
        m = meta.get(cid)
        if m is None:
            missing.append(cid)
        ppm = float(r['px_per_mm'])
        xy = [round(float(r[f'{c}{k}']) / ppm, 5) for k in range(1, n + 1) for c in 'xy']
        sp = (m or {}).get('Species', '') or species_of(cid, r['cohort'], pm, col_sp).replace('UNKNOWN', '')  # not in PRIME: from the ID/colony
        md = dict(species=sp, host=(m or {}).get('Host', ''), treatment=(m or {}).get('Treatment', ''),
                  colony=colony_of(cid, r['cohort'], pm), population=(m or {}).get('Population', ''))
        if cid in overrides:
            md.update(overrides[cid]); used_overrides.add(cid)
        kept.append([m['ID'] if m else cid, side, r['cohort'], md['species'], md['host'], md['treatment'], md['colony'],
                     md['population'], r['px_per_mm'], r['cal_source'], r['source'], r['key'], r['flags'], str(r['qc_pass']).upper()] + xy)

    head = ['ID', 'side', 'cohort', 'species', 'host', 'treatment', 'colony', 'population', 'px_per_mm',
            'cal_source', 'source', 'key', 'qc_flags', 'qc_pass'] + [f'{c}{k}' for k in range(1, n + 1) for c in 'XY']
    with open(os.path.join(out, 'Saw_v12_XY.csv'), 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(head); w.writerows(kept)
    with open(os.path.join(out, 'Saw_v12_sliders.csv'), 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['before', 'slide', 'after']); w.writerows(scheme.curves_slider_matrix())
    with open(os.path.join(out, 'landmark_key_v12.csv'), 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['number', 'id', 'role', 'definition'])
        for i, (pid, role) in enumerate(ORDER, 1):
            w.writerow([i, pid, role, scheme.ANCHORS[pid]['definition'] if pid in scheme.ANCHORS else 'sliding semilandmark on the ' + pid.split(':')[0] + ' curve'])
    npass = sum(k[13] == 'TRUE' for k in kept)
    lines = [f'{len(rows)} images -> {len(kept)} saws ({npass} pass QC, {len(kept) - npass} flagged)',
             f'saws without PRIME metadata ({len(missing)}): {missing}',
             f'metadata_overrides.csv applied to {len(used_overrides)} IDs'
             + (f'; override IDs matching no saw: {sorted(set(overrides) - used_overrides)}' if set(overrides) - used_overrides else ''),
             'several images of one saw:'] + report
    open(os.path.join(out, 'export_report.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines[:3]))
    print('->', out)


if __name__ == '__main__':
    main()
