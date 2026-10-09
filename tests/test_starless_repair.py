"""Regression tests for blue-star donuts in optional StarNet foreground cleanup."""
from __future__ import annotations

import numpy as np

from astromotion.starless_repair import repair_bright_star_holes


def scene(corrupt: bool):
    h = w = 192
    yy, xx = np.mgrid[:h, :w]
    base = np.zeros((h, w, 3), np.float32)
    base[:] = [.15, .2, .42]
    base += (xx / w)[..., None] * [.02, .03, .05]
    star = np.exp(-((xx - 88)**2 + (yy - 90)**2) / (2 * 2.0**2))
    source = np.clip(base + star[..., None] * [.84, .78, .62], 0, 1)
    starless = base.copy()
    if corrupt:
        inner = (xx - 88)**2 + (yy - 90)**2 < 5**2
        starless[inner] = [.35, .01, .45]
    return source, base, starless


def test_bright_blue_star_hole_repaired():
    photo, background, broken = scene(True)
    fixed, count = repair_bright_star_holes(photo, broken)
    assert count == 1
    np.testing.assert_allclose(fixed[90, 88], background[90, 88], atol=.03)
    assert np.array_equal(fixed[:40, :40], broken[:40, :40])


def test_clean_starnet_stays_untouched():
    photo, background, _ = scene(False)
    fixed, count = repair_bright_star_holes(photo, background)
    assert count == 0
    assert np.array_equal(fixed, background)


def test_diffuse_nebula_not_mistaken_for_star():
    _, background, broken = scene(True)
    fixed, count = repair_bright_star_holes(background, broken)
    assert count == 0
    assert np.array_equal(fixed, broken)
