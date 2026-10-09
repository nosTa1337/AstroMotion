"""Create permitted Seestar photo previews with independent, moving stars.

Demo-only OpenCV point-source approximation: no StarNet binary or weights.
For high-quality real projects, supply a genuine starless image to main.py.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cv2
import numpy as np

from astromotion.animation import Animator
from astromotion.captions import CaptionOverlay
from astromotion.config import load_config
from astromotion.demo_separation import approximate_demo_layers
from astromotion.effects import EffectProcessor
from astromotion.encoding import VideoEncoder, resolve_binary
from astromotion.imaging import load_image, resize_work
from astromotion.looping import camera_phase, prepare_audio_loop
from astromotion.music import resolve_audio_seed
from astromotion.starfield import PerspectiveStars


def make_preview(video: Path, gif: Path, ffmpeg: str) -> None:
    """Replace GIF atomically after a verified complete render."""
    tmp = gif.with_name(f".{gif.stem}.partial.gif")
    tmp.unlink(missing_ok=True)
    command = [resolve_binary(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
               "-i", str(video), "-filter_complex",
               "fps=8,scale=280:-2:flags=lanczos,split[a][b];"
               "[a]palettegen=max_colors=64[p];[b][p]paletteuse=dither=bayer:bayer_scale=3",
               "-loop", "0", str(tmp)]
    try:
        result = subprocess.run(command, capture_output=True, timeout=180)
        if result.returncode or not tmp.is_file() or tmp.stat().st_size < 100:
            raise RuntimeError(f"GIF-Vorschau fehlgeschlagen: {result.stderr.decode(errors='replace')[-1200:]}")
        tmp.replace(gif)
    finally:
        tmp.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=30)
    parser.add_argument("--seed", type=int, help="Optionaler fester Musik-Seed")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--only", choices=("orion", "pleiades"), help="Nur ein Objekt rendern")
    parser.add_argument("--no-gif", action="store_true", help="Keine neue GIF-Vorschau")
    args = parser.parse_args()
    cv2.setNumThreads(2)
    folder = ROOT / "examples" / "real"
    for stem, title, subtitle in (("orion", "Orionnebel", "MESSIER 42"),
                                  ("pleiades", "Plejaden", "MESSIER 45")):
        if args.only and stem != args.only:
            continue
        output = folder / f"{stem}_demo.mp4"
        if output.exists() and not args.overwrite:
            raise FileExistsError(f"{output} existiert; --overwrite verwenden.")
        cfg = load_config(ROOT / "configs" / "photo_demo.yaml",
                          {"duration": args.duration, "audio": {"seed": args.seed}})
        cfg.audio = resolve_audio_seed(cfg.audio)
        cfg.caption.title, cfg.caption.subtitle = title, subtitle
        photo = resize_work(load_image(folder / f"{stem}.jpg", cfg.max_input_pixels), cfg.work_long_edge)
        layers = approximate_demo_layers(photo)
        animator = Animator(layers, cfg.size, cfg.motion)
        processor = EffectProcessor(cfg.effects, cfg.size, layers.blend)
        particles = PerspectiveStars(layers, animator, cfg.starfield, cfg.fps, cfg.loop) if cfg.starfield.enabled else None
        caption = CaptionOverlay(cfg.caption, cfg.size)
        assets = output.parent / (output.stem + "_assets")
        assets.mkdir(parents=True, exist_ok=True)
        audio = assets / "ambient_loop.wav"
        print(f"{title}: {int(layers.diagnostics['demo_approximate_star_cores'])} Sternkerne, "
              f"Musik-Seed {cfg.audio.seed}, {cfg.frame_count} Frames", flush=True)
        prepare_audio_loop(audio, cfg)
        with VideoEncoder(output, cfg, audio, assets / "ffmpeg.log") as encoder:
            for i in range(cfg.frame_count):
                phase = i / cfg.frame_count
                nebula, stars = animator.frame_layers(camera_phase(phase), 0, 0)
                if particles:
                    stars *= cfg.starfield.farfield_gain
                rgb = processor.apply(nebula, stars)
                if particles:
                    rgb = particles.composite(rgb, phase, cfg.actual_duration)
                rgb = caption.apply(rgb, i / cfg.fps, cfg.actual_duration)
                encoder.write(np.clip(np.floor(rgb * 255 + .5), 0, 255).astype(np.uint8))
                if (i + 1) % cfg.fps == 0:
                    print(f"{title}: {i + 1}/{cfg.frame_count}", flush=True)
        report = {"mode": "independent photo-derived stars (approximate OpenCV demo extraction; no StarNet)",
                  "input": f"examples/real/{stem}.jpg", "config": asdict(cfg),
                  "diagnostics": layers.diagnostics, "starfield": particles.stats if particles else None,
                  "probe": encoder.info}
        (assets / "render_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        if not args.no_gif:
            gif = folder / f"{stem}_preview.gif"
            make_preview(output, gif, cfg.encoding.ffmpeg)
            print(f"GIF-Vorschau: {gif.name}", flush=True)
        print(f"Fertig: {output.name}", flush=True)


if __name__ == "__main__":
    main()
