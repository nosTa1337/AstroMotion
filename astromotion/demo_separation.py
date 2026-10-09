"""Lightweight, demo-only star extraction from a finished RGB photo.

This is an artistic approximation, NOT a replacement for StarNet or a source of
scientific starless data. It operates only in scripts/render_photo_demo.py;
production renders continue to require a real starless image or StarNet.
"""
from __future__ import annotations

import cv2
import numpy as np

from .imaging import FloatImage, to_linear
from .separation import Layers


def approximate_demo_layers(rgb: FloatImage, max_stars: int = 4500) -> Layers:
    """Find compact point sources, locally inpaint them, retain RGB star light.

    Operates in display sRGB for stable peak detection and inpainting. The
    returned screen layers are linear light and reconstruct the input image.
    Large diffuse highlights are intentionally left in the background.
    """
    if rgb.ndim != 3 or rgb.shape[2] != 3 or not np.isfinite(rgb).all():
        raise ValueError("Erwartet wird ein endliches RGB-Astrofoto.")
    if not 1 <= max_stars <= 50000:
        raise ValueError("max_stars muss zwischen 1 und 50000 liegen.")
    rgb = np.clip(rgb.astype(np.float32, copy=False), 0, 1)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    smooth = cv2.GaussianBlur(gray, (0, 0), 2.0)
    residual = gray - smooth
    maxima = cv2.dilate(gray, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    # A compact bright peak above its immediate surroundings is likely a star.
    points = (gray >= maxima - 1e-6) & (gray > .085) & (residual > .042)
    points[:5] = False
    points[-5:] = False
    points[:, :5] = False
    points[:, -5:] = False
    ys, xs = np.nonzero(points)
    if len(xs) == 0:
        raise ValueError("Keine ausreichend hellen Sternkerne im Demo-Foto erkannt.")
    if len(xs) > max_stars:
        order = np.argsort(residual[ys, xs])[-max_stars:]
        ys, xs = ys[order], xs[order]
    seed = np.zeros(gray.shape, np.uint8)
    seed[ys, xs] = 255
    # A small halo around a pinpoint replaces its PSF with interpolated local sky.
    # A larger radius would destroy nebular filaments and clustered stellar detail.
    mask = cv2.dilate(seed, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    original_u8 = np.round(rgb * 255).astype(np.uint8)
    base_rgb = cv2.inpaint(original_u8, mask, 4, cv2.INPAINT_TELEA).astype(np.float32) / 255
    original_linear = to_linear(rgb)
    # Constrain the background to be no brighter than the measured source so
    # that no negative star flux arises from inpainting bright local patches.
    nebula = np.minimum(to_linear(base_rgb), original_linear)
    stars = np.maximum(original_linear - nebula, 0) / np.maximum(1 - nebula, 1e-6)
    # Only animate light within the detected star footprints; preserve the
    # rest of the photograph in the stationary nebular layer.
    outside = mask == 0
    nebula[outside] = original_linear[outside]
    stars[outside] = 0
    layers = Layers(nebula.astype(np.float32), np.clip(stars, 0, 1).astype(np.float32), "screen", {
        "demo_approximate_star_cores": float(len(xs)),
        "demo_inpaint_fraction": float(np.count_nonzero(mask) / mask.size),
    })
    layers.diagnostics["reconstruction_max_error_linear"] = float(np.max(np.abs(layers.composite() - original_linear)))
    return layers
