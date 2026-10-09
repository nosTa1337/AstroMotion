"""Independent layer cameras with smooth motion and analytic crop safety."""
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
        # Both layers start coincident. Foreground increasingly outruns background.
        self.max_rotation = math.radians((abs(m.rotation_deg) + abs(m.star_rotation_deg) * p) * m.speed / 2)
        dx = abs(m.pan_x) * ow * m.speed * (1 + .65 * p) / 2
        dy = abs(m.pan_y) * oh * m.speed * (1 + .65 * p) / 2
        # Transform inverse maps all viewport corners into the source rectangle.
        # Bound translation by its norm for every angle, with interpolation margin.
        radius = math.hypot(dx, dy)
        ex = _rotated_extent(ow / 2 + 3, oh / 2 + 3, self.max_rotation) + radius
        ey = _rotated_extent(oh / 2 + 3, ow / 2 + 3, self.max_rotation) + radius
        cx, cy = m.center_x * (self.w - 1), m.center_y * (self.h - 1)
        self.center = (cx, cy)
        self.base_scale = max(ex / min(cx, self.w - 1 - cx),
                              ey / min(cy, self.h - 1 - cy)) * m.overscan
        self.twinkle_mask: FloatImage | None = None

    def matrix(self, t: float, stars: bool = False) -> np.ndarray:
        m = self.motion
        u = smootherstep(t)
        foreground = m.parallax if stars else 0.0
        zoom = 1 + (m.zoom + m.star_zoom_extra * foreground) * u * m.speed
        angle = (m.rotation_deg + m.star_rotation_deg * foreground) * (u - .5) * m.speed
        mat = cv2.getRotationMatrix2D(self.center, angle, self.base_scale * zoom)
        ow, oh = self.size
        cx, cy = self.center
        mat[0, 2] += ow / 2 - cx + m.pan_x * ow * (u - .5) * m.speed * (1 + .65 * foreground)
        mat[1, 2] += oh / 2 - cy + m.pan_y * oh * (u - .5) * m.speed * (1 + .65 * foreground)
        return mat

    def warp(self, image: FloatImage, matrix: np.ndarray) -> FloatImage:
        # No mirrored or repeated stars. Geometry guarantees all samples are inside.
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
