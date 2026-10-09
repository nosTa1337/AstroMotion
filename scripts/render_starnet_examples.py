"""Render both Seestar photo demos with the real, separately installed StarNet2 CLI.

No heuristic star separation or alternative demo mode. Source JPGs are unchanged.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from astromotion.config import load_config
from astromotion.encoding import resolve_binary
from astromotion.pipeline import render

OBJECTS = (("orion", "Orionnebel", "MESSIER 42"),
           ("pleiades", "Plejaden", "MESSIER 45"))


def make_preview(video: Path, gif: Path, ffmpeg: str) -> None:
    """Replace a GIF only after a complete, successful video-to-GIF export."""
    tmp = gif.with_name(f".{gif.stem}.partial.gif")
    tmp.unlink(missing_ok=True)
    command = [resolve_binary(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
               "-i", str(video), "-filter_complex",
               "fps=8,scale=280:-2:flags=lanczos,split[a][b];"
               "[a]palettegen=max_colors=64[p];[b][p]paletteuse=dither=bayer:bayer_scale=3",
               "-loop", "0", str(tmp)]
    try:
        result = subprocess.run(command, capture_output=True, timeout=240)
        if result.returncode or not tmp.is_file() or tmp.stat().st_size < 1000:
            raise RuntimeError(f"GIF failed: {result.stderr.decode(errors='replace')[-1200:]}")
        tmp.replace(gif)
    finally:
        tmp.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--starnet", type=Path, required=True, help="Path to licensed official StarNet2 CLI")
    parser.add_argument("--starnet-mode", choices=("modern", "legacy", "auto"), default="modern")
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "immersive_loop.yaml")
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--resolution", choices=("720p", "1080p", "4k"), default="1080p")
    parser.add_argument("--only", choices=("orion", "pleiades"))
    parser.add_argument("--seed", type=int, help="Fixed music seed; defaults to random ambient")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--no-gif", action="store_true")
    args = parser.parse_args()

    starnet = args.starnet.expanduser().resolve()
    if not starnet.is_file():
        parser.error(f"StarNet2 executable not found: {starnet}")
    root = ROOT / "examples" / "real"
    for stem, title, subtitle in OBJECTS:
        if args.only and args.only != stem:
            continue
        image = root / f"{stem}.jpg"
        if not image.is_file():
            raise FileNotFoundError(f"Missing photo: {image}")
        cfg = load_config(args.config, {
            "duration": args.duration,
            "resolution": args.resolution,
            "separation": {"executable": str(starnet), "mode": args.starnet_mode},
            "audio": {"seed": args.seed, "mode": "ambient"},
            "caption": {"enabled": True, "title": title, "subtitle": subtitle},
        })
        output = root / f"{stem}_starnet_demo.mp4"
        if output.exists() and not args.overwrite:
            raise FileExistsError(f"{output} exists; pass --overwrite")
        print(f"Real StarNet2: {title}, {cfg.actual_duration:.1f}s, {cfg.size}, {cfg.fps} fps", flush=True)
        report = render(image, output, cfg, overwrite=args.overwrite)
        if report.get("starless") != "StarNet" or report.get("starfield", {}).get("detected_star_particles", 0) < 10:
            raise RuntimeError(f"Failed StarNet2 provenance check for {stem}")
        if not args.no_gif:
            gif = root / f"{stem}_starnet_preview.gif"
            make_preview(output, gif, cfg.encoding.ffmpeg)
        print(f"Complete: {output}", flush=True)


if __name__ == "__main__":
    main()
