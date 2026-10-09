# Eigene Aufnahmen und Foto-Demos

**Seestar S50 Pro + AstroWizard · eigene Aufnahmen von Philipp / nosTa1337 – dürfen verwendet werden.** Eine Quellenangabe ist willkommen, zum Beispiel: „Aufnahme: Philipp / nosTa1337, Seestar S50 Pro; Bearbeitung: AstroWizard; Animation: AstroMotion“.

Die Erlaubnis umfasst die hier enthaltenen Originalfotos, die daraus erzeugten Demo-MP4s inklusive lokal synthetisierter Ambient-Musik und die GIF-Vorschauen. Es werden damit keine Rechte an AstroWizard, Seestar, StarNet oder anderen externen Produkten übertragen. Die MIT-Lizenz des Projektcodes ist separat in `../../LICENSE` beschrieben.

| Objekt | Originalfoto | Video mit Musik | Stumme README-Vorschau |
|---|---|---|---|
| Orionnebel / Messier 42 | [orion.jpg](orion.jpg) | [orion_demo.mp4](orion_demo.mp4) | [orion_preview.gif](orion_preview.gif) |
| Plejaden / Messier 45 | [pleiades.jpg](pleiades.jpg) | [pleiades_demo.mp4](pleiades_demo.mp4) | [pleiades_preview.gif](pleiades_preview.gif) |

Die Fotos wurden unverändert aus den bereitgestellten JPEGs kopiert. Die Videos zeigen neben Zoom, Rotation und Beschriftung eine **unabhängige perspektivische Sternbewegung**. Dazu werden kompakte Lichtpunkte direkt aus den eigenen Fotos geschätzt und ihre kleinen Bildbereiche lokal aufgefüllt (OpenCV-Inpainting). Diese **künstlerische Demo-Näherung ist keine verlässliche Sternentfernung** und kann in besonders hellen Nebelbereichen Sternkerne verpassen bzw. Bildartefakte erzeugen. StarNet und dessen Modelle werden **nicht** verwendet. Für hochwertige eigene Videos empfiehlt sich das Hauptprogramm mit einem echten Starless-Bild. Farben werden nicht automatisch korrigiert; Grading, Sättigungsanhebung, Bloom, Glow und Vignette sind weiterhin deaktiviert.

Im Projektordner bei aktivierter Python-Umgebung:

```bash
python scripts/render_photo_demo.py --overwrite
# Nur Orion erneut rendern:
python scripts/render_photo_demo.py --only orion --overwrite
```

Musik variiert zufällig bei jedem Lauf. Mit `--seed ZAHL` lässt sich eine Variante erneut erzeugen. Die aktuell versionierten MP4/GIF-Dateien wurden mit den angegebenen Seeds erstellt; nach erneutem Rendern werden neue Seeds in den lokalen Render-Berichten festgehalten. Die Render-Berichte und WAVs entstehen lokal in den ignorierten `*_assets`-Ordnern. Einstellungen: [photo_demo.yaml](../../configs/photo_demo.yaml).

Mit dem Demo-Render-Skript werden die GIFs automatisch zusammen mit den MP4s neu erzeugt (8 FPS, 280 Pixel Breite, ohne Ton). Die GIF-Vorschauen enthalten denselben vollständigen 30-Sekunden-Bildzyklus in kleiner Auflösung ohne Ton. In der Haupt-README sind sie mit den MP4s verlinkt. Große neue Videos besser außerhalb der Git-Historie hosten, etwa in GitHub Releases oder bei YouTube/Vimeo.
