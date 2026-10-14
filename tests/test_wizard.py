"""Exercise complete interactive sessions without invoking StarNet or FFmpeg."""
from dataclasses import asdict
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

import wizard
from astromotion.config import apply_profile, load_config


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
                          paths['ffmpeg'], paths['ffprobe'], 'final', image.name, 'custom',
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
    answers(monkeypatch, ['', 'final', image.name, '0', 'custom', '', '', '', '', '', '', 'ambient', 'random', 'zufall', 'n', '', 'j'])
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
    assert wizard.main(['--language', 'en', '--no-preview', '--settings', str(settings_path), '--input', image.name, '--dry-run']) == 0
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
    monkeypatch.setattr(wizard, 'collect_render', lambda *a, **kw: (_ for _ in ()).throw(EOFError()))
    assert wizard.main(['--language', 'en', '--no-preview', '--settings', str(settings_path), '--setup']) == 130
    assert wizard.load_settings(settings_path)['paths'] == paths


def test_cancelled_render_is_not_started(monkeypatch, environment):
    image, _, settings_path, paths = environment
    wizard.save_settings(settings_path, {'version': 1, 'paths': paths, 'defaults': {}})
    answers(monkeypatch, [image.name, 'custom', '', '', '', '', '', '', 'none', 'n', '', 'n'])
    monkeypatch.setattr(wizard.subprocess, 'run', lambda *a, **kw: pytest.fail('Cancelled render launched a process'))
    assert wizard.main(['--language', 'en', '--no-preview', '--settings', str(settings_path)]) == 0
    assert not wizard.load_settings(settings_path).get('history')


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
    assert wizard.main(['--language', language, '--no-preview', '--settings', str(settings_path), '--input', image.name]) == 0
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
        assert wizard.main(['--no-preview', '--settings', str(settings_path), '--input', image.name, '--dry-run']) == 0
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


@pytest.mark.parametrize('language,yes,random_word', [('en', 'y', 'random'), ('de', 'j', 'zufall')])
def test_preview_then_full_video_share_timing_random_choices_and_explicit_overwrite(
        monkeypatch, environment, capsys, language, yes, random_word):
    image, output, settings_path, paths = environment
    output.mkdir()
    target = output / 'Pleiades M45_astromotion.mp4'
    target.write_bytes(b'original movie')
    original = apply_profile(load_config(wizard.PRESET), 'explore')
    original.loop.star_cycles = 2
    wizard.save_settings(settings_path, {'version': 1, 'paths': paths,
                                        'defaults': wizard.remembered_defaults(original)})
    prompts = answers(monkeypatch, [
        '', '', '', '', '', '', 'Pleiades', 'MESSIER 45',
        '', '', random_word, 'n', '', yes, yes, yes,
    ])
    calls = []

    def fake_render(command, **kwargs):
        cfg = load_config(Path(command[command.index('--config') + 1]))
        destination = Path(command[command.index('--output') + 1])
        if not calls:
            assert target.read_bytes() == b'original movie'
            assert destination == wizard.preview_output_path(target)
            assert '--overwrite' not in command
        else:
            assert target.read_bytes() == b'original movie'
            assert destination == target and '--overwrite' in command
        calls.append((destination, cfg))
        destination.write_bytes(b'preview' if len(calls) == 1 else b'full movie')
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(wizard.subprocess, 'run', fake_render)
    assert wizard.main(['--language', language, '--preview', '--settings', str(settings_path), '--input', image.name]) == 0
    assert len(calls) == 2
    preview, full = calls[0][1], calls[1][1]
    assert preview.size == (360, 640) and full.size == (1080, 1920)
    assert preview.frame_count == full.frame_count == 900
    assert preview.actual_duration == full.actual_duration == 30
    assert preview.loop.star_cycles == full.loop.star_cycles == 2
    assert asdict(preview) == {**asdict(full), 'resolution': '360p'}
    assert isinstance(full.profile_seed, int) and isinstance(full.audio.seed, int)
    assert full.audio.style in ('warm', 'deep', 'shimmer', 'pulse')
    assert full.work_long_edge == original.work_long_edge
    assert full.separation.executable == paths['starnet']
    stored = wizard.load_settings(settings_path)
    assert stored['defaults']['resolution'] == stored['history'][0]['defaults']['resolution'] == '1080p'
    assert stored['defaults']['profile_seed'] is None and stored['defaults']['audio']['seed'] is None
    assert stored['defaults']['audio']['style'] == 'random'
    assert len(stored['history']) == 1 and stored['history'][0]['defaults']['caption']['title'] == ''
    assert sum('Replace it' in prompt or 'Ersetzen' in prompt for prompt in prompts) == 1
    assert ('Preview ready:' if language == 'en' else 'Vorschau fertig:') in capsys.readouterr().out


def test_interactive_preview_can_stop_without_touching_full_video(monkeypatch, environment):
    image, output, settings_path, paths = environment
    output.mkdir()
    target = output / 'Pleiades M45_astromotion.mp4'
    target.write_bytes(b'original movie')
    wizard.save_settings(settings_path, {'version': 1, 'paths': paths, 'defaults': {}})
    answers(monkeypatch, ['preview', 'custom', '', '', '', '', '', '', 'none', 'n', '', 'y', 'n'])
    calls = []

    def fake_render(command, **kwargs):
        calls.append(command)
        Path(command[command.index('--output') + 1]).write_bytes(b'preview')
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(wizard.subprocess, 'run', fake_render)
    assert wizard.main(['--language', 'en', '--settings', str(settings_path), '--input', image.name]) == 0
    assert len(calls) == 1
    assert Path(calls[0][calls[0].index('--output') + 1]) == wizard.preview_output_path(target)
    assert target.read_bytes() == b'original movie'
    assert len(wizard.load_settings(settings_path)['history']) == 1


def test_existing_preview_requires_confirmation_independently_of_full_video(monkeypatch, environment):
    image, output, _, paths = environment
    output.mkdir()
    target = output / 'Pleiades M45_astromotion.mp4'
    target.write_bytes(b'original full movie')
    preview = wizard.preview_output_path(target)
    preview.write_bytes(b'original preview')
    prompts = answers(monkeypatch, ['custom', '', '', '', '', '', '', 'none', 'n', '', 'n', 'different.mp4'])
    _, chosen, cfg, overwrite = wizard.collect_render({'paths': paths}, image, preview=True)
    assert chosen == output / 'different.mp4' and not overwrite
    assert cfg.resolution == '1080p'
    assert sum('Replace it' in prompt for prompt in prompts) == 1
    assert target.read_bytes() == b'original full movie' and preview.read_bytes() == b'original preview'


@pytest.mark.parametrize('dry_run', [False, True])
def test_failed_preview_and_dry_run_do_not_add_history(monkeypatch, environment, dry_run):
    image, _, settings_path, paths = environment
    wizard.save_settings(settings_path, {'version': 1, 'paths': paths, 'defaults': {}})
    values = ['custom', '', '', '', '', '', '', 'none', 'n', '']
    if not dry_run:
        values.append('y')
    prompts = answers(monkeypatch, values)
    calls = []
    monkeypatch.setattr(wizard.subprocess, 'run', lambda *a, **kw: calls.append(a) or SimpleNamespace(returncode=7))
    args = ['--language', 'en', '--preview', '--settings', str(settings_path), '--input', image.name]
    assert wizard.main(args + (['--dry-run'] if dry_run else [])) == (0 if dry_run else 7)
    stored = wizard.load_settings(settings_path)
    assert not stored.get('history') and stored['defaults']['resolution'] == '1080p'
    assert len(calls) == (0 if dry_run else 1)
    assert not any('full-resolution video now' in prompt for prompt in prompts)


def test_history_keeps_five_distinct_setups_and_moves_reused_one_to_top(environment):
    image, _, settings_path, paths = environment
    settings = {'version': 1, 'paths': paths, 'defaults': {}}
    cfg = load_config(wizard.PRESET)
    for duration in range(30, 37):
        cfg.duration = float(duration)
        wizard.remember_recent_settings(settings, image, cfg)
    assert [entry['defaults']['duration'] for entry in settings['history']] == [36, 35, 34, 33, 32]
    cfg.motion.zoom = .4
    assert settings['history'][0]['defaults']['motion']['zoom'] != .4
    reused = load_config(wizard.PRESET, settings['history'][3]['defaults'])
    wizard.remember_recent_settings(settings, image.with_name('new photo.jpg'), reused)
    assert [entry['defaults']['duration'] for entry in settings['history']] == [33, 36, 35, 34, 32]
    assert settings['history'][0]['image'] == 'new photo.jpg'
    wizard.save_settings(settings_path, settings)
    assert wizard.load_settings(settings_path) == settings


@pytest.mark.parametrize('language', ['en', 'de'])
def test_recent_template_can_be_edited_without_changing_snapshot_or_current_paths(monkeypatch, environment, language):
    image, _, _, paths = environment
    monkeypatch.setattr(wizard, 'LANGUAGE', language)
    cfg = apply_profile(load_config(wizard.PRESET), 'explore')
    cfg.duration, cfg.fps, cfg.resolution, cfg.format = 45.0, 60, '4k', 'landscape'
    cfg.starfield.count, cfg.starfield.color_strength = 1234, .4
    cfg.loop.star_cycles = 3
    cfg.audio.style, cfg.audio.seed = 'pulse', 44
    cfg.separation.executable = '/old/computer/starnet2'
    cfg.encoding.ffmpeg = '/old/computer/ffmpeg'
    settings = {'paths': paths, 'defaults': {}}
    wizard.remember_recent_settings(settings, image, cfg)
    before = json.dumps(settings['history'])
    answers(monkeypatch, ['1', '', '40', '', '', '', '', 'New object', '', '', '', '', 'n', ''])
    _, _, selected, _ = wizard.collect_render(settings, image)
    assert selected.profile == 'explore' and selected.duration == 40 and selected.fps == 60
    assert selected.resolution == '4k' and selected.format == 'landscape'
    assert selected.starfield.count == 1234 and selected.starfield.color_strength == .4
    assert selected.loop.star_cycles == 3
    assert selected.audio.style == 'pulse' and selected.audio.seed == 44
    assert selected.separation.executable == paths['starnet'] and selected.encoding.ffmpeg == paths['ffmpeg']
    assert selected.caption.title == 'New object'
    assert json.dumps(settings['history']) == before and settings['defaults'] == {}


def test_reconfiguring_paths_preserves_recent_templates(monkeypatch, environment):
    image, _, _, paths = environment
    settings = {'paths': paths, 'defaults': {}}
    wizard.remember_recent_settings(settings, image, load_config(wizard.PRESET))
    answers(monkeypatch, ['', '', '', '', ''])
    configured = wizard.configure_paths(settings)
    assert configured['history'] == settings['history'] and configured['paths'] == paths
