"""Restrained linear-light glow, bounded highlights, and display color grading."""
from __future__ import annotations

import cv2
import numpy as np

from .config import Effects
from .imaging import FloatImage, to_srgb
from .separation import composite


def soft_blur(image: FloatImage, sigma: float) -> FloatImage:
    h, w = image.shape[:2]
    factor = min(1.0, 480 / max(h, w))
    small = cv2.resize(image, (max(2, round(w * factor)), max(2, round(h * factor))), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), max(.35, sigma * factor), borderType=cv2.BORDER_REFLECT_101)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


class EffectProcessor:
    def __init__(self, cfg: Effects, size: tuple[int, int], blend: str):
        self.cfg, self.blend = cfg, blend
        w, h = size
        self.scale = min(w, h) / 1080
        y, x = np.mgrid[:h, :w].astype(np.float32)
        r2 = ((x - (w - 1) / 2) / (w / 2)) ** 2 + ((y - (h - 1) / 2) / (h / 2)) ** 2
        self.vignette = (1 - cfg.vignette * np.clip(r2 / 2, 0, 1) ** 1.4)[..., None]

    def apply(self, nebula: FloatImage, stars: FloatImage) -> FloatImage:
        e = self.cfg
        frame = composite(nebula, stars, self.blend)
        if e.bloom:
            bright = stars * np.clip((stars.max(axis=2, keepdims=True) - .025) / .25, 0, 1)
            glow = soft_blur(bright, e.bloom_radius * self.scale)
            # Headroom-aware mixing never clips bright stars or nebula centers.
            frame += (1 - frame) * np.clip(glow * e.bloom, 0, 1)
        if e.glow:
            luma = (nebula * np.array([.2126, .7152, .0722], dtype=np.float32)).sum(axis=2, keepdims=True)
            bright = nebula * np.clip((luma - .07) / .4, 0, 1)
            glow = soft_blur(bright, e.glow_radius * self.scale)
            frame += (1 - frame) * np.clip(glow * e.glow, 0, 1)
        rgb = to_srgb(frame)
        if e.contrast != 1:
            # A mild S curve preserves black/white points instead of hard clipping.
            rgb += (e.contrast - 1) * (rgb - .5) * rgb * (1 - rgb) * 2
        if e.saturation != 1:
            luma = (rgb * np.array([.2126, .7152, .0722], dtype=np.float32)).sum(axis=2, keepdims=True)
            delta = (rgb - luma) * (e.saturation - 1)
            rgb += delta * (1 - rgb)  # protect highlights from saturation clipping
        if e.grade:
            shadows = (1 - rgb.mean(axis=2, keepdims=True)) ** 2
            tint = np.array([-.012, .004, .018], dtype=np.float32)
            rgb += e.grade * shadows * tint * (1 - rgb)
        rgb *= self.vignette
        return np.clip(rgb, 0, 1).astype(np.float32)
