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
        self.pan_radius = math.hypot(dx, dy)
        self.center = (m.center_x * (self.w - 1), m.center_y * (self.h - 1))
        self.base_scale = min(ow / self.w, oh / self.h)
        self.crop_scale = self._coverage_scale(1)
        self.twinkle_mask: FloatImage | None = None

    def _coverage_scale(self, progress: float) -> float:
        """Monotone coverage bound for every pose up to this motion progress."""
        ow, oh = self.size
        angle = self.max_rotation * progress
        a, b = (ow - 1) / 2 + 3 * progress, (oh - 1) / 2 + 3 * progress
        ex = _rotated_extent(a, b, angle) + self.pan_radius * progress
        ey = _rotated_extent(b, a, angle) + self.pan_radius * progress
        cx = (self.w - 1) / 2 + (self.center[0] - (self.w - 1) / 2) * progress
        cy = (self.h - 1) / 2 + (self.center[1] - (self.h - 1) / 2) * progress
        return max(ex / min(cx, self.w - 1 - cx),
                   ey / min(cy, self.h - 1 - cy)) * (1 + (self.motion.overscan - 1) * progress)

    def matrix(self, t: float, stars: bool = False) -> np.ndarray:
        m = self.motion
        u = motion_progress(t, m.timing)
        if not m.speed or not any((m.zoom, m.rotation_deg, m.pan_x, m.pan_y,
                                   m.star_zoom_extra * m.parallax, m.star_rotation_deg * m.parallax)):
            u = 0.0
        foreground = m.parallax if stars else 0.0
        zoom = 1 + (m.zoom + m.star_zoom_extra * foreground) * m.speed
        scale = self.base_scale + (self.crop_scale * zoom - self.base_scale) * u
        pose = u
        if self._coverage_scale(pose) > scale:
            # Zoom first; release only as much rotation/pan/focus as fits safely.
            low, high = 0.0, pose
            for _ in range(24):
                middle = (low + high) / 2
                if self._coverage_scale(middle) <= scale:
                    low = middle
                else:
                    high = middle
            pose = low
        angle = (m.rotation_deg + m.star_rotation_deg * foreground) * pose * m.speed
        cx = (self.w - 1) / 2 + (self.center[0] - (self.w - 1) / 2) * pose
        cy = (self.h - 1) / 2 + (self.center[1] - (self.h - 1) / 2) * pose
        mat = cv2.getRotationMatrix2D((cx, cy), angle, scale)
        ow, oh = self.size
        mat[0, 2] += (ow - 1) / 2 - cx + m.pan_x * ow * pose * m.speed * (1 + .65 * foreground)
        mat[1, 2] += (oh - 1) / 2 - cy + m.pan_y * oh * pose * m.speed * (1 + .65 * foreground)
        return mat

    def warp(self, image: FloatImage, matrix: np.ndarray) -> FloatImage:
        # Only initial aspect-ratio bars remain black; never mirror or repeat stars.
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
