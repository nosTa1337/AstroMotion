"""Publish *existing* StarNet2 clips and GIFs in README; never render video.

Run locally with an existing examples/real media set, or pass --source-dir
pointing to GitHub's previously completed artifact exports. This script does
not download a model, call StarNet, invoke FFmpeg for encoding or create GIFs.
Before publishing, consider the separate StarNet2 product-assets restriction.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "examples" / "real"
OBJECTS = ("orion", "pleiades")


def verify(mp4: Path, gif: Path) -> None:
    if not mp4.is_file() or mp4.stat().st_size < 100_000:
        raise FileNotFoundError(f"MP4 fehlt/leer: {mp4}")
    if not gif.is_file() or gif.stat().st_size < 100_000:
        raise FileNotFoundError(f"GIF fehlt/leer: {gif}")
    with mp4.open("rb") as f:
        header = f.read(16)
    if header[4:8] != b"ftyp":
        raise ValueError(f"Keine MP4-Datei: {mp4}")
    with gif.open("rb") as f:
        header = f.read(12)
    if header[:6] not in (b"GIF89a", b"GIF87a"):
        raise ValueError(f"Keine GIF-Datei: {gif}")
    # ffprobe is for verification only; it never renders or alters the movie.
    if shutil.which("ffprobe"):
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_format", "-show_streams",
             "-of", "json", str(mp4)], capture_output=True,
            text=True, check=True, timeout=30)
        meta = json.loads(result.stdout)
        if not 29.9 <= float(meta["format"]["duration"]) <= 30.2:
            raise ValueError(f"Unerwartete Videolänge: {mp4}")
        streams = meta["streams"]
        if not {"h264", "aac"}.issubset(
                {entry.get("codec_name") for entry in streams}):
            raise ValueError(f"H.264-Video oder AAC-Musik fehlt: {mp4}")


def install_media(source: Path) -> None:
    # Validate all inputs before copying anything to the project.
    targets = []
    for stem in OBJECTS:
        src_movie = source / f"{stem}_starnet_30s.mp4"
        src_gif = source / f"{stem}_starnet_preview.gif"
        verify(src_movie, src_gif)
        targets.extend(((src_movie, MEDIA / f"{stem}_starnet_demo.mp4"),
                        (src_gif, MEDIA / f"{stem}_starnet_preview.gif")))
    for src, dst in targets:
        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)


GALLERY = """## Eigene Seestar-Aufnahmen und Video-Demos

Die Aufnahmen stammen vom **Seestar S50 Pro**, wurden mit **AstroWizard**
bearbeitet und von Philipp / nosTa1337 zur Verwendung freigegeben.

**Die aktuellen animierten GIFs und MP4s verwenden echte StarNet2-Sterntrennung.**
Nebel und Sterne werden unabhängig animiert; die Sterne erhalten künstlerisch
verteilte Tiefenwerte (keine gemessenen Sternentfernungen). Beide 30-Sekunden-
Videos sind in **1080 × 1920 bei 30 FPS** gerendert und enthalten jeweils
eine eigene synthetisierte Ambient-Musik. Die GIFs sind stumm.

| Orionnebel · M42 | Plejaden · M45 |
|---|---|
| [![Orionnebel – StarNet2-Sternflug](examples/real/orion_starnet_preview.gif)](examples/real/orion_starnet_demo.mp4) | [![Plejaden – StarNet2-Sternflug](examples/real/pleiades_starnet_preview.gif)](examples/real/pleiades_starnet_demo.mp4) |
| [Originalfoto](examples/real/orion.jpg) · [30s-MP4 mit Musik](examples/real/orion_starnet_demo.mp4) | [Originalfoto](examples/real/pleiades.jpg) · [30s-MP4 mit Musik](examples/real/pleiades_starnet_demo.mp4) |

Die älteren **OpenCV-Demos ohne StarNet2** bleiben als Vergleich erhalten:
[Orion](examples/real/orion_demo.mp4) ·
[Plejaden](examples/real/pleiades_demo.mp4).

**Rechtlicher Hinweis:** StarNet2 und dessen Modellgewichte sind kein Bestandteil
des MIT-lizenzierten AstroMotion-Projekts. Die gesonderte
[StarNet2-Lizenz](THIRD_PARTY_NOTICES.md) erlaubt grundsätzlich die
Veröffentlichung eigener Bildbearbeitungen, schränkt aber in Abschnitt 5 die
Verwendung ihrer Ausgaben als Assets anderer Softwareprodukte ein. Diese
README-Galerie kann darunter fallen; eine separate Zustimmung des
Rechteinhabers wäre die rechtssichere Lösung. Die hier verwendeten
Bildbearbeitungsresultate werden deshalb nicht als allgemein freigegebene
StarNet2-Produktassets bezeichnet.

### Videos mit StarNet2 lokal neu erstellen

Die offizielle [StarNet2-CLI](https://starnetastro.com/cli-tools/starnet/)
separat installieren, Lizenz lesen und akzeptieren. Es werden keine Modelle
oder StarNet-Programme im Repository mitgeliefert.

\`\`\`bash
python scripts/render_starnet_examples.py --starnet "/path/to/starnet2" --overwrite
\`\`\`

Aus bereits vorhandenen passenden Starless-Bildern:

\`\`\`bash
python scripts/render_starnet_examples.py --starless-dir "/path/to/starless" --overwrite
\`\`\`

Um fertige, bereits gerenderte MP4s/GIFs in die Galerie zu übernehmen,
kann man lokal \`python scripts/publish_starnet_gallery.py\` verwenden.
GitHub Actions wird **nicht** zum Rendern verwendet; der einmalige
Import der hier gezeigten Medien war ausschließlich eine Dateikopie.

"""


MEDIA_README = """# Eigene Astroaufnahmen und Beispielvideos

Eigene Aufnahmen von **Philipp / nosTa1337**, aufgenommen mit **Seestar S50 Pro**,
bearbeitet mit **AstroWizard**. Die Originalfotos dürfen verwendet werden;
eine Quellenangabe ist willkommen.

| Objekt | Original | StarNet2-Video (30 s, Ton) | Animiertes GIF |
|---|---|---|---|
| Orionnebel · M42 | [orion.jpg](orion.jpg) | [orion_starnet_demo.mp4](orion_starnet_demo.mp4) | [orion_starnet_preview.gif](orion_starnet_preview.gif) |
| Plejaden · M45 | [pleiades.jpg](pleiades.jpg) | [pleiades_starnet_demo.mp4](pleiades_starnet_demo.mp4) | [pleiades_starnet_preview.gif](pleiades_starnet_preview.gif) |

Die Videos wurden aus den eigenen Aufnahmen mit der **separat installierten
StarNet2-CLI** und AstroMotion erstellt. Die Tiefenbewegung ist künstlerisch;
sie misst keine astronomischen Entfernungen. Stereo-Ambient-Musik ist lokal
synthetisiert, die GIFs haben keinen Ton.

Die früheren OpenCV-Varianten bleiben als Vergleich bestehen:
[Orion](orion_demo.mp4) und [Plejaden](pleiades_demo.mp4).

**StarNet2 ist separat lizenziert und nicht Teil von AstroMotions MIT-Lizenz.**
Die Lizenz erlaubt grundsätzlich die Veröffentlichung eigener Bildbearbeitung,
schränkt die Nutzung solcher Ergebnisse als Software-Produktassets jedoch ein.
Vor öffentlicher Nutzung als Software-Demos ist eine schriftliche Freigabe
des StarNet2-Anbieters die rechtssichere Lösung. Siehe
[THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md).
"""


def update_docs() -> None:
    p = ROOT / "README.md"
    current = p.read_text(encoding="utf-8")
    begin = current.index("## Eigene Seestar-Aufnahmen und Video-Demos")
    end = current.index("### AstroMotion v1.2 – Cinematic Intelligence", begin)
    updated = current[:begin] + GALLERY + current[end:]
    p.write_text(updated, encoding="utf-8")
    (MEDIA / "README.md").write_text(MEDIA_README, encoding="utf-8")
    notices = ROOT / "THIRD_PARTY_NOTICES.md"
    note = notices.read_text(encoding="utf-8")
    first = note.index("Die zurzeit im Git-Repository eingebetteten älteren GIFs/MP4s")
    last = note.index("\n\nDie historische Python-Implementierung", first)
    paragraph = (
        "Die README zeigt die von eigenen Seestar-S50-Pro-Fotos abgeleiteten "
        "StarNet2-MP4s und GIF-Vorschauen; die früheren OpenCV-Demos liegen "
        "weiterhin im Repository. StarNet2-Software und Modellgewichte werden "
        "nicht mitgeliefert. **Abschnitt 5 der Lizenz schränkt die Verwendung "
        "von Outputs als Assets anderer Softwareprodukte ausdrücklich ein, "
        "unabhängig davon, ob die Software kommerziell ist.** Die Verwendung "
        "in einer AstroMotion-README-Galerie ist damit möglicherweise nicht "
        "ohne zusätzliche schriftliche Genehmigung gedeckt. "
        "Die eigenen Bildrechte und AstroMotions MIT-Lizenz heben dies nicht auf. "
        "Nutzer müssen die StarNet2-Lizenz für ihre jeweilige installierte "
        "Version selbst lesen und akzeptieren; alternativ kann ein zulässig "
        "erstelltes Starless-Bild über --starless verarbeitet werden."
    )
    note = note[:first] + paragraph + note[last:]
    notices.write_text(note, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path,
                        help="Ordner mit fertig gerenderten, vorher geprüften StarNet2-Dateien")
    args = parser.parse_args()
    if args.source_dir:
        install_media(args.source_dir)
    for stem in OBJECTS:
        verify(MEDIA / f"{stem}_starnet_demo.mp4",
               MEDIA / f"{stem}_starnet_preview.gif")
    update_docs()
    print("Vorhandene StarNet2-Videos/GIFs geprüft und README aktualisiert.")
    print("Kein Video/GIF erzeugt; alte OpenCV-Medien unverändert.")
    print("VOR Veröffentlichung: StarNet2-Abschnitt 5 (Software-Produktassets) prüfen.")


if __name__ == "__main__":
    main()
