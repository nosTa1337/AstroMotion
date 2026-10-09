# Eigene Seestar-Aufnahmen und Videos

Originalfotos von **Philipp / nosTa1337**, aufgenommen mit dem **Seestar S50 Pro**
und bearbeitet in **AstroWizard**. Die hier enthaltenen Original-JPEGs dürfen
verwendet werden; eine Quellenangabe ist willkommen.

## Öffentliche Demo-Medien – OpenCV, ohne StarNet

| Objekt | Originalfoto | MP4 mit Ambient-Musik | Animiertes GIF (stumm) |
|---|---|---|---|
| Orionnebel · M42 | [orion.jpg](orion.jpg) | [orion_demo.mp4](orion_demo.mp4) | [orion_preview.gif](orion_preview.gif) |
| Plejaden · M45 | [pleiades.jpg](pleiades.jpg) | [pleiades_demo.mp4](pleiades_demo.mp4) | [pleiades_preview.gif](pleiades_preview.gif) |

Die beiden aktualisierten Demos laufen 30 Sekunden in 720 × 1280 bei 30 FPS.
Ein lokaler OpenCV-Algorithmus trennt kompakte Sternkerne näherungsweise für
eine **künstlerische** unabhängige Animation. Dies ist keine vollständige
Sternentfernung und kein wissenschaftliches Verfahren. Weder eine StarNet-CLI
noch StarNet-Modellgewichte wurden für diese Demo-Videos verwendet.
Die Bilder und diese vier OpenCV-Demo-Medien sind zur Verwendung freigegeben.

Neu rendern (einschließlich neu erzeugter Musik und GIF-Vorschauen):

```bash
python scripts/render_photo_demo.py --overwrite
```

Optionen: `--only orion` / `--only pleiades`, `--duration 45` sowie
`--seed 1234` für eine wiederholbare Musik-Variante. Ohne Seed wird bei
jedem Lauf eine neue verwandte Ambient-Komposition erzeugt. Die Renderberichte
und temporären WAVs werden lokal im ignorierten `*_assets`-Ordner abgelegt.

## Persönliche StarNet2-Videos (nicht die öffentlichen Demo-Vorschauen)

Die ebenfalls archivierten
[Orion-StarNet2-MP4](orion_starnet_demo.mp4),
[Plejaden-StarNet2-MP4](pleiades_starnet_demo.mp4)
sowie die
[Orion-StarNet2-GIF](orion_starnet_preview.gif) und
[Plejaden-StarNet2-GIF](pleiades_starnet_preview.gif)
wurden mit einer **separat installierten StarNet2-CLI** erstellt.
Diese älteren Versionen wurden nicht neu gerendert und können sichtbare
Farbringe an hellen Sternen enthalten.

**Lizenz:** Die StarNet2-Ausgaben sind nicht durch AstroMotions MIT-Lizenz
freigegeben. Ihre Nutzung als Software-Produktassets kann nach der separaten
StarNet2-Lizenz eingeschränkt sein. Für entsprechende Veröffentlichungen
ist eine schriftliche Erlaubnis des Rechteinhabers die sichere Lösung.
Siehe [Drittanbieterhinweise](../../THIRD_PARTY_NOTICES.md).
