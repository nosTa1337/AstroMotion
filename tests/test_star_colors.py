"""Color regression tests using small synthetic layers; no video rendering."""
from pathlib import Path

import numpy as np
import pytest

from astromotion.animation import Animator
from astromotion.cli import main
from astromotion.config import Loop, Motion, Starfield, load_config
from astromotion.separation import Layers
from astromotion.starfield import PerspectiveStars
from astromotion.starprofiles import StarProfiles, soften_star_colors

LUMA = np.array([.2126, .7152, .0722], np.float32)


def test_color_strength_reduces_red_excess_without_changing_luminance_or_whites():
    rgb = np.array([[1, .01, .005], [.1, .2, 1], [1, 1, 1]], np.float32)
    original = rgb.copy()
    softer = soften_star_colors(rgb, .6)
    assert softer[0].max() - softer[0].min() < .61 * (rgb[0].max() - rgb[0].min())
    np.testing.assert_allclose(softer @ LUMA, rgb @ LUMA, atol=1e-7)
    np.testing.assert_array_equal(softer[2], rgb[2])
    np.testing.assert_array_equal(rgb, original)
    np.testing.assert_array_equal(soften_star_colors(rgb, 1), rgb)
    neutral = soften_star_colors(rgb, 0)
    np.testing.assert_allclose(neutral[:, 0], neutral[:, 1])
    np.testing.assert_allclose(neutral[:, 1], neutral[:, 2])


def red_star_layer():
    source = np.zeros((48, 48, 3), np.float32)
    yy, xx = np.mgrid[:48, :48]
    source[:] = np.exp(-((xx - 24)**2 + (yy - 24)**2) / 3)[..., None] * [1, .002, .001]
    return source


def test_photo_profiles_keep_alpha_shape_and_luminance_at_all_mip_levels():
    source = red_star_layer()
    unchanged = source.copy()
    cores = np.zeros(source.shape[:2], bool)
    cores[24, 24] = True
    full = StarProfiles(source, np.array([24]), np.array([24]), cores, 1)
    soft = StarProfiles(source, np.array([24]), np.array([24]), cores, .6)
    for a, b in zip(full.mips, soft.mips):
        np.testing.assert_array_equal(a[..., 3], b[..., 3])
        np.testing.assert_allclose(a[..., :3] @ LUMA, b[..., :3] @ LUMA, atol=2e-7)
        assert np.all(b[..., :3] <= b[..., 3:4] + 1e-7)
        assert np.all(b[..., :3][b[..., 3] == 0] == 0)
    np.testing.assert_array_equal(full.sigma, soft.sigma)
    np.testing.assert_array_equal(source, unchanged)


@pytest.mark.parametrize('profiles', [False, True])
def test_star_color_control_keeps_background_geometry_and_loop(profiles):
    background = np.full((48, 48, 3), [.07, .03, .12], np.float32)
    source = red_star_layer()
    layers = Layers(background, source, 'screen', {})
    camera = Animator(layers, (48, 48), Motion(zoom=0, rotation_deg=0, pan_x=0, pan_y=0))
    full = PerspectiveStars(layers, camera, Starfield(photo_profiles=profiles, color_strength=1), 30, Loop(enabled=True))
    soft = PerspectiveStars(layers, camera, Starfield(photo_profiles=profiles, color_strength=.6), 30, Loop(enabled=True))
    np.testing.assert_array_equal(full.initial_z, soft.initial_z)
    np.testing.assert_array_equal(full.world_xy, soft.world_xy)
    old_background = background.copy()
    # Keep one star visible to exercise actual compositing in both render paths.
    for field in (full, soft):
        field.world_xy[:] = 0
        field.initial_z[:] = .5
    a, b = full.composite(background, 0, 30), soft.composite(background, 0, 30)
    assert np.max(np.abs(a - b)) > .01
    np.testing.assert_allclose(a @ LUMA, b @ LUMA, atol=2e-6)
    np.testing.assert_array_equal(background, old_background)
    np.testing.assert_array_equal(b[0, 0], background[0, 0])
    np.testing.assert_allclose(b, soft.composite(background, 1, 30), atol=1e-6)


def test_cli_color_override_combines_with_depth_mode_and_presets(capsys):
    preset = Path(__file__).parents[1] / 'configs/immersive_loop.yaml'
    assert load_config(preset).starfield.color_strength == .6
    assert main(['--config', str(preset), '--star-color-strength', '0.3',
                 '--depth-mode', 'adaptive', '--print-config']) == 0
    import json
    data = json.loads(capsys.readouterr().out)
    assert data['starfield']['color_strength'] == .3
    assert data['starfield']['depth_mode'] == 'adaptive'
    for invalid in (-.1, 1.1, float('nan')):
        with pytest.raises(ValueError):
            load_config(overrides={'starfield': {'color_strength': invalid}})
