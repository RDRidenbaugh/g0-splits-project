"""Gaussian heatmap target generation and sub-pixel decoding."""
from __future__ import annotations

import numpy as np
import torch


def make_heatmaps(points_hm: np.ndarray, size: int, sigma: float) -> np.ndarray:
    """points_hm: (K, 2) array of (x, y) in heatmap-pixel space (may be
    fractional / out of bounds -- out-of-bounds points get an all-zero
    heatmap, which the loss should down-weight via the accompanying mask).
    Returns (K, size, size) float32 array, each channel peak-normalized to 1.
    """
    k = points_hm.shape[0]
    out = np.zeros((k, size, size), dtype=np.float32)
    valid = np.ones(k, dtype=bool)
    ys, xs = np.mgrid[0:size, 0:size]
    for i, (x, y) in enumerate(points_hm):
        if not (0 <= x < size and 0 <= y < size):
            valid[i] = False
            continue
        out[i] = np.exp(-((xs - x) ** 2 + (ys - y) ** 2) / (2 * sigma**2))
    return out, valid


def soft_argmax_decode(heatmaps: torch.Tensor, window: int = 5) -> torch.Tensor:
    """heatmaps: (..., K, H, W) -> (..., K, 2) (x, y) in heatmap-pixel space,
    via a windowed centroid around each channel's argmax for sub-pixel
    precision (plain argmax alone is integer-only)."""
    *lead, k, h, w = heatmaps.shape
    flat = heatmaps.reshape(-1, k, h, w)
    n = flat.shape[0]
    out = torch.zeros(n, k, 2)
    half = window // 2
    for b in range(n):
        for c in range(k):
            hm = flat[b, c]
            idx = torch.argmax(hm)
            py, px = divmod(idx.item(), w)
            y0, y1 = max(0, py - half), min(h, py + half + 1)
            x0, x1 = max(0, px - half), min(w, px + half + 1)
            patch = hm[y0:y1, x0:x1]
            patch = torch.clamp(patch, min=0)
            total = patch.sum()
            if total <= 0:
                out[b, c] = torch.tensor([float(px), float(py)])
                continue
            ys, xs = torch.meshgrid(
                torch.arange(y0, y1, dtype=torch.float32),
                torch.arange(x0, x1, dtype=torch.float32),
                indexing="ij",
            )
            cx = (patch * xs).sum() / total
            cy = (patch * ys).sum() / total
            out[b, c] = torch.tensor([cx.item(), cy.item()])
    return out.reshape(*lead, k, 2)
