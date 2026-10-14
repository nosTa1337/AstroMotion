from dataclasses import asdict, replace
import json
from pathlib import Path
import wave

import numpy as np
import pytest

from astromotion.animation import Animator
from astromotion.cli import main
from astromotion.config import Audio, Config, Loop, load_config
from astromotion.looping import prepare_audio_loop
from astromotion.music import main as music_preview, resolve_audio_seed, synthesize_ambient
from astromotion.profiles import resolve_profile_variation
from astromotion.separation import Layers
from astromotion.starfield import PerspectiveStars


@pytest.mark.parametrize('name,count', [('relax', 2200), ('drift', 3500), ('explore', 4500)])
def test_profiles_keep_clean_starnet_flight_and_perfect_loop(name, count):
    cfg = load_config(overrides={'profile': name, 'profile_seed': 7})
    assert cfg.duration == 30 and cfg.size == (1080, 1920) and cfg.fps == 30
    assert cfg.audio.mode == 'ambient' and cfg.audio.style == 'random' and cfg.audio.seed is None
    assert cfg.starfield.enabled and cfg.starfield.photo_profiles and cfg.starfield.count == count
    assert cfg.starfield.close_passes == 0 and not cfg.separation.foreground_cleanup
    assert cfg.loop.enabled and cfg.loop.star_cycles == 1
    assert cfg.effects.bloom == cfg.effects.glow == cfg.effects.twinkle == cfg.effects.grade == 0
    assert cfg.effects.contrast == cfg.effects.saturation == 1
    cfg = resolve_profile_variation(cfg)
    stars = np.zeros((120, 120, 3), np.float32)
    stars[20:101:20, 20:101:20] = [.9, .85, .8]
    layers = Layers(np.full_like(stars, .1), stars, 'screen', {})
    flight = PerspectiveStars(layers, Animator(layers, (120, 120), cfg.motion), cfg.starfield, 30, cfg.loop)
    np.testing.assert_allclose(flight.composite(layers.nebula, 0, 30),
                               flight.composite(layers.nebula, 1, 30), atol=1e-6)


def test_profile_cli_overrides_file_and_individual_flags_still_win(capsys):
    path = Path(__file__).parents[1] / 'configs' / 'immersive_loop.yaml'
    assert main(['--config', str(path), '--profile', 'drift', '--music-style', 'deep',
                 '--duration', '45', '--no-profile-variation', '--star-color-strength', '.4', '--print-config']) == 0
    data = json.loads(capsys.readouterr().out)
    assert data['profile'] == 'drift' and data['starfield']['count'] == 3500
    assert data['duration'] == 45 and data['audio']['style'] == 'deep'
    assert not data['profile_variation'] and data['starfield']['color_strength'] == .4
    assert main(['--profile', 'relax', '--music', 'none', '--no-loop', '--print-config']) == 0
    data = json.loads(capsys.readouterr().out)
    assert data['audio']['mode'] == 'none' and not data['loop']['enabled']


def test_file_profile_can_be_tuned_and_custom_preserves_existing_config(tmp_path):
    path = tmp_path / 'profile.yaml'
    path.write_text('profile: explore\nstarfield:\n  count: 1234\nmotion:\n  zoom: 0.09\n')
    cfg = load_config(path)
    assert cfg.profile == 'explore' and cfg.starfield.count == 1234 and cfg.motion.zoom == .09
    assert cfg.motion.overscan == 1.10 and cfg.starfield.enabled
    existing = load_config(Path(__file__).parents[1] / 'configs' / 'immersive_loop.yaml')
    assert existing.profile == 'custom' and resolve_profile_variation(existing) is existing
    assert existing.starfield.count == 4500 and existing.motion.zoom == .14


def test_profile_variation_is_bounded_reproducible_and_keeps_the_input(monkeypatch):
    cfg = load_config(overrides={'profile': 'drift', 'profile_seed': 123})
    unchanged = asdict(cfg)
    a, b = resolve_profile_variation(cfg), resolve_profile_variation(cfg)
    assert asdict(a) == asdict(b) and asdict(cfg) == unchanged
    assert resolve_profile_variation(a) is a
    replay = load_config(overrides=asdict(a))
    assert asdict(resolve_profile_variation(replay)) == asdict(a)
    outcomes = []
    for seed in range(16):
        varied = resolve_profile_variation(replace(cfg, profile_seed=seed))
        assert .9 * cfg.starfield.count <= varied.starfield.count <= 1.1 * cfg.starfield.count
        assert .94 * cfg.motion.zoom <= varied.motion.zoom <= 1.06 * cfg.motion.zoom
        assert .9 * abs(cfg.starfield.drift_x) <= abs(varied.starfield.drift_x) <= 1.1 * abs(cfg.starfield.drift_x)
        assert asdict(varied.effects) == asdict(cfg.effects)
        assert varied.starfield.color_strength == cfg.starfield.color_strength
        outcomes.append(varied.starfield.drift_x)
    assert min(outcomes) < 0 < max(outcomes)
    assert resolve_profile_variation(replace(cfg, profile_variation=False)).motion is cfg.motion
    monkeypatch.setattr('astromotion.profiles.secrets.randbits', lambda bits: 789)
    assert resolve_profile_variation(replace(cfg, profile_seed=None)).profile_seed == 789


@pytest.mark.parametrize('zoom,rotation', [(.75, 300), (1.0, 360)])
def test_profile_variation_retains_larger_rotation_and_steady_timing(zoom, rotation):
    cfg = load_config(overrides={'profile': 'explore', 'profile_seed': 123,
                                'motion': {'timing': 'steady', 'zoom': zoom, 'rotation_deg': rotation},
                                'starfield': {'rotation_deg': -rotation}})
    varied = resolve_profile_variation(cfg)
    assert varied.motion.timing == 'steady'
    assert .94 * zoom <= varied.motion.zoom <= min(1.0, 1.06 * zoom)
    assert .9 * rotation <= abs(varied.motion.rotation_deg) <= min(360, 1.1 * rotation)
    assert .9 * rotation <= abs(varied.starfield.rotation_deg) <= min(360, 1.1 * rotation)
    varied.validate()


def pcm(path):
    with wave.open(str(path)) as wav:
        assert wav.getnchannels() == 2 and wav.getsampwidth() == 2 and wav.getframerate() == 48000
        return np.frombuffer(wav.readframes(wav.getnframes()), '<i2').reshape(-1, 2).astype(float) / 32768


@pytest.mark.parametrize('style', ['warm', 'deep', 'shimmer', 'pulse', 'classic'])
def test_each_style_is_reproducible_complete_stereo_and_fades_cleanly(tmp_path, style):
    cfg = Audio(style=style, seed=77, fade_seconds=.2)
    a, b, c = [tmp_path / f'{name}.wav' for name in ('a', 'b', 'c')]
    synthesize_ambient(a, 2, cfg)
    synthesize_ambient(b, 2, cfg)
    synthesize_ambient(c, 2, replace(cfg, seed=78))
    assert a.read_bytes() == b.read_bytes() and a.read_bytes() != c.read_bytes()
    data = pcm(a)
    assert data.shape == (96000, 2) and 0 < abs(data).max() < 1
    assert not data[0].any() and not data[-1].any()
    assert not np.array_equal(data[:, 0], data[:, 1])


def test_style_variation_changes_register_and_rhythmic_arrangement(tmp_path):
    data = {}
    centroids = {}
    for style in ('warm', 'deep', 'shimmer', 'pulse'):
        path = tmp_path / f'{style}.wav'
        synthesize_ambient(path, 6, Audio(style=style, seed=77, fade_seconds=0))
        data[style] = pcm(path)[24000:264000].mean(axis=1)
        power = abs(np.fft.rfft(data[style])) ** 2
        frequencies = np.fft.rfftfreq(len(data[style]), 1 / 48000)
        centroids[style] = float((power * frequencies).sum() / power.sum())
    assert centroids['deep'] < .6 * centroids['warm']
    assert centroids['shimmer'] > 2 * centroids['warm']
    # Pulse adds deliberate note attacks; warm is a sustained pad arrangement.
    levels = {style: np.sqrt(np.mean(values.reshape(-1, 2400) ** 2, axis=1))
              for style, values in data.items()}
    changes = {style: np.mean(np.abs(np.diff(values))) / values.mean() for style, values in levels.items()}
    assert changes['pulse'] > 1.3 * changes['warm']


@pytest.mark.parametrize('style', ['warm', 'deep', 'shimmer', 'pulse'])
def test_new_styles_remain_complete_and_continuous_in_audio_loops(tmp_path, style):
    cfg = Config(duration=3, audio=Audio(mode='ambient', style=style, seed=77), loop=Loop(enabled=True))
    path = tmp_path / f'{style}.wav'
    prepare_audio_loop(path, cfg)
    data = pcm(path)
    assert data.shape == (144000, 2)
    assert np.sqrt(np.mean(data[:1000] ** 2)) > .001
    assert np.sqrt(np.mean(data[-1000:] ** 2)) > .001
    assert abs(data[0] - data[-1]).max() <= 1.1 * abs(np.diff(data, axis=0)).max()
    assert cfg.audio.seed == 77 and cfg.audio.style == style


def test_random_style_resolves_once_and_seed_replays_the_choice():
    cfg = Audio(seed=42)
    resolved = resolve_audio_seed(cfg)
    assert cfg.style == 'random' and resolved.style != 'random'
    assert resolve_audio_seed(resolved) == resolved
    assert resolved == resolve_audio_seed(cfg)
    styles = {resolve_audio_seed(Audio(seed=seed)).style for seed in range(32)}
    assert styles == {'warm', 'deep', 'shimmer', 'pulse'}


def test_invalid_profile_and_music_settings_fail_before_rendering():
    for override in ({'profile': 'invalid'}, {'profile_seed': -1}, {'profile_seed': True},
                     {'profile_variation': 1}, {'audio': {'style': 'invalid'}}):
        with pytest.raises(ValueError):
            load_config(overrides=override)


@pytest.mark.parametrize('development', [-.1, 1.1, float('nan')])
def test_invalid_music_development_preserves_existing_audio(tmp_path, development):
    path = tmp_path / 'original.wav'
    path.write_bytes(b'existing audio')
    with pytest.raises(ValueError):
        load_config(overrides={'audio': {'development': development}})
    with pytest.raises(ValueError):
        synthesize_ambient(path, 2, Audio(style='warm', seed=77, development=development))
    assert path.read_bytes() == b'existing audio'
    assert not list(tmp_path.glob('.*.wav'))


def test_music_development_cli_and_preview_controls(tmp_path, capsys):
    assert main(['--music-style', 'deep', '--music-development', '.8', '--print-config']) == 0
    assert json.loads(capsys.readouterr().out)['audio']['development'] == .8
    path = tmp_path / 'preview.wav'
    assert music_preview(['--style', 'warm', '--seed', '77', '--development', '0', '--duration', '2', '--output', str(path)]) == 0
    steady = path.read_bytes()
    assert music_preview(['--style', 'warm', '--seed', '77', '--development', '1', '--duration', '2', '--output', str(path), '--overwrite']) == 0
    assert path.read_bytes() != steady and pcm(path).shape == (96000, 2)


@pytest.mark.parametrize('style', ['warm', 'deep'])
def test_development_increases_musical_change_throughout_thirty_second_loop(tmp_path, style):
    def movement(data):
        mono = data.mean(axis=1).reshape(-1, 24000)
        power = abs(np.fft.rfft(mono * np.hanning(24000), axis=1)) ** 2
        frequencies = np.fft.rfftfreq(24000, 1 / 48000)
        edges = [20, 63, 125, 250, 500, 1000, 2000, 4000, 10000]
        bands = np.array([power[:, (frequencies >= low) & (frequencies < high)].sum(axis=1)
                          for low, high in zip(edges, edges[1:])]).T
        bands /= bands.sum(axis=1, keepdims=True)
        return float(abs(np.diff(bands, axis=0)).sum(axis=1).mean())

    scores = []
    for development in (0, .65):
        cfg = Config(duration=30, audio=Audio(mode='ambient', style=style, seed=77, development=development),
                     loop=Loop(enabled=True))
        path = tmp_path / f'{development}.wav'
        prepare_audio_loop(path, cfg)
        data = pcm(path)
        assert data.shape == (1440000, 2) and 0 < abs(data).max() < .65
        assert abs(data[0] - data[-1]).max() <= 1.1 * abs(np.diff(data, axis=0)).max()
        scores.append(movement(data))
    assert scores[1] > scores[0] * 1.05


def test_music_preview_needs_no_video_and_protects_existing_files(tmp_path, capsys):
    path = tmp_path / 'preview.wav'
    args = ['--style', 'pulse', '--seed', '77', '--duration', '.2', '--output', str(path)]
    assert music_preview(args) == 0
    assert pcm(path).shape == (9600, 2)
    assert 'pulse' in capsys.readouterr().out
    original = path.read_bytes()
    assert music_preview(args) == 1
    assert '--overwrite' in capsys.readouterr().err
    assert path.read_bytes() == original
    assert music_preview(args + ['--overwrite']) == 0
