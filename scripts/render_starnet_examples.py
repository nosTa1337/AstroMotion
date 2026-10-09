"""Render both own Seestar photos with a locally installed StarNet2 CLI.

No GitHub Actions, no downloaded StarNet binaries or models, no cloud service.
Produces MP4s and matching GIF previews in examples/real. The source photos are
never modified. Read and accept the applicable StarNet license before use.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from astromotion.config import load_config
from astromotion.pipeline import render
from scripts.render_photo_demo import make_preview

OBJECTS = (("orion", "Orionnebel", "MESSIER 42"),
           ("pleiades", "Plejaden", "MESSIER 45"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--starnet", type=Path, help="Pfad zur separat installierten starnet2 CLI")
    source.add_argument("--starless-dir", type=Path, help="Ordner mit orion_starless / pleiades_starless Bildpaaren")
    parser.add_argument("--starnet-mode", choices=("modern", "legacy", "auto"), default="modern")
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "immersive_loop.yaml")
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--resolution", choices=("720p", "1080p", "4k"), default="1080p")
    parser.add_argument("--only", choices=("orion", "pleiades"))
    parser.add_argument("--seed", type=int, help="Optionaler identischer Musik-Seed bei beiden Videos")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--no-gif", action="store_true")
    args = parser.parse_args()

    starnet = args.starnet.resolve() if args.starnet else None
    if starnet is not None and not starnet.is_file():
        parser.error(f"StarNet-CLI existiert nicht: {starnet}")
    root = ROOT / "examples" / "real"
    for stem, title, subtitle in OBJECTS:
        if args.only and args.only != stem:
            continue
        image = root / f"{stem}.jpg"
        if not image.is_file():
            raise FileNotFoundError(f"Foto fehlt: {image}")
        cfg = load_config(args.config, {
            "duration": args.duration,
            "resolution": args.resolution,
            "audio": {"seed": args.seed, "mode": "ambient"},
            "caption": {"enabled": True, "title": title, "subtitle": subtitle},
        })
        if starnet:
            cfg.separation.executable = str(starnet)
            cfg.separation.mode = args.starnet_mode
        starless = None
        if args.starless_dir:
            folder = args.starless_dir.resolve()
            candidates = [folder / (stem + "_starless" + ext)
                          for ext in (".tif", ".tiff", ".png", ".jpg")]
            starless = next((f for f in candidates if f.is_file()), None)
            if starless is None:
                raise FileNotFoundError(f"Passendes Starless-Bild für {stem} fehlt unter {folder}")
        output = root / (stem + "_starnet_demo.mp4")
        if output.exists() and not args.overwrite:
            raise FileExistsError(f"{output} existiert bereits. --overwrite verwenden.")
        print(f"Rendere {title}: {cfg.actual_duration:.1f}s, {cfg.size}, {cfg.fps} FPS", flush=True)
        report = render(image, output, cfg, starless_path=starless, overwrite=args.overwrite)
        if not args.no_gif:
            gif = root / (stem + "_starnet_preview.gif")
            make_preview(output, gif, cfg.encoding.ffmpeg)
            print(f"GIF: {gif}", flush=True)
        print(f"MP4: {output}; detected stars: "
              f"{report.get('starfield', {}).get('detected_star_particles', 'not enabled')}", flush=True)


if __name__ == "__main__":
    main()
