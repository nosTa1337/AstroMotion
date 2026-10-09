"""UI-independent orchestration. A future Gradio UI can call render() directly."""
from __future__ import annotations

from dataclasses import asdict, replace
import json
import logging
from pathlib import Path
import time
from typing import Callable

import cv2
import numpy as np

from .animation import Animator
from .captions import CaptionOverlay
from .config import Config
from .effects import EffectProcessor
from .encoding import VideoEncoder, resolve_binary
from .imaging import load_image, resize_work, save_png, to_srgb
from .intelligence import resolve_cinematic
from .music import resolve_audio_seed, synthesize_ambient
from .looping import camera_phase, prepare_audio_loop
from .separation import extract_layers, run_starnet
from .starfield import PerspectiveStars

LOG = logging.getLogger(__name__)
Progress = Callable[[int, int, float], None]


def render(input_path: Path, output: Path, cfg: Config, starless_path: Path | None = None,
           progress: Progress | None = None, overwrite: bool = False) -> dict:
    """Render synchronously; exceptions propagate; callback runs once per frame.

    Video is committed atomically only after successful encoding and verification.
    Diagnostic files live beside the output under <stem>_assets/.
    """
    cfg.validate()
    if cfg.audio.mode == "ambient":
        cfg = replace(cfg, audio=resolve_audio_seed(cfg.audio))
    input_path, output = input_path.resolve(), output.resolve()
    if output.suffix.lower() != ".mp4":
        raise ValueError("Ausgabe muss eine .mp4-Datei sein.")
    if output == input_path or (starless_path and output == starless_path.resolve()):
        raise ValueError("Ausgabe darf kein Eingabebild überschreiben.")
    if output.exists() and not overwrite:
        raise FileExistsError(f"Ausgabe existiert bereits: {output}. Mit --overwrite ersetzen.")
    resolve_binary(cfg.encoding.ffmpeg)
    if cfg.encoding.verify:
        resolve_binary(cfg.encoding.ffprobe)
    if not starless_path and not cfg.separation.executable:
        raise ValueError("Keine zuverlässige Sternentrennung verfügbar. --starless BILD oder --starnet EXE verwenden.")
    audio_path = Path(cfg.audio.file).expanduser().resolve() if cfg.audio.mode == "file" and cfg.audio.file else None
    if audio_path and (not audio_path.is_file() or audio_path.suffix.lower() not in (".mp3", ".wav")):
        raise ValueError("Eigene Musik muss eine existierende MP3-/WAV-Datei sein.")
    workspace = output.parent / (output.stem + "_assets")
    workspace.mkdir(parents=True, exist_ok=True)
    log_handler = logging.FileHandler(workspace / "render.log", mode="w", encoding="utf-8")
    log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(log_handler)
    cv2.setNumThreads(2)
    start = time.monotonic()
    try:
        if cfg.audio.mode == "ambient":
            LOG.info("Ambient-Musik: Seed %d (mit --seed wiederholbar).", cfg.audio.seed)
        original_full = load_image(input_path, cfg.max_input_pixels)
        original_shape = original_full.shape
        original = resize_work(original_full, cfg.work_long_edge)
        del original_full
        effective_motion, effective_effects, cinematic_metrics = resolve_cinematic(
            original, cfg.motion, cfg.effects, cfg.cinematic)
        if cinematic_metrics:
            LOG.info("Cinematic intelligence: focus=(%.3f, %.3f) contrast=%.3f saturation=%.3f",
                     effective_motion.center_x, effective_motion.center_y,
                     effective_effects.contrast, effective_effects.saturation)
        if starless_path:
            raw_starless = load_image(starless_path.resolve(), cfg.max_input_pixels)
            if raw_starless.shape != original_shape:
                raise ValueError("Original und Starless müssen vor der Verkleinerung exakt dieselbe Größe haben.")
            starless = resize_work(raw_starless, cfg.work_long_edge)
            del raw_starless
        else:
            starless = run_starnet(original, cfg.separation, workspace)
        layers = extract_layers(original, starless, cfg.separation)
        del original, starless
        if cfg.save_layers:
            save_png(workspace / "nebula.png", to_srgb(layers.nebula))
            # stars.png stores the linear screen fraction encoded as sRGB, not
            # an ordinary additive star photograph. Manifest documents the blend.
            save_png(workspace / "stars.png", to_srgb(layers.stars))
        if cfg.loop.enabled and cfg.audio.mode != "none":
            source_audio = audio_path
            audio_path = workspace / "ambient_loop.wav"
            prepare_audio_loop(audio_path, cfg, source_audio)
        elif cfg.audio.mode == "ambient":
            audio_path = workspace / "ambient.wav"
            LOG.info("Synthetisiere originale Ambient-Musik (Seed %d).", cfg.audio.seed)
            synthesize_ambient(audio_path, cfg.actual_duration, cfg.audio)
        animator = Animator(layers, cfg.size, effective_motion)
        processor = EffectProcessor(effective_effects, cfg.size, layers.blend)
        particles = PerspectiveStars(layers, animator, cfg.starfield, cfg.fps, cfg.loop) if cfg.starfield.enabled else None
        caption = CaptionOverlay(cfg.caption, cfg.size) if cfg.caption.enabled else None
        if animator.base_scale > 1:
            LOG.warning("Ausschnitt wird %.2fx hochskaliert. Für mehr Details ein größeres Foto/work_long_edge verwenden.",
                        animator.base_scale)
        LOG.info("Render %dx%d, %d FPS, %d Frames, %.3f s. Crop-Skalierung %.3f.",
                 *cfg.size, cfg.fps, cfg.frame_count, cfg.actual_duration, animator.base_scale)
        # Stable sub-LSB ordered dithering reduces dark-gradient 8-bit banding.
        bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32)
        w, h = cfg.size
        dither = np.tile((bayer + .5) / 16 - .5, ((h + 3) // 4, (w + 3) // 4))[:h, :w, None]
        with VideoEncoder(output, cfg, audio_path, workspace / "ffmpeg.log") as encoder:
            for i in range(cfg.frame_count):
                # Periodic samples exclude the duplicated endpoint: N-1 -> 0
                # is exactly one frame interval, with no extra freeze frame.
                t = i / cfg.frame_count if cfg.loop.enabled else i / max(1, cfg.frame_count - 1)
                camera_t = camera_phase(t) if cfg.loop.enabled else t
                twinkle_time = 2 * np.pi * t / 1.4 if cfg.loop.enabled else i / cfg.fps
                nebula, stars = animator.frame_layers(camera_t, twinkle_time, cfg.effects.twinkle)
                if particles:
                    stars = stars * cfg.starfield.farfield_gain
                rgb = processor.apply(nebula, stars)
                if particles:
                    rgb = particles.composite(rgb, t, cfg.actual_duration)
                if caption:
                    rgb = caption.apply(rgb, i / cfg.fps, cfg.actual_duration if cfg.loop.enabled else None)
                frame = np.clip(np.floor(rgb * 255 + .5 + dither), 0, 255).astype(np.uint8)
                encoder.write(frame)
                if progress:
                    progress(i + 1, cfg.frame_count, time.monotonic() - start)
        report = {"input": str(input_path), "starless": str(starless_path) if starless_path else "StarNet",
                  "output": str(output), "config": asdict(cfg), "diagnostics": layers.diagnostics,
                  "base_scale": animator.base_scale, "actual_duration": cfg.actual_duration,
                  "elapsed_seconds": time.monotonic() - start, "probe": encoder.info,
                  "cinematic_intelligence": cinematic_metrics,
                  "layer_encoding": "sRGB PNG; decode sRGB to linear then use separation.blend"}
        if particles:
            report["starfield"] = particles.stats
        (workspace / "render_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        LOG.info("Fertig: %s (%.1f Sekunden).", output, report["elapsed_seconds"])
        return report
    finally:
        logging.getLogger().removeHandler(log_handler)
        log_handler.close()
