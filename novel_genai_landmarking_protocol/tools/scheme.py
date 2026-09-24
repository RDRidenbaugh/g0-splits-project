"""Single source of truth for the lance landmarking protocol (v1.4).

anchors  : fixed landmarks a human (or the CNN) places directly.
           old  = matching point number in Lance_Imaging_Morphometrics_v2
                  (used to seed the figures and to migrate existing data).
           snap = the point lies on the cuticle outline.
computed : Type III points derived geometrically, never hand-placed.
curves   : sliding-semilandmark curves, resampled at equal arc length
           between two anchors (path="outline") or along an interior margin.
"""
import numpy as np


def _dorsal_start(apex, heel, window0, ventral_ref):
    """Start of the dorsal curve (v1.4): moving dorsally from the window's
    proximal end (R11/L11) along the line perpendicular to the lance's own axis
    (heel-ventral junction -> apex), the first place the line reaches the
    lance's dorsal edge. Computed, never clicked.

    v1.3 used the line through the suture-1 ventral end instead. That start lies
    next to the heel, where the golden basal flap often sits over the dorsal
    margin, and all the curve's evenly spaced semilandmarks hang from it; in the
    round-2 comparison the window-level start gave better repeatability and no
    failures on never-seen specimens with flaps. "First" crossing: a flap above
    the edge is crossed further up and is never taken."""
    def fn(P, C, near):
        L = np.linalg.norm(P[apex] - P[heel])
        ax = (P[apex] - P[heel]) / L
        nr = np.array([-ax[1], ax[0]])
        up = np.sign((P[window0] - P[ventral_ref]) @ nr)  # dorsal side (the window lies dorsal of the ventral margin)
        rel = C - P[window0]
        along, across = rel @ ax, up * (rel @ nr)
        cand = np.flatnonzero((np.abs(along) < 3) & (across > 0))
        return C[cand[np.argmin(across[cand])]]
    return fn


def _bottom_frame(P):
    """Lance-intrinsic frame for the Bottom view: origin between the two
    4th-from-apex sutures, unit long axis toward the apices, unit normal."""
    base = (P["B06"] + P["B10"]) / 2
    ax = (P["B01"] + P["B02"]) / 2 - base
    ax /= np.linalg.norm(ax)
    return base, ax, np.array([-ax[1], ax[0]])


def _arc(C, i, j, avoid):
    n = len(C)
    arc = [(i + k) % n for k in range((j - i) % n + 1)]
    if avoid in arc:
        arc = [(i - k) % n for k in range((i - j) % n + 1)]
    return np.array(arc)


def _basal_notch(P, C, near):
    # deepest (most distal) point of the median emargination in the proximal
    # margin, i.e. the most distal outline point near the midline, proximal to the lobes
    base, ax, nr = _bottom_frame(P)
    t, l = (C - base) @ ax, (C - base) @ nr
    # "near the midline" is judged against the shaft width at the 4th sutures,
    # not the widest lateral extent, which attached flaps can inflate
    sw = np.linalg.norm(P["B06"] - P["B10"])
    cand = (t < -0.5 * sw) & (np.abs(l) < 0.3 * sw)
    idx = np.flatnonzero(cand)
    return C[idx[np.argmax(t[idx])]]


def _turning(C, w):
    """Signed turning angle at each contour point over +-w points; positive = convex."""
    a, b = C - np.roll(C, w, 0), np.roll(C, -w, 0) - C
    ang = np.arctan2(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0], (a * b).sum(1))
    area = 0.5 * np.sum(C[:, 0] * np.roll(C[:, 1], -1) - np.roll(C[:, 0], -1) * C[:, 1])
    return ang * np.sign(area)


def _first_deep_concavity(pts, depth):
    """Deepest point of the first concavity along an open outline arc that is
    deeper than `depth` below the arc's convex envelope; None if there is none."""
    from scipy.spatial import ConvexHull
    if len(pts) < 4:
        return None
    hv = np.sort(ConvexHull(pts).vertices)
    for a, b in zip(hv[:-1], hv[1:]):
        if b - a < 3:
            continue
        p, q = pts[a], pts[b]
        d = q - p
        dep = np.abs(d[0] * (pts[a:b, 1] - p[1]) - d[1] * (pts[a:b, 0] - p[0])) / np.linalg.norm(d)
        if dep.max() > depth:
            return a + int(np.argmax(dep))
    return None


def _without_attachments(C, P, sw):
    """Outline with attached flaps/rods cut off: morphological opening of the
    filled outline with a disk of radius sw/3 (sw = shaft width at the 4th-from-
    apex sutures), keeping the piece that contains the median notch. Anything
    joined to the lance by a neck narrower than 2/3 of the shaft width falls
    away; the lance body proximal to the 4th sutures is wider than that, and an
    opening leaves concave corners such as the shoulder in place. Used only to
    search for the shoulder."""
    from scipy import ndimage as ndi
    from skimage.draw import polygon
    from skimage.measure import find_contours
    from skimage.morphology import disk, opening
    f = 4  # work at 1/4 resolution
    lo = C.min(0) - 5
    Q = (C - lo) / f
    shp = (int(Q[:, 1].max()) + 3, int(Q[:, 0].max()) + 3)
    m = np.zeros(shp, bool)
    rr, cc = polygon(Q[:, 1], Q[:, 0], shp)
    m[rr, cc] = True
    m = opening(m, disk(max(2, int(round(sw / 3 / f)))))
    lab, _ = ndi.label(m)
    probe = (P["B11"] - lo) / f
    # the notch lies on the edge, so take the component nearest to it
    ys, xs = np.nonzero(lab)
    k = np.argmin((xs - probe[0]) ** 2 + (ys - probe[1]) ** 2)
    m = lab == lab[ys[k], xs[k]]
    c = max(find_contours(m.astype(float), 0.5), key=len)[:, ::-1] * f + lo
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(c, axis=0), axis=1))]
    t = np.arange(0, s[-1], 2.0)
    return np.c_[np.interp(t, s, c[:, 0]), np.interp(t, s, c[:, 1])]


def _shoulder(suture):
    """Shoulder of the basal lobe on the side of the given 4th-from-apex suture:
    where the outer margin begins to curve outward into the lobe.

    Definition: moving proximally along the outer margin from that suture, the
    first concavity deeper than 0.15 x the shaft width at the 4th sutures,
    measured from the margin's convex envelope (a straight edge laid against
    the shaft margin and the front of the lobe); B12/B13 is its deepest point.
    Serration dents are far shallower than the threshold, and concavities on
    the lobe itself come after the shoulder.

    The shoulder always lies well distal to B11's level on the long axis. If
    the result is within 5% of the B11-to-apex length of that level (or behind it), a foreign structure (a rod or the basal flap) is
    merged into the outline; no guess is made -- the point is flagged for
    manual placement."""
    def fn(P, C, near):
        sw = np.linalg.norm(P["B06"] - P["B10"])
        tip = (P["B01"] + P["B02"]) / 2
        ax = (tip - P["B11"]) / np.linalg.norm(tip - P["B11"])
        Cs = _without_attachments(C, P, sw)
        near_s = lambda p: int(np.argmin(np.linalg.norm(Cs - p, axis=1)))
        pts = Cs[_arc(Cs, near_s(P[suture]), near_s(P["B11"]), near_s(P["B01"]))]
        k = _first_deep_concavity(pts, 0.15 * sw)
        # a real shoulder sits well distal to B11 (median 30% of the way to
        # the apices in a 40-specimen test); anything within 5% is a merged structure
        if k is None or (pts[k] - P["B11"]) @ ax < 0.05 * np.linalg.norm(tip - P["B11"]):
            raise ValueError("shoulder not found distal to B11: outline has a merged "
                             "rod/flap; place by hand")
        return C[near(pts[k])]  # back onto the real outline
    return fn


def _fork_crotch(P, C, near):
    # deepest point of the fork: on the medial arc between the two apices,
    # the point closest to the base along the lance's own long axis
    # (axis runs from the median basal notch B11 to the midpoint of the apices)
    base = P["B11"]
    tip = (P["B01"] + P["B02"]) / 2
    ax = (tip - base) / np.linalg.norm(tip - base)
    i, j, avoid = near(P["B01"]), near(P["B02"]), near(P["B04"])
    n = len(C)
    arc = [(i + k) % n for k in range((j - i) % n + 1)]
    if avoid in arc:
        arc = [(i - k) % n for k in range((i - j) % n + 1)]
    arc = np.array(arc)
    return C[arc[np.argmin((C[arc] - base) @ ax)]]


def _lateral(side, n_sut, old_apex, old_split, old_win_end, dropped_old):
    s = side
    a = {
        f"{s}01": dict(old=old_apex, snap=(s == "R"), type="II", name="apex"),
        f"{s}02": dict(old=3, snap=True, type="I", name="heel-ventral junction"),
        f"{s}03": dict(old=1, snap=True, type="II", name="proximal heel notch"),
    }
    k = 4
    for i in range(n_sut):
        a[f"{s}{k:02d}"] = dict(old=4 + i, snap=True, type="I", name=f"suture {i + 1} ventral end")
        k += 1
    if old_split:
        a[f"{s}{k:02d}"] = dict(old=old_split, snap=True, type="II", name="ventral split point")
        k += 1
    win0 = k
    a[f"{s}{k:02d}"] = dict(old=14, snap=False, type="I", name="window proximal end"); k += 1
    tops = []
    for i, o in enumerate((15, 17, 19, 21, 23)):
        a[f"{s}{k:02d}"] = dict(old=o, snap=False, type="I", name=f"suture {i + 2} dorsal end")
        tops.append(f"{s}{k:02d}"); k += 1
    a[f"{s}{k:02d}"] = dict(old=old_win_end, snap=False, type="I", name="window distal end")
    win1 = k; k += 1
    comp = f"{s}{k:02d}"
    distal_start = f"{s}{win0 - 1:02d}"  # split point if present, else last suture
    return dict(
        anchors=a,
        computed={comp: dict(fn=_dorsal_start(f"{s}01", f"{s}02", f"{s}{win0:02d}", f"{s}04"), type="III",
                             name="dorsal curve start: first point where the line through the window's proximal "
                                  "end, perpendicular to the heel-ventral junction -> apex axis, reaches the "
                                  "lance's dorsal edge (not the basal flap above it)")},
        curves=[
            dict(name=f"{s}.heel", path="outline", **{"from": f"{s}03"}, to=f"{s}02", avoid=f"{s}01", n=4),
            dict(name=f"{s}.vbase", path="outline", **{"from": f"{s}02"}, to=f"{s}04", avoid=f"{s}01", n=2),
            # Left: distal to the split the short half's ventral edge is an interior
            # edge (the long half's tip forms the silhouette), so trace it, not the outline
            dict(name=f"{s}.vdist", path="outline", **{"from": distal_start}, to=f"{s}01", avoid=f"{s}02", n=4)
            if s == "R" else
            dict(name=f"{s}.vdist", path="interior", through=[distal_start, 11, 12, f"{s}01"],
                 slide_old=[11, 12], n=2),
            dict(name=f"{s}.dorsal", path="outline", **{"from": comp}, to=f"{s}01", avoid=f"{s}02", n=10),
            dict(name=f"{s}.window", path="interior",
                 through=[f"{s}{win0:02d}", tops[0], 16, tops[1], 18, tops[2], 20, tops[3], 22, tops[4],
                          f"{s}{win1:02d}"],
                 slide_old=[16, 18, 20, 22], n=4),
        ],
        dropped_old=dropped_old,
    )


SCHEME = {
    "Right": _lateral("R", 7, old_apex=13, old_split=None, old_win_end=25,
                      dropped_old=[2, 11, 12, 24, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36]),
    "Left": _lateral("L", 6, old_apex=13, old_split=10, old_win_end=24,
                     dropped_old=[2, 25, 26, 27, 28, 29, 30, 31, 32]),
    "Bottom": dict(
        anchors={
            "B01": dict(old=1, snap=True, type="II", name="long-half apex"),
            "B02": dict(old=13, snap=True, type="II", name="short-half apex"),
            **{f"B{3 + i:02d}": dict(old=2 + i, snap=True, type="I",
                                     name=f"long half, suture {i + 1} from apex, outer end") for i in range(4)},
            **{f"B{7 + i:02d}": dict(old=14 + i, snap=True, type="I",
                                     name=f"short half, suture {i + 1} from apex, outer end") for i in range(4)},
            # proximal (basal) region -- no old-protocol equivalent
            "B11": dict(old=None, snap=True, type="II", locate=_basal_notch,
                        name="median basal notch: deepest point of the proximal median emargination between the two basal lobes"),
            "B12": dict(old=None, snap=True, type="II", locate=_shoulder("B06"),
                        name="long half shoulder: where the outer margin begins to curve outward into the basal lobe -- deepest point of the first concavity (>0.15 shaft widths) proximal to the 4th-from-apex suture, measured from a straight edge laid against the shaft margin and the front of the lobe"),
            "B13": dict(old=None, snap=True, type="II", locate=_shoulder("B10"),
                        name="short half shoulder (as B12)"),
        },
        computed={"B14": dict(fn=_fork_crotch, type="III", name="fork crotch")},
        curves=[
            dict(name="B.medL", path="outline", **{"from": "B14"}, to="B01", avoid="B02", n=3),
            dict(name="B.medS", path="outline", **{"from": "B14"}, to="B02", avoid="B01", n=3),
            dict(name="B.outL", path="outline", **{"from": "B03"}, to="B01", avoid="B14", n=3),
            dict(name="B.outS", path="outline", **{"from": "B07"}, to="B02", avoid="B14", n=3),
            # outer margin of each half from the 4th-from-apex suture back along
            # the shaft to the shoulder. Nothing proximal to the shoulders is
            # sampled: that margin can be hidden by membrane or the basal flap.
            dict(name="B.sideL", path="outline", **{"from": "B06"}, to="B12", avoid="B01", n=6),
            dict(name="B.sideS", path="outline", **{"from": "B10"}, to="B13", avoid="B01", n=6),
        ],
        dropped_old=[6, 7, 8, 9, 10, 11, 12],
    ),
}

for v in SCHEME.values():
    v.setdefault("label_offset", {})
SCHEME["Right"]["render_scale"] = 0.9
SCHEME["Left"]["render_scale"] = 0.9
SCHEME["Bottom"]["render_scale"] = 0.9
# lateral views: exclude the pale membrane fringe at the heel; Bottom has no
# fringe but its purple-tinged tips fail the amber/dark test
SCHEME["Right"]["mask"] = SCHEME["Left"]["mask"] = "sclerite"
SCHEME["Bottom"]["mask"] = "bottom"
