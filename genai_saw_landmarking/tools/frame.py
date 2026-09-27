"""Image frames for the saw.

marked frame    apex LEFT, teeth DOWN: the frame the old human digitizations and the marked TIFFs use
                (raw images mirrored horizontally when needed). Human points are read in this frame.
protocol frame  apex LEFT, teeth UP (lab convention from 2026-09-27): the marked frame flipped top to bottom,
                so the saw is shown the way it sits on the lance (as in the SEM: saw above, its rachis along
                the lower edge against the lance). Every output is in this frame: labels, figures, overlays,
                the prepared CNN images and the mm export. Point names stay anatomical (V/T = ventral, toothed).

Coordinates are continuous pixel positions with the origin at the top-left image corner, so a top-to-bottom
flip of an image of height H maps y -> H - y (and x is unchanged).
"""
import numpy as np


def to_protocol(pts, height):
    """Marked-frame points (..., 2) -> protocol frame."""
    p = np.array(pts, dtype=float, copy=True)
    p[..., 1] = height - p[..., 1]
    return p


def image_to_protocol(a):
    """Marked-frame image -> protocol frame (flip top to bottom)."""
    return np.ascontiguousarray(a[::-1])
