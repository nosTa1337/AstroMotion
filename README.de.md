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

Am Anfang wählst du die **Sprache: English (`en`) oder Deutsch (`de`)**. Beim ersten Start ist Englisch die Vorgabe; deine Auswahl wird gespeichert und beim nächsten Start wieder angeboten. Direkt ohne Sprachfrage starten: `start_wizard.bat --language de` oder `start_wizard.bat --language en`. Linux/macOS: `python wizard.py --language de` beziehungsweise `--language en`.

Beim ersten Start fragt das Skript nach der **StarNet2-EXE**, dem **Bilderordner**, dem **Videoordner** und **FFmpeg/FFprobe**. Danach reicht der Bildname aus dem gespeicherten Ordner oder ein vollständiger Bildpfad. Bereits gespeicherte Pfade und Videoeinstellungen bleiben beim Sprachwechsel erhalten.

Pro Video wählst du Sternflug-Profil, Länge, FPS, Auflösung, Format, Perfect Loop, Titel, Untertitel und Musikstil. **Enter übernimmt die Vorgabe**; die Videoeinstellungen werden für den nächsten Start gespeichert. Titel und Untertitel bleiben an das jeweilige Bild gebunden und werden jedes Mal neu abgefragt. `-` leert ein optionales Feld. Musikstil `random` und Seed `zufall` (`random` auf Englisch) erzeugen neue Arrangements. Ja/Nein-Abfragen zeigen auf Deutsch `j/n`, auf Englisch `y/n`; beide Schreibweisen funktionieren. Profilnamen, Musikstile und Konfigurationswerte bleiben in beiden Sprachen gleich.

Ein optionales Menü bietet Hintergrundzoom, Drehung, seitliche Sternbewegung, Sternanzahl, Helligkeit, Loop-Tempo, Lautstärke und Textgröße. Vor dem Rendern zeigt das Skript die Auswahl und fragt nach dem Start. Vorhandene Videos werden nur nach ausdrücklicher Bestätigung ersetzt.

Wähle **`preview`** als Ausgabe für eine **360p-Vorschau mit gleicher Dauer, FPS, Loop und Animationseinstellungen** wie das volle Video (vertikal 360 × 640). Der Dateiname bekommt den Zusatz `_preview`. Danach bietet der Wizard das volle Video mit derselben zufälligen Bewegungsvariante und demselben Musikarrangement an. Die gespeicherte Auflösung für das volle Video bleibt erhalten. StarNet2 läuft einmal; der volle Export übernimmt die geprüfte Ausgabe in Arbeitsgröße aus dem `_assets`-Ordner der Vorschau.

Wenn du den vollen Export ablehnst, öffnet **Anpassungen vornehmen?** den Wizard erneut für dasselbe Foto. Alle Vorschau-Werte sind vorbelegt, einschließlich Titel, Untertitel, Dateiname und der aufgelösten Bewegungs-/Musik-Seeds. Werte ändern und erneut eine Vorschau rendern; Enter behält den aktuellen Wert, `-` löscht optionalen Text. Der geprüfte StarNet2-Cache wird auch bei einem neuen Dateinamen verwendet. Nach jeder Vorschau kannst du voll exportieren oder erneut anpassen.

Diesen Ordner behalten, damit die Trennung auch bei einem späteren vollen Export mit demselben Videodateinamen wiederverwendet wird. Der Cache prüft Ausgangsfoto, Arbeitspixel/-größe, StarNet2-Einstellungen, EXE/Modelldateien und die Prüfsumme der Ausgabe. Bei fehlendem, geändertem oder beschädigtem Cache wird mit echtem StarNet2 neu getrennt. Wiederholte Renders können auch ihren eigenen `_assets`-Cache nutzen. `render_report.json` dokumentiert die Wiederverwendung. Bei getrennten CLI-Exports `--starnet-cache "photo_preview_assets"` ergänzen und die StarNet2-EXE weiterhin konfigurieren; `--starless` bleibt für extern getrennte Bilder in Originalgröße.

Der Wizard speichert die **fünf letzten unterschiedlichen, fertig eingegebenen Entwürfe**, neueste zuerst. Alle konfigurierten Werte bleiben erhalten, einschließlich individuellem Zoom, Hintergrund-/Sterndrehung, Kameraverlauf, Sternhelligkeit/-farbe, Loop- und Musikeinstellungen. Gespeichert wird vor der Frage nach dem Renderstart: Auch bei einem abgelehnten Start, Dry Run oder Renderfehler bleiben die Werte erhalten. Zoom und Drehung erscheinen in der Vorlagenliste und Renderübersicht. Nach der Bildauswahl eine Vorlage oder `0` für aktuelle Vorgaben wählen; Enter behält den jeweiligen Wert, ein anderes eingebautes Sternflugprofil übernimmt dessen Vorgaben. Erneutes Verwenden schiebt einen Entwurf nach oben. Titel und Untertitel werden für jedes Foto neu eingegeben; Pfade stammen aus deiner aktuellen Einrichtung. Ein Abbruch vor Abschluss der Eingaben speichert keinen unvollständigen Entwurf.

Für dauerhafte Profile im Vorlagenmenü **`speichern`** eingeben, einen der letzten Entwürfe auswählen und einen **Profilnamen** vergeben. Die benannten Profile bleiben unabhängig von den fünf letzten Entwürfen erhalten und lassen sich über ihre angezeigte Nummer auswählen. Vorhandene Namen werden nur nach Bestätigung ersetzt. Bei generierter Ambient-Musik fragt der Wizard **`random` oder `exact`**: `random` erzeugt jedes Mal einen neuen Musik-Seed innerhalb des gewählten Stils (Stil `random` variiert zusätzlich den Stil); `exact` speichert den tatsächlich gewählten Musikstil/-Seed und den Bewegungs-Seed für dieselbe Musik und Bewegungsvariante. Neue Entwürfe erfassen diese Seeds bereits vor dem Rendering. Ältere Entwürfe ohne gespeicherte Seeds benötigen für eine exakte Kopie eine neue Vorschau. Benannte Profile können nach der Auswahl angepasst werden und bleiben beim Neueinrichten der Pfade erhalten.

Direkt eine Vorschau starten: `start_wizard.bat --preview` oder `python wizard.py --preview`. `--no-preview` überspringt die Ausgabeauswahl und rendert in der gewählten vollen Auflösung. Auch `main.py --preview` behält jetzt die volle Dauer und FPS bei. Für gleiche Zufallsvarianten bei getrennten CLI-Starts denselben `--profile-seed` und Musik-`--seed` verwenden.

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
| Sternflug-Profil | `--profile relax`, `drift` oder `explore` |
| Ambient-Stil | `--music-style random`, `warm`, `deep`, `shimmer`, `pulse` oder `classic` |
| Längeres, langsameres Loop-Video | `--duration 45` |
| Gleichmäßigerer Hintergrundzoom und Drehverlauf | `--camera-timing steady` |
| Durchgehend vorwärts laufende Kamera | `--camera-timing steady --no-loop` |
| Querformat / quadratisch | `--format landscape` / `--format square` |
| Auflösung | `--resolution 360p`, `720p`, `1080p` oder `4k` |
| 360p-Vorschau mit voller Dauer und FPS | `--preview` |
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

### Sternflug-Profile

Alle drei Profile beginnen mit **30 Sekunden, vertikalem 1080p, 30 FPS, individuellen Sternen aus dem Foto, Perfect Loop und Ambient-Musik**. Sie behalten natürliche Farben bei und ergänzen keine Bildeffekte.

| Profil | Wirkung |
|---|---|
| `relax` | Sehr ruhiger Hintergrund, weniger fliegende Sterne und wenig seitliche Bewegung |
| `drift` | Deutlicherer seitlicher Sternflug mit sanfter Drehung |
| `explore` | Engerer Ausschnitt, mehr Sterne und stärkere Annäherung des Hintergrunds |

Zum Beispiel **`--profile drift --music-style shimmer`** an den Startbefehl anhängen. Im Wizard das Profil vor den Videoeinstellungen wählen; `custom` behält die eigenen Vorgaben. Ein Profilwechsel lädt dessen Standardwerte; beim Beibehalten des gespeicherten Profils bleiben eigene Anpassungen erhalten. Dauer, FPS, Format und andere CLI-Optionen können Profilvorgaben weiterhin überschreiben.

Die Profile variieren Richtung, Drehung, Zoom und Sternanzahl in kleinen Grenzen. `--profile-seed 123` wiederholt die Variation; `--no-profile-variation` verwendet feste Profilwerte. Der Musik-Seed ist unabhängig davon. Ein Profil in der Konfigurationsdatei liefert Vorgaben für diese Datei; ein ausdrücklich gewähltes CLI-Profil überschreibt die Datei vor einzelnen CLI-Optionen.

### Ambient-Musikstile

| Stil | Klang |
|---|---|
| `warm` | Weiche Dur-/Moll-Flächen, sanfter Bass und kurze Melodiephrasen |
| `deep` | Tiefe Drone-Akkorde mit leisen Antworttönen über der dunkleren Tonlage |
| `shimmer` | Helle, luftige Flächen und wechselnde, weiche Glockenmotive |
| `pulse` | Runde Synthesizer-Töne mit sanft variiertem Arpeggio und kleinen Pausen |

`random` ist die Vorgabe: Pro Rendering werden Stil, Tonart, Akkordreihenfolge, Timing und Klangdetails neu gewählt. Ein fester Stil behält seinen Charakter; `--seed 1234` wiederholt das Arrangement. `classic` erhält den bisherigen Synth samt `audio.harmony` / `audio.accents`; `audio.transpose` gilt für alle Stile. Die Musik entsteht lokal ohne aufgenommene Samples. Die bestehende Loop-Überblendung bleibt aktiv.

Die vier Stile entwickeln sich auch innerhalb eines Clips: Akkordstimmen und Klangfarbe bewegen sich langsam, warm/deep ergänzen zusammenhängende Melodiephrasen, shimmer/pulse variieren Motive und Betonung. **`--music-development 0.65`** oder `audio.development` steuert die Stärke (`0..1`): `0` erhält das bisherige gleichmäßige Arrangement, `0.65` ist die Vorgabe und `1` bringt stärkere Entwicklung. Der Wizard bietet den Regler im optionalen Menü an. `classic` und eigene Musikdateien behalten ihr bisheriges Verhalten. Zufalls-Seeds und Loop-Überblendung bleiben reproduzierbar.

Vor dem Videorendering probehören (ohne StarNet oder FFmpeg):

```powershell
python -m astromotion.music --style shimmer --seed 1234 --duration 12 --output shimmer_preview.wav
```

Mit `--development 0.8` beim reinen Musikbefehl lässt sich eine stärkere Variation vor dem Videorendering probehören.

Render-Protokoll und `render_report.json` enthalten den tatsächlichen Profil-Seed und den gewählten Musikstil samt Seed. `--print-config` zeigt die eingestellten Werte vor dem Auflösen der Zufallswerte.

**Tempo im Loop:** Bei gleicher Konfiguration verteilt sich die Bewegung auf die Videolänge. 45 Sekunden wirken langsamer als 30 Sekunden; ein 2-Sekunden-Test komprimiert den gesamten Flug. `--speed` steuert die Hintergrundbewegung und ist kein allgemeiner Tempo-Regler für den Sternflug.

Für eigene Bewegungseinstellungen eine Kopie anlegen:

```powershell
Copy-Item configs\immersive_loop.yaml meine_config.yaml
```

Die Werte in `meine_config.yaml` bearbeiten und im Startbefehl **`--config meine_config.yaml`** verwenden:

| Einstellung | Wert im empfohlenen Setup | Wirkung |
|---|---|---|
| `motion.timing` | `smooth` | `steady` für gleichmäßige Kamerafahrt; `smooth` behält langsames Anfahren/Abbremsen |
| `motion.zoom` | `0.14` | Animierter Hintergrundzoom: `0..1`; bei Speed `1` bedeutet `0.14` +14 %, `1.0` +100 % (2×), `0` = kein Zoom |
| `motion.rotation_deg` | `2.0` | Zielwinkel des Hintergrunds ab der Originalausrichtung bei Speed `1`; `-360..360`, `0` = keine Drehung |
| `starfield.drift_x` / `drift_y` | `0.12` / `-0.035` | Seitliche Bewegung des Sternflugs; kleinere Beträge = weniger Drift |
| `starfield.rotation_deg` | `4.75` | Drehbereich des Sternflugs in Grad; `-360..360`, `0` = keine Drehung |
| `starfield.count` | `4500` | Obergrenze der animierten, tatsächlich erkannten Sterne |
| `starfield.color_strength` | `0.6` | Farbstärke fliegender Sterne: `0` = neutral, `1` = volle Farbe |
| `starfield.foreground_gain` | `1.15` | Helligkeit der fliegenden Sterne |
| `starfield.seed` | `2026` | Wiederholbare künstlerische Tiefenverteilung der Sterne |
| `audio.gain` | `0.7` | Lautstärke |
| `audio.style` | `random` | Instrumentierung und Arrangement der Ambient-Musik |
| `audio.seed` | `null` | Neue Ambient-Musik pro Rendering; eine Ganzzahl wiederholt die Variante |

Die Farben der fliegenden Sterne stammen aus dem StarNet2-Residuum. Stark gefärbte Reste können beim Vergrößern übertrieben wirken; deshalb beträgt ihre Farbstärke standardmäßig `0.6`. Die Anpassung erhält Helligkeit, Sternprofile und Bewegung und verändert keine Hintergrundfarben. Kleinere Werte ergeben neutralere Sterne; `1` entspricht der bisherigen vollen Farbstärke. Im Wizard liegt die Einstellung im optionalen Menü.

Der Sternflug verwendet künstlerisch zugewiesene Tiefen, keine gemessenen astronomischen Entfernungen. Im Perfect Loop fliegen die Sterne vorwärts, während der Hintergrund sanft vor und zurück fährt. Die Musik wird am Übergang überblendet. Im Abschnitt `loop` lässt sich zusätzlich `star_cycles: 1` setzen: `2` bedeutet zwei vollständige Sterndurchläufe pro Video und damit mehr Tempo. Für einen ruhigen Flug bei `1` bleiben. `starfield.travel` beeinflusst den Flug nur bei ausgeschaltetem Loop.

Für kurze Clips im optionalen Wizard-Menü **Kameraverlauf: `steady`** wählen. Damit entfallen die langen Beschleunigungs- und Bremsphasen: Im Loop läuft die Kamera während 90 % der Zeit gleichmäßig, mit kurzen weichen Richtungswechseln (bei 10 Sekunden jeweils 0,25 Sekunden auf jeder Seite des Umkehrpunkts). Der Hintergrund fährt weiterhin vor und zurück, damit der Loop schließt. Für durchgehend vorwärts laufenden Zoom Perfect Loop ausschalten und `steady` verwenden; Anfang und Ende des Videos unterscheiden sich dann. Die einzelnen Sterne behalten im Loop ihre vorwärts laufende Tiefenbewegung. Größere Drehwerte schneiden mehr vom Foto ab, damit keine freien Bildränder entstehen; negative Werte kehren die Richtung um. Mit 10–20° Drehbereich beginnen und `motion.zoom` reduzieren, falls ein 10-Sekunden-Clip weiterhin zu schnell wirkt.

Die Hintergrunddrehung startet bei **0°: der Originalausrichtung des Fotos**. Bei Speed `1` dreht der Wert `40` von `0°` auf `40°`; im Perfect Loop anschließend wieder auf `0°` zurück. Negative Werte kehren die Richtung um. Der erste Frame ist nicht mehr um den halben eingestellten Winkel vorgedreht.

Jedes Video beginnt mit **100 % des sichtbaren Fotos**, zentriert und in Originalausrichtung, unabhängig von Zoom, Drehung, Fokus, Versatz oder Overscan. Die Proportionen bleiben erhalten; bei anderem Videoformat entstehen anfangs schwarze Ränder. Sobald sich die Kamera bewegt, zoomt sie automatisch zu einem sicheren Zielausschnitt für Drehung und Versatz. `motion.zoom` vergrößert diesen Zielausschnitt zusätzlich. Während der Annäherung können kurz freie schwarze Bereiche sichtbar bleiben, bis der Ausschnitt das Video ausfüllt, auch bei `motion.zoom: 0`. Fokus und Versatz setzen ebenfalls erst ab dem zentrierten Start ein. Perfect Loop kehrt zum gleichen vollständigen Startbild zurück. Bei Speed `0` oder vollständig deaktivierter Kamerabewegung bleibt das ganze Foto unverändert stehen.

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
