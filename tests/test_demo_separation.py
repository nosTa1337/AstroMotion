"""Tests for deliberately approximate and isolated public demo star extraction."""
import cv2
import numpy as np
import pytest

from astromotion.demo_separation import approximate_demo_layers
from astromotion.imaging import to_linear


def test_demo_star_extraction_moves_real_detected_light_and_reconstructs():
    h, w = 144, 192
    image = np.full((h, w, 3), .065, np.float32)
    for x, y, col in ((40, 50, (.95, .84, .75)), (108, 90, (.78, .88, 1.0)),
                      (150, 35, (.9, .92, .99))):
        yy, xx = np.mgrid[:h, :w]
        peak = np.exp(-((xx-x)**2+(yy-y)**2)/(2*1.1**2)).astype(np.float32)
        image += peak[..., None] * np.array(col, np.float32) * .75
    image = np.clip(image, 0, 1)
    layers = approximate_demo_layers(image)
    assert layers.diagnostics["demo_approximate_star_cores"] >= 3
    assert layers.stars.max() > .15
    assert layers.nebula[50, 40].max() < to_linear(image)[50, 40].max()
    np.testing.assert_allclose(layers.composite(), to_linear(image), atol=2e-6)


def test_demo_requires_detectable_points():
    with pytest.raises(ValueError, match="Sternkerne"):
        approximate_demo_layers(np.full((64, 64, 3), .03, np.float32))


@pytest.mark.parametrize("count", [0, 50001])
def test_demo_rejects_invalid_max_count(count):
    with pytest.raises(ValueError, match="max_stars"):
        approximate_demo_layers(np.zeros((32, 32, 3), np.float32), max_stars=count)
