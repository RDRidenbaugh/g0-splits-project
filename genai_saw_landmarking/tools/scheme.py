"""Single source of truth for the saw (first valvula / lancet) landmark scheme, protocol v1.2.

v1.1 (2026-09-27): adds the rachis curve (the saw side of the olistheter, which slides on the lance),
so saw and lance can be compared within individuals along their shared interface (see Saw_Landmarking_Protocol.md §8).
v1.2 (2026-09-27, lab decision after reviewing the overlays): the rachis curve stops at R7 (distal of annulus 7
the rachis fades into the tip and the semilandmarks there were inconsistent), and the pale dorsal outline curve
and its start point C01 are dropped (the faint, out-of-focus margin could not be traced reproducibly; dorsal
shape is carried by the band ends D1-D7). 52 points.

Orientation convention (applied in software, never by the digitizer): apex to the LEFT, serrulae
(teeth) UP (the protocol frame, tools/frame.py; lab convention since 2026-09-27, matching the SEM, where
the saw sits above the lance with its rachis along the lower edge). Human digitizations were made with
teeth down and are flipped top to bottom on output.

Point roles
  anchor      fixed landmark, placed by a person or a CNN heatmap
  semi        sliding semilandmark, spaced by software along a traced curve segment

Annuli are counted from the BASE (annulus 1 = most proximal complete annulus). Only annuli 1-7 carry
anchors because every specimen of both species has at least 8; the distal annuli (8 and, in
N. lecontei, 9) are crowded, often out of focus, and not the same count in the two species, so the
distal region is covered by curves plus a separate variable-count annulus record (see ANNULUS_RECORD).
"""
from collections import OrderedDict

N_ANN = 7  # anchored annuli

ANCHORS = OrderedDict()


def _a(pid, typ, name, definition, old):
    ANCHORS[pid] = dict(type=typ, name=name, definition=definition, old=old)


_a('S01', 'II', 'Apex',
   'Distal tip of the saw: the point of maximum curvature where the ventral and dorsal outlines meet.', [15])
for k, old in zip(range(1, N_ANN + 1), [1, 2, 5, 8, 10, 11, 12]):
    _a(f'V{k}', 'I', f'Annulus {k}, ventral end',
       (f'Where the dark band of annulus {k} meets the ventral (toothed) outline, i.e. the proximal base of '
        f'serrula {k}.') if k > 1 else
       ('Ventral end of the dark band of annulus 1. The ventral margin here is pale membrane, so the '
        'point is often a few um inside the outline; place it at the end of the band, not on the membrane.'), [old])
for k, old in zip(range(2, 5), [3, 6, 9]):
    _a(f'T{k}', 'II', f'Serrula {k}, tip',
       f'Distal tip of serrula {k}: the most protruding point of the tooth lobe that lies distal to V{k}, '
       f'measured perpendicular to the line V{k} -> V{k + 1} (not "lowest in the image").', [old])
for k, old in zip(range(1, N_ANN + 1), range(16, 23)):
    _a(f'R{k}', 'I', f'Annulus {k} x rachis',
       f'Where the distal (toothed) edge of annulus {k} crosses the ventral margin of the rachis '
       f'(the dark longitudinal strip).', [old])
for k, old in zip(range(1, N_ANN + 1), [23, 24, 27, 28, 29, 30, 31]):
    _a(f'D{k}', 'I' if k <= 2 else 'II', f'Annulus {k}, dorsal end',
       (f'Where annulus {k} crosses the dorsal margin of the rachis. A pale cuticle strip lies above '
        f'the rachis, so this point is inside the saw, not on its outline.') if k <= 2 else
       (f'Dorsal end of the dark band of annulus {k}, above the rachis. It lies BELOW the dorsal outline '
        f'(a pale cuticle strip separates them); do not place it on the outline.'), [old])

# Computed (Type III) points: never placed by hand.
COMPUTED = OrderedDict()  # v1.2: none (C01, the dorsal-outline start, was dropped with the dorsal curve)

# Curves: ordered chains of anchors; the integer between two anchors is the number of sliding
# semilandmarks spaced evenly (by arc length) on the outline between them.
CURVES = OrderedDict([
    ('ventral', ['V2', 1, 'T2', 2, 'V3', 1, 'T3', 2, 'V4', 1, 'T4', 2, 'V5', 3, 'V6', 3, 'V7', 6, 'S01']),
    # ventral margin of the rachis, traced as an internal edge (dark above, light below); v1.2: ends at R7
    ('rachis', ['R1', 1, 'R2', 1, 'R3', 1, 'R4', 1, 'R5', 1, 'R6', 1, 'R7']),
])

# How each curve is traced: 'outline' = silhouette contour; 'edge' = internal edge (outline.trace_edge).
CURVE_TRACE = {'ventral': 'outline', 'rachis': 'edge'}

# Old-protocol points with no new equivalent, and why.
DROPPED_OLD = OrderedDict([
    (4, 'notch after annulus 2: 95% of its inter-observer error lies along the outline -> ventral semilandmarks'),
    (7, 'notch after annulus 3: 86% along the outline -> ventral semilandmarks'),
    (13, 'annulus 8 ventral end: last annulus in N. pinetum, second-to-last in N. lecontei -> ventral curve + annulus record'),
    (14, 'N. lecontei: annulus 9; N. pinetum: pre-apical notch. Not the same structure -> removed from the fixed set'),
    (25, 'annulus 1 "most proximal part above the rachis": worst inter-observer error (19 um median), 74% across-outline'),
    (26, 'annulus 2 equivalent of 25: 12 um median error; D2 (old 24) already marks annulus 2 dorsally'),
    (32, 'annulus 8 dorsal end: same count problem as 13 -> annulus record'),
])

ANNULUS_RECORD = ('For every complete annulus (1..n, n usually 8 in N. pinetum and 9 in N. lecontei), record '
                  '(a) its crossing of the rachis curve as arc-length distance from the apex S01 in mm (the '
                  'coordinate shared with the lance, whose sutures are recorded the same way along its interface '
                  'edge), and (b) its ventral end V_k as an arc-length fraction of the ventral outline V1 -> S01. '
                  'n and the spacings are phenotypes in their own right; they are not part of the Procrustes '
                  'configuration.')


def point_order():
    """Configuration order written to files: anchors in ANCHORS order, then each curve's semilandmarks."""
    order = [(pid, 'anchor') for pid in ANCHORS] + [(pid, 'computed') for pid in COMPUTED]
    for cname, chain in CURVES.items():
        for i in range(1, len(chain) - 1, 2):
            a, n, b = chain[i - 1], chain[i], chain[i + 1]
            order += [(f'{cname}:{a}-{b}:{j + 1}', 'semi') for j in range(n)]
    return order


def curves_slider_matrix():
    """geomorph 'curves' matrix (before, slider, after), 1-based indices into point_order()."""
    order = [p for p, _ in point_order()]
    ix = {p: i + 1 for i, p in enumerate(order)}
    rows = []
    for cname, chain in CURVES.items():
        for i in range(1, len(chain) - 1, 2):
            a, n, b = chain[i - 1], chain[i], chain[i + 1]
            seq = [a] + [f'{cname}:{a}-{b}:{j + 1}' for j in range(n)] + [b]
            for j in range(1, len(seq) - 1):
                rows.append((ix[seq[j - 1]], ix[seq[j]], ix[seq[j + 1]]))
    return rows


def old_to_new():
    return {o: pid for pid, a in ANCHORS.items() for o in a['old']}


if __name__ == '__main__':
    po = point_order()
    print(len(ANCHORS), 'anchors;', sum(r == 'semi' for _, r in po), 'semilandmarks;', len(po), 'points')
    print('sliders', len(curves_slider_matrix()))
