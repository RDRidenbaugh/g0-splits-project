"""Drawing helper for the linear-measure figures: crop an image around a set of points, then draw points,
distances, curves, perpendicular distances and angles with labels."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# distinguishable on the saw/lance colours (yellow-brown tissue, grey/green/pink backgrounds)
PALETTE = [(214, 39, 40), (31, 119, 180), (44, 160, 44), (148, 103, 189), (255, 127, 14),
           (23, 190, 207), (227, 119, 194), (140, 86, 75)]


def _font(size):
    for name in ("DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


class Fig:
    def __init__(self, img, crop_pts, width=1800, pad=90):
        img = np.asarray(img)
        if img.ndim == 2:
            img = np.stack([img] * 3, -1)
        h, w = img.shape[:2]
        pts = np.asarray(crop_pts, float)
        self.x0, self.y0 = np.maximum(pts.min(0) - pad, 0).astype(int)
        x1, y1 = np.minimum(pts.max(0) + pad, [w, h]).astype(int)
        crop = Image.fromarray(np.ascontiguousarray(img[self.y0:y1, self.x0:x1, :3]).astype(np.uint8))
        self.s = width / crop.width
        self.im = crop.resize((width, round(crop.height * self.s)), Image.LANCZOS).convert("RGB")
        self.d = ImageDraw.Draw(self.im)

    def to(self, q):
        q = np.asarray(q, float)
        return (q - [self.x0, self.y0]) * self.s

    def text(self, q, s, color, size=24, dx=8, dy=-30):
        x, y = self.to(q)
        self.d.text((x + dx, y + dy), s, fill=color, font=_font(size), stroke_width=3, stroke_fill=(255, 255, 255))

    def points(self, pts, color=(90, 90, 90), r=3, outline=None):
        for x, y in self.to(np.atleast_2d(pts)):
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=color, outline=outline)

    def _seg(self, a, b, color, width, dashed):
        a, b = self.to(a), self.to(b)
        if not dashed:
            self.d.line([tuple(a), tuple(b)], fill=color, width=width)
            return
        L = np.linalg.norm(b - a); n = max(int(L / 14), 1)
        for i in range(0, n, 2):
            self.d.line([tuple(a + (b - a) * i / n), tuple(a + (b - a) * min(i + 1, n) / n)], fill=color, width=width)

    def line(self, a, b, color, label=None, width=4, dashed=False, label_t=0.5, label_dx=8, label_dy=-30, ends=True):
        a, b = np.asarray(a, float), np.asarray(b, float)
        self._seg(a, b, color, width, dashed)
        if ends and not dashed:
            for q in (a, b):
                x, y = self.to(q); self.d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=color)
        if label:
            self.text(a + (b - a) * label_t, label, color, dx=label_dx, dy=label_dy)

    def poly(self, pts, color, label=None, width=4, label_at=0.5, label_dx=8, label_dy=-30):
        q = [tuple(v) for v in self.to(pts)]
        self.d.line(q, fill=color, width=width, joint="curve")
        if label:
            self.text(pts[int(label_at * (len(pts) - 1))], label, color, dx=label_dx, dy=label_dy)

    def angle(self, v, a, b, color, label, radius=70):
        """Arc at vertex v between the directions v->a and v->b, with a label."""
        V = self.to(v); A = self.to(a) - V; B = self.to(b) - V
        t0, t1 = sorted([np.degrees(np.arctan2(A[1], A[0])), np.degrees(np.arctan2(B[1], B[0]))])
        if t1 - t0 > 180:
            t0, t1 = t1, t0 + 360
        self.d.arc([V[0] - radius, V[1] - radius, V[0] + radius, V[1] + radius], t0, t1, fill=color, width=4)
        if not label:
            return
        mid = np.radians((t0 + t1) / 2)
        self.d.text((V[0] + (radius + 12) * np.cos(mid), V[1] + (radius + 12) * np.sin(mid) - 12), label,
                    fill=color, font=_font(24), stroke_width=3, stroke_fill=(255, 255, 255))

    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.im.save(path, quality=90)
