"""Preview timing and render configuration checks; no StarNet or video rendering."""
from dataclasses import asdict
import json
from pathlib import Path

import pytest

import astromotion.cli as cli
from astromotion.config import Config, apply_profile
from astromotion.preview import preview_config


@pytest.mark.parametrize('format', ['vertical', 'square', 'landscape'])
@pytest.mark.parametrize('progress', [0, .3, 1])
def test_photo_preview_matches_renderer_camera_without_changing_inputs(format, progress):
    import cv2
    import numpy as np
    from astromotion.animation import Animator
    from astromotion.preview import photo_preview_frame
    from astromotion.separation import Layers

    y, x = np.mgrid[:120, :160].astype(np.float32)
    image = np.stack((x / 160, y / 120, np.full_like(x, .4)), axis=2)
    before = image.copy()
    cfg = Config(format=format, resolution='360p')
    cfg.motion.center_x, cfg.motion.center_y = .7, .3
    cfg.motion.rotation_deg, cfg.motion.zoom = -40, .25
    config_before = asdict(cfg)
    camera = Animator(Layers(image, image, 'screen', {}), cfg.size, cfg.motion)
    expected = camera.warp(image, camera.matrix(progress))
    np.testing.assert_array_equal(photo_preview_frame(image, cfg, progress, cfg.size), expected)
    size = tuple(side // 2 for side in cfg.size)
    small = photo_preview_frame(image, cfg, progress, size)
    assert small.shape == (size[1], size[0], 3)
    if progress == 1:  # Safe crop has no bars; smooth gradients can be compared after resizing.
        np.testing.assert_allclose(small, cv2.resize(expected, size), atol=5e-4)
    np.testing.assert_array_equal(image, before)
    assert asdict(cfg) == config_before


@pytest.mark.parametrize('format,size', [('vertical', (360, 640)), ('square', (360, 360)), ('landscape', (640, 360))])
@pytest.mark.parametrize('fps', [24, 30, 60])
def test_preview_only_changes_output_size_and_keeps_loop_timing(format, size, fps):
    cfg = apply_profile(Config(), 'explore')
    cfg.format, cfg.fps, cfg.duration = format, fps, 30.0
    cfg.loop.star_cycles = 2
    cfg.audio.seed, cfg.profile_seed = 123, 456
    before = asdict(cfg)
    preview = preview_config(cfg)
    assert preview.size == size and preview.frame_count == 30 * fps
    assert preview.actual_duration == cfg.actual_duration == 30
    assert asdict(preview) == {**before, 'resolution': '360p'}
    assert asdict(cfg) == before


def test_cli_preview_keeps_file_duration_fps_and_explicit_overrides(tmp_path, capsys):
    path = tmp_path / 'setup.json'
    path.write_text(json.dumps({'profile': 'explore', 'duration': 45.0, 'fps': 60,
                                'loop': {'star_cycles': 2}, 'audio': {'style': 'pulse', 'seed': 55}}))
    assert cli.main(['--config', str(path), '--preview', '--print-config']) == 0
    data = json.loads(capsys.readouterr().out)
    assert data['duration'] == 45 and data['fps'] == 60 and data['resolution'] == '360p'
    assert data['profile'] == 'explore' and data['loop']['star_cycles'] == 2
    assert data['audio']['style'] == 'pulse' and data['audio']['seed'] == 55
    assert cli.main(['--profile', 'explore', '--preview', '--duration', '10', '--fps', '30', '--print-config']) == 0
    data = json.loads(capsys.readouterr().out)
    assert (data['duration'], data['fps'], data['resolution']) == (10, 30, '360p')


def test_cli_preview_uses_separate_default_filename_and_genuine_separation(monkeypatch, tmp_path):
    recorded = []
    monkeypatch.setattr(cli, 'render', lambda image, output, cfg, *args: recorded.append((image, output, cfg)))
    image = tmp_path / 'photo.jpg'
    assert cli.main(['--input', str(image), '--starnet', str(tmp_path / 'starnet2'), '--profile', 'explore', '--preview']) == 0
    _, output, cfg = recorded[0]
    assert output == image.with_name('photo_preview.mp4')
    assert cfg.duration == 30 and cfg.size == (360, 640)
    assert cfg.separation.executable == str(tmp_path / 'starnet2')
