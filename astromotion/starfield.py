"""Perspective fly-through of photo-derived stars, composited in front of nebula.

Positions/colors originate in the actual separated star image. Depths are seeded
artistic assignments, not distances measured from astrophotography. Each star is
a billboard light sprite with its own X/Y/Z; projection is X/Z and Y/Z. This is
different from applying a single zoom matrix to the entire star photograph.
"""
from __future__ import annotations

import logging
import math

import cv2
import numpy as np

from .animation import Animator, smootherstep
from .config import Loop, Starfield
from .imaging import FloatImage, to_srgb
from .separation import Layers
from .starprofiles import StarProfiles

LOG = logging.getLogger(__name__)


class PerspectiveStars:
    def __init__(self, layers: Layers, animator: Animator, cfg: Starfield, fps: int,
                 loop: Loop | None = None):
        self.cfg, self.size, self.fps = cfg, animator.size, fps
        self.loop = loop or Loop()
        self.w, self.h = self.size
        self.scale = min(self.size) / 1080
        self.focal = self.h * .78
        self.center = np.array([self.w / 2, self.h / 2], np.float32)
        source = layers.stars
        peak = source.max(axis=2)
        lum = source @ np.array([.2126, .7152, .0722], np.float32)
        lum = cv2.GaussianBlur(lum, (0, 0), .45)
        rng = np.random.default_rng(cfg.seed)
        # Tiny deterministic jitter resolves equal-valued plateaus into one core.
        lum += rng.random(lum.shape, dtype=np.float32) * 1e-9
        maxima = cv2.dilate(lum, np.ones((5, 5), np.uint8))
        neutral = source.min(axis=2) / np.maximum(peak, 1e-6)
        mask = (lum >= maxima) & (peak > .004) & (neutral > .12)
        mask[:3] = mask[-3:] = False
        mask[:, :3] = mask[:, -3:] = False
        y, x = np.nonzero(mask)
        if len(x) == 0:
            raise ValueError("Keine verlässlichen Sternkerne für den perspektivischen Flug gefunden.")
        coords = np.column_stack((x, y, np.ones(len(x))))
        projected = coords @ animator.matrix(0).T
        inside = ((projected[:, 0] >= 2) & (projected[:, 0] < self.w - 2) &
                  (projected[:, 1] >= 2) & (projected[:, 1] < self.h - 2))
        x, y, projected = x[inside], y[inside], projected[inside]
        if len(x) == 0:
            raise ValueError("Keine Sternkerne im gewählten Videoausschnitt.")
        strength = peak[y, x]
        if len(x) > cfg.count:
            # Keep prominent stars, and sample the remaining real detected stars
            # rather than replacing them with arbitrary generated positions.
            bright = np.argsort(strength)[-min(80, cfg.count):]
            rest = np.setdiff1d(np.arange(len(x)), bright)
            sampled = rng.choice(rest, cfg.count - len(bright), replace=False)
            selected = np.concatenate((bright, sampled))
            x, y, projected, strength = x[selected], y[selected], projected[selected], strength[selected]
        self.count = len(x)
        self.initial_z = rng.uniform(cfg.near, cfg.far, self.count).astype(np.float32)
        # Distribute photo-derived X/Y independently of Z in a genuine volume.
        # Matching every initial pixel would create a widening cone: after the
        # first near stars passed, its narrow front would appear almost empty.
        # This artistic mode deliberately rearranges the original star positions.
        reference_depth = cfg.far * .55
        self.world_xy = ((projected - self.center) / self.focal * reference_depth).astype(np.float32)
        rgb = to_srgb(source[y, x][None])[0]
        self.colors = np.clip(rgb / np.maximum(rgb.max(axis=1, keepdims=True), .01), 0, 1)
        self.brightness = (.45 + .55 * np.clip(np.sqrt(strength / .25), 0, 1)).astype(np.float32)
        self.size_factor = rng.uniform(.8, 1.3, self.count).astype(np.float32)
        self.stats: dict[str, float] = {"detected_star_particles": float(self.count)}
        self.profiles = StarProfiles(source, x, y, mask) if cfg.photo_profiles else None
        self.featured = np.zeros(self.count, np.float32)
        # Feature only a few existing stars whose paths skim the viewport edge.
        # Choose them once for the entire clip, avoiding per-frame rank popping.
        for t in np.linspace(.18, .88, cfg.close_passes):
            xy, z, _, _ = self.project(float(t))
            edge = np.max(np.abs((xy - self.center) / self.center), axis=1)
            suitable = (z < .65) & (z > cfg.near + .06) & (edge > .6) & (edge < 1.12) & (self.featured == 0)
            indices = np.flatnonzero(suitable)
            if len(indices):
                choice = indices[np.argmin(np.abs(z[indices] - .36) + np.abs(edge[indices] - .9) * .2)]
                self.featured[choice] = 1
        self.stats["photo_profiles_enabled"] = float(cfg.photo_profiles)
        self.stats["featured_close_passes"] = float(self.featured.sum())
        LOG.info("Perspektivischer Sternflug: %d echte Sternkerne, eigene X/Y/Z-Projektion.", self.count)

    def project(self, t: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        cfg = self.cfg
        u = smootherstep(t)
        distance = cfg.travel * u
        span = cfg.far - cfg.near
        if self.loop.enabled:
            # An integer number of traversals closes every star's depth exactly.
            # Constant forward velocity; periodic lateral drift/roll, no rewind.
            phase = t % 1.0
            distance = span * self.loop.star_cycles * phase
        raw_z = self.initial_z.astype(np.float64) - distance if self.loop.enabled else self.initial_z - distance
        cycles = np.floor((raw_z - cfg.near) / span)
        z = (raw_z - cfg.near) % span + cfg.near
        # Periodic volume recycling happens at the clipping plane, with fades.
        # It reuses the actual detected stars; no extra stars are hallucinated.
        camera_xy = np.array([cfg.drift_x, cfg.drift_y], np.float32) * distance
        xy = self.world_xy - camera_xy
        angle = math.radians(cfg.rotation_deg * u)
        if self.loop.enabled:
            camera_xy = (np.array([cfg.drift_x, cfg.drift_y], np.float32) *
                         span * self.loop.star_cycles * math.sin(2 * math.pi * phase) / (2 * math.pi))
            xy = self.world_xy - camera_xy
            angle = math.radians(cfg.rotation_deg * .5 * math.sin(2 * math.pi * phase))
        rotation = np.array([[math.cos(angle), -math.sin(angle)],
                             [math.sin(angle), math.cos(angle)]], np.float32)
        projected = (xy @ rotation.T) * (self.focal / z[:, None]) + self.center
        return projected, z, cycles, raw_z

    def composite(self, background: FloatImage, t: float, duration: float) -> FloatImage:
        """Far-to-near alpha-over, so close cores cover nebular pixels visibly."""
        frame = background.copy()
        xy, z, cycles, _ = self.project(t)
        dt = self.cfg.shutter / (self.fps * max(duration, 1e-6))
        previous, previous_z, previous_cycles, _ = self.project(t - dt if self.loop.enabled else max(0, t - dt))
        velocity = xy - previous
        wrapped = np.abs(z - previous_z) > (self.cfg.far - self.cfg.near) / 2 if self.loop.enabled else cycles != previous_cycles
        velocity[wrapped] = 0  # no trail across a recycled jump
        sigma = np.clip((.85 + .7 * self.brightness) * self.size_factor * (.8 / z),
                        .55, self.cfg.max_radius) * self.scale
        proximity = np.clip((.75 - z) / max(.75 - self.cfg.near, .05), 0, 1)
        feature = self.featured * proximity * proximity * (3 - 2 * proximity)
        sigma *= 1 + (self.cfg.close_scale - 1) * feature
        blur = self.cfg.close_blur * self.scale * feature
        peak_alpha = np.clip(self.brightness * (.95 / z) ** .7 * self.cfg.foreground_gain, 0, .985)
        # Fade near the eye and after re-entry at the back of the depth volume.
        near_fade = np.clip((z - self.cfg.near) / .08, 0, 1)
        far_fade = np.where(cycles < 0, np.clip((self.cfg.far - z) / .18, 0, 1), 1)
        if self.loop.enabled:
            # Apply on every cycle, including the initial frame: same alpha at seam.
            far_fade = np.clip((self.cfg.far - z) / .18, 0, 1)
        peak_alpha *= near_fade * far_fade
        margin = sigma * 5
        if self.profiles:
            margin = np.maximum(margin, sigma * 8.5 / self.profiles.sigma + blur * 3)
        visible = ((xy[:, 0] > -margin) & (xy[:, 0] < self.w + margin) &
                   (xy[:, 1] > -margin) & (xy[:, 1] < self.h + margin) & (peak_alpha > .01))
        indices = np.nonzero(visible)[0]
        self.stats["visible_particles_last_frame"] = float(len(indices))
        self.stats["visible_near_particles_last_frame"] = float(np.count_nonzero(z[indices] < .8))
        self.stats["visible_featured_stars_last_frame"] = float(np.count_nonzero(feature[indices] > .1))
        # Far objects first; nearby opaque cores are the last layer on the image.
        indices = indices[np.argsort(z[indices])[::-1]]
        for i in indices:
            px, py = float(xy[i, 0]), float(xy[i, 1])
            s = float(sigma[i])
            vx, vy = map(float, velocity[i])
            length = min(math.hypot(vx, vy), 14 * self.scale)
            if length:
                factor = length / max(math.hypot(vx, vy), 1e-6)
                vx, vy = vx * factor, vy * factor
            radius = 4 * s + length
            if self.profiles:
                radius = max(radius, 8.5 * s / float(self.profiles.sigma[i]) + 3 * float(blur[i]) + length)
            x0, x1 = max(0, math.floor(px - radius)), min(self.w, math.ceil(px + radius + 1))
            y0, y1 = max(0, math.floor(py - radius)), min(self.h, math.ceil(py + radius + 1))
            if x0 >= x1 or y0 >= y1:
                continue
            if self.profiles:
                rgba = self.profiles.draw(int(i), (x1 - x0, y1 - y0), (px - x0, py - y0),
                                          s, float(blur[i]), (vx, vy))
                alpha = rgba[..., 3:4] * peak_alpha[i]
                patch = frame[y0:y1, x0:x1]
                patch *= 1 - alpha
                patch += rgba[..., :3] * peak_alpha[i]
                continue
            gx = np.arange(x0, x1, dtype=np.float32)[None, :] - px
            gy = np.arange(y0, y1, dtype=np.float32)[:, None] - py
            alpha = np.zeros((y1 - y0, x1 - x0), np.float32)
            for sample in (0., .5, 1.):
                r2 = (gx + vx * sample) ** 2 + (gy + vy * sample) ** 2
                core = np.exp(-r2 / (2 * s * s))
                halo = .10 * np.exp(-r2 / (9 * s * s))
                alpha += (core + halo) / 3
            alpha = np.minimum(alpha * peak_alpha[i], .985)[..., None]
            patch = frame[y0:y1, x0:x1]
            patch *= 1 - alpha
            patch += self.colors[i] * alpha
        return np.clip(frame, 0, 1)
