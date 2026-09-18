"""Shared constants for the lance-landmarking CNN pipeline.

Landmark numbering and anchor/derived classification below are transcribed
from Lance_Imaging_Morphometrics_v2.docx's per-view landmark definitions
(1-indexed, matching the order landmarks are clicked/exported in). "Anchor"
points are independently-perceived anatomical features; "derived" points are
explicitly defined in the protocol as arithmetic/geometric functions of
other landmarks (e.g. "two equidistant points between point 10 and the
tip", "point directly above landmark N") rather than independently placed.

v1 trains heatmaps on ALL points (anchor + derived) rather than
reconstructing derived points geometrically post-hoc -- the protocol's
"equidistant"/"directly above" language isn't precise enough (equidistant
along a straight line vs. along the curved edge? "directly above" in image
Y or normal-to-the-edge?) to hard-code a formula with confidence, and
heatmap CNNs routinely learn this kind of local interpolation fine on
their own. ANCHOR_1INDEXED is kept here so a future iteration can restrict
the loss/eval to anchors, or build a geometric reconstruction, without
re-deriving this from the protocol text again.
"""
from __future__ import annotations

ANGLES = ("Bottom", "Left", "Right")

EXPECTED_N = {"Bottom": 17, "Left": 32, "Right": 36}

# 1-indexed landmark numbers that are independently-perceived anatomical
# points (as opposed to "equidistant between X and Y" / "directly above
# landmark N" derived points). Complement of this set, within 1..N, is derived.
ANCHOR_1INDEXED = {
    "Bottom": {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17},
    "Left": {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25},
    "Right": {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 25, 28, 29},
}


def anchor_mask(angle: str) -> list[bool]:
    n = EXPECTED_N[angle]
    anchors = ANCHOR_1INDEXED[angle]
    return [(i + 1) in anchors for i in range(n)]


# --- image / heatmap geometry ---
INPUT_SIZE = 512          # network input is INPUT_SIZE x INPUT_SIZE, letterboxed
HEATMAP_STRIDE = 4        # output heatmap is INPUT_SIZE/HEATMAP_STRIDE per side
HEATMAP_SIZE = INPUT_SIZE // HEATMAP_STRIDE
HEATMAP_SIGMA = 2.0       # gaussian sigma, in heatmap-pixel units

MANIFEST_PATH = "manifest.csv"  # relative to lance_landmarking/
