"""Regression tests for opt-in cinematic intelligence and depth assignment."""
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from astromotion.animation import Animator
from astromotion.config import Cinematic, Effects, Motion, Starfield, load_config
from astromotion.intelligence import analyze_photo, resolve_cinematic
from astromotion.separation import Layers
from astromotion.starfield import PerspectiveStars


def off_center_object():
    h, w = 160, 240
    yy, xx = np.mgrid[:h, :w]
    body = np.exp(-(((xx - 174)/23)**2 + ((yy - 48)/19)**2)/2)
    image = np.full((h, w, 3), .015, np.float32)
    image += body[..., None] * np.array([.65, .08, .32], np.float32)
    return np.clip(image, 0, 1)


def test_focus_is_bounded_and_tracks_diffuse_nebula_not_stars():
    photo = off_center_object()
    photo[120, 12] = 1.0
    metrics = analyze_photo(photo)
    assert .55 < metrics["subject_x"] <= .70
    assert .30 <= metrics["subject_y"] < .50
    assert 0 < metrics["focus_confidence"] <= 1
    assert 1 <= metrics["suggested_contrast"] <= 1.065
    assert .985 <= metrics["suggested_saturation"] <= 1.055


def test_flat_sky_keeps_center_and_original_config():
    photo = np.full((100, 100, 3), .04, np.float32)
    motion, effects = Motion(), Effects()
    m, e, metrics = resolve_cinematic(photo, motion, effects, Cinematic(True, True))
    assert abs(metrics["subject_x"] - .5) < 1e-6
    assert abs(m.center_x - .5) < 1e-6
    assert m is not motion and e is not effects
    assert motion.center_x == .5
    assert effects.contrast == 1.015


def test_opt_in_off_preserves_original_motion_and_grading():
    img = off_center_object()
    motion, effects = Motion(), Effects()
    m, e, stats = resolve_cinematic(img, motion, effects, Cinematic())
    assert m is motion and e is effects and stats == {}


def test_auto_intelligence_is_deterministic_and_non_mutating():
    img = off_center_object()
    originals = img.copy()
    motion, effects = Motion(), Effects()
    cfg = Cinematic(auto_focus=True, auto_color=True, focus_strength=.95)
    first = resolve_cinematic(img, motion, effects, cfg)
    second = resolve_cinematic(img, motion, effects, cfg)
    assert first == second
    assert .50 < first[0].center_x <= .70
    np.testing.assert_array_equal(img, originals)
    assert motion.center_x == .5 and effects.contrast == 1.015


def test_validation_and_new_profile():
    root = Path(__file__).resolve().parents[1]
    cfg = load_config(root / "configs/cinematic_intelligence.yaml")
    assert cfg.cinematic.auto_focus and cfg.cinematic.auto_color
    assert cfg.starfield.depth_mode == "adaptive" and cfg.starfield.enabled
    for value in (-.1, 1.1):
        with pytest.raises(ValueError):
            load_config(overrides={"cinematic": {"focus_strength": value}})
    with pytest.raises(ValueError):
        load_config(overrides={"starfield": {"depth_mode": "fake"}})


def test_adaptive_depth_stays_bounded_and_reproducible():
    stars = np.zeros((120, 120, 3), np.float32)
    for j, amp in enumerate(np.linspace(.08, .9, 30)):
        y, x = 10 + (j // 6) * 18, 10 + (j % 6) * 18
        stars[y, x] = amp
    layers = Layers(np.full_like(stars, .03), stars, "screen", {})
    camera = Animator(layers, (120, 120), Motion())
    cfg = Starfield(enabled=True, count=30, depth_mode="adaptive", depth_correlation=.5)
    a = PerspectiveStars(layers, camera, cfg, 30)
    b = PerspectiveStars(layers, camera, cfg, 30)
    np.testing.assert_array_equal(a.initial_z, b.initial_z)
    assert a.initial_z.min() >= cfg.near and a.initial_z.max() <= cfg.far
    assert np.std(a.initial_z) > .1
    rnd = PerspectiveStars(layers, camera, replace(cfg, depth_mode="random"), 30)
    assert not np.array_equal(a.initial_z, rnd.initial_z)
