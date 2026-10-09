<p align="center"><img src="assets/astromotion-logo.png" alt="AstroMotion" width="320"></p>

# AstroMotion

AstroMotion erstellt **Videos mit individuellem Sternflug aus echten Astrofotos**: StarNet2 trennt die Sterne vom Nebel; erkannte Sterne bewegen sich anschließend mit eigener perspektivischer Projektion vor dem ruhigen Nebelhintergrund. Dazu gibt es frei wählbare Videolängen, nahtlose Loops und lokal erzeugte, zufällige Ambient-Musik.

## TL;DR

1. Python 3.11+ (empfohlen: 3.12), FFmpeg/FFprobe und die separat angebotene [StarNet2-CLI](https://starnetastro.com/cli-tools/starnet/) installieren.
2. Unter Windows `setup_windows.bat` starten. Das installiert **alle Pakete aus requirements.txt, einschließlich tifffile**, in `.venv`.
3. Mit genau diesem Python starten und bei `--starnet` den **vollständigen Pfad zur EXE**, nicht zum Ordner, angeben:

```powershell
.\.venv\Scripts\python.exe main.py --input examples\real\pleiades.jpg --starnet "C:\Program Files\StarNet2\bin\starnet2.exe" --config configs\immersive_loop.yaml --duration 30 --output Plejaden_video.mp4
```

Alternativ: `start_windows.bat --input ...` nutzt ebenfalls `.venv`.
`--duration 45` ändert die Länge, `--seed 1234` wiederholt eine Musikvariante,
`--overwrite` ersetzt ein bestehendes Video. Ohne Seed entsteht neue Musik.

## Saubere Pipeline

Die fehlerhafte `foreground_cleanup`-Umverteilung und nachträgliche Lochreparatur bleiben entfernt. `starfield.py` und `starprofiles.py` sind wieder eingebunden, damit einzelne Sterne sichtbar durch den Raum fliegen. Die bisherigen Sternprofile werden zunächst unverändert verwendet; ihre Farbqualität wird getrennt am kurzen Testvideo beurteilt. Zusätzliche Nahvorbeiflüge sind deaktiviert.

- Nur echte StarNet2-Trennung oder ein passendes, bereits mit StarNet2 erzeugtes Starless-Bild; kein OpenCV-Ersatz.
- Der Sternflug verwendet Positionen und Profile aus dem echten StarNet2-Residuum. Die künstlerische Tiefenverteilung verändert die projizierten Positionen; sie misst keine astronomischen Entfernungen.
- Hintergrund = kanalweises Minimum von Original und StarNet2-Ausgabe in linearem Licht. Diese Begrenzung ermöglicht eine nichtnegative, rekonstruierbare Sternebene; es ist kein Reparaturfilter.
- Alle mitgelieferten Presets sind farbneutral: kein Bloom, Glow, Vignette, Twinkle oder automatisches Grading. Manuell konfigurierte Effekte und Autofokus bleiben optional.
- `immersive_loop.yaml`: individueller Sternflug, 30 Sekunden, 1080p/30 FPS und zufällige Ambient-Musik. `clean_loop.yaml` bleibt als Alternative mit reiner Ebenenbewegung verfügbar.
- Perfect Loop: periodischer, vorwärts laufender Sternflug; der Nebelhintergrund fährt sanft vor und zurück. Die Musik wird am Übergang überblendet.

`immersive_loop.yaml` und `cinematic_intelligence.yaml` aktivieren wieder den Sternflug (`starfield.enabled: true`). `foreground_cleanup` bleibt ein ignoriertes Kompatibilitätsfeld und kann die fehlerhafte Umverteilung nicht wieder aktivieren.

Die Qualität der ursprünglichen StarNet2-Ausgabe bleibt maßgeblich. Bereits dort vorhandene Halos werden nicht künstlich wegretuschiert. Bei auffälligem Abdriften: `motion.star_zoom_extra` reduzieren, bei Bedarf auf `0` (gleiche Zoombewegung).

**Aktueller Prüfstand:** Der wiederhergestellte Sternflug wurde mit einem echten 2-Sekunden-M45-Video geprüft und vom Projektbetreiber visuell freigegeben. Der vollständige Loop ist im Kurztest entsprechend schneller. Die 30-Sekunden-Demos werden anschließend über GitHub Actions mit derselben Pipeline gerendert; spätere manuelle Prüfungen verwenden standardmäßig wieder den 2-Sekunden-Test.

Details zu Ursache, Git-History und Prüfung: [CLEAN_PIPELINE_REPORT.md](CLEAN_PIPELINE_REPORT.md).

## Eigene Aufnahmen und Demos

**Seestar S50 Pro + AstroWizard**, eigene Aufnahmen von Philipp / nosTa1337. Die Fotos dürfen verwendet werden; eine Quellenangabe ist willkommen.

| Orionnebel · M42 | Plejaden · M45 |
|---|---|
| [![Orion](examples/real/orion_starnet_preview.gif)](examples/real/orion_starnet_demo.mp4) | [![Plejaden](examples/real/pleiades_starnet_preview.gif)](examples/real/pleiades_starnet_demo.mp4) |
| [Original](examples/real/orion.jpg) · [MP4 mit Musik](examples/real/orion_starnet_demo.mp4) | [Original](examples/real/pleiades.jpg) · [MP4 mit Musik](examples/real/pleiades_starnet_demo.mp4) |

30 Sekunden, 1080 × 1920, 30 FPS, H.264/AAC. GIFs sind stumm und durch ihre Farbpalette nur Vorschauen; die MP4-Dateien sind für die Qualitätsbeurteilung maßgeblich.

## Einrichtung

### Windows

Repository klonen oder ZIP vollständig entpacken. Python mit Python Launcher installieren, dann `setup_windows.bat` ausführen. FFmpeg und FFprobe müssen im PATH liegen:

```powershell
ffmpeg -version
ffprobe -version
.\.venv\Scripts\python.exe -m pip check
```

Bei `ModuleNotFoundError` immer prüfen, ob du `.venv\Scripts\python.exe` statt einer anderen globalen Python-Installation verwendest. Zum erneuten Installieren:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Das vollständige StarNet2-Paket mit Bibliotheken und Modellgewichten zusammenlassen. Je nach Paket liegt die EXE direkt im Paketordner oder in `bin`. Für ältere CLI-Pakete mit positional arguments gibt es `--starnet-mode legacy`.

### Linux / macOS

Python 3.11+, `venv` und FFmpeg/FFprobe installieren (z. B. Ubuntu: `sudo apt install python3-venv ffmpeg`; macOS mit Homebrew: `brew install python ffmpeg`).

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py --input examples/real/pleiades.jpg --starnet "/pfad/zu/starnet2" --config configs/immersive_loop.yaml --output Plejaden_video.mp4
```

Passendes offizielles StarNet2-Paket für Betriebssystem und Architektur installieren. Falls nötig, dessen ausführbare Datei mit `chmod +x /pfad/zu/starnet2` freigeben. Der aktuelle Fix wurde unter Linux getestet; Windows und macOS wurden hier nicht ausgeführt.

## Bedienung

```bash
# Passendes, bereits mit StarNet2 erzeugtes Starless verwenden
python main.py --input foto.tif --starless foto_starless.tif --config configs/immersive_loop.yaml --output video.mp4

# Schnelle 3-Sekunden-Vorschau (720p, 24 FPS)
python main.py --input foto.jpg --starnet /pfad/zu/starnet2 --config configs/immersive_loop.yaml --preview

# Querformat, längeres Video, eigener Titel
python main.py --input foto.jpg --starless foto_starless.tif --config configs/immersive_loop.yaml --format landscape --duration 45 --title "Plejaden" --subtitle "MESSIER 45" --output m45.mp4

# Eigene Musik oder keine Musik
python main.py --input foto.jpg --starless foto_starless.tif --config configs/immersive_loop.yaml --audio musik.wav --output video.mp4
python main.py --input foto.jpg --starless foto_starless.tif --config configs/immersive_loop.yaml --music none --output stumm.mp4
```

Original und Starless müssen exakt dieselbe Ausrichtung und Größe haben. Keine separate Streckung oder Farbbearbeitung nach der Trennung. Verarbeitet werden fertig gestreckte RGB-Bilder. `--format`: vertical/square/landscape; `--resolution`: 720p/1080p/4k. `--loop` und `--no-loop` überschreiben das Preset. `--print-config` zeigt die effektiven Einstellungen.

Konfiguration: Defaults → Preset → YAML/JSON → CLI. Relative Pfade innerhalb einer Konfiguration beziehen sich auf deren Ordner. `start_windows.bat` mit Drag-and-drop nutzt `config.yaml`; dort den eigenen StarNet-Pfad hinterlegen.

## Demos prüfen und neu rendern

Zuerst echte Trennung und Standbilder prüfen, ohne Video zu erzeugen:

```bash
python scripts/render_starnet_examples.py --starnet /pfad/zu/starnet2 --check-only
```

Standardmäßig wird nur M45 geprüft. Die Ordner `test-renders/<objekt>_starnet_demo_assets` enthalten rohe StarNet-TIFFs, Log, `visual_review.jpg` und `separation_qa.json`. Vor einem neuen Demo-Export besonders die hellen blauen M45-Sterne bei den verschiedenen Kamerapositionen prüfen.

Nach erfolgreicher Sichtprüfung dieselben StarNet-Dateien wiederverwenden. `--reuse-starnet CACHE` erwartet Unterordner `orion/` und `pleiades/` mit jeweils `starnet_input.tif`, `starnet_starless.tif` und `starnet.log`. Das Skript vergleicht den gespeicherten Input pixelweise mit dem aktuellen Foto und protokolliert SHA-256-Prüfsummen. Alternativ neu mit `--starnet` trennen:

```bash
python scripts/render_starnet_examples.py --starnet /pfad/zu/starnet2 --duration 2 --only pleiades --no-gif --overwrite
```

Standard: 2 Sekunden, 720p, nur Plejaden, Ausgabe unter `test-renders/`. Die bestehende Galerie bleibt unverändert. Nach erfolgreicher Sichtprüfung vollständige Demos explizit mit `--only all --duration 30 --resolution 1080p --output-dir examples/real --overwrite` erzeugen. Optional: `--seed 1234`, `--no-gif`. Vor dem Encoding müssen die Rekonstruktions- und Hintergrundprüfungen bestehen. Diese technischen Checks ersetzen die Sichtprüfung nicht.

Der manuell gestartete [StarNet2-Workflow](.github/workflows/starnet-demos.yml) lädt das offizielle Modell, testet die Pipeline und stellt ausschließlich einen 2-Sekunden-Plejaden-Clip als Artefakt bereit. Er veröffentlicht nichts automatisch in der Galerie. Es gibt keine Ersatz-Sterntrennung.

## Tests und Diagnose

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests decken Rekonstruktion, blaue Sternkerne und Halos, deaktivierte Legacy-Filter, Kamerageometrie, Loop-Übergänge, zufällige/reproduzierbare Musik, CLI und echte FFmpeg-Exporte ab. Synthetische Testbilder prüfen interne Mathematik, nicht die Qualität des StarNet2-Modells.

Neben dem Export liegen unter `<video>_assets/` Ebenen-PNGs, Renderbericht, Logs und ggf. Ambient-WAV. Fehler überschreiben keine vorhandene MP4. Der `--starless`-Pfad setzt voraus, dass die angegebene Datei tatsächlich aus StarNet2 stammt; beliebige externe Dateien lassen sich nicht allein am TIFF-Format authentifizieren.

## Lizenzen

Siehe [LICENSE](LICENSE), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) und [Medienhinweise](examples/real/README.md). StarNet2 und seine Gewichte werden nicht mitgeliefert und separat lizenziert. Nach Mitteilung des Projektbetreibers liegt eine Freigabe für die StarNet2-basierten Demos vor. Ambient-Musik wird lokal synthetisiert, ohne Samples fremder Aufnahmen.
