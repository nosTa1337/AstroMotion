import wave

import numpy as np
import pytest

from astromotion.config import Audio, Starfield, load_config
from astromotion.music import synthesize_ambient
from astromotion.starprofiles import StarProfiles
from test_starfield import field


def profiles():
    y, x = np.mgrid[:49, :49].astype(np.float32)
    r2 = (x - 24)**2 + (y - 24)**2
    core = np.exp(-((x - 24)**2 / 8 + (y - 24)**2 / 2))
    halo = .08 * np.exp(-r2 / 18)
    rgb = np.stack((core * .8 + halo, core * .7 + halo * .4,
                    core * .6 + halo * .1), axis=2).astype(np.float32)
    cores = np.zeros((49, 49), bool)
    cores[24, 24] = True
    return StarProfiles(rgb, np.array([24]), np.array([24]), cores)


def test_photo_profile_retains_asymmetric_shape_and_colored_halo():
    p = profiles()
    a = p.rgba[0, ..., 3]
    y, x = np.mgrid[-8:9, -8:9]
    bright_core = np.maximum(a - .5, 0)
    assert (bright_core * x*x).sum() > 1.4 * (bright_core * y*y).sum()
    rgb = p.rgba[0, ..., :3]
    core_ratio = rgb[8, 8, 2] / rgb[8, 8, 0]
    halo_ratio = rgb[12, 8, 2] / rgb[12, 8, 0]
    # Chromaticity is deliberately regularized to prevent amplified sensor
    # fringes, while the halo remains warmer than the core.
    assert halo_ratio < core_ratio * .95
    assert (rgb <= a[..., None] + 1e-6).all()
    assert not p.rgba[0, 0].any()  # no patch rectangle


def test_profile_defocus_spreads_energy_without_dark_or_colored_fringe():
    p = profiles()
    sharp = p.draw(0, (101, 101), (50, 50), 4, 0, (0, 0))
    soft = p.draw(0, (101, 101), (50, 50), 4, 3, (0, 0))
    y, x = np.mgrid[-50:51, -50:51]
    r2 = x*x + y*y
    def variance(a):
        return (a * r2).sum() / a.sum()
    assert variance(soft[..., 3]) > variance(sharp[..., 3])
    np.testing.assert_allclose(soft[..., :3].sum(axis=(0, 1)), sharp[..., :3].sum(axis=(0, 1)), rtol=.002)
    assert (soft[..., :3] <= soft[..., 3:4] + 1e-6).all()


def test_profile_excludes_neighboring_detected_star():
    source = np.zeros((49, 49, 3), np.float32)
    source[24, 24] = [.4, .35, .3]
    source[24, 30] = [.9, .9, .9]
    cores = source.max(axis=2) > 0
    p = StarProfiles(source, np.array([24]), np.array([24]), cores)
    assert p.rgba[0, 8, 8, 3] > .99
    assert p.rgba[0, 8, 14, 3] == 0


def test_tiny_sensor_color_pixels_do_not_become_saturated_rgb_blocks():
    source = np.zeros((49, 49, 3), np.float32)
    source[24, 23, 0] = source[24, 24, 1] = source[24, 25, 2] = .6
    cores = np.zeros((49, 49), bool)
    cores[24, 24] = True
    p = StarProfiles(source, np.array([24]), np.array([24]), cores)
    rgba = p.rgba[0]
    bright = rgba[..., 3] > .4
    colors = rgba[bright, :3] / rgba[bright, 3:4]
    assert colors.min() > .5


def test_close_stars_are_selected_once_and_few_over_entire_clip():
    p = field(Starfield(close_passes=6, photo_profiles=True))
    selected = p.featured.copy()
    assert 0 < selected.sum() <= 6
    for t in (0, .25, .5, .75, 1):
        out = p.composite(np.zeros((120, 120, 3), np.float32), t, 15)
        assert np.isfinite(out).all() and out.min() >= 0 and out.max() <= 1
        np.testing.assert_array_equal(p.featured, selected)


def test_ambient_accents_are_reproducible_audible_and_fade_cleanly(tmp_path):
    pcm = []
    for i, accents in enumerate((0., .45, .45)):
        path = tmp_path / f"{i}.wav"
        synthesize_ambient(path, 6, Audio(seed=73, accents=accents, harmony="floating"))
        with wave.open(str(path)) as wav:
            assert wav.getnframes() == 288000
            data = np.frombuffer(wav.readframes(wav.getnframes()), "<i2")
        assert not data[:2].any() and not data[-2:].any()
        assert np.abs(data).max() < 32767
        pcm.append(data)
    np.testing.assert_array_equal(pcm[1], pcm[2])
    assert np.sqrt(np.mean((pcm[0].astype(float) - pcm[1])**2)) > 30
    with pytest.raises(ValueError):
        load_config(overrides={"audio": {"accents": 1.1}})
