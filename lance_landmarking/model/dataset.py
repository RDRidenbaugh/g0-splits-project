"""PyTorch Dataset for lance landmarking: raw TIFF -> letterboxed tensor +
Gaussian heatmap targets."""
from __future__ import annotations

import numpy as np
import tifffile
import torch
from PIL import Image
from torch.utils.data import Dataset

from constants import HEATMAP_SIGMA, HEATMAP_SIZE, HEATMAP_STRIDE, INPUT_SIZE
from heatmap import make_heatmaps
from splits import Sample

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def load_rgb(path: str) -> np.ndarray:
    arr = tifffile.imread(path)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=-1)
    elif arr.shape[-1] == 4:
        arr = arr[..., :3]
    elif arr.shape[-1] != 3:
        raise ValueError(f"unexpected channel count in {path}: shape={arr.shape}")
    if arr.dtype != np.uint8:
        # defensive: all lance TIFFs observed are 8-bit, but don't silently
        # mis-scale a 16-bit image if one ever shows up
        arr = (arr.astype(np.float32) / arr.max() * 255).astype(np.uint8)
    return arr


def letterbox(img: np.ndarray, size: int):
    h, w = img.shape[:2]
    scale = min(size / w, size / h)
    new_w, new_h = max(1, round(w * scale)), max(1, round(h * scale))
    resized = np.asarray(Image.fromarray(img).resize((new_w, new_h), Image.BILINEAR))
    canvas = np.zeros((size, size, 3), dtype=np.uint8)
    pad_x, pad_y = (size - new_w) // 2, (size - new_h) // 2
    canvas[pad_y : pad_y + new_h, pad_x : pad_x + new_w] = resized
    return canvas, scale, pad_x, pad_y


class LanceLandmarkDataset(Dataset):
    def __init__(self, samples: list[Sample], input_size: int = INPUT_SIZE, cache: bool = False):
        self.samples = samples
        self.input_size = input_size
        # opt-in: keep each letterboxed uint8 canvas after first decode. Decoding
        # the LZW TIFFs is ~2/3 of per-sample time and there is no augmentation,
        # so later epochs are identical. (Per DataLoader worker process.)
        self._cache = {} if cache else None

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx: int):
        s = self.samples[idx]
        if self._cache is not None and idx in self._cache:
            canvas, scale, pad_x, pad_y = self._cache[idx]
        else:
            canvas, scale, pad_x, pad_y = letterbox(load_rgb(s.raw_image), self.input_size)
            if self._cache is not None:
                self._cache[idx] = (canvas, scale, pad_x, pad_y)

        pts = np.asarray(s.landmarks_px, dtype=np.float32)  # (K, 2) orig pixel space
        pts_input = pts * scale + np.array([pad_x, pad_y], dtype=np.float32)  # INPUT_SIZE space
        pts_heatmap = pts_input / HEATMAP_STRIDE

        heatmaps, valid = make_heatmaps(pts_heatmap, HEATMAP_SIZE, HEATMAP_SIGMA)

        image = canvas.astype(np.float32) / 255.0
        image = (image - IMAGENET_MEAN) / IMAGENET_STD
        image = np.transpose(image, (2, 0, 1))  # C,H,W

        return {
            "image": torch.from_numpy(image.copy()),
            "heatmaps": torch.from_numpy(heatmaps),
            "valid": torch.from_numpy(valid),
            "landmarks_input_px": torch.from_numpy(pts_input),
            "scale": torch.tensor(scale, dtype=torch.float32),
            "pad": torch.tensor([pad_x, pad_y], dtype=torch.float32),
            "key": s.key,
            "group": s.group,
            "marked_tiff": s.marked_tiff,
        }
