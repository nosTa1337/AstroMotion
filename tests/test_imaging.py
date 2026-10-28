"""Transparent photo import flattens onto black without changing source files."""
import cv2
import numpy as np
from PIL import Image, ImageCms
import pytest

from astromotion.imaging import load_image


@pytest.mark.parametrize('dtype', [np.uint8, np.uint16])
@pytest.mark.parametrize('suffix', ['.png', '.tif'])
def test_rgba_flattens_alpha_on_black_and_preserves_precision(tmp_path, dtype, suffix):
    maximum = np.iinfo(dtype).max
    rgba = np.full((20, 24, 4), [maximum, maximum // 3, 17, maximum], dtype=dtype)
    rgba[:, :8, 3] = 0
    rgba[:, 8:16, 3] = maximum // 2
    path = tmp_path / ('transparent' + suffix)
    ok, encoded = cv2.imencode(suffix, rgba[..., [2, 1, 0, 3]])
    assert ok
    encoded.tofile(path)
    before = path.read_bytes()
    actual = load_image(path)
    expected = rgba[..., :3].astype(np.float32) / maximum * (rgba[..., 3:].astype(np.float32) / maximum)
    assert actual.shape == (20, 24, 3) and actual.dtype == np.float32
    np.testing.assert_allclose(actual, expected, atol=1e-7)
    assert path.read_bytes() == before


@pytest.mark.parametrize('icc', [False, True])
def test_palette_transparency_including_partial_alpha(tmp_path, icc):
    indices = np.tile(np.repeat(np.arange(3, dtype=np.uint8), 8), (20, 1))
    image = Image.fromarray(indices).convert('P')
    image.putpalette([255, 0, 0, 0, 255, 0, 0, 0, 255] + [0] * (768 - 9))
    options = {'transparency': bytes([0, 128, 255])}
    if icc:
        options['icc_profile'] = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    path = tmp_path / 'palette.png'
    image.save(path, **options)
    actual = load_image(path)
    np.testing.assert_array_equal(actual[:, :8], 0)
    np.testing.assert_allclose(actual[:, 8:16], np.broadcast_to([0, 128 / 255, 0], (20, 8, 3)), atol=1e-7)
    np.testing.assert_array_equal(actual[:, 16:], np.broadcast_to([0, 0, 1], (20, 8, 3)))


def test_grayscale_alpha_and_orientation_stay_aligned(tmp_path):
    image = Image.new('LA', (24, 20), (180, 255))
    image.paste((180, 0), (0, 0, 8, 20))
    exif = Image.Exif()
    exif[274] = 6
    path = tmp_path / 'gray.png'
    image.save(path, exif=exif)
    actual = load_image(path)
    assert actual.shape == (24, 20, 3)
    np.testing.assert_array_equal(actual[:8], 0)
    np.testing.assert_allclose(actual[8:], 180 / 255, atol=1e-7)
