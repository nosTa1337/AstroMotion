# Eigene Aufnahmen und Foto-Demos

**Seestar S50 Pro + AstroWizard · eigene Aufnahmen von Philipp / nosTa1337 – dürfen verwendet werden.** Eine Quellenangabe ist willkommen, zum Beispiel: „Aufnahme: Philipp / nosTa1337, Seestar S50 Pro; Bearbeitung: AstroWizard; Animation: AstroMotion“.

Die Erlaubnis umfasst die hier enthaltenen Originalfotos, die daraus erzeugten Demo-MP4s inklusive lokal synthetisierter Ambient-Musik und die GIF-Vorschauen. Es werden damit keine Rechte an AstroWizard, Seestar, StarNet oder anderen externen Produkten übertragen. Die MIT-Lizenz des Projektcodes ist separat in `../../LICENSE` beschrieben.

| Objekt | Originalfoto | Video mit Musik | Stumme README-Vorschau |
|---|---|---|---|
| Orionnebel / Messier 42 | [orion.jpg](orion.jpg) | [orion_demo.mp4](orion_demo.mp4) | [orion_preview.gif](orion_preview.gif) |
| Plejaden / Messier 45 | [pleiades.jpg](pleiades.jpg) | [pleiades_demo.mp4](pleiades_demo.mp4) | [pleiades_preview.gif](pleiades_preview.gif) |

Die Fotos wurden unverändert aus den bereitgestellten JPEGs kopiert. Die 30-Sekunden-Videos zeigen eine sanfte 2D-Kamerafahrt mit Beschriftung: 720 × 1280, 30 FPS, H.264, AAC-Stereo. Es gibt keine separate Sternebene und keinen unabhängigen Sternflug. StarNet wurde nicht verwendet. Farben werden nicht automatisch korrigiert; Grading, Sättigungsanhebung, Bloom, Glow und Vignette sind deaktiviert.

Im Projektordner bei aktivierter Python-Umgebung:

```bash
python scripts/render_photo_demo.py --overwrite
```

Musik variiert zufällig bei jedem Lauf. Mit `--seed ZAHL` lässt sich eine Variante erneut erzeugen. Die hier enthaltenen Videos verwenden Seed **629488976** für Orion; **690608432** für die Plejaden. Die Render-Berichte und WAVs entstehen lokal in den ignorierten `*_assets`-Ordnern. Einstellungen: [photo_demo.yaml](../../configs/photo_demo.yaml).

Die GIF-Vorschauen enthalten denselben vollständigen 30-Sekunden-Bildzyklus in kleiner Auflösung ohne Ton. In der Haupt-README sind sie mit den MP4s verlinkt. Große neue Videos besser außerhalb der Git-Historie hosten, etwa in GitHub Releases oder bei YouTube/Vimeo.
