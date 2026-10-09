from dataclasses import replace
import json
import shutil
import subprocess
import wave

import numpy as np
import pytest

from astromotion.animation import Animator
from astromotion.captions import CaptionOverlay
from astromotion.cli import main
from astromotion.config import Audio, Caption, Config, Loop, Motion, Starfield, load_config
from astromotion.imaging import save_png, to_srgb
from astromotion.looping import camera_phase, prepare_audio_loop, splice_audio_loop
from astromotion.music import synthesize_ambient
from astromotion.pipeline import render
from astromotion.separation import Layers, composite


def scene():
    background = np.full((120, 160, 3), [.25, .1, .08], np.float32)
    stars = np.zeros_like(background)
    for y in range(10, 112, 12):
        for x in range(10, 152, 12):
            stars[y, x] = [.9, .85, .8]
    return Layers(background, stars, "screen", {})


def test_periodic_camera_and_twinkle_cover_source_without_borders():
    white = np.ones((331, 477, 3), np.float32)
    animator = Animator(Layers(white, white, "screen", {}), (320, 180),
        Motion(zoom=.5, rotation_deg=10, pan_x=.15, pan_y=-.15, parallax=3, speed=3))
    assert camera_phase(0) == camera_phase(1) == 0
    assert camera_phase(.5) == 1
    for phase in np.linspace(0, 1, 41):
        assert animator.warp(white, animator.matrix(camera_phase(float(phase)))).min() > .9999
    for endpoint in [0., 1.]:
        bg, st = animator.frame_layers(camera_phase(endpoint), 2 * np.pi * endpoint / 1.4, .5)
        if endpoint == 0:
            first = bg, st
        else:
            np.testing.assert_allclose(first[0], bg, atol=1e-6)
            np.testing.assert_allclose(first[1], st, atol=1e-6)


def test_short_loop_caption_is_closed_at_both_ends():
    overlay = CaptionOverlay(Caption(title="Nebel", start_seconds=0, hold_seconds=30), (160, 160))
    background = np.zeros((160, 160, 3), np.float32)
    assert overlay.apply(background, 0, 3) is background
    assert overlay.apply(background, 3, 3) is background
    assert np.max(overlay.apply(background, 3 - .00001, 3)) < 1e-8


def test_splice_seam_is_regular_next_source_sample_and_atomic(tmp_path):
    sr, count, overlap = 48000, 48000, 8000
    t = np.arange(count + overlap) / sr
    pcm = np.column_stack([np.sin(t * 2 * np.pi * 113.7), np.sin(t * 2 * np.pi * 147.1)]) * 9000
    pcm = np.rint(pcm).astype("<i2")
    source, output = tmp_path / "source.wav", tmp_path / "loop.wav"
    with wave.open(str(source), "wb") as wav:
        wav.setparams((2, 2, sr, 0, "NONE", "not compressed"))
        wav.writeframes(pcm.tobytes())
    splice_audio_loop(source, output, count, overlap)
    with wave.open(str(output), "rb") as wav:
        assert wav.getnframes() == count
        result = np.frombuffer(wav.readframes(count), "<i2").reshape(-1, 2)
    np.testing.assert_array_equal(result[0], pcm[count])
    np.testing.assert_array_equal(result[-1], pcm[count - 1])
    np.testing.assert_array_equal(result[overlap:], pcm[overlap:count])
    assert np.max(np.abs(result[0].astype(int) - result[-1])) < 200
    previous = output.read_bytes()
    with pytest.raises(ValueError):
        splice_audio_loop(source, output, count * 2, overlap)
    assert output.read_bytes() == previous
    assert not list(tmp_path.glob(".*.wav"))


@pytest.mark.parametrize("mode", ["ambient", "file"])
def test_audio_loop_reproducible_complete_and_no_silence_at_seam(tmp_path, mode):
    if mode == "file" and not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg fehlt")
    cfg = Config(duration=2, audio=Audio(mode=mode, seed=42, fade_seconds=2, accents=.45), loop=Loop(enabled=True))
    source = None
    if mode == "file":
        source = tmp_path / "source.wav"
        synthesize_ambient(source, 3, replace(cfg.audio, fade_seconds=0))
    a, b = tmp_path / "a.wav", tmp_path / "b.wav"
    prepare_audio_loop(a, cfg, source)
    prepare_audio_loop(b, cfg, source)
    assert a.read_bytes() == b.read_bytes()
    with wave.open(str(a), "rb") as wav:
        assert wav.getnframes() == 96000
        pcm = np.frombuffer(wav.readframes(wav.getnframes()), "<i2").reshape(-1, 2).astype(float) / 32768
    assert np.sqrt(np.mean(pcm[:1000] ** 2)) > .001
    assert np.sqrt(np.mean(pcm[-1000:] ** 2)) > .001
    assert np.max(np.abs(pcm[0] - pcm[-1])) < .02
    assert not list(tmp_path.glob(".*.wav"))


def test_loop_cli_defaults_and_validation(capsys):
    assert main(["--print-config", "--duration", "45", "--loop"]) == 0
    cfg = json.loads(capsys.readouterr().out)
    assert cfg["duration"] == 45 and cfg["loop"]["enabled"]
    assert main(["--print-config", "--no-loop"]) == 0
    assert not json.loads(capsys.readouterr().out)["loop"]["enabled"]
    assert Config().duration == 30
    for value in [0, 1.5, True, 6]:
        with pytest.raises(ValueError):
            load_config(overrides={"loop": {"star_cycles": value}})
        with pytest.raises(ValueError):
            Config(loop=Loop(star_cycles=value)).validate()


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg fehlt")
@pytest.mark.video_render
def test_complete_loop_render_with_caption_twinkle_music(tmp_path):
    layers = scene()
    original, starless = tmp_path / "input.png", tmp_path / "starless.png"
    save_png(original, to_srgb(composite(layers.nebula, layers.stars)))
    save_png(starless, to_srgb(layers.nebula))
    cfg = Config(duration=.5, fps=24, format="square", resolution="720p",
                 audio=Audio(mode="ambient"), loop=Loop(enabled=True),
                 starfield=Starfield(enabled=True, photo_profiles=True, count=30),
                 caption=Caption(enabled=True, title="Nebel", start_seconds=0))
    cfg.encoding.preset = "ultrafast"
    cfg.effects.twinkle = .2
    report = render(original, tmp_path / "loop.mp4", cfg, starless)
    assert int(report["probe"]["streams"][0]["nb_frames"]) == 12
    assert report["actual_duration"] == .5
    result = subprocess.run(["ffmpeg", "-v", "error", "-i", str(tmp_path / "loop.mp4"), "-f", "null", "-"], capture_output=True)
    assert result.returncode == 0 and not result.stderr
