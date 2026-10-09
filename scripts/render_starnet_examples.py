"""Render both Seestar photo demos with the real, separately installed StarNet2 CLI.

No heuristic star separation or alternative demo mode. Source JPGs are unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
from dataclasses import replace

import numpy as np
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from astromotion.config import load_config
from astromotion.encoding import resolve_binary
from astromotion.pipeline import render
from astromotion.imaging import load_image, resize_work
from astromotion.quality import check_layers, save_contact_sheet
from astromotion.separation import run_starnet, extract_layers

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
    parser.add_argument("--starnet", type=Path, help="Path to licensed official StarNet2 CLI")
    parser.add_argument("--starnet-mode", choices=("modern", "legacy", "auto"), default="modern")
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "immersive_loop.yaml")
    parser.add_argument("--duration", type=float, default=2.0)
    parser.add_argument("--resolution", choices=("720p", "1080p", "4k"), default="720p")
    parser.add_argument("--only", choices=("orion", "pleiades", "all"), default="pleiades")
    parser.add_argument("--seed", type=int, help="Fixed music seed; defaults to random ambient")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--no-gif", action="store_true")
    parser.add_argument("--check-only", action="store_true", help="Prepare and inspect layers/stills; no video")
    parser.add_argument("--reuse-starnet", type=Path,
                        help="Folder containing <object>/starnet_input.tif, starnet_starless.tif and starnet.log")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "test-renders")
    args = parser.parse_args()

    starnet = args.starnet.expanduser().resolve() if args.starnet else None
    if not args.reuse_starnet and (starnet is None or not starnet.is_file()):
        parser.error("Provide --starnet EXE or --reuse-starnet with genuine cached StarNet2 output")
    root = ROOT / "examples" / "real"
    for stem, title, subtitle in OBJECTS:
        if args.only != "all" and args.only != stem:
            continue
        image = root / f"{stem}.jpg"
        if not image.is_file():
            raise FileNotFoundError(f"Missing photo: {image}")
        cfg = load_config(args.config, {
            "duration": args.duration,
            "resolution": args.resolution,
            "separation": {"executable": str(starnet) if starnet else None, "mode": args.starnet_mode},
            "audio": {"seed": args.seed, "mode": "ambient"},
            "caption": {"enabled": True, "title": title, "subtitle": subtitle},
        })
        args.output_dir.mkdir(parents=True, exist_ok=True)
        output = args.output_dir / f"{stem}_starnet_demo.mp4"
        if output.exists() and not args.overwrite and not args.check_only:
            raise FileExistsError(f"{output} exists; pass --overwrite")
        work = output.parent / (output.stem + "_assets")
        work.mkdir(exist_ok=True)
        original = resize_work(load_image(image), cfg.work_long_edge)
        if args.reuse_starnet:
            cache = args.reuse_starnet / stem
            cached_input = load_image(cache / "starnet_input.tif")
            if cached_input.shape != original.shape or not np.allclose(cached_input, original, atol=2/65535, rtol=0):
                raise ValueError(f"Cached StarNet2 input does not match {stem}")
            log = (cache / "starnet.log").read_text()
            if "StarNet2" not in log or "Writing starless image" not in log:
                raise ValueError("Cache needs the successful genuine StarNet2 log")
            for name in ("starnet_input.tif", "starnet_starless.tif", "starnet.log"):
                src, dst = cache / name, work / name
                if src.resolve() != dst.resolve():
                    shutil.copy2(src, dst)
            starless = load_image(work / "starnet_starless.tif")
        else:
            starless = run_starnet(original, cfg.separation, work)
        layers = extract_layers(original, starless, cfg.separation)
        metrics = check_layers(original, starless, layers)
        save_contact_sheet(work / "visual_review.jpg", original, starless, layers, cfg)
        evidence = {"source": "StarNet2", "cached": bool(args.reuse_starnet), "checks": metrics,
                    "sha256": {name: hashlib.sha256((work/name).read_bytes()).hexdigest()
                               for name in ("starnet_input.tif", "starnet_starless.tif", "starnet.log")}}
        (work / "separation_qa.json").write_text(json.dumps(evidence, indent=2))
        print(f"{stem}: layer checks passed; inspect {work / 'visual_review.jpg'}", flush=True)
        if args.check_only:
            continue
        # Encode exactly the checked pair, without a second inference or resize.
        # This also supports full-resolution originals above work_long_edge.
        render_cfg = replace(cfg, work_long_edge=max(original.shape[:2]))
        report = render(work / "starnet_input.tif", output, render_cfg,
                        work / "starnet_starless.tif", overwrite=args.overwrite)
        expected_mode = "starnet_starfield" if cfg.starfield.enabled else "starnet_layers"
        if report.get("animation_mode") != expected_mode:
            raise RuntimeError(f"Unexpected animation pipeline for {stem}")
        if not args.no_gif:
            gif = output.parent / f"{stem}_starnet_preview.gif"
            make_preview(output, gif, cfg.encoding.ffmpeg)
        print(f"Complete: {output}", flush=True)


if __name__ == "__main__":
    main()
