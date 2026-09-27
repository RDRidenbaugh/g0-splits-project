"""Draw the saw scheme (tools/scheme.py) on real specimens: anchors from the old human points (mapped through
scheme.old_to_new), curves traced on the automatic silhouette between those anchors.

  python tools/draw_protocol.py <marked tif> <old txt> <out.jpg> [--mask]
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
import tifffile
from scheme import ANCHORS, COMPUTED, CURVES, CURVE_TRACE, old_to_new
from outline import silhouette, contour, arc, resample, trace_edge
from frame import to_protocol, image_to_protocol

CAL = 2160.7  # px/mm the digitizers entered


def load_rgb(f):
    t = tifffile.TiffFile(f); a = t.series[0].asarray(); ax = t.series[0].axes
    if a.ndim == 3 and ax.startswith('C'):
        a = np.moveaxis(a, 0, -1)
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
    return np.ascontiguousarray(a[..., :3]).astype(np.uint8)


def dorsal_hit(mask, v, d, step=1.0):
    """First point beyond d on the ray v -> d where the silhouette ends (the dorsal outline)."""
    u = (d - v) / np.linalg.norm(d - v); p = d.astype(float).copy()
    h, w = mask.shape
    for _ in range(3000):
        q = p + u * step
        if not (0 <= q[0] < w and 0 <= q[1] < h) or not mask[int(q[1]), int(q[0])]:
            return p
        p = q
    return p


def new_config(a, old_px):
    o2n = old_to_new()
    anc = {o2n[i + 1]: old_px[i] for i in range(len(old_px)) if (i + 1) in o2n}
    mask = silhouette(a); c = contour(mask)
    if 'C01' in COMPUTED:  # v1.1 only
        anc['C01'] = dorsal_hit(mask, anc['V1'], anc['D1'])
    semis, paths = {}, {}
    for cname, chain in CURVES.items():
        for i in range(1, len(chain) - 1, 2):
            p, n, q = chain[i - 1], chain[i], chain[i + 1]
            if CURVE_TRACE[cname] == 'edge':
                path = trace_edge(a, anc[p], anc[q])
            else:
                path = np.vstack([anc[p], arc(c, anc[p], anc[q]), anc[q]])  # route through the anchors
            paths[(p, q)] = path
            for j, xy in enumerate(resample(path, n)):
                semis[f'{cname}:{p}-{q}:{j + 1}'] = xy
    return anc, semis, paths, mask


def draw(a, anc, semis, paths, out, mask=None, title=''):
    """Draw in the PROTOCOL frame (apex left, teeth up): a, points and mask are given in the marked frame."""
    h = a.shape[0]
    a = image_to_protocol(a)
    mask = image_to_protocol(mask) if mask is not None else None
    anc = {k: to_protocol(v, h) for k, v in anc.items()}
    semis = {k: to_protocol(v, h) for k, v in semis.items()}
    paths = {k: to_protocol(v, h) for k, v in paths.items()}
    im = Image.fromarray(a).convert('RGB')
    if mask is not None:
        ov = np.array(im); ov[mask] = (0.6 * ov[mask] + 0.4 * np.array([255, 0, 255])).astype(np.uint8); im = Image.fromarray(ov)
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype('DejaVuSans-Bold.ttf', 30)
    except OSError:
        font = ImageFont.load_default()
    for (p, q), path in paths.items():
        col = (0, 170, 90) if p[0] == 'R' else (30, 110, 255)   # rachis curve green
        d.line([tuple(x) for x in path], fill=col, width=4)
    for k in range(1, 8):  # annulus bands V-R-D
        if all(f'{c}{k}' in anc for c in 'VRD'):
            d.line([tuple(anc[f'V{k}']), tuple(anc[f'R{k}']), tuple(anc[f'D{k}'])], fill=(255, 200, 0), width=2)
    for xy in semis.values():
        x, y = xy; d.ellipse([x - 7, y - 7, x + 7, y + 7], outline=(0, 0, 0), fill=(255, 255, 255), width=2)
    for pid, (x, y) in anc.items():
        if pid.startswith('C'):
            d.polygon([(x, y - 12), (x + 12, y), (x, y + 12), (x - 12, y)], fill=(150, 40, 200), outline=(0, 0, 0))
        else:
            d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=(230, 20, 20), outline=(0, 0, 0), width=2)
        dy = -44 if pid[0] in 'VT' else 14  # teeth are up in the protocol frame: V/T labels above
        d.text((x - 18, y + dy), pid, fill=(0, 0, 0), font=font, stroke_width=3, stroke_fill=(255, 255, 255))
    if title:
        d.text((30, 30), title, fill=(0, 0, 0), font=font, stroke_width=3, stroke_fill=(255, 255, 255))
    im.save(out, quality=90)


if __name__ == '__main__':
    tif, txt, out = sys.argv[1:4]
    a = load_rgb(tif)
    old = np.loadtxt(txt)[:32] * CAL
    anc, semis, paths, mask = new_config(a, old)
    draw(a, anc, semis, paths, out, mask if '--mask' in sys.argv else None,
         title=sys.argv[sys.argv.index('--title') + 1] if '--title' in sys.argv else '')
