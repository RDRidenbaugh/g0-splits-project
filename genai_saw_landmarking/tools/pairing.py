"""Pair saw images with the same female's lance images (g0/raw_corresponding_lances).

Saw filename: <ID>_<L|R>[_vN].tif  (L/R = which saw; apex direction)
Lance filename: <ID>_<R|L|B>.tif    (Right / Left / Bottom lance views, lance protocol), in
  <cohort>/raw_corresponding_lances/ for every cohort (g0 now; splits as they are imaged)
IDs are spelled inconsistently (AG078-F4 vs AG078_F4, RB017_G0_F3, RID-X055-F), so both sides go
through norm_id(). Writes analysis/data/saw_lance_pairs.csv.
"""
import csv, glob, os, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def norm_id(stem):
    s = stem.upper().replace('-', '_')
    s = re.sub(r'_G\d+(?=_F)', '', s)          # RB017_G0_F3 -> RB017_F3
    s = re.sub(r'_F0*(\d+)', r'_F\1', s)
    s = re.sub(r'__+', '_', s)
    return s


def split_view(stem, views):
    m = re.match(r'(.+?)[_ ]((?:%s))\d*(?:[_ ]?V\d+)?$' % '|'.join(views), stem, re.I)  # R2 = second frame
    return (m.group(1), m.group(2).upper()) if m else (stem, None)


def saw_images():
    out = collections.defaultdict(list)
    for f in glob.glob(os.path.join(ROOT, '*/raw_images/**/*'), recursive=True):
        if not f.lower().endswith(('.tif', '.jpg')):
            continue
        base, side = split_view(os.path.splitext(os.path.basename(f))[0], ['L', 'R'])
        out[norm_id(base)].append((side, os.path.relpath(f, ROOT)))
    return out


def lance_images():
    out = collections.defaultdict(list)
    for f in glob.glob(os.path.join(ROOT, '*/raw_corresponding_lances/**/*'), recursive=True):  # g0 and splits
        if not f.lower().endswith(('.tif', '.jpg')):
            continue
        base, view = split_view(os.path.splitext(os.path.basename(f))[0], ['L', 'R', 'B'])
        out[norm_id(base)].append((view, os.path.relpath(f, ROOT)))
    return out


def main():
    saw, lance = saw_images(), lance_images()
    rows = []
    for k in sorted(set(saw) | set(lance)):
        sv = sorted({s for s, _ in saw.get(k, [])} - {None}); lv = sorted({v for v, _ in lance.get(k, [])} - {None})
        rows.append(dict(id=k, saw_sides=''.join(sv), lance_views=''.join(lv),
                         saw_files=';'.join(f for _, f in saw.get(k, [])),
                         lance_files=';'.join(f for _, f in lance.get(k, []) if f.endswith('.tif')) or
                                     ';'.join(f for _, f in lance.get(k, []))))
    os.makedirs(os.path.join(ROOT, 'analysis/data'), exist_ok=True)
    with open(os.path.join(ROOT, 'analysis/data/saw_lance_pairs.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    both = [r for r in rows if r['saw_sides'] and r['lance_views']]
    print('specimens with saw:', sum(bool(r['saw_sides']) for r in rows), ' with lance:', sum(bool(r['lance_views']) for r in rows),
          ' both:', len(both))
    print('lance views among paired:', collections.Counter(r['lance_views'] for r in both))
    print('lance-only IDs:', [r['id'] for r in rows if r['lance_views'] and not r['saw_sides']][:60])
    print('g0 saw-only IDs:', [r['id'] for r in rows if r['saw_sides'] and not r['lance_views'] and 'g0/' in r['saw_files']][:60])


if __name__ == '__main__':
    main()
