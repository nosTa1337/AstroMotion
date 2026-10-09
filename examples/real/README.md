# Eigene Astrofotos und Demo-Medien

**Seestar S50 Pro + AstroWizard** · Originalaufnahmen von Philipp / nosTa1337.
Die eigenen Originalfotos dürfen verwendet werden; eine Quellenangabe ist willkommen
(z. B. „Seestar S50 Pro, Aufnahme: nosTa1337, Bearbeitung: AstroWizard“).

## Im Repository vorhandene Bilder und OpenCV-Demos

| Objekt | Originalfoto | Bisheriges MP4 mit Ton | Bisherige GIF-Vorschau |
|---|---|---|---|
| Orionnebel · M42 | [orion.jpg](orion.jpg) | [orion_demo.mp4](orion_demo.mp4) | [orion_preview.gif](orion_preview.gif) |
| Plejaden · M45 | [pleiades.jpg](pleiades.jpg) | [pleiades_demo.mp4](pleiades_demo.mp4) | [pleiades_preview.gif](pleiades_preview.gif) |

**Wichtig:** Die hier bereits eingecheckten Demovideos/GIFs verwenden die
künstlerische OpenCV-Sternabschätzung, **nicht StarNet2**. Sie sind lediglich
historische Technikbeispiele und zeigen unabhängige Sternbewegung mit
künstlich zugewiesener Tiefe.

## Bessere StarNet2-Beispiele manuell rendern

Der empfohlene lokale Weg nutzt echte StarNet2-Sterntrennung, die separat
installierte offizielle CLI oder eine passende vorliegende Starless-Datei.
Die Einzelbilder bleiben unverändert. Mit dem Skript:

```bash
python scripts/render_starnet_examples.py --starnet "/path/to/starnet2" --overwrite
```

Alternative für bereits getrennte Originale:

```bash
python scripts/render_starnet_examples.py --starless-dir "/path/to/starless" --overwrite
```

Es entstehen pro Objekt ein 30-Sekunden-MP4 mit H.264/AAC und eigener,
zufällig generierter Ambient-Musik sowie eine tonlose GIF-Vorschau:

- `orion_starnet_demo.mp4`, `orion_starnet_preview.gif`
- `pleiades_starnet_demo.mp4`, `pleiades_starnet_preview.gif`

Die Dateien müssen **normal mit Git** eingecheckt werden, falls eine
Veröffentlichung gewünscht ist. Es werden keine GitHub Actions verwendet.

Der ursprüngliche StarNet2-Testlauf vom 09.10.2026 hat zwei 1080p-Videos
mit GIF-Vorschauen erzeugt. Die Medien sind nicht mit den alten,
bereits eingecheckten OpenCV-Dateien zu verwechseln.

**Lizenz:** Die Bilder und AstroMotion-Code/Musik behalten ihre jeweiligen
Rechte; die StarNet2-CLI und ihre Modelle werden nicht mitgeliefert.
StarNet2-Ausgaben können zusätzlichen Nutzungseinschränkungen unterliegen,
insbesondere als Software-Produktassets. Vor einer Veröffentlichung dieser
Vorschauen als Produktdemos die Rechte prüfen; siehe
[THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md).
