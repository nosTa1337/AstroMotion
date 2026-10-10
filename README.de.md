<p align="center"><img src="assets/astromotion-logo.png" alt="AstroMotion" width="320"></p>

[English](README.md) · **Deutsch**

# AstroMotion

**Aus deinem Astrofoto wird ein ruhiger Flug durch die Sterne.** StarNet2 trennt Sterne und Nebel. Sterne aus der Aufnahme bewegen sich mit individueller Tiefe vor dem sanft bewegten Hintergrund. Das empfohlene Setup erzeugt ein **30-Sekunden-Video mit Perfect Loop und zufälliger Ambient-Musik**. Bewegung, Format, Länge und Musik lassen sich konfigurieren.

## TL;DR – unter Windows starten

1. **Python 3.11+** (empfohlen: 3.12), **FFmpeg mit FFprobe** und die offizielle [StarNet2-CLI](https://starnetastro.com/cli-tools/starnet/) installieren. FFmpeg und FFprobe müssen im PATH liegen.
2. Repository klonen oder vollständig entpacken und **`setup.bat`** starten. Es erstellt oder verwendet `.venv` und installiert alle Pakete.
3. Im Repository-Ordner ausführen:

```powershell
.\.venv\Scripts\python.exe main.py --input examples\real\pleiades.jpg --starnet "C:\Program Files\StarNet2\bin\starnet2.exe" --config configs\immersive_loop.yaml --output Plejaden_video.mp4
```

Für dein eigenes Foto den Pfad hinter `--input` ersetzen.

## Geführter Start ohne lange Befehle

Unter Windows **`start_wizard.bat`** doppelklicken oder ein Bild darauf ziehen. Alternativ:

```powershell
.\.venv\Scripts\python.exe wizard.py
```

Beim ersten Start fragt das Skript nach der **StarNet2-EXE**, dem **Bilderordner**, dem **Videoordner** und **FFmpeg/FFprobe**. Danach reicht der Bildname aus dem gespeicherten Ordner oder ein vollständiger Bildpfad.

Pro Video wählst du Länge, FPS, Auflösung, Format, Perfect Loop, Titel, Untertitel und Musik. **Enter übernimmt die Vorgabe**; die Videoeinstellungen werden für den nächsten Start gespeichert. Titel und Untertitel bleiben an das jeweilige Bild gebunden und werden jedes Mal neu abgefragt. `-` leert ein optionales Feld. Ambient-Musik bleibt mit `zufall` bei jedem Render neu.

Ein optionales Menü bietet Hintergrundzoom, Drehung, seitliche Sternbewegung, Sternanzahl, Helligkeit, Loop-Tempo, Lautstärke und Textgröße. Vor dem Rendern zeigt das Skript die Auswahl und fragt nach dem Start. Vorhandene Videos werden nur nach ausdrücklicher Bestätigung ersetzt.

Pfade neu einrichten: `start_wizard.bat --setup`. Einstellungen prüfen, ohne ein Video zu rendern: `start_wizard.bat --dry-run`. Linux/macOS: `python wizard.py` in der aktivierten Projektumgebung.

Die lokalen Einstellungen liegen in `.astromotion-wizard.json` und werden von Git ignoriert. Das Skript nutzt dieselbe StarNet2-Pipeline und denselben Python-Interpreter wie der Startbefehl.

## Demos

**Seestar S50 Pro + AstroWizard**, eigene Aufnahmen von mir. Die enthaltenen Fotos und Demo-Medien dürfen verwendet werden.

| Orionnebel · M42 | Plejaden · M45 |
|---|---|
| [![Orion](examples/real/orion_starnet_preview.gif)](examples/real/orion_starnet_demo.mp4) | [![Plejaden](examples/real/pleiades_starnet_preview.gif)](examples/real/pleiades_starnet_demo.mp4) |
| [Originalfoto](examples/real/orion.jpg) · [Video mit Musik](examples/real/orion_starnet_demo.mp4) | [Originalfoto](examples/real/pleiades.jpg) · [Video mit Musik](examples/real/pleiades_starnet_demo.mp4) |

Jeweils 30 Sekunden, 1080 × 1920, 30 FPS, H.264/AAC. Die GIFs sind stumme Vorschauen mit reduzierter Farbpalette; für Bildqualität und Musik die MP4s öffnen.

## Einrichtung

### Windows

`setup.bat` verwendet denselben Interpreter wie `start_windows.bat`: **`.venv\Scripts\python.exe`**. Eine vorhandene Projektumgebung wird wiederverwendet. Das Setup installiert `requirements.txt`, prüft die Paketimporte und bricht bei Fehlern mit einer verständlichen Meldung ab. `setup_windows.bat` bleibt als alternativer Dateiname verfügbar.

Manuell installieren: Bei vorhandener `.venv` die erste Zeile auslassen.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Falls PowerShell die Aktivierung blockiert, direkt mit dem Projektinterpreter installieren und auch AstroMotion damit starten:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Linux / macOS

Python 3.11+, `venv`, FFmpeg/FFprobe und das passende offizielle StarNet2-CLI-Paket installieren.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py --input examples/real/pleiades.jpg --starnet "/pfad/zu/starnet2" --config configs/immersive_loop.yaml --output Plejaden_video.mp4
```

Falls nötig, die StarNet2-Datei mit `chmod +x /pfad/zu/starnet2` ausführbar machen.

## Dein Video anpassen

Verwende **[`configs/immersive_loop.yaml`](configs/immersive_loop.yaml)** als Ausgangspunkt. Dieses Setup entspricht dem Haupteffekt der Demos: individueller Sternflug, ruhiger Hintergrund und Loop, ohne zusätzliche Bildeffekte.

Die folgenden Optionen an den Startbefehl anhängen:

| Wunsch | Option |
|---|---|
| Längeres, langsameres Loop-Video | `--duration 45` |
| Querformat / quadratisch | `--format landscape` / `--format square` |
| Auflösung | `--resolution 720p`, `1080p` oder `4k` |
| Bildrate | `--fps 24`, `30` oder `60` |
| Dezentere Sternfarben | `--star-color-strength 0.6` |
| Dieselbe Musikvariante wiederholen | `--seed 1234` |
| Eigene Musik / stumm | `--audio "musik.wav"` / `--music none` |
| Objektname einblenden | `--title "Plejaden"` |
| Zweite Textzeile ergänzen | `--subtitle "MESSIER 45"` |
| Loop ausschalten | `--no-loop` |
| Bestehende Ausgabedatei ersetzen | `--overwrite` |

**Optionale Texteinblendung:** `--title` aktiviert die Beschriftung, `--subtitle` ergänzt eine zweite Zeile. Zum Beispiel an den Startbefehl anhängen:

```powershell
--title "Plejaden" --subtitle "MESSIER 45"
```

Ohne diese Optionen bleibt die Texteinblendung im empfohlenen Setup deaktiviert.

**Tempo im Loop:** Bei gleicher Konfiguration verteilt sich die Bewegung auf die Videolänge. 45 Sekunden wirken langsamer als 30 Sekunden; ein 2-Sekunden-Test komprimiert den gesamten Flug. `--speed` steuert die Hintergrundbewegung und ist kein allgemeiner Tempo-Regler für den Sternflug.

Für eigene Bewegungseinstellungen eine Kopie anlegen:

```powershell
Copy-Item configs\immersive_loop.yaml meine_config.yaml
```

Die Werte in `meine_config.yaml` bearbeiten und im Startbefehl **`--config meine_config.yaml`** verwenden:

| Einstellung | Wert im empfohlenen Setup | Wirkung |
|---|---|---|
| `motion.zoom` | `0.14` | Hintergrundzoom um bis zu 14 %; kleiner = ruhiger, `0` = kein Zoom |
| `motion.rotation_deg` | `2.0` | Drehbereich des Hintergrunds in Grad; `0` = keine Drehung |
| `starfield.drift_x` / `drift_y` | `0.12` / `-0.035` | Seitliche Bewegung des Sternflugs; kleinere Beträge = weniger Drift |
| `starfield.rotation_deg` | `4.75` | Drehbereich des Sternflugs in Grad; `0` = keine Drehung |
| `starfield.count` | `4500` | Obergrenze der animierten, tatsächlich erkannten Sterne |
| `starfield.color_strength` | `0.6` | Farbstärke fliegender Sterne: `0` = neutral, `1` = volle Farbe |
| `starfield.foreground_gain` | `1.15` | Helligkeit der fliegenden Sterne |
| `starfield.seed` | `2026` | Wiederholbare künstlerische Tiefenverteilung der Sterne |
| `audio.gain` | `0.7` | Lautstärke |
| `audio.seed` | `null` | Neue Ambient-Musik pro Rendering; eine Ganzzahl wiederholt die Variante |

Die Farben der fliegenden Sterne stammen aus dem StarNet2-Residuum. Stark gefärbte Reste können beim Vergrößern übertrieben wirken; deshalb beträgt ihre Farbstärke standardmäßig `0.6`. Die Anpassung erhält Helligkeit, Sternprofile und Bewegung und verändert keine Hintergrundfarben. Kleinere Werte ergeben neutralere Sterne; `1` entspricht der bisherigen vollen Farbstärke. Im Wizard liegt die Einstellung im optionalen Menü.

Der Sternflug verwendet künstlerisch zugewiesene Tiefen, keine gemessenen astronomischen Entfernungen. Im Perfect Loop fliegen die Sterne vorwärts, während der Hintergrund sanft vor und zurück fährt. Die Musik wird am Übergang überblendet. Im Abschnitt `loop` lässt sich zusätzlich `star_cycles: 1` setzen: `2` bedeutet zwei vollständige Sterndurchläufe pro Video und damit mehr Tempo. Für einen ruhigen Flug bei `1` bleiben. `starfield.travel` beeinflusst den Flug nur bei ausgeschaltetem Loop.

CLI-Optionen überschreiben die Konfigurationsdatei. Relative Dateipfade innerhalb einer Konfiguration beziehen sich auf deren Ordner. `--print-config` zeigt die effektiven Einstellungen, ohne zu rendern.

## Fotos und Sterntrennung

Als Eingabe ein fertig gestrecktes RGB-Astrofoto verwenden, etwa JPG, PNG oder TIFF. AstroMotion nutzt ausschließlich **echte StarNet2-Trennung**. Ein bereits mit StarNet2 erzeugtes Starless-Bild kann die erneute Trennung ersetzen:

```powershell
.\.venv\Scripts\python.exe main.py --input foto.tif --starless foto_starless.tif --config configs\immersive_loop.yaml --output video.mp4
```

Original und Starless müssen dieselbe Größe und Ausrichtung haben und aus derselben Bearbeitung stammen. Die Qualität der StarNet2-Ausgabe bleibt maßgeblich. Die Trennung verwendet keine nachträglichen Lochreparaturen oder Umverteilung von Sternfarben in den Nebel.

## Fehler und Entwicklung

- **`ModuleNotFoundError`, etwa für `tifffile`:** `setup.bat` erneut ausführen und mit `.venv\Scripts\python.exe` starten.
- **FFmpeg fehlt:** `ffmpeg -version` und `ffprobe -version` prüfen; beide Programme müssen erreichbar sein.
- **StarNet2 startet nicht:** EXE-Pfad und Vollständigkeit des StarNet2-Pakets prüfen. Ältere CLI-Pakete mit Positionsargumenten unterstützen `--starnet-mode legacy`.

Protokolle, Ebenenbilder und Renderbericht liegen neben dem Video unter `<video>_assets/`.

Für die Entwicklung zunächst den kleinen [StarNet2-Demotest](examples/real/README.md) verwenden. Der [Actions-Workflow](.github/workflows/starnet-demos.yml) startet manuell standardmäßig einen 2-Sekunden-M45-Test; vollständige Demos werden ausdrücklich über `gallery` gewählt. Tests ohne Videorendering:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q -m "not video_render"
```

Die Fehleranalyse und frühere Prüfungen stehen im [Pipeline-Bericht](CLEAN_PIPELINE_REPORT.md).

## Lizenzen

AstroMotion: [MIT](LICENSE). Externe Komponenten: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). StarNet2 und Modellgewichte werden separat bezogen und lizenziert. Die Ambient-Musik wird lokal synthetisiert, ohne Samples fremder Aufnahmen.
