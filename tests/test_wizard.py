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
    prompts = []

    def answer(prompt):
        prompts.append(prompt)
        return next(iterator)

    monkeypatch.setattr('builtins.input', answer)
    return prompts


@pytest.fixture(autouse=True)
def default_language(monkeypatch):
    monkeypatch.setattr(wizard, 'LANGUAGE', 'en')


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
    prompts = answers(monkeypatch, ['', paths['starnet'], paths['input_dir'], paths['output_dir'],
                          paths['ffmpeg'], paths['ffprobe'], image.name, 'custom',
                          '45', '60', '720p', 'square', '', 'Plejaden', 'MESSIER 45',
                          '', 'random', 'zufall', 'n', '', 'j'])
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
    assert '[en]' in prompts[0]
    assert any('StarNet2: full path to the executable' in prompt for prompt in prompts)
    assert recorded[0]['caption']['title'] == 'Plejaden'
    assert recorded[0]['caption']['subtitle'] == 'MESSIER 45'
    stored = wizard.load_settings(settings_path)
    assert stored['language'] == 'en'
    assert stored['paths'] == paths
    assert stored['defaults']['duration'] == 45
    assert stored['defaults']['caption']['title'] == ''
    assert stored['defaults']['caption']['enabled'] is False
    assert stored['defaults']['audio']['seed'] is None
    # No setup questions on subsequent runs; Enter keeps previous video settings.
    answers(monkeypatch, ['', image.name, 'custom', '', '', '', '', '', '', 'ambient', 'random', 'zufall', 'n', '', 'j'])
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
    answers(monkeypatch, [image.name, 'custom', '', '', '', '', '', '', 'none', 'n', '', 'n', 'new.mp4'])
    _, selected, _, overwrite = wizard.collect_render(settings)
    assert selected == output / 'new.mp4' and not overwrite
    assert existing.read_bytes() == b'original movie'


def test_replacement_flag_only_on_explicit_approval(monkeypatch, environment):
    image, output, _, paths = environment
    output.mkdir()
    (output / 'Pleiades M45_astromotion.mp4').write_bytes(b'original movie')
    answers(monkeypatch, [image.name, 'custom', '', '', '', '', '', '', 'none', 'n', '', 'j'])
    image, selected, _, overwrite = wizard.collect_render({'paths': paths})
    command = wizard.render_command(image, selected, Path('config.json'), overwrite)
    assert '--overwrite' in command


def test_dry_run_does_not_launch_a_process_and_accepts_safe_custom_audio(monkeypatch, environment):
    image, _, settings_path, paths = environment
    music = image.parent / 'ambient track.wav'
    music.write_bytes(b'not decoded')
    wizard.save_settings(settings_path, {'version': 1, 'paths': paths, 'defaults': {}})
    answers(monkeypatch, ['custom', '', '', '', '', '', 'Stars " & | test', '', 'file', f'"{music}"', 'n', 'video & test.mp4'])
    monkeypatch.setattr(wizard.subprocess, 'run', lambda *a, **kw: pytest.fail('Dry run launched a process'))
    assert wizard.main(['--language', 'en', '--settings', str(settings_path), '--input', image.name, '--dry-run']) == 0
    command = wizard.render_command(image, image.parent / 'video & test.mp4', Path('config.json'), False)
    assert command[command.index('--output') + 1].endswith('video & test.mp4')
    assert '--overwrite' not in command


def test_invalid_fps_and_duration_are_reprompted(monkeypatch, environment):
    image, _, _, paths = environment
    answers(monkeypatch, [image.name, 'custom', 'nan', '0', '30', '999', '30', '', '', '', '', 'none', 'n', ''])
    _, _, cfg, _ = wizard.collect_render({'paths': paths})
    assert cfg.duration == 30 and cfg.fps == 30


def test_unreadable_settings_fail_with_setup_hint_and_can_be_reset(monkeypatch, environment, capsys):
    _, _, settings_path, paths = environment
    settings_path.write_text('{broken json')
    assert wizard.main(['--settings', str(settings_path)]) == 1
    assert '--setup' in capsys.readouterr().err
    answers(monkeypatch, [paths['starnet'], paths['input_dir'], paths['output_dir'], paths['ffmpeg'], paths['ffprobe']])
    monkeypatch.setattr(wizard, 'collect_render', lambda *a: (_ for _ in ()).throw(EOFError()))
    assert wizard.main(['--language', 'en', '--settings', str(settings_path), '--setup']) == 130
    assert wizard.load_settings(settings_path)['paths'] == paths


def test_cancelled_render_is_not_started(monkeypatch, environment):
    image, _, settings_path, paths = environment
    wizard.save_settings(settings_path, {'version': 1, 'paths': paths, 'defaults': {}})
    answers(monkeypatch, [image.name, 'custom', '', '', '', '', '', '', 'none', 'n', '', 'n'])
    monkeypatch.setattr(wizard.subprocess, 'run', lambda *a, **kw: pytest.fail('Cancelled render launched a process'))
    assert wizard.main(['--language', 'en', '--settings', str(settings_path)]) == 0


def test_missing_starnet_is_detected_before_render_questions(environment):
    _, _, _, paths = environment
    paths['starnet'] = 'nonexistent-starnet-file'
    with pytest.raises(ValueError, match='--setup'):
        wizard.validate_paths({'paths': paths})


def test_profile_and_music_style_are_saved_and_individual_edits_survive(monkeypatch, environment):
    image, _, _, paths = environment
    answers(monkeypatch, ['drift', '', '', '', '', '', '', 'ambient', 'pulse', '42', 'n', ''])
    _, _, cfg, _ = wizard.collect_render({'paths': paths}, image)
    assert cfg.profile == 'drift' and cfg.starfield.count == 3500
    assert cfg.audio.style == 'pulse' and cfg.audio.seed == 42
    assert cfg.duration == 30 and cfg.loop.enabled and cfg.profile_seed is None
    assert cfg.separation.executable == paths['starnet']
    cfg.starfield.count = 1234
    cfg.duration = 45
    defaults = wizard.remembered_defaults(cfg)
    answers(monkeypatch, ['', '', '', '', '', '', '', '', '', '', 'n', ''])
    _, _, reused, _ = wizard.collect_render({'paths': paths, 'defaults': defaults}, image)
    assert reused.profile == 'drift' and reused.starfield.count == 1234
    assert reused.duration == 45 and reused.audio.style == 'pulse'
    assert reused.audio.seed == 42 and reused.profile_seed is None


@pytest.mark.parametrize('language,yes,random_word,title_prompt', [
    ('en', 'y', 'random', 'Title (empty = no text)'),
    ('de', 'j', 'zufall', 'Titel (leer = ohne Text)'),
])
def test_complete_localized_session_keeps_render_settings_and_protects_existing_video(
        monkeypatch, environment, capsys, language, yes, random_word, title_prompt):
    image, output, settings_path, paths = environment
    output.mkdir()
    existing = output / 'existing.mp4'
    existing.write_bytes(b'original movie')
    wizard.save_settings(settings_path, {'version': 1, 'paths': paths, 'defaults': {}})
    prompts = answers(monkeypatch, [
        'drift', '', '', '', '', '', 'Pleiades', 'MESSIER 45',
        'ambient', 'pulse', '42', yes,
        yes, random_word,  # Profile variation and seed.
        '', '', '', '', '', '1234', '', '', '', '', '', '', '',
        'existing.mp4', 'n', 'new.mp4', yes,
    ])
    recorded = []

    def fake_render(command, **kwargs):
        cfg = load_config(Path(command[command.index('--config') + 1]))
        recorded.append(asdict(cfg))
        assert '--overwrite' not in command
        assert command[0] == sys.executable
        assert command[command.index('--output') + 1] == str(output / 'new.mp4')
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(wizard.subprocess, 'run', fake_render)
    assert wizard.main(['--language', language, '--settings', str(settings_path), '--input', image.name]) == 0
    assert all('Language / Sprache' not in prompt for prompt in prompts)
    assert any(title_prompt in prompt for prompt in prompts)
    assert any(f'({yes} / n)' in prompt for prompt in prompts)
    assert any(f'[{random_word}]' in prompt for prompt in prompts)
    cfg = recorded[0]
    assert cfg['duration'] == 30 and cfg['fps'] == 30 and cfg['resolution'] == '1080p'
    assert cfg['profile'] == 'drift' and cfg['profile_variation'] and cfg['profile_seed'] is None
    assert cfg['starfield']['count'] == 1234 and cfg['starfield']['photo_profiles']
    assert cfg['separation']['executable'] == paths['starnet'] and not cfg['separation']['foreground_cleanup']
    assert cfg['loop']['enabled'] and cfg['loop']['star_cycles'] == 1
    assert cfg['audio']['style'] == 'pulse' and cfg['audio']['seed'] == 42
    assert cfg['caption']['title'] == 'Pleiades' and cfg['caption']['subtitle'] == 'MESSIER 45'
    assert existing.read_bytes() == b'original movie'
    stored = wizard.load_settings(settings_path)
    assert stored['language'] == language and stored['paths'] == paths
    assert stored['defaults']['caption']['title'] == ''
    assert ('Music style: pulse' if language == 'en' else 'Musikstil: pulse') in capsys.readouterr().out


def test_saved_language_is_offered_and_can_be_changed_without_reconfiguring_paths(monkeypatch, environment):
    image, _, settings_path, paths = environment
    # Legacy settings contain no language field.
    wizard.save_settings(settings_path, {'version': 1, 'paths': paths, 'defaults': {'duration': 45}})
    monkeypatch.setattr(wizard.subprocess, 'run', lambda *a, **kw: pytest.fail('Dry run launched a process'))
    previous_defaults = None
    for choice, expected, previous in [('de', 'de', 'en'), ('', 'de', 'de'), ('en', 'en', 'de')]:
        prompts = answers(monkeypatch, [choice, '', '', '', '', '', '', '', 'none', 'n', ''])
        assert wizard.main(['--settings', str(settings_path), '--input', image.name, '--dry-run']) == 0
        assert f'[{previous}]' in prompts[0]
        assert any(('Sternflug-Profil' if expected == 'de' else 'Star-flight profile') in prompt for prompt in prompts)
        stored = wizard.load_settings(settings_path)
        assert stored['language'] == expected and stored['paths'] == paths
        assert stored['defaults']['duration'] == 45
        if previous_defaults is not None:
            assert stored['defaults'] == previous_defaults
        previous_defaults = stored['defaults']


@pytest.mark.parametrize('language,description,help_text', [
    ('en', 'guided video launcher', 'Reconfigure saved paths'),
    ('de', 'gefuehrter Video-Start', 'Gespeicherte Grundpfade neu einrichten'),
])
def test_localized_help_needs_no_input_or_render(monkeypatch, capsys, language, description, help_text):
    monkeypatch.setattr('builtins.input', lambda *a: pytest.fail('Help requested input'))
    with pytest.raises(SystemExit) as exc:
        wizard.main(['--language', language, '--help'])
    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert description in output and help_text in output and '--language' in output


@pytest.mark.parametrize('language,expected', [
    ('en', 'Saved StarNet2 executable is missing.'),
    ('de', 'Gespeicherte StarNet2-EXE fehlt.'),
])
def test_localized_path_errors_and_language_persistence_before_render(monkeypatch, environment, capsys, language, expected):
    _, _, settings_path, paths = environment
    paths['starnet'] = 'missing-starnet-file'
    wizard.save_settings(settings_path, {'version': 1, 'paths': paths, 'defaults': {}})
    monkeypatch.setattr('builtins.input', lambda *a: pytest.fail('CLI language requested input'))
    assert wizard.main(['--language', language, '--settings', str(settings_path)]) == 1
    assert expected in capsys.readouterr().err
    assert wizard.load_settings(settings_path)['language'] == language


@pytest.mark.parametrize('language,word', [('en', 'random'), ('en', 'zufall'), ('de', 'random'), ('de', 'zufall')])
def test_random_seed_words_work_in_either_language(monkeypatch, language, word):
    monkeypatch.setattr(wizard, 'LANGUAGE', language)
    answers(monkeypatch, [word])
    assert wizard.ask_seed('Seed', 123) is None
