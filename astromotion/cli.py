from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import logging
from pathlib import Path
import sys
import time

from .config import PRESETS, load_config
from .pipeline import render


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AstroMotion – lokale 2,5D-Deep-Sky-Videos")
    parser.add_argument("--input", type=Path, help="Fertiges, gestretchtes RGB-Astrofoto")
    parser.add_argument("--starless", type=Path, help="Passendes sternenloses Bild, statt StarNet")
    parser.add_argument("--starnet", help="Pfad zu starnet2.exe oder starnet++.exe")
    parser.add_argument("--starnet-mode", choices=("auto", "modern", "legacy"))
    parser.add_argument("--config", type=Path, help="YAML-/JSON-Datei")
    parser.add_argument("--output", type=Path, help="MP4-Ausgabe (Standard: <input>_astromotion.mp4)")
    parser.add_argument("--preset", choices=tuple(PRESETS))
    parser.add_argument("--format", choices=("vertical", "square", "landscape"))
    parser.add_argument("--resolution", choices=("720p", "1080p", "4k"))
    parser.add_argument("--duration", type=float)
    parser.add_argument("--loop", action=argparse.BooleanOptionalAction, default=None,
                        help="Nahtloser Video-/Musik-Loop; --no-loop deaktiviert ihn")
    parser.add_argument("--fps", type=int, choices=(24, 30, 60))
    parser.add_argument("--music", choices=("none", "ambient"))
    parser.add_argument("--audio", type=Path, help="Eigene MP3-/WAV-Datei (hat Vorrang vor --music)")
    parser.add_argument("--seed", type=int, help="Musik reproduzieren; ohne festen Seed zufällige Variante")
    parser.add_argument("--parallax", type=float)
    parser.add_argument("--speed", type=float)
    parser.add_argument("--title", help="Dezenter Objektname; aktiviert die Beschriftung")
    parser.add_argument("--subtitle", help="Optionale zweite Zeile, z. B. MESSIER 42")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--print-config", action="store_true", help="Effektive Konfiguration ausgeben; kein Render")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s: %(message)s")
    overrides = {k: getattr(args, k) for k in ("preset", "format", "resolution", "duration", "fps")
                 if getattr(args, k) is not None}
    if args.loop is not None:
        overrides["loop"] = {"enabled": args.loop}
    for group, values in {
        "separation": {"executable": args.starnet, "mode": args.starnet_mode},
        "motion": {"parallax": args.parallax, "speed": args.speed},
        "audio": {"mode": "file" if args.audio else args.music,
                  "file": str(args.audio.resolve()) if args.audio else None, "seed": args.seed},
    }.items():
        clean = {k: v for k, v in values.items() if v is not None}
        if clean:
            overrides[group] = clean
    # CLI paths are always relative to the caller, even with --config.
    if args.starnet:
        overrides["separation"]["executable"] = str(Path(args.starnet).resolve())
    if args.title is not None or args.subtitle is not None:
        overrides["caption"] = {"enabled": True}
        if args.title is not None:
            overrides["caption"]["title"] = args.title
        if args.subtitle is not None:
            overrides["caption"]["subtitle"] = args.subtitle
    try:
        cfg = load_config(args.config, overrides)
        if args.print_config:
            print(json.dumps(asdict(cfg), indent=2, ensure_ascii=False))
            return 0
        if not args.input:
            parser.error("--input wird benötigt (außer bei --print-config).")
        output = args.output or args.input.with_name(args.input.stem + "_astromotion.mp4")
        last = [0.0]

        def progress(done: int, total: int, elapsed: float) -> None:
            now = time.monotonic()
            if now - last[0] >= 1 or done == total:
                rate = done / max(elapsed, .01)
                eta = (total - done) / max(rate, .01)
                print(f"\rRender: {done / total:6.1%} | {done}/{total} Frames | {rate:.1f} FPS | Rest ~{eta:.0f}s",
                      end="\n" if done == total else "", file=sys.stderr, flush=True)
                last[0] = now

        render(args.input, output, cfg, args.starless, progress, args.overwrite)
        print(f"Video: {output.resolve()}")
        return 0
    except KeyboardInterrupt:
        print("\nRender abgebrochen; unvollständige MP4 entfernt.", file=sys.stderr)
        return 130
    except Exception as exc:
        logging.error("%s", exc, exc_info=args.verbose)
        return 1
