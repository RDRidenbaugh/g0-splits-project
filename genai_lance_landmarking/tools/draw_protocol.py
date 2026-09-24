"""Render the lance landmarking protocol on a real specimen.

Fixed anchors are taken from the specimen's existing human digitization
(old-protocol ImageJ ROI) wherever the new definition coincides with an old
point; outline anchors are snapped to the segmented cuticle outline; curve
semilandmarks are resampled at equal arc length along that outline; Type III
points are computed. This is the same post-processing the deep-learning
pipeline would apply to predicted anchors + predicted outline.

usage: python draw_protocol.py <key> <out_dir>
       key = manifest key stem, e.g. feb1xpbx012-1-v35
"""
import csv, json, sys, os
import numpy as np, tifffile
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from skimage.filters import threshold_otsu, gaussian
from skimage.measure import find_contours
from skimage.morphology import disk, opening, closing

LANCE = "/home/labradorite/g0-splits-project/lance_landmarking/cnn/"  # the manifests live here; their image paths are relative to it
sys.path.insert(0, os.path.dirname(__file__))
from scheme import SCHEME  # noqa: E402


def load(key, angle):
    for r in csv.DictReader(open(LANCE + "manifest.csv")):
        if r["key"].rsplit("_", 1)[0] == key and r["angle"] == angle:
            img = tifffile.imread(LANCE + r["raw_image"])[..., :3]
            return img, np.array(json.loads(r["landmarks_px_json"]))
    raise KeyError(key, angle)


def outline(img, old, mode="sclerite", erase=None):
    """Main sclerotized-cuticle outline as an (N,2) xy closed contour, sub-pixel."""
    # sclerite = amber (R >> B) or dark (heavily sclerotized ventral band and
    # tips, which are near-black). Background and the pale membrane fringe
    # around the heel are neither, so they drop out.
    a = gaussian(img.astype(float), 2, channel_axis=-1)
    rb = a[..., 0] - a[..., 2]
    lum = a.mean(2)
    bg_lum = np.median(np.r_[lum[:30].ravel(), lum[-30:].ravel()])
    scl = (rb > threshold_otsu(rb)) | (lum < 0.6 * bg_lum)
    b = np.concatenate([a[:30].reshape(-1, 3), a[-30:].reshape(-1, 3)])
    d = np.linalg.norm(a - np.median(b, 0), axis=2)
    bgm = d > max(threshold_otsu(d), 25)
    if mode == "sclerite":
        m = scl
    elif mode == "background":  # anything that differs from the background colour
        m = bgm
    else:  # "bottom": whole dorsal view
        # distal to the 4th-from-apex sutures the purple-tinged tips fail the
        # sclerite test, so use the background mask there; proximally use the
        # sclerite mask (drops the pale membrane over the basal lobes) opened
        # hard enough to cut off the thin golden rods attached to the lobes
        base = (old[4] + old[16]) / 2
        ax = (old[0] + old[12]) / 2 - base
        ax /= np.linalg.norm(ax)
        yy, xx = np.mgrid[: img.shape[0], : img.shape[1]]
        distal = (xx - base[0]) * ax[0] + (yy - base[1]) * ax[1] > 0
        m = np.where(distal, bgm, opening(scl, disk(14)))
    m = closing(opening(m, disk(4)), disk(6))
    m = ndi.binary_fill_holes(m)
    for poly in erase or []:  # hand cuts: attached rods / flaps that touch the lance
        from skimage.draw import polygon as _poly
        rr, cc = _poly([q[1] for q in poly], [q[0] for q in poly], m.shape)
        m[rr, cc] = False
    lab, _ = ndi.label(m)
    ids = [lab[int(y), int(x)] for x, y in old if lab[int(y), int(x)] > 0]
    m = lab == np.bincount(ids).argmax()
    c = max(find_contours(gaussian(m.astype(float), 1.5), 0.5), key=len)
    return c[:, ::-1]


def arc_indices(n, i, j, avoid):
    """Contour indices from i to j (inclusive) along the arc not containing avoid."""
    fwd = [(i + k) % n for k in range((j - i) % n + 1)]
    if avoid in fwd:
        fwd = [(i - k) % n for k in range((i - j) % n + 1)]
    return fwd


def resample(pts, k):
    """k interior points at equal arc length along polyline pts."""
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    t = np.linspace(0, s[-1], k + 2)[1:-1]
    return np.c_[np.interp(t, s, pts[:, 0]), np.interp(t, s, pts[:, 1])]


EDITS = json.load(open(os.path.join(os.path.dirname(__file__), "mask_edits.json")))


def build(angle, img, old, key=""):
    sch = SCHEME[angle]
    C = outline(img, old, sch["mask"], EDITS.get(f"{key}/{angle}", {}).get("erase"))
    # uniform ~2 px spacing so curvature windows mean the same thing everywhere
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))]
    t = np.arange(0, s[-1], 2.0)
    C = np.c_[np.interp(t, s, C[:, 0]), np.interp(t, s, C[:, 1])]
    near = lambda p: int(np.argmin(np.linalg.norm(C - p, axis=1)))
    P, kind = {}, {}
    for name, spec in sch["anchors"].items():
        if spec["old"] is None:
            continue  # new anchor with no old-protocol equivalent; located below
        p = old[spec["old"] - 1].astype(float)
        if spec.get("snap"):
            p = C[near(p)]
        P[name], kind[name] = p, "anchor"
    # For the figures only: anchors that have no human digitization yet are
    # located by the geometric rule that encodes their definition, then
    # checked by eye. In production they are clicked / predicted like any anchor.
    for name, spec in sch["anchors"].items():
        if spec["old"] is None:
            P[name], kind[name] = spec["locate"](P, C, near), "anchor"
    for name, spec in sch.get("computed", {}).items():
        P[name], kind[name] = spec["fn"](P, C, near), "computed"
    curves = []
    for cv in sch["curves"]:
        if cv["path"] == "outline":
            idx = arc_indices(len(C), near(P[cv["from"]]), near(P[cv["to"]]), near(P[cv["avoid"]]))
            poly = C[idx]
            poly[0], poly[-1] = P[cv["from"]], P[cv["to"]]
        else:  # interior curve through listed points (old human points as guides)
            poly = np.array([P[n] if isinstance(n, str) else old[n - 1] for n in cv["through"]], float)
        if cv.get("slide_old"):
            semis = np.array([old[n - 1] for n in cv["slide_old"]], float)
        else:
            semis = resample(poly, cv["n"])
        for k, s in enumerate(semis):
            P[f"{cv['name']}{k + 1}"], kind[f"{cv['name']}{k + 1}"] = s, "semi"
        curves.append((cv["name"], poly, semis))
    return C, P, kind, curves


def render(angle, img, C, P, kind, curves, out, scale):
    allp = np.array(list(P.values()))
    x0, y0 = allp.min(0) - 110
    x1, y1 = allp.max(0) + 110
    # show the whole structure (e.g. the basal lobes) for context, but not far-off debris
    cx0, cy0 = np.maximum(C.min(0) - 40, allp.min(0) - 600)
    cx1, cy1 = np.minimum(C.max(0) + 40, allp.max(0) + 600)
    x0, y0, x1, y1 = min(x0, cx0), min(y0, cy0), max(x1, cx1), max(y1, cy1)
    im = Image.fromarray(img).crop((int(x0), int(y0), int(x1), int(y1)))
    im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    dr = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(15 * max(scale, 0.8)))
    except OSError:
        f = ImageFont.load_default()
    T = lambda p: ((p[0] - x0) * scale, (p[1] - y0) * scale)
    for name, poly, semis in curves:
        dr.line([T(p) for p in poly], fill=(0, 190, 255), width=2)
    r = 6
    for name, p in P.items():
        x, y = T(p)
        if kind[name] == "semi":
            dr.ellipse((x - 4, y - 4, x + 4, y + 4), outline=(0, 120, 255), fill=(255, 255, 255), width=2)
        elif kind[name] == "computed":
            dr.polygon([(x, y - 8), (x + 8, y), (x, y + 8), (x - 8, y)], fill=(170, 0, 200), outline="white")
        elif kind[name] == "occluded":  # position is a guess: hidden by membrane/flap
            dr.ellipse((x - r - 2, y - r - 2, x + r + 2, y + r + 2), outline=(230, 20, 20), width=3)
        else:
            dr.ellipse((x - r, y - r, x + r, y + r), fill=(230, 20, 20), outline="white", width=2)
    for name, p in P.items():
        if kind[name] == "semi":
            continue
        x, y = T(p)
        off = SCHEME[angle]["label_offset"].get(name, (9, -20))
        label = name + (" (occluded)" if kind[name] == "occluded" else "")
        dr.text((x + off[0], y + off[1]), label, fill="black", font=f, stroke_width=3, stroke_fill="white")
    im.save(out, quality=92)


if __name__ == "__main__":
    key, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    summary = {}
    for angle in ("Right", "Left", "Bottom"):
        img, old = load(key, angle)
        C, P, kind, curves = build(angle, img, old, key)
        scale = SCHEME[angle]["render_scale"]
        for n in EDITS.get(f"{key}/{angle}", {}).get("occluded", []):
            kind[n] = "occluded"
        render(angle, img, C, P, kind, curves, f"{outdir}/protocol_{angle}_{key}.jpg", scale)
        summary[angle] = {k: sum(1 for v in kind.values() if v == k) for k in ("anchor", "occluded", "computed", "semi")}
    print(key, summary)
