"""Preview timing and render configuration checks; no StarNet or video rendering."""
from dataclasses import asdict
import json
from pathlib import Path

import pytest

import astromotion.cli as cli
from astromotion.config import Config, apply_profile
from astromotion.preview import preview_config


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
