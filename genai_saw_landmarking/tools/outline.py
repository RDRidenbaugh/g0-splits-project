"""Saw silhouette and outline arcs between anchors (used for figures and automatic curve labels)."""
import numpy as np
from scipy import ndimage as ndi
from skimage import filters, measure, morphology


def silhouette(a):
    """Boolean mask of the saw. Background colour varies by session (green/pink/grey/white), so the
    foreground is 'far from the border colour' in RGB, thresholded by Otsu, largest component, holes filled."""
    f = a.astype(float)
    border = np.concatenate([f[:40].reshape(-1, 3), f[-40:].reshape(-1, 3), f[:, :40].reshape(-1, 3)])
    bg = np.median(border, 0)
    dist = np.sqrt(((f - bg) ** 2).sum(2))
    dist = filters.gaussian(dist, 2)
    m = dist > filters.threshold_otsu(dist) * 0.6
    m = morphology.binary_opening(m, morphology.disk(3))
    lab = measure.label(m)
    if lab.max() == 0:
        return m
    k = np.argmax(np.bincount(lab.ravel())[1:]) + 1
    return ndi.binary_fill_holes(lab == k)


def contour(mask):
    cs = measure.find_contours(mask.astype(float), 0.5)
    c = max(cs, key=len)[:, ::-1]  # (x, y)
    return c


def arc(c, p, q):
    """Shorter contour path from the contour point nearest p to the one nearest q, as (x, y) array."""
    i = int(np.argmin(((c - p) ** 2).sum(1))); j = int(np.argmin(((c - q) ** 2).sum(1)))
    n = len(c)
    fwd = (j - i) % n; bwd = (i - j) % n
    idx = [(i + t) % n for t in range(fwd + 1)] if fwd <= bwd else [(i - t) % n for t in range(bwd + 1)]
    return c[idx]


def resample(path, n):
    """n interior points evenly spaced by arc length (end points excluded)."""
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    t = np.linspace(0, d[-1], n + 2)[1:-1]
    return np.c_[np.interp(t, d, path[:, 0]), np.interp(t, d, path[:, 1])]


def trace_edge(a, p, q, polarity=+1, band=40, sigma=2.0):
    """Minimum-cost path from p to q along an internal edge (e.g. the ventral margin of the rachis).
    polarity=+1: darker on the dorsal side of the p->q direction (image up when apex is left), lighter ventrally.
    Returns an (x, y) path including p and q."""
    from skimage import color, graph
    from scipy import ndimage as ndi
    p = np.asarray(p, float); q = np.asarray(q, float)
    x0, y0 = np.floor(np.minimum(p, q) - band).astype(int); x1, y1 = np.ceil(np.maximum(p, q) + band).astype(int)
    h, w = a.shape[:2]; x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, w - 1), min(y1, h - 1)
    g = ndi.gaussian_filter(color.rgb2gray(a[y0:y1 + 1, x0:x1 + 1]), sigma)
    gy, gx = np.gradient(g)
    t = (q - p) / np.linalg.norm(q - p)
    n = np.array([-t[1], t[0]])            # normal; with apex-left (t points left/distal) this points ventral (+y)
    if n[1] < 0:
        n = -n
    edge = polarity * (gx * n[0] + gy * n[1])   # >0 where brightness rises ventrally
    edge = np.clip(edge / (np.percentile(edge, 99) + 1e-9), 0, 1)
    # keep the path inside a band around the chord
    yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
    d = np.abs((xx - p[0]) * n[0] + (yy - p[1]) * n[1])
    cost = 1.0 / (0.02 + edge) + np.where(d > band, 1e3, 0)
    s = (int(round(p[1] - y0)), int(round(p[0] - x0))); e = (int(round(q[1] - y0)), int(round(q[0] - x0)))
    path, _ = graph.route_through_array(cost, s, e, fully_connected=True, geometric=True)
    path = np.array(path)[:, ::-1] + [x0, y0]
    return np.vstack([p, path, q]).astype(float)
