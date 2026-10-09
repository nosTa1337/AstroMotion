"""Conservative, deterministic photographic analysis for optional cinematic settings.

These heuristics are aesthetic decisions, not astronomical position or distance
measurements. Never modify or write the source photo. Values are bounded.
"""
from __future__ import annotations

from dataclasses import replace
import cv2
import numpy as np

from .config import Cinematic, Effects, Motion
from .imaging import FloatImage


def analyze_photo(image: FloatImage) -> dict[str, float]:
    """Estimate a saliency-weighted subject center and modest color suggestions."""
    if image.ndim != 3 or image.shape[2] != 3 or not np.isfinite(image).all():
        raise ValueError("Bildanalyse erwartet ein endliches RGB-Bild.")
    h, w = image.shape[:2]
    if min(w, h) < 16:
        raise ValueError("Bildanalyse benötigt mindestens 16 Pixel pro Achse.")
    ratio = min(1.0, 320.0 / max(h, w))
    small = cv2.resize(np.clip(image, 0, 1), (max(16, round(w * ratio)),
                                                  max(16, round(h * ratio))),
                       interpolation=cv2.INTER_AREA).astype(np.float32)
    # Blur bright isolated stars away: the subject should be the extended nebula.
    blur = cv2.GaussianBlur(small, (0, 0), 7.0, borderType=cv2.BORDER_REFLECT_101)
    lum = blur @ np.array([.2126, .7152, .0722], np.float32)
    chroma = blur.max(axis=2) - blur.min(axis=2)
    score = lum * .7 + chroma * .3
    baseline = float(np.percentile(score, 55))
    saliency = np.maximum(score - baseline, 0).astype(np.float32)
    # Subtle center preference keeps diffuse, noisy regions from pulling the
    # camera all the way to a corner, while genuine off-axis subjects still win.
    hh, ww = saliency.shape
    yy, xx = np.mgrid[:hh, :ww].astype(np.float32)
    normx = (xx + .5) / ww
    normy = (yy + .5) / hh
    center_prior = np.clip(1 - .20 * ((normx - .5)**2 + (normy - .5)**2), .85, 1)
    saliency *= center_prior
    total = float(saliency.sum())
    if total < 1e-5:
        cx = cy = .5
        confidence = 0.
    else:
        cx = float((saliency * normx).sum() / total)
        cy = float((saliency * normy).sum() / total)
        # Uniform-looking images should not trigger major automatic reframing.
        confidence = float(np.clip((float(np.percentile(score, 95)) - baseline) /
                                   max(float(np.percentile(score, 95)), .01), 0, 1))
    # Avoid destructive cropping from the subject centering.
    cx = float(np.clip(cx, .30, .70))
    cy = float(np.clip(cy, .30, .70))
    full_gray = small @ np.array([.2126, .7152, .0722], np.float32)
    p95 = float(np.percentile(full_gray, 95))
    max_rgb = small.max(axis=2)
    sat = (max_rgb - small.min(axis=2)) / np.maximum(max_rgb, .05)
    sat_med = float(np.median(sat[max_rgb > .055])) if np.any(max_rgb > .055) else 0.
    # Protect carefully graded AstroWizard photos: +/- single-digit percent.
    contrast = float(np.clip(1.025 + (.30 - p95) * .12, 1.0, 1.065))
    saturation = float(np.clip(1.035 + (.20 - sat_med) * .08, .985, 1.055))
    return {
        "subject_x": cx, "subject_y": cy, "focus_confidence": confidence,
        "p95_luminance": p95, "median_saturation": sat_med,
        "suggested_contrast": contrast, "suggested_saturation": saturation,
    }


def resolve_cinematic(image: FloatImage, motion: Motion, effects: Effects,
                      cfg: Cinematic) -> tuple[Motion, Effects, dict[str, float]]:
    """Compute effective parameters without mutating the reusable configuration."""
    if not cfg.auto_focus and not cfg.auto_color:
        return motion, effects, {}
    metrics = analyze_photo(image)
    if cfg.auto_focus:
        # Confidence prevents movement on plain skies with no clear subject.
        t = cfg.focus_strength * np.clip(metrics["focus_confidence"] * 1.5, 0, 1)
        motion = replace(motion,
                         center_x=float(np.clip(motion.center_x * (1-t) + metrics["subject_x"] * t, .1, .9)),
                         center_y=float(np.clip(motion.center_y * (1-t) + metrics["subject_y"] * t, .1, .9)))
    if cfg.auto_color:
        t = cfg.color_strength
        effects = replace(effects,
                          contrast=float(np.clip(effects.contrast *
                                  (1 + t * (metrics["suggested_contrast"] - 1)), .1, 2)),
                          saturation=float(np.clip(effects.saturation *
                                  (1 + t * (metrics["suggested_saturation"] - 1)), 0, 2)))
    metrics["effective_focus_x"] = motion.center_x
    metrics["effective_focus_y"] = motion.center_y
    metrics["effective_contrast"] = effects.contrast
    metrics["effective_saturation"] = effects.saturation
    return motion, effects, metrics
