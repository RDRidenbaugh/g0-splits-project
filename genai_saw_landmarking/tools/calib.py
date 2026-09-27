"""Per-image px/mm lookup from analysis/data/calibration.csv (built by tools/calibration_survey.py).

Every image is calibrated from its own scale bar (cal_source own_bar). Images without a usable bar get
the median of their imager/session (cal_source session_median) so interim analyses run; they are listed
in calibration_problems.csv and should be re-exported with a bar."""
import csv, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CAL = None


def _load():
    global _CAL
    if _CAL is None:
        _CAL = {}
        for r in csv.DictReader(open(os.path.join(ROOT, 'analysis/data/calibration.csv'))):
            ppm = r['px_per_mm'] or r['px_per_mm_session']
            key = (r['kind'], os.path.splitext(os.path.basename(r['image']))[0].upper())
            _CAL[key] = (float(ppm) if ppm else None, r['cal_source'])
    return _CAL


def px_per_mm(kind, stem):
    """(px/mm, cal_source) for an image stem (file name without extension, any case), or (None, 'none')."""
    return _load().get((kind, stem.upper()), (None, 'none'))


def saw_px_per_mm_for_label(txt_rel, nominal=2141.4):
    """Calibration for a digitized saw: its raw image's own bar; if the raw file is missing or named
    differently, the bar in the marked TIFF itself (same pixel grid, mirrored bar)."""
    import glob, re
    stem = re.sub(r'_(MARK|XY)_[A-Z]+$', '', os.path.splitext(os.path.basename(txt_rel))[0])
    ppm, src = px_per_mm('saw', stem)
    if ppm:
        return ppm, src
    for (kind, s), v in _load().items():  # side missing from the txt name (e.g. 097_04_F1 -> 097_04_F1_L)
        if kind == 'saw' and re.fullmatch(re.escape(stem.upper()) + r'_[LR](_V\d+)?', s) and v[0]:
            return v[0], v[1] + '_by_prefix'
    from scalebar import calibrate
    from draw_protocol import load_rgb
    d = os.path.join(ROOT, os.path.dirname(os.path.dirname(txt_rel)), 'marked')
    for f in glob.glob(os.path.join(d, '*.tif')):
        if os.path.basename(f).rsplit('_', 2)[0].upper() == stem.upper():
            ppm, _, _, flags = calibrate(load_rgb(f), nominal)
            if ppm:
                return ppm, 'own_bar_marked_tif'
    return None, 'none'
