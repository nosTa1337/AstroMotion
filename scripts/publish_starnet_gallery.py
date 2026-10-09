"""Switch README demo gallery to existing StarNet MP4/GIF assets locally.

This performs *no* GitHub/API calls and does not download or render anything.
Copy files to examples/real first, then run this script in the repo checkout
and push manually with ordinary git. Preserves the original OpenCV examples.
"""
from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "examples" / "real"
OBJECTS = ("orion", "pleiades")

def main() -> None:
    for stem in OBJECTS:
        mp4 = MEDIA / f"{stem}_starnet_demo.mp4"
        gif = MEDIA / f"{stem}_starnet_preview.gif"
        for p in (mp4, gif):
            if not p.is_file() or p.stat().st_size < 1000:
                raise FileNotFoundError(f"Missing or empty media file: {p}")
        probe = json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-show_format", "-show_streams",
            "-of", "json", str(mp4)], text=True))
        if not (29.9 < float(probe["format"]["duration"]) < 30.2):
            raise ValueError(f"Expected 30s demo video: {mp4}")
        if not {"h264", "aac"}.issubset({stream.get("codec_name") for stream in probe["streams"]}):
            raise ValueError(f"Missing H.264 video / AAC audio: {mp4}")
        with Image.open(gif) as image:
            if image.n_frames < 150:
                raise ValueError(f"Expected animated multi-frame GIF: {gif}")
        print(f"Valid: {stem} – 30s MP4 + animated GIF", flush=True)

    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    for stem in OBJECTS:
        text = text.replace(f"examples/real/{stem}_preview.gif",
                            f"examples/real/{stem}_starnet_preview.gif")
        text = text.replace(f"examples/real/{stem}_demo.mp4",
                            f"examples/real/{stem}_starnet_demo.mp4")
    note = """Die bisherigen GIFs und MP4s im Repository wurden noch mit einer
**OpenCV-Näherung** erstellt, nicht mit StarNet2; sie bleiben als
technischer Vergleich erhalten und werden nicht fälschlich als
StarNet-Renderings bezeichnet."""
    updated = """**StarNet2-Video-Demos:** Die hier eingebetteten GIFs und verlinkten MP4s
wurden mit echter StarNet2-Sterntrennung aus unseren Seestar-S50-Pro-Aufnahmen
und AstroMotion erstellt. Beide Clips dauern 30 Sekunden (1080 × 1920,
30 FPS), haben eine eigene synthetisierte Ambient-Musik und unabhängige
perspektivische Sternbewegung. Die früheren OpenCV-Beispiele bleiben
unter `orion_demo.mp4` und `pleiades_demo.mp4` verfügbar.
Siehe die separat geltenden StarNet2-Lizenzbedingungen."""
    text = text.replace(note, updated)
    text = text.replace("bestehende OpenCV-GIF", "StarNet2-GIF")
    text = text.replace("bisheriges Video", "StarNet2-MP4 mit Ambient-Musik")
    if not all(f"examples/real/{stem}_starnet_preview.gif" in text for stem in OBJECTS):
        raise RuntimeError("Could not locate README gallery; refusing partial update")
    readme.write_text(text, encoding="utf-8")
    print("README gallery updated locally. Review license notices before publication.")
    print("git add README.md examples/real/*_starnet_demo.mp4 examples/real/*_starnet_preview.gif")
    print('git commit -m "Publish StarNet2 video and GIF demo gallery"')
    print("git push")

if __name__ == "__main__":
    try:
        main()
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
