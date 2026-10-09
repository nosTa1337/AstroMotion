"""Exercise complete interactive sessions without invoking StarNet or FFmpeg."""
from dataclasses import asdict
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

import wizard
from astromotion.config import load_config


def answers(monkeypatch, values):
    iterator = iter(values)
    monkeypatch.setattr('builtins.input', lambda prompt: next(iterator))


@pytest.fixture
def environment(tmp_path):
    images = tmp_path / 'Astro photos'
    images.mkdir()
    image = images / 'Pleiades M45.jpg'
    image.write_bytes(b'test image - not decoded')
    output = tmp_path / 'Finished videos'
    settings_path = tmp_path / 'settings.json'
    executable = str(Path(sys.executable).resolve())
    paths = {'starnet': executable, 'input_dir': str(images), 'output_dir': str(output),
             'ffmpeg': executable, 'ffprobe': executable}
    return image, output, settings_path, paths


def test_first_setup_and_next_image_reuse_defaults_without_reusing_caption(monkeypatch, environment):
    image, output, settings_path, paths = environment
    # First run: initialize paths, change video settings, supply a caption.
    answers(monkeypatch, [paths['starnet'], paths['input_dir'], paths['output_dir'],
                          paths['ffmpeg'], paths['ffprobe'], image.name,
                          '45', '60', '720p', 'square', '', 'Plejaden', 'MESSIER 45',
                          '', 'zufall', 'n', '', 'j'])
    recorded = []

    def fake_render(command, **kwargs):
        assert kwargs['cwd'] == wizard.ROOT and kwargs['check'] is False
        assert command[0] == sys.executable
        assert command[command.index('--input') + 1] == str(image)
        config_path = Path(command[command.index('--config') + 1])
        config = load_config(config_path)
        assert config.starfield.enabled and config.starfield.photo_profiles
        assert config.loop.enabled and not config.separation.foreground_cleanup
        assert config.starfield.close_passes == 0
        assert config.effects.bloom == config.effects.glow == config.effects.grade == 0
        recorded.append(asdict(config))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(wizard.subprocess, 'run', fake_render)
    assert wizard.main(['--settings', str(settings_path)]) == 0
    assert recorded[0]['caption']['title'] == 'Plejaden'
    assert recorded[0]['caption']['subtitle'] == 'MESSIER 45'
    stored = wizard.load_settings(settings_path)
    assert stored['paths'] == paths
    assert stored['defaults']['duration'] == 45
    assert stored['defaults']['caption']['title'] == ''
    assert stored['defaults']['caption']['enabled'] is False
    assert stored['defaults']['audio']['seed'] is None
    # No setup questions on subsequent runs; Enter keeps previous video settings.
    answers(monkeypatch, [image.name, '', '', '', '', '', '', '', '', 'n', '', 'j'])
    assert wizard.main(['--settings', str(settings_path)]) == 0
    assert len(recorded) == 2
    assert (recorded[1]['duration'], recorded[1]['fps'], recorded[1]['resolution'], recorded[1]['format']) == (45, 60, '720p', 'square')
    assert recorded[1]['caption']['enabled'] is False
    assert not list(settings_path.parent.glob('settings.json.*.tmp'))
    assert not (output / 'Pleiades M45_astromotion.mp4').exists()


def test_existing_output_is_not_overwritten_without_confirmation(monkeypatch, environment):
    image, output, _, paths = environment
    output.mkdir()
    existing = output / 'Pleiades M45_astromotion.mp4'
    existing.write_bytes(b'original movie')
    settings = {'version': 1, 'paths': paths, 'defaults': {}}
    answers(monkeypatch, [image.name, '', '', '', '', '', '', 'none', 'n', '', 'n', 'new.mp4'])
    _, selected, _, overwrite = wizard.collect_render(settings)
    assert selected == output / 'new.mp4' and not overwrite
    assert existing.read_bytes() == b'original movie'


def test_replacement_flag_only_on_explicit_approval(monkeypatch, environment):
    image, output, _, paths = environment
    output.mkdir()
    (output / 'Pleiades M45_astromotion.mp4').write_bytes(b'original movie')
    answers(monkeypatch, [image.name, '', '', '', '', '', '', 'none', 'n', '', 'j'])
    image, selected, _, overwrite = wizard.collect_render({'paths': paths})
    command = wizard.render_command(image, selected, Path('config.json'), overwrite)
    assert '--overwrite' in command


def test_dry_run_does_not_launch_a_process_and_accepts_safe_custom_audio(monkeypatch, environment):
    image, _, settings_path, paths = environment
    music = image.parent / 'ambient track.wav'
    music.write_bytes(b'not decoded')
    wizard.save_settings(settings_path, {'version': 1, 'paths': paths, 'defaults': {}})
    answers(monkeypatch, ['', '', '', '', '', 'Stars " & | test', '', 'file', f'"{music}"', 'n', 'video & test.mp4'])
    monkeypatch.setattr(wizard.subprocess, 'run', lambda *a, **kw: pytest.fail('Dry run launched a process'))
    assert wizard.main(['--settings', str(settings_path), '--input', image.name, '--dry-run']) == 0
    command = wizard.render_command(image, image.parent / 'video & test.mp4', Path('config.json'), False)
    assert command[command.index('--output') + 1].endswith('video & test.mp4')
    assert '--overwrite' not in command


def test_invalid_fps_and_duration_are_reprompted(monkeypatch, environment):
    image, _, _, paths = environment
    answers(monkeypatch, [image.name, 'nan', '0', '30', '999', '30', '', '', '', '', 'none', 'n', ''])
    _, _, cfg, _ = wizard.collect_render({'paths': paths})
    assert cfg.duration == 30 and cfg.fps == 30


def test_unreadable_settings_fail_with_setup_hint_and_can_be_reset(monkeypatch, environment, capsys):
    _, _, settings_path, paths = environment
    settings_path.write_text('{broken json')
    assert wizard.main(['--settings', str(settings_path)]) == 1
    assert '--setup' in capsys.readouterr().err
    answers(monkeypatch, [paths['starnet'], paths['input_dir'], paths['output_dir'], paths['ffmpeg'], paths['ffprobe']])
    monkeypatch.setattr(wizard, 'collect_render', lambda *a: (_ for _ in ()).throw(EOFError()))
    assert wizard.main(['--settings', str(settings_path), '--setup']) == 130
    assert wizard.load_settings(settings_path)['paths'] == paths


def test_cancelled_render_is_not_started(monkeypatch, environment):
    image, _, settings_path, paths = environment
    wizard.save_settings(settings_path, {'version': 1, 'paths': paths, 'defaults': {}})
    answers(monkeypatch, [image.name, '', '', '', '', '', '', 'none', 'n', '', 'n'])
    monkeypatch.setattr(wizard.subprocess, 'run', lambda *a, **kw: pytest.fail('Cancelled render launched a process'))
    assert wizard.main(['--settings', str(settings_path)]) == 0


def test_missing_starnet_is_detected_before_render_questions(environment):
    _, _, _, paths = environment
    paths['starnet'] = 'nonexistent-starnet-file'
    with pytest.raises(ValueError, match='--setup'):
        wizard.validate_paths({'paths': paths})
