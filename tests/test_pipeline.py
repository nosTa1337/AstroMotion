from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess
import sys
import wave

import cv2
import numpy as np
import pytest
from PIL import Image

from astromotion.animation import Animator, smootherstep
from astromotion.cli import main
from astromotion.config import Audio, Config, Effects, Motion, Separation, load_config
from astromotion.effects import EffectProcessor
from astromotion.encoding import probe
from astromotion.imaging import load_image, save_png, save_tiff, to_linear, to_srgb
from astromotion.music import synthesize_ambient
from astromotion.pipeline import render
from astromotion.separation import Layers, composite, extract_layers, run_starnet, starnet_command


@pytest.fixture
def pair():
    rng = np.random.default_rng(123)
    base = rng.uniform(.002, .3, (64, 96, 3)).astype(np.float32)
    stars = np.zeros_like(base)
    stars[20:23, 40:43] = [.8, .65, .5]
    return to_srgb(composite(base, stars)), to_srgb(base)


@pytest.mark.parametrize("blend", ["screen", "additive"])
def test_reconstruction(pair, blend):
    original, starless = pair
    layers = extract_layers(original, starless, Separation(blend=blend))
    np.testing.assert_allclose(layers.composite(), to_linear(original), atol=2e-7)
    assert np.max(layers.stars[:10]) < 1e-6


@pytest.mark.parametrize("blend", ["screen", "additive"])
def test_foreground_cleanup_keeps_colorful_remnants_in_background(blend):
    base = np.full((64, 96, 3), .02, np.float32)
    stars = np.zeros_like(base)
    stars[20:22, 20:22] = [.6, .55, .5]  # compact, nearly neutral star
    stars[40:42, 50:75] = [.12, .005, .001]  # highly chromatic elongated remnant
    original = to_srgb(composite(base, stars, blend))
    cleaned = extract_layers(original, to_srgb(base), Separation(blend=blend, foreground_cleanup=True))
    np.testing.assert_allclose(cleaned.composite(), to_linear(original), atol=3e-7)
    assert cleaned.stars[20:22, 20:22].max() > .45
    assert cleaned.stars[40:42, 50:75].max() < .002
    assert cleaned.nebula[40:42, 50:75, 0].mean() > .1


def test_mismatched_and_missing_stars_fail(pair):
    original, starless = pair
    with pytest.raises(ValueError, match="gleich"):
        extract_layers(original, starless[:, :-1], Separation())
    with pytest.raises(ValueError, match="passt nicht"):
        extract_layers(original, np.ones_like(starless), Separation())
    with pytest.raises(ValueError, match="Keine separate"):
        extract_layers(original, original, Separation())
    with pytest.raises(ValueError, match="schwarz"):
        extract_layers(original, np.zeros_like(starless), Separation())


@pytest.mark.parametrize("format", ["vertical", "square", "landscape"])
@pytest.mark.parametrize("center", [(.5, .5), (.1, .9)])
def test_no_black_corners_under_extreme_motion(format, center):
    cfg = Config(format=format, resolution="720p")
    m = Motion(zoom=.5, star_zoom_extra=.5, rotation_deg=-10, star_rotation_deg=-5,
               pan_x=.15, pan_y=-.15, parallax=3, speed=3, overscan=1,
               center_x=center[0], center_y=center[1])
    # A white source makes any out-of-source sampling immediately detectable.
    source = np.ones((331, 477, 3), np.float32)
    animator = Animator(Layers(source, source, "screen", {}), cfg.size, m)
    for t in np.linspace(0, 1, 11):
        for stars in (False, True):
            warped = animator.warp(source, animator.matrix(float(t), stars))
            assert float(warped.min()) >= .9999


def test_real_parallax_and_speed_zero(pair):
    layers = extract_layers(*pair, Separation())
    animator = Animator(layers, (160, 120), Motion())
    assert not np.allclose(animator.matrix(1), animator.matrix(1, True))
    disabled = Animator(layers, (160, 120), Motion(parallax=0))
    np.testing.assert_allclose(disabled.matrix(.73), disabled.matrix(.73, True))
    frozen = Animator(layers, (160, 120), Motion(speed=0))
    np.testing.assert_allclose(frozen.matrix(0), frozen.matrix(1, True))
    assert smootherstep(0) == 0 and smootherstep(1) == 1
    assert smootherstep(.5) == .5


@pytest.mark.parametrize("suffix", [".tif", ".png", ".jpg"])
def test_image_formats_preserve_precision(pair, suffix, tmp_path):
    original, _ = pair
    path = tmp_path / ("Sterne Ü" + suffix)
    if suffix == ".tif":
        save_tiff(path, original)
    elif suffix == ".png":
        save_png(path, original)
    else:
        Image.fromarray(np.round(original * 255).astype(np.uint8)).save(path, quality=100, subsampling=0)
    loaded = load_image(path)
    assert loaded.shape == original.shape and loaded.dtype == np.float32
    if suffix == ".jpg":
        # JPEG is lossy even at quality=100: verify the decoder against the
        # stored JPEG pixels, then check that overall color/error stays small.
        reference = np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255
        np.testing.assert_allclose(loaded, reference, atol=1 / 255)
        assert float(np.abs(loaded - original).mean()) < .004
    else:
        np.testing.assert_allclose(loaded, original, atol=1 / 65535)


def test_icc_and_exif_orientation(tmp_path):
    from PIL import ImageCms
    im = Image.new("RGB", (70, 40), (100, 50, 20))
    exif = Image.Exif()
    exif[274] = 6
    path = tmp_path / "oriented.jpg"
    im.save(path, exif=exif, icc_profile=ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes())
    assert load_image(path).shape == (70, 40, 3)


def test_config_precedence_and_validation(tmp_path):
    path = tmp_path / "custom.yaml"
    path.write_text("preset: calm\nmotion:\n  zoom: 0.07\naudio:\n  file: 'music/track.wav'\n", encoding="utf-8")
    cfg = load_config(path, {"fps": 60, "motion": {"speed": 1.4}})
    assert cfg.motion.zoom == .07 and cfg.motion.rotation_deg == .65 and cfg.motion.speed == 1.4
    assert cfg.fps == 60 and Path(cfg.audio.file).is_absolute()
    path.write_text("motion:\n  zomm: 0.1", encoding="utf-8")
    with pytest.raises(ValueError, match="Unbekannter"):
        load_config(path)
    for override in ({"duration": float("nan")}, {"fps": True}, {"audio": {"mode": "file"}},
                     {"separation": {"stride": 255}}, {"effects": {"bloom": 2.0}}):
        with pytest.raises(ValueError):
            load_config(overrides=override)


def test_effects_are_finite_bounded_and_disableable(pair):
    layers = extract_layers(*pair, Separation())
    none = Effects(bloom=0, glow=0, vignette=0, contrast=1, saturation=1, grade=0)
    result = EffectProcessor(none, (96, 64), "screen").apply(layers.nebula, layers.stars)
    np.testing.assert_allclose(result, pair[0], atol=2e-7)
    bright = np.ones_like(layers.nebula)
    result = EffectProcessor(Effects(bloom=1, glow=1), (96, 64), "screen").apply(bright, bright)
    assert np.isfinite(result).all() and result.min() >= 0 and result.max() <= 1


def test_ambient_is_reproducible_with_correct_duration_and_fades(tmp_path):
    a, b, c = (tmp_path / name for name in ("a.wav", "b.wav", "c.wav"))
    cfg = Audio(mode="ambient", fade_seconds=.4)
    synthesize_ambient(a, 1.25, cfg)
    synthesize_ambient(b, 1.25, cfg)
    synthesize_ambient(c, 1.25, replace(cfg, seed=999))
    assert a.read_bytes() == b.read_bytes() and a.read_bytes() != c.read_bytes()
    with wave.open(str(a)) as w:
        assert w.getnchannels() == 2 and w.getnframes() == 60000
        data = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, 2)
    assert abs(data).max() < 32767 and abs(data[0]).max() == 0 and abs(data[-1]).max() == 0
    assert np.sqrt(np.mean(data[500:2500].astype(float)**2)) < np.sqrt(np.mean(data[24000:26000].astype(float)**2))


def test_ambient_harmony_variants_change_pitch_material_without_clipping(tmp_path):
    results = []
    for harmony in ("original", "floating", "dusk"):
        path = tmp_path / (harmony + ".wav")
        synthesize_ambient(path, 1.25, Audio(seed=73, harmony=harmony, transpose=2))
        with wave.open(str(path)) as wav:
            pcm = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
            assert wav.getnchannels() == 2 and wav.getnframes() == 60000
        assert 0 < np.abs(pcm).max() < 32767
        assert not pcm[:2].any() and not pcm[-2:].any()
        results.append(pcm)
    # Same seed/instrument/duration, distinct harmonies: compare the sustained
    # middle, rather than only fade or phase offsets.
    for first, second in zip(results, results[1:]):
        assert np.sqrt(np.mean((first[30000:70000].astype(float) - second[30000:70000])**2)) > 100
    with pytest.raises(ValueError):
        load_config(overrides={"audio": {"harmony": "unknown"}})
    with pytest.raises(ValueError):
        load_config(overrides={"audio": {"transpose": 13}})


def test_full_15_second_ambient_is_complete_and_failure_preserves_existing(tmp_path):
    path = tmp_path / "ambient.wav"
    synthesize_ambient(path, 15, Audio(seed=73, harmony="floating"))
    original_bytes = path.read_bytes()
    with wave.open(str(path)) as wav:
        assert wav.getnframes() == 720000 and wav.getframerate() == 48000
        data = np.frombuffer(wav.readframes(wav.getnframes()), "<i2")
        assert data.size == 1440000
        assert not data[:2].any() and not data[-2:].any()
    with pytest.raises(ValueError):
        synthesize_ambient(path, 15, Audio(harmony="invalid"))
    assert path.read_bytes() == original_bytes
    assert not list(tmp_path.glob(".*.wav"))


@pytest.mark.parametrize("mode,exe", [("modern", "starnet2.exe"), ("legacy", "starnet++.exe")])
def test_starnet_arguments_not_shell_strings(tmp_path, mode, exe):
    program = tmp_path / exe
    program.touch()
    cfg = Separation(executable=str(program))
    cmd = starnet_command(cfg, tmp_path / "input with spaces.tif", tmp_path / "out.tif")
    assert ("--input" in cmd) == (mode == "modern")
    assert str(tmp_path / "input with spaces.tif") in cmd


def test_starnet_adapter_io_contract_without_real_model(tmp_path, monkeypatch):
    # This test verifies the adapter contract only. It is NOT StarNet/model QA.
    program = tmp_path / "starnet2.exe"
    program.touch()
    work = tmp_path / "job with spaces"
    work.mkdir()
    original = np.full((512, 512, 3), .15, np.float32)
    def external(command, **kwargs):
        assert kwargs["cwd"] == tmp_path
        assert kwargs["check"] is False
        data = load_image(Path(command[command.index("--input") + 1]))
        save_tiff(Path(command[command.index("--output") + 1]), data * .9)
        return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(subprocess, "run", external)
    result = run_starnet(original, Separation(executable=str(program)), work)
    np.testing.assert_allclose(result, original * .9, atol=2 / 65535)


def test_starnet_does_not_accept_stale_output(tmp_path, monkeypatch):
    program = tmp_path / "starnet2.exe"
    program.touch()
    work = tmp_path / "job"
    work.mkdir()
    original = np.full((512, 512, 3), .2, np.float32)
    save_tiff(work / "starnet_starless.tif", original * .8)
    monkeypatch.setattr(subprocess, "run", lambda command, **kw: subprocess.CompletedProcess(command, 0))
    with pytest.raises(RuntimeError, match="keine Ersatz"):
        run_starnet(original, Separation(executable=str(program)), work)


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg/FFprobe fehlen")
def test_interrupted_render_preserves_existing_output(pair, tmp_path):
    original, starless = pair
    input_path, starless_path = tmp_path / "input.png", tmp_path / "starless.png"
    save_png(input_path, original)
    save_png(starless_path, starless)
    output = tmp_path / "keep.mp4"
    output.write_bytes(b"previous output")
    cfg = Config(format="square", resolution="720p", duration=.25, fps=24)
    def cancelled(done, total, elapsed):
        raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        render(input_path, output, cfg, starless_path, cancelled, overwrite=True)
    assert output.read_bytes() == b"previous output"
    assert not list(tmp_path.glob(".*.partial.mp4"))


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg/FFprobe fehlen")
@pytest.mark.parametrize("audio", ["none", "ambient", "file"])
def test_complete_streamed_render(pair, tmp_path, audio):
    original, starless = pair
    input_path, starless_path = tmp_path / "input.png", tmp_path / "starless.png"
    save_png(input_path, original)
    save_png(starless_path, starless)
    output = tmp_path / f"{audio}.mp4"
    cfg = Config(format="square", resolution="720p", duration=.25, fps=24)
    cfg.encoding.preset = "ultrafast"
    cfg.effects.bloom = cfg.effects.glow = 0
    cfg.audio.mode = audio
    # Exercise the perspective path with generated synthetic stars, not model
    # output. Other audio cases continue to cover the original layer camera.
    cfg.starfield.enabled = audio == "ambient"
    cfg.starfield.photo_profiles = audio == "ambient"
    cfg.starfield.close_passes = 2 if audio == "ambient" else 0
    cfg.audio.accents = .45 if audio == "ambient" else 0
    cfg.caption.enabled = audio == "ambient"
    cfg.caption.title = "Nebel"
    cfg.caption.subtitle = "Synthetischer Test"
    cfg.caption.start_seconds = .01
    cfg.caption.fade_seconds = .03
    cfg.caption.hold_seconds = .1
    if audio == "file":
        wav = tmp_path / "short.wav"
        synthesize_ambient(wav, .10, Audio(fade_seconds=0))  # shorter than video; loop
        cfg.audio.file = str(wav)
    progress = []
    report = render(input_path, output, cfg, starless_path, lambda done, total, elapsed: progress.append(done))
    assert progress == list(range(1, 7))
    streams = report["probe"]["streams"]
    if cfg.starfield.enabled:
        assert report["starfield"]["detected_star_particles"] > 0
    assert len(streams) == (1 if audio == "none" else 2)
    assert float(streams[0]["duration"]) == pytest.approx(.25)
    # Decode every video frame, not just the container metadata.
    result = subprocess.run(["ffmpeg", "-v", "error", "-i", str(output), "-f", "null", "-"], capture_output=True)
    assert result.returncode == 0 and not result.stderr
    with pytest.raises(FileExistsError):
        render(input_path, output, cfg, starless_path)
    assert not list(tmp_path.glob("*.partial.mp4"))


def test_no_silent_fallback_or_partial_output(tmp_path):
    with pytest.raises(ValueError, match="zuverlässige"):
        render(tmp_path / "input.png", tmp_path / "out.mp4", Config())
    assert not (tmp_path / "out.mp4").exists()


def test_cli_config_and_bad_options(capsys):
    assert main(["--print-config", "--preset", "epic", "--music", "ambient"]) == 0
    config = json.loads(capsys.readouterr().out)
    assert config["motion"]["parallax"] == 1.5 and config["audio"]["mode"] == "ambient"
    assert main(["--input", "missing.png", "--duration", "-10"]) == 1
