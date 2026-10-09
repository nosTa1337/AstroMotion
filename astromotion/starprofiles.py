"""Small isolated, premultiplied RGBA patches from the actual star residual.

Each patch retains its own shape and spatial color variations. A Voronoi mask
excludes neighboring detected stars; a soft edge avoids visible patch rectangles.
No sharpening or generated star details are added.
"""
from __future__ import annotations

import cv2
import numpy as np

from .imaging import FloatImage, to_srgb


class StarProfiles:
    side = 17

    def __init__(self, source: FloatImage, x: np.ndarray, y: np.ndarray,
                 cores: np.ndarray):
        _, labels = cv2.distanceTransformWithLabels((~cores).astype(np.uint8),
                          cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
        pad = self.side // 2
        pixels = np.pad(source, ((pad, pad), (pad, pad), (0, 0)))
        ownership = np.pad(labels, pad)
        gy, gx = np.mgrid[-pad:pad + 1, -pad:pad + 1].astype(np.float32)
        r2 = gx * gx + gy * gy
        taper = np.clip((pad - np.sqrt(r2)) / 3, 0, 1)
        self.rgba = np.empty((len(x), self.side, self.side, 4), np.float32)
        self.sigma = np.empty(len(x), np.float32)
        for i, (px, py) in enumerate(zip(x, y)):
            patch = pixels[py:py + self.side, px:px + self.side].copy()
            own = (ownership[py:py + self.side, px:px + self.side] == labels[py, px]).astype(np.float32)
            confidence = cv2.GaussianBlur(own, (3, 3), .45) * taper
            patch *= confidence[..., None]
            strength = patch.max(axis=2)
            self.sigma[i] = np.clip(np.sqrt((strength * r2).sum() /
                                    max(2 * float(strength.sum()), 1e-8)), .6, 3.5)
            rgb = to_srgb(patch)
            rgb /= max(float(rgb[pad, pad].max()), 1e-5)
            rgb = np.clip(rgb, 0, 1)
            alpha = cv2.GaussianBlur(rgb.max(axis=2), (0, 0), .5)
            alpha *= taper
            alpha /= max(float(alpha.max()), 1e-5)
            # Tiny JPEG/Bayer stars may have individual red/green/blue pixels.
            # Preserve the measured brightness shape, but smooth chromaticity
            # locally so magnification does not turn these into colored blocks.
            chroma = cv2.GaussianBlur(rgb, (0, 0), .8)
            chroma /= np.maximum(chroma.max(axis=2, keepdims=True), 1e-6)
            core_weight = np.exp(-r2 / (2 * max(float(self.sigma[i]), 1.2)**2)) * alpha
            core_color = (rgb * core_weight[..., None]).sum(axis=(0, 1)) / max(float(core_weight.sum()), 1e-6)
            core_color /= max(float(core_color.max()), 1e-6)
            # StarNet differences can magnify chromatic sensor/registration
            # fringes. Anchor spatial hue variation to the integrated core,
            # retaining gentle real color halos instead of rainbow artifacts.
            chroma = core_color + .2 * (chroma - core_color)
            chroma /= np.maximum(chroma.max(axis=2, keepdims=True), 1e-6)
            # Premultiplied color: every channel <= alpha; RGB is zero when
            # transparent, so interpolation/defocus cannot create dark fringes.
            self.rgba[i, ..., :3] = chroma * alpha[..., None]
            self.rgba[i, ..., 3] = alpha
        self.mips = [self.rgba]
        for side in (9, 5):
            bank = np.stack([cv2.resize(p, (side, side), interpolation=cv2.INTER_AREA)
                             for p in self.rgba])
            bank /= np.maximum(bank[..., 3].max(axis=(1, 2))[:, None, None, None], 1e-6)
            self.mips.append(bank)

    def draw(self, index: int, size: tuple[int, int], position: tuple[float, float],
             sigma: float, blur: float, velocity: tuple[float, float]) -> FloatImage:
        """Warp one RGBA profile into a small ROI, with subpixel motion/defocus."""
        scale = sigma / float(self.sigma[index])
        mip = 2 if scale < .4 else 1 if scale < .75 else 0
        source = self.mips[mip][index]
        scale *= self.side / source.shape[0]
        center = (source.shape[0] - 1) / 2
        px, py = position
        vx, vy = velocity
        samples = (0., .5, 1.) if vx * vx + vy * vy > .5 else (.5,)
        rgba = np.zeros((size[1], size[0], 4), np.float32)
        for sample in samples:
            matrix = np.array([[scale, 0, px - center * scale - vx * sample],
                               [0, scale, py - center * scale - vy * sample]], np.float32)
            rgba += cv2.warpAffine(source, matrix, size, flags=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_CONSTANT) / len(samples)
        # Slight sampling filter plus optional shallow depth of field. Blur
        # premultiplied RGB and alpha together, keeping colored halos clean.
        rgba = cv2.GaussianBlur(rgba, (0, 0), max(.3, blur), borderType=cv2.BORDER_CONSTANT)
        return np.clip(rgba, 0, 1)
