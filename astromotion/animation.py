"""Independent layer cameras that approach a safe crop from the full photo."""
from __future__ import annotations

import math

import cv2
import numpy as np

from .config import Motion
from .imaging import FloatImage
from .separation import Layers


def smootherstep(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * t * (t * (t * 6 - 15) + 10)


def motion_progress(t: float, timing: str) -> float:
    return min(1.0, max(0.0, t)) if timing == "steady" else smootherstep(t)


def _rotated_extent(a: float, b: float, max_angle: float) -> float:
    """Maximum a*cos(theta)+b*sin(theta) on [0,max_angle]."""
    theta = min(max_angle, math.atan2(b, a))
    return a * math.cos(theta) + b * math.sin(theta)


class Animator:
    def __init__(self, layers: Layers, size: tuple[int, int], motion: Motion):
        self.layers, self.size, self.motion = layers, size, motion
        self.h, self.w = layers.nebula.shape[:2]
        ow, oh = size
        m = motion
        p = m.parallax
        # Reserve rotation/pan coverage for the destination, never the first frame.
        self.max_rotation = math.radians((abs(m.rotation_deg) + abs(m.star_rotation_deg) * p) * m.speed)
        dx = abs(m.pan_x) * ow * m.speed * (1 + .65 * p)
        dy = abs(m.pan_y) * oh * m.speed * (1 + .65 * p)
        # Transform inverse maps all viewport corners into the source rectangle.
        # Bound translation by its norm for every angle, with interpolation margin.
        radius = math.hypot(dx, dy)
        ex = _rotated_extent(ow / 2 + 3, oh / 2 + 3, self.max_rotation) + radius
        ey = _rotated_extent(oh / 2 + 3, ow / 2 + 3, self.max_rotation) + radius
        cx, cy = m.center_x * (self.w - 1), m.center_y * (self.h - 1)
        self.center = (cx, cy)
        self.base_scale = min(ow / self.w, oh / self.h)
        self.crop_scale = max(ex / min(cx, self.w - 1 - cx),
                              ey / min(cy, self.h - 1 - cy)) * m.overscan
        self.twinkle_mask: FloatImage | None = None

    def matrix(self, t: float, stars: bool = False) -> np.ndarray:
        m = self.motion
        u = motion_progress(t, m.timing)
        if not m.speed or not any((m.zoom, m.rotation_deg, m.pan_x, m.pan_y,
                                   m.star_zoom_extra * m.parallax, m.star_rotation_deg * m.parallax)):
            u = 0.0
        foreground = m.parallax if stars else 0.0
        zoom = 1 + (m.zoom + m.star_zoom_extra * foreground) * m.speed
        scale = self.base_scale + (self.crop_scale * zoom - self.base_scale) * u
        angle = (m.rotation_deg + m.star_rotation_deg * foreground) * u * m.speed
        cx = (self.w - 1) / 2 + (self.center[0] - (self.w - 1) / 2) * u
        cy = (self.h - 1) / 2 + (self.center[1] - (self.h - 1) / 2) * u
        mat = cv2.getRotationMatrix2D((cx, cy), angle, scale)
        ow, oh = self.size
        mat[0, 2] += (ow - 1) / 2 - cx + m.pan_x * ow * u * m.speed * (1 + .65 * foreground)
        mat[1, 2] += (oh - 1) / 2 - cy + m.pan_y * oh * u * m.speed * (1 + .65 * foreground)
        return mat

    def warp(self, image: FloatImage, matrix: np.ndarray) -> FloatImage:
        # Uncovered areas stay black while approaching the crop; never repeat stars.
        return cv2.warpAffine(image, matrix, self.size, flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    def frame_layers(self, t: float, seconds: float, twinkle: float = 0) -> tuple[FloatImage, FloatImage]:
        nebula = self.warp(self.layers.nebula, self.matrix(t))
        stars = self.layers.stars
        if twinkle:
            if self.twinkle_mask is None:
                y, x = np.mgrid[:self.h, :self.w].astype(np.float32)
                # Spatial phase, rather than pulsing the whole star field together.
                self.twinkle_mask = (np.sin(x * .117 + y * .083) * np.pi)[..., None]
            gain = 1 + twinkle * .2 * np.sin(seconds * 1.4 + self.twinkle_mask)
            stars = np.minimum(stars * gain, 1)
        return nebula, self.warp(stars, self.matrix(t, stars=True))
