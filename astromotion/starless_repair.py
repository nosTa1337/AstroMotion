"""Conservatively repair tiny colored pits left at bright stars by star removal.

Optional aesthetic repair, not a substitute for real starless separation.
Only invoked when foreground_cleanup is enabled.
"""
from __future__ import annotations

import cv2
import numpy as np

from .imaging import FloatImage


def repair_bright_star_holes(original: FloatImage, starless: FloatImage) -> tuple[FloatImage, int]:
    """Inpaint suspicious compact-star artifacts, leave all other pixels unchanged.

    OpenCV's float32 TELEA inpaint can overshoot wildly; use uint16 input for
    the masked area, while preserving the untouched float32 source exactly.
    """
    src = np.clip(original.astype(np.float32, copy=False), 0, 1)
    base = np.clip(starless.astype(np.float32, copy=False), 0, 1)
    peak = src.max(axis=2)
    highpass = peak - cv2.GaussianBlur(peak, (0, 0), 4)
    residual = np.max(np.maximum(src - base, 0), axis=2)
    maxima = cv2.dilate(peak, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    candidates = ((peak >= maxima - 1e-5) & (peak >= .7) &
                  (highpass > .085) & (residual > .17)).astype(np.uint8)
    count, _, stats, centers = cv2.connectedComponentsWithStats(candidates, 8)
    h, w = src.shape[:2]
    radius = max(5, min(28, round(13 * max(h, w) / 1920)))
    smoothed = cv2.GaussianBlur(base, (0, 0), max(4, radius * 1.2))
    mask = np.zeros((h, w), np.uint8)
    for i in range(1, count):
        if stats[i, cv2.CC_STAT_AREA] > radius * radius:
            continue  # extended nebulosity, not a compact point source
        x, y = np.round(centers[i]).astype(int)
        if min(x, y, w - x - 1, h - y - 1) <= radius:
            continue
        # Do not touch an already smooth/clean StarNet background.
        if np.max(np.abs(base[y, x] - smoothed[y, x])) < .055:
            continue
        cv2.circle(mask, (x, y), radius, 255, thickness=-1)
    if not np.any(mask):
        return base, 0
    repaired = np.stack([
        cv2.inpaint(np.round(base[..., ch] * 65535).astype(np.uint16),
                    mask, radius, cv2.INPAINT_TELEA).astype(np.float32) / 65535
        for ch in range(3)
    ], axis=-1)
    out = base.copy()
    out[mask > 0] = np.clip(repaired[mask > 0], 0, 1)
    return out, int(cv2.connectedComponents(mask)[0] - 1)
