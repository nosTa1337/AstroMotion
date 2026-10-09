"""Render the permitted original photos as explicit 2D demos, without StarNet.

Uses AstroMotion's camera, captions, ambient synthesis and checked encoder.
It does not pretend to separate stars or demonstrate the perspective starflight.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cv2
import numpy as np

from astromotion.animation import Animator
from astromotion.captions import CaptionOverlay
from astromotion.config import load_config
from astromotion.effects import EffectProcessor
from astromotion.encoding import VideoEncoder
from astromotion.imaging import load_image, resize_work, to_linear
from astromotion.looping import camera_phase, prepare_audio_loop
from astromotion.music import resolve_audio_seed
from astromotion.separation import Layers


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=30)
    parser.add_argument("--seed", type=int, help="Optionaler fester Musik-Seed")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    cv2.setNumThreads(2)
    folder = ROOT / "examples" / "real"
    for stem, title, subtitle in (("orion", "Orionnebel", "MESSIER 42"),
                                  ("pleiades", "Plejaden", "MESSIER 45")):
        output = folder / f"{stem}_demo.mp4"
        if output.exists() and not args.overwrite:
            raise FileExistsError(f"{output} existiert; --overwrite verwenden.")
        cfg = load_config(ROOT / "configs" / "photo_demo.yaml",
                          {"duration": args.duration, "audio": {"seed": args.seed}})
        cfg.audio = resolve_audio_seed(cfg.audio)
        cfg.caption.title, cfg.caption.subtitle = title, subtitle
        photo = to_linear(resize_work(load_image(folder / f"{stem}.jpg", cfg.max_input_pixels), cfg.work_long_edge))
        layers = Layers(photo, np.zeros_like(photo), "screen", {})
        animator = Animator(layers, cfg.size, cfg.motion)
        processor = EffectProcessor(cfg.effects, cfg.size, layers.blend)
        caption = CaptionOverlay(cfg.caption, cfg.size)
        assets = output.parent / (output.stem + "_assets")
        assets.mkdir(parents=True, exist_ok=True)
        audio = assets / "ambient_loop.wav"
        print(f"{title}: Musik-Seed {cfg.audio.seed}; {cfg.frame_count} Frames", flush=True)
        prepare_audio_loop(audio, cfg)
        with VideoEncoder(output, cfg, audio, assets / "ffmpeg.log") as encoder:
            for i in range(cfg.frame_count):
                phase = i / cfg.frame_count
                nebula, stars = animator.frame_layers(camera_phase(phase), 0, 0)
                rgb = caption.apply(processor.apply(nebula, stars), i / cfg.fps, cfg.actual_duration)
                encoder.write(np.clip(np.floor(rgb * 255 + .5), 0, 255).astype(np.uint8))
                if (i + 1) % cfg.fps == 0:
                    print(f"{title}: {i + 1}/{cfg.frame_count}", flush=True)
        report = {"mode": "2D original-photo animation; no star separation",
                  "input": f"examples/real/{stem}.jpg", "config": asdict(cfg), "probe": encoder.info}
        (assets / "render_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Fertig: {output.name}", flush=True)


if __name__ == "__main__":
    main()
