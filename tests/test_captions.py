from pathlib import Path

import numpy as np
import pytest

from astromotion.captions import CaptionOverlay
from astromotion.config import Caption, Config, load_config


def test_caption_fades_and_leaves_scene_unchanged_outside_text():
    cfg = Caption(enabled=True, title="Orionnebel", subtitle="MESSIER 42")
    overlay = CaptionOverlay(cfg, (720, 1280))
    background = np.full((1280, 720, 3), .12, np.float32)
    assert overlay.apply(background, 1) is background
    assert overlay.apply(background, 7) is background
    assert overlay.opacity(2.45) == pytest.approx(.38)
    assert overlay.opacity(3.5) == pytest.approx(.76)
    assert overlay.opacity(6.05) == pytest.approx(.38)
    visible = overlay.apply(background, 3.5)
    assert np.array_equal(visible[:overlay.y], background[:overlay.y])
    assert np.array_equal(background, np.full_like(background, .12))
    assert np.count_nonzero(visible != background) > 100
    assert visible.min() >= 0 and visible.max() <= 1


def test_unicode_caption_and_long_line_fit_frame():
    overlay = CaptionOverlay(Caption(enabled=True, title="Größerer Reflexionsnebel – weit draußen im All"), (720, 720))
    assert overlay.x + overlay.alpha.shape[1] <= 720
    assert overlay.y + overlay.alpha.shape[0] <= 720


def test_missing_explicit_font_fails_clearly():
    with pytest.raises(ValueError, match="Schriftfont"):
        CaptionOverlay(Caption(enabled=True, title="Nebel", font="missing_nonexistent.ttf"), (720, 1280))


def test_caption_config_validation_and_relative_font_path(tmp_path: Path):
    with pytest.raises(ValueError, match="leer"):
        Config(caption=Caption(enabled=True)).validate()
    with pytest.raises(ValueError, match="Steuerzeichen"):
        Config(caption=Caption(title="Nebel\nM42")).validate()
    file = tmp_path / "caption.yaml"
    file.write_text('caption:\n  enabled: true\n  title: Orionnebel\n  font: fonts/local.ttf\n')
    cfg = load_config(file)
    assert cfg.caption.font == str((tmp_path / "fonts/local.ttf").resolve())
