"""Read ImageJ-embedded landmark coordinates and image metadata from lance TIFFs.

The manual digitizing protocol places landmarks in ImageJ with a global mm
scale set (see Lance_Imaging_Morphometrics_v2.docx), so the .txt coordinate
exports are in millimeters, not pixels. The marked TIFFs also carry the
original ImageJ multi-point ROI (sub-pixel resolution) in the IJMetadata
TIFF tag (50839), which gives the landmarks directly in pixel space. This
module decodes that ROI so pixel-space ground truth can be reconstructed
without needing the per-image mm->px conversion.

The ROI binary layout used here (ImageJ's "Iout" .roi format, point ROI,
sub-pixel resolution variant) was reverse-engineered and cross-validated
against the calibrated mm .txt exports (pixel = mm * XResolution) to
sub-pixel agreement; see the byte offsets inline below.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

import tifffile

SUB_PIXEL_RESOLUTION = 128  # bit flag in the ROI "options" field
POINT_ROI_TYPE = 10


@dataclass
class ImageMeta:
    width: int
    height: int
    bits_per_sample: tuple
    samples_per_pixel: int
    compression: int
    unit: str | None       # e.g. "mm", parsed from ImageDescription
    px_per_unit: float | None  # from XResolution, only meaningful if unit is set


@dataclass
class RoiPoints:
    points: list[tuple[float, float]]  # pixel-space (x, y), sub-pixel precision
    roi_type: int
    n: int


def read_image_meta(tif_path: str) -> ImageMeta:
    with tifffile.TiffFile(tif_path) as tf:
        page = tf.pages[0]
        tags = {t.code: t for t in page.tags}
        desc = tags.get(270)
        unit = None
        if desc is not None and isinstance(desc.value, str):
            for line in desc.value.splitlines():
                if line.startswith("unit="):
                    unit = line.split("=", 1)[1].strip()
        xres = tags.get(282)
        px_per_unit = None
        if xres is not None:
            num, den = xres.value
            if den:
                px_per_unit = num / den
        return ImageMeta(
            width=page.imagewidth,
            height=page.imagelength,
            bits_per_sample=tuple(page.bitspersample) if isinstance(page.bitspersample, (tuple, list)) else (page.bitspersample,),
            samples_per_pixel=page.samplesperpixel,
            compression=int(page.compression),
            unit=unit,
            px_per_unit=px_per_unit,
        )


def _parse_point_roi(roi_bytes: bytes) -> RoiPoints:
    if roi_bytes[:4] != b"Iout":
        raise ValueError("not an ImageJ ROI block (missing 'Iout' magic)")
    roi_type = roi_bytes[6]
    (n,) = struct.unpack(">h", roi_bytes[16:18])
    (options,) = struct.unpack(">h", roi_bytes[50:52])
    subpixel = bool(options & SUB_PIXEL_RESOLUTION)
    coord_off = 64
    if subpixel:
        int_end = coord_off + 4 * n  # skip the parallel int16 x/y arrays
        xs = struct.unpack(f">{n}f", roi_bytes[int_end : int_end + 4 * n])
        ys = struct.unpack(f">{n}f", roi_bytes[int_end + 4 * n : int_end + 8 * n])
        points = list(zip(xs, ys))
    else:
        (top, left, _bottom, _right) = struct.unpack(">hhhh", roi_bytes[8:16])
        xs = struct.unpack(f">{n}h", roi_bytes[coord_off : coord_off + 2 * n])
        ys = struct.unpack(f">{n}h", roi_bytes[coord_off + 2 * n : coord_off + 4 * n])
        points = [(left + x, top + y) for x, y in zip(xs, ys)]
    return RoiPoints(points=points, roi_type=roi_type, n=n)


def read_landmark_roi(tif_path: str) -> RoiPoints | None:
    """Return pixel-space landmark points embedded in a marked TIFF, or None
    if the file has no IJMetadata ROI (e.g. a raw/unlandmarked image)."""
    with tifffile.TiffFile(tif_path) as tf:
        page = tf.pages[0]
        ij_tag = next((t for t in page.tags if t.code == 50839), None)
        if ij_tag is None:
            return None
        ij_value = ij_tag.value
        roi_bytes = None
        if isinstance(ij_value, dict):
            roi_bytes = ij_value.get("ROI")
        if roi_bytes is None:
            return None
        return _parse_point_roi(roi_bytes)


def read_txt_landmarks_mm(txt_path: str) -> list[tuple[float, float]]:
    pts = []
    with open(txt_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            x_str, y_str = line.split()
            pts.append((float(x_str), float(y_str)))
    return pts
