"""Protect saturated stars, unmodified backgrounds and the clean loop presets."""
from pathlib import Path

import numpy as np
import pytest

from astromotion.animation import Animator
from astromotion.config import Separation, load_config
from astromotion.imaging import to_linear, to_srgb
from astromotion.looping import camera_phase
from astromotion.separation import composite, extract_layers


@pytest.mark.parametrize('blend', ['screen', 'additive'])
def test_blue_star_core_halo_and_background_are_preserved(blend):
    y, x = np.mgrid[:128, :128]
    r2 = (x-64)**2 + (y-64)**2
    base = np.full((128, 128, 3), [.015, .035, .12], np.float32)
    stars = (np.exp(-r2/8)[..., None]*[.5, .65, .7] +
             np.exp(-r2/100)[..., None]*[.001, .015, .13]).astype(np.float32)
    original = to_srgb(composite(base, stars, blend))
    raw = to_srgb(base)
    photo_before, raw_before = original.copy(), raw.copy()
    for legacy_cleanup in (False, True):
        layers = extract_layers(original, raw, Separation(blend=blend, foreground_cleanup=legacy_cleanup))
        np.testing.assert_allclose(layers.nebula, base, atol=2e-7)
        np.testing.assert_allclose(layers.stars, stars, atol=2e-7)
        np.testing.assert_allclose(layers.composite(), to_linear(original), atol=2e-7)
    np.testing.assert_array_equal(original, photo_before)
    np.testing.assert_array_equal(raw, raw_before)


def test_nonnegative_bound_is_the_only_background_change():
    original = np.full((32, 32, 3), .3, np.float32)
    raw = original.copy()
    raw[8, 8] = [.4, .2, .25]
    layers = extract_layers(original, raw, Separation(foreground_cleanup=True))
    np.testing.assert_array_equal(layers.nebula, np.minimum(to_linear(raw), to_linear(original)))
    np.testing.assert_allclose(layers.composite(), to_linear(original), atol=2e-7)


def test_shipped_presets_disable_special_effects_and_keep_visible_loop_motion():
    root = Path(__file__).resolve().parents[1]
    for path in (root/'configs').glob('*.yaml'):
        cfg = load_config(path)
        assert not cfg.starfield.enabled and not cfg.separation.foreground_cleanup
        assert not cfg.cinematic.auto_color
        assert cfg.effects.bloom == cfg.effects.glow == cfg.effects.grade == 0
        assert cfg.effects.contrast == cfg.effects.saturation == 1
    cfg = load_config(root/'configs/clean_loop.yaml')
    assert cfg.duration == 30 and cfg.loop.enabled
    assert cfg.audio.mode == 'ambient' and cfg.audio.seed is None
    base = np.full((128, 128, 3), .1, np.float32)
    stars = np.zeros_like(base); stars[40:43, 90:93] = [.4, .6, .9]
    layers = extract_layers(to_srgb(composite(base, stars)), to_srgb(base), cfg.separation)
    camera = Animator(layers, (120, 120), cfg.motion)
    a = camera.frame_layers(camera_phase(0), 0)
    b = camera.frame_layers(camera_phase(1), 30)
    for first, end in zip(a, b):
        np.testing.assert_array_equal(first, end)
    position = np.array([90., 40., 1.])
    bg = camera.matrix(1) @ position
    fg = camera.matrix(1, stars=True) @ position
    assert np.linalg.norm(bg-fg) > .6


def test_demo_gate_rejects_background_redistribution_even_when_reconstruction_matches():
    from astromotion.quality import check_layers
    from astromotion.separation import Layers
    base = np.full((64, 64, 3), .03, np.float32)
    stars = np.zeros_like(base); stars[30:34, 30:34] = [.005, .05, .7]
    original = to_srgb(composite(base, stars))
    clean = extract_layers(original, to_srgb(base), Separation())
    assert check_layers(original, to_srgb(base), clean)['background_error_linear'] == 0
    moved_stars = clean.stars * .5
    broken_base = (to_linear(original) - moved_stars) / (1 - moved_stars)
    broken = Layers(broken_base, moved_stars, 'screen', {})
    np.testing.assert_allclose(broken.composite(), to_linear(original), atol=2e-7)
    with pytest.raises(ValueError, match='no demo render'):
        check_layers(original, to_srgb(base), broken)
