"""Per-image calibration from the burned-in scale bar (used for every saw and lance image).

Bars seen in this project:
  saw, ZEN, black, 10-px end ticks, 0.1 or 0.2 mm       e.g. 224 px outer / 214 px tick-centre = 0.1 mm
  saw, ZEN, red, 2-px end ticks, 0.2 mm (2024 sessions)  434 px outer / 432 px tick-centre
  lance, red line without ticks, 1 mm (3840x2160)        ~918-929 px
The bar's length is measured between tick CENTRES when there are ticks (the drawing software places
the nominal length there), otherwise over the whole line. The printed value (0.1 mm, 0.2 mm, 1 mm ...)
is not read by OCR: it is the round length whose px/mm is closest to the system's nominal scale.
Round lengths differ by >= 2x, so a nominal within +-30% picks the label unambiguously; the result is
flagged (and not used) when it is more than 2% from nominal: a broken bar or a real magnification change. Sessions differ by <= 1%.
"""
import numpy as np
from scipy import ndimage as ndi

ROUND_MM = np.array([0.02, 0.05, 0.1, 0.2, 0.25, 0.5, 1.0, 2.0])


def bar_mask(a):
    a = a.astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    black = (r < 70) & (g < 70) & (b < 70)
    red = (r > 150) & (g < 90) & (b < 90)
    return black, red


def _measure(comp):
    """comp: boolean crop of one component. Returns (length_px, thickness, has_ticks) or None."""
    h, w = comp.shape
    colh = comp.sum(0)
    if w < 120:
        return None
    mid = colh[w // 4: 3 * w // 4]
    thick = int(np.median(mid))
    if thick == 0 or thick > 16 or (mid == 0).mean() > 0.02:
        return None  # not a continuous thin horizontal line
    tall = np.flatnonzero(colh > thick + 3)
    edge = max(w // 10, 12)
    left, right = tall[tall < edge], tall[tall >= w - edge]
    if len(left) and len(right):
        # first contiguous run of tall columns at the left end, last one at the right end
        l_run = np.split(left, np.flatnonzero(np.diff(left) > 1) + 1)[0]
        r_run = np.split(right, np.flatnonzero(np.diff(right) > 1) + 1)[-1]
        return float(r_run.mean() - l_run.mean()), thick, True
    xs = np.flatnonzero(colh > 0)
    return float(xs.max() - xs.min() + 1), thick, False


def find_bar(a, bottom_frac=0.35):
    """Return dict(length_px, colour, ticks, thickness, box) for the best bar candidate, or None."""
    h, w, _ = a.shape
    y0 = int(h * (1 - bottom_frac))
    black, red = bar_mask(a[y0:])
    best = None
    for colour, m in (('black', black), ('red', red)):
        lab, n = ndi.label(m)
        for i, sl in enumerate(ndi.find_objects(lab), 1):
            if sl is None:
                continue
            comp = lab[sl] == i
            if comp.shape[1] < 120 or comp.shape[0] > 120:
                continue
            r = _measure(comp)
            if r and (best is None or r[0] > best['length_px']):
                best = dict(length_px=r[0], colour=colour, ticks=r[2], thickness=r[1],
                            box=(sl[1].start, sl[0].start + y0, sl[1].stop, sl[0].stop + y0),
                            truncated=sl[1].start <= 1 or sl[1].stop >= w - 1)
    return best


def calibrate(a, nominal_px_per_mm):
    """px/mm from the image's own bar. Returns (px_per_mm, bar_mm, info, flags)."""
    b = find_bar(a)
    if b is None:
        return None, None, None, ['no_bar']
    if b['truncated']:
        return None, None, b, ['bar_truncated']  # runs off the frame: its length is unknown
    cand = b['length_px'] / ROUND_MM
    k = int(np.argmin(np.abs(np.log(cand / nominal_px_per_mm))))
    ppm = float(cand[k]); flags = []
    if abs(np.log(ppm / nominal_px_per_mm)) > np.log(1.02):
        return None, float(ROUND_MM[k]), b, ['bar_far_from_nominal']  # broken bar or zoom change: review
    return ppm, float(ROUND_MM[k]), b, flags
