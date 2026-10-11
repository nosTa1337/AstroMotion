import cv2
import numpy as np
import pytest

from astromotion.animation import Animator
from astromotion.config import Loop, Motion, Starfield
from astromotion.separation import Layers
from astromotion.starfield import PerspectiveStars


def detect(stars, photo_profiles=False):
    layers = Layers(np.zeros_like(stars), stars, "screen", {})
    side = stars.shape[0]
    camera = Animator(layers, (side, side), Motion(
        zoom=0, rotation_deg=0, pan_x=0, pan_y=0, parallax=0))
    flight = PerspectiveStars(layers, camera, Starfield(
        count=1000, photo_profiles=photo_profiles), 30, Loop(enabled=True))
    projected = flight.world_xy / (flight.cfg.far * .55) * flight.focal + flight.center
    coords = np.c_[projected, np.ones(flight.count)] @ cv2.invertAffineTransform(camera.matrix(0)).T
    return flight, coords


@pytest.mark.parametrize("angle", [0, 45, 90, 135])
@pytest.mark.parametrize("photo_profiles", [False, True])
def test_rippled_light_ridge_does_not_become_a_line_of_flying_stars(angle, photo_profiles):
    y, x = np.mgrid[:240, :240]
    radians = np.deg2rad(angle)
    c, s = np.cos(radians), np.sin(radians)
    across = (x - 120) * c + (y - 120) * s
    along = -(x - 120) * s + (y - 120) * c
    ridge = .15 * np.exp(-.5 * (across / 1.2) ** 2)
    ridge *= 1 + .05 * np.cos(along * np.pi / 4)
    ridge *= np.abs(along) < 85
    stars = np.repeat(ridge[..., None], 3, axis=2).astype(np.float32)
    real = []
    for offset in (-50, 50):
        for length in (-65, -20, 35, 65):
            sx, sy = 120 + offset * c - length * s, 120 + offset * s + length * c
            real.append((sx, sy))
            stars += (.6 * np.exp(-((x - sx) ** 2 + (y - sy) ** 2) / 2))[..., None]
    unchanged = stars.copy()
    flight, coords = detect(stars, photo_profiles)
    assert flight.count == len(real)
    assert flight.stats["rejected_noncompact_star_candidates"] > 0
    distances = np.linalg.norm(coords[:, None] - np.array(real)[None], axis=2)
    assert np.all(distances.min(axis=0) < 1)
    assert np.all(distances.min(axis=1) < 1)
    np.testing.assert_array_equal(stars, unchanged)
    for start, end in zip(flight.project(0), flight.project(1)):
        np.testing.assert_array_equal(start, end)
    if photo_profiles:
        assert len(flight.profiles.rgba) == len(real)


def test_saturated_plateau_has_one_core_and_keeps_the_bright_star():
    y, x = np.mgrid[:160, :160]
    stars = np.zeros((160, 160, 3), np.float32)
    real = [(45, 50), (110, 105)]
    for sx, sy in real:
        stars += np.minimum(2 * np.exp(-((x - sx) ** 2 + (y - sy) ** 2) / 72), .8)[..., None]
    flight, coords = detect(stars, photo_profiles=True)
    assert flight.count == 2
    np.testing.assert_allclose(coords, real, atol=.01)


def test_real_stars_aligned_in_a_line_are_preserved():
    y, x = np.mgrid[:240, :240]
    stars = np.zeros((240, 240, 3), np.float32)
    real = [(120, sy) for sy in range(30, 211, 12)]
    for sx, sy in real:
        stars += (.6 * np.exp(-((x - sx) ** 2 + (y - sy) ** 2) / 2))[..., None]
    flight, coords = detect(stars)
    assert flight.count == len(real)
    np.testing.assert_allclose(coords, real, atol=.01)


def test_real_colored_and_elongated_star_on_a_ridge_is_preserved():
    y, x = np.mgrid[:160, :160]
    ridge = .12 * np.exp(-.5 * ((x - 80) / 1.2) ** 2)
    ridge *= 1 + .05 * np.cos(y * np.pi / 4)
    stars = np.repeat(ridge[..., None], 3, axis=2).astype(np.float32)
    stars += np.exp(-.5 * (((x - 80) / 1.3) ** 2 + ((y - 80) / 2) ** 2))[..., None] * np.array([.8, .03, .02])
    stars += np.exp(-.5 * ((x - 40) ** 2 + (y - 45) ** 2))[..., None] * np.array([.04, .08, .9])
    flight, coords = detect(stars)
    assert flight.count == 2
    np.testing.assert_allclose(coords, [(40, 45), (80, 80)], atol=.01)


def test_constant_bright_residual_is_not_a_star():
    with pytest.raises(ValueError, match="Sternkerne"):
        detect(np.full((120, 120, 3), .1, np.float32))
