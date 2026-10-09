"""Generate a synthetic emission nebula and its exact, known starless companion.

This is a fixture generator, NOT a simulated replacement for star removal.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
from PIL import Image

from astromotion.imaging import save_png, save_tiff, to_srgb
from astromotion.separation import composite


def generate(folder: Path, seed: int = 2026, size: tuple[int, int] = (1440, 1920)) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    w, h = size
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[:h, :w].astype(np.float32)
    x = (x - w / 2) / (w / 2)
    y = (y - h / 2) / (h / 2)
    fractal = np.zeros((h, w), np.float32)
    for n, gain in ((5, .45), (10, .24), (24, .14), (56, .08), (128, .04)):
        noise = rng.random((n, n), dtype=np.float32)
        fractal += cv2.resize(noise, (w, h), interpolation=cv2.INTER_CUBIC) * gain
    ridge = x + .3 * np.sin(y * 3.8) - .15
    body = np.exp(-(ridge**2 / .30 + (y + .05)**2 / .85))
    filaments = np.clip((fractal - .28) * 3, 0, 1.3) ** 1.6
    emission = body * filaments
    dust = np.exp(-((ridge + .07)**2 / .018 + (y - .05)**2 / .9)) * (.45 + fractal)
    nebula = np.zeros((h, w, 3), np.float32) + np.array([.0045, .0055, .010], np.float32)
    nebula += emission[..., None] * np.array([.29, .045, .12], np.float32)
    blue = np.exp(-((x + .27)**2 / .14 + (y + .32)**2 / .20)) * filaments
    nebula += blue[..., None] * np.array([.018, .065, .16], np.float32)
    nebula *= (1 - np.clip(dust * .78, 0, .85))[..., None]
    core = np.exp(-((x - .17)**2 / .045 + (y + .06)**2 / .075))
    nebula += core[..., None] * np.array([.13, .095, .12], np.float32)
    nebula = np.clip(nebula, 0, .85)
    stars = np.zeros_like(nebula)
    for _ in range(round(w * h / 3200)):
        sx, sy = int(rng.integers(0, w)), int(rng.integers(0, h))
        sigma = float(rng.uniform(.45, 1.3))
        amp = float(rng.uniform(.025, .72) ** 1.15)
        if rng.random() < .022:
            sigma, amp = sigma * 2.2, .95
        radius = int(np.ceil(sigma * 6))
        xx0, xx1 = max(0, sx - radius), min(w, sx + radius + 1)
        yy0, yy1 = max(0, sy - radius), min(h, sy + radius + 1)
        gy, gx = np.mgrid[yy0:yy1, xx0:xx1]
        r2 = (gx - sx)**2 + (gy - sy)**2
        psf = np.exp(-r2 / (2 * sigma**2)) + .024 * np.exp(-r2 / (10 * sigma**2))
        color = np.array([1, .86, .70]) if rng.random() < .3 else np.array([.77, .87, 1])
        stars[yy0:yy1, xx0:xx1] += (psf[..., None] * amp * color).astype(np.float32)
    original = to_srgb(composite(nebula, np.clip(stars, 0, 1)))
    starless = to_srgb(nebula)
    save_png(folder / "deep_sky.png", original)
    save_png(folder / "deep_sky_starless.png", starless)
    save_tiff(folder / "deep_sky_16bit.tif", original)
    Image.fromarray(np.round(original * 255).astype(np.uint8)).save(folder / "deep_sky_preview.jpg", quality=95)
    print(f"Demo-Paar erstellt: {folder.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("examples"))
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    generate(args.output, args.seed)
