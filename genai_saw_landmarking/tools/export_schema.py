"""Write landmark_schema.json from tools/scheme.py."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import scheme

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = dict(
    protocol='Neodiprion saw (first valvula) landmark + semilandmark protocol',
    version='1.2', date='2026-09-27',
    orientation='protocol frame: apex LEFT, serrulae (teeth) UP; images are mirrored left-right when needed and flipped top to bottom in software (tools/frame.py)',
    calibration='per image, from its own burned-in scale bar (tools/scalebar.py; analysis/data/calibration.csv)',
    n_points=len(scheme.point_order()),
    anchors=scheme.ANCHORS,
    computed=scheme.COMPUTED,
    curves={k: v for k, v in scheme.CURVES.items()},
    curve_trace=scheme.CURVE_TRACE,
    point_order=[dict(id=p, role=r) for p, r in scheme.point_order()],
    geomorph_curves=scheme.curves_slider_matrix(),
    old_to_new={str(k): v for k, v in scheme.old_to_new().items()},
    old_dropped={str(k): v for k, v in scheme.DROPPED_OLD.items()},
    annulus_record=scheme.ANNULUS_RECORD,
)
json.dump(out, open(os.path.join(ROOT, 'landmark_schema.json'), 'w'), indent=1)
print('wrote landmark_schema.json:', out['n_points'], 'points')
