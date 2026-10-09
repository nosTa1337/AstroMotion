# AstroMotion 1.1 – Testbericht

Ursprünglicher Test am 08.10.2026, Erweiterung am 09.10.2026.
Für den ursprünglichen Test war noch keine echte Astroaufnahme bereitgestellt.
Der Test nutzt ein reproduzierbar generiertes synthetisches Deep-Sky-Bild mit
bekannter Nebelebene (Seed 2026, 1440 × 1920, sRGB, 16-Bit-PNG und TIFF).

## Umgebung

- Linux, Python 3.12.14, isolierte virtuelle Umgebung.
- NumPy 2.2.6, OpenCV headless 4.12.0.88, Pillow 11.3.0,
  PyYAML 6.0.2, tifffile 2025.6.11.
- pytest 8.4.2.
- FFmpeg/FFprobe 6.1.1, libx264 verfügbar.
- Beim ursprünglichen synthetischen Demo-Test war StarNet nicht installiert.
  Ein späterer echter CLI-Lauf ist im Nachtrag unten beschrieben.
- Windows 11 und Batchdateien hier nicht ausführbar; auf Windows zu verifizieren.

## Automatisierte Tests

```text
python -m pytest -q
27 passed in 2.57s
```

Geprüft wurden:

- 16-Bit-PNG/TIFF mit erhaltenen Tonwerten, JPG-Decodierung, Unicode-Dateipfade,
  EXIF-Rotation und sRGB-ICC-Verarbeitung.
- Screen und additive Dekomposition: Rekonstruktion innerhalb Float-Rundung;
  ungültige Geometrie, schwarzes Starless und fehlende Sternebene werden abgelehnt.
- Getrennte Stern-/Nebeltransformationen, deaktivierte Parallax und Speed 0.
- Bildränder für alle drei Seitenverhältnisse, Fokus mittig/außermittig und
  extreme erlaubte Zoom-, Pan- und Rotationsparameter an 11 Zeitpunkten je Ebene.
- Konfigurationspriorität, relative Pfade, unbekannte Schlüssel und ungültige Werte.
- Effekte: endlich, auf 0..1 begrenzt, bei Deaktivierung Originalrekonstruktion.
- Ambient-Audio: deterministisch bei gleichem Seed, neue Ausgabe bei anderem Seed,
  Stereo, richtige Samplezahl, Fade-in/-out, keine PCM-Clippingwerte.
- StarNet-Prozessadapter: moderne/alte Argumentform, Arbeitsverzeichnis,
  16-Bit-TIFF-I/O und Ablehnung alter Ausgabedateien. Der externe Prozess wurde
  **nur im Adaptertest ersetzt**; dies prüft keine Sternentfernungsqualität.
- Echte gestreamte FFmpeg-Exporte mit keinem Audio, Ambient und eigener kurzer WAV
  (Wiederholung), Streamprüfung und vollständige Decodierung.
- Render-Abbruch: vorhandene Ausgabe bleibt erhalten, temporäre MP4 wird entfernt.

## Vollständiger Demo-Render

```bat
python main.py --input examples\deep_sky.png --starless examples\deep_sky_starless.png --preset cinematic --format vertical --resolution 1080p --duration 20 --fps 30 --music ambient --output examples\AstroMotion_Demo.mp4
```

| Prüfung | Ergebnis |
|---|---|
| Auflösung | 1080 × 1920, 9:16 |
| Videocodec | H.264 / libx264 |
| Pixelformat | yuv420p |
| Farbraum-Metadaten | BT.709 |
| Bildrate | 30/1 FPS |
| Videoframes | 600 |
| Video-/Containerdauer | 20,000000 s |
| Audiocodec | AAC |
| Audio | 48.000 Hz, Stereo |
| Audiodauer | 20,000000 s |
| Dateigröße | 3.336.244 Bytes |
| Gesamter Render | 233,8 s in dieser Entwicklungsumgebung |
| Rekonstruktionsfehler | max. ca. 5,96 × 10⁻⁸ in linearem RGB |
| Gesamte Datei decodiert | FFmpeg exit 0, keine Fehlerausgabe |

Zusätzliche Sichtprüfung: Frames 0, 300 und 599 als Kontaktbogen betrachtet;
keine schwarzen Randflächen oder offensichtlichen Layerlöcher. Die synthetische
Nebelebene enthält konstruktionsbedingt keine Fehler einer Sternenentfernung.
Farbwirkung entspricht dem Testbild mit den moderaten Preset-Effekten.

Eine Beispielposition in der Quelle (1100, 1000) hat im letzten Frame rund
(+24,6, −7,8) Pixel Sternbewegung **relativ zum Nebel**. Beide Ebenen werden somit
wirklich unabhängig animiert. Die Sterne sind als Vordergrund gewählt;
dies ist künstlerische 2,5D und keine astrophysikalisch gemessene Tiefenkarte.

Ambient-Quell-WAV: Peak ca. 0,139, RMS ca. 0,0287 relativ zu Full Scale;
kein Clipping, weiche Fades. Diese Messung ersetzt keine subjektive Hörbewertung.

## Zusätzliche Exports

| Preset | Format | Auflösung | FPS | Frames | Dauer | Ergebnis |
|---|---|---|---:|---:|---:|---|
| Epic | Square | 720 × 720 | 60 | 60 | 1,000 s | FFprobe-Prüfung bestanden |
| Calm | Landscape | 3840 × 2160 | 24 | 2 | 0,083333 s | FFprobe-Prüfung bestanden |

4K wurde als kurzer Funktionscheck exportiert. Das kleine Testfoto wird dabei
hochskaliert; das bestätigt keinen 4K-Detailgewinn und keinen langen 4K-Dauertest.

## Noch auf deinem Windows-Rechner prüfen

1. `setup_windows.bat` ausführen; FFmpeg/FFprobe im PATH prüfen.
2. `render_demo_windows.bat` ausführen, Video und Musik ansehen/anhören.
3. Offizielle StarNet-CLI separat installieren, Paketlizenz lesen und Pfad setzen.
4. Eigenes gestretchtes Seestar-RGB-Bild mit StarNet verarbeiten; Nebelebene auf
   Löcher, Halos und falsch entfernte Nebeldetails prüfen. Anschließend rendern.
5. EXE-Dateiname und Modus prüfen: `starnet2.exe` modern, `starnet++.exe` legacy.

Kein Testresultat behauptet, dass StarNet hier bereits auf Windows getestet wurde
oder dass alle realen Astrofotos artefaktfrei getrennt werden können.

## Nachtrag: Starflight und echte CLI-Integration

- StarNet2 2.6.2 Linux/ONNX-CPU wurde vom offiziellen Download bezogen und die
  SHA-256-Prüfsumme gegen die Anbieterangabe geprüft. Der Nutzer hat der vollständigen
  Paketlizenz ausdrücklich zugestimmt, bevor sein Foto verarbeitet wurde.
- Die Integration verarbeitete ein gestretchtes RGB-16-Bit-TIFF und las die
  Sternenentfernung erfolgreich zurück; auch `--upsample` wurde ausgeführt.
  Diese persönliche Bildverarbeitung ist separat vom synthetischen Testpaket.
  Weder Nutzerfoto/StarNet-Ausgaben noch StarNet-Programm/Gewichte werden im ZIP
  als Produktassets oder Testfixtures mitgeliefert.
- Neues Konfigurationsprofil `configs/starflight.yaml`: Hintergrundkamera konstant,
  Sternzoom 1× → 2,5×, Gesamtrotation 4,5°, 10 s, 1080 × 1920 bei 30 FPS.
- Optionale Vordergrundauswahl hält stark farbige Differenzreste im Hintergrund.
  Zwei zusätzliche synthetische Tests prüfen die exakte Rekonstruktion bei Screen
  und additive sowie die Trennung eines neutralen Sternkerns von einem farbigen
  länglichen Rest. Reale StarNet-Ausgaben sind keine Testfixtures dieser Tests.
- Aktuelle Testsuite: **29 passed in 2.38s**.
- Windows/StarNet-Windows-Build weiterhin nicht hier ausgeführt.

## Nachtrag: Einzelstern-Flug durch ein Tiefenvolumen

- `starfield.py` erzeugt perspektivische X/Y/Z-Projektionen aus erkannten Kernen
  der bereits getrennten Sternebene. Das Tiefenvolumen ist künstlerisch mit Seed
  verteilt, keine astronomische Entfernungsmessung. Lichtpunkte ersetzen dabei
  ursprüngliche Sternprofile und verändern die räumliche Anordnung.
- `configs/immersive.yaml` hält die Nebelkamera unverändert; nahe Sterne werden
  per Alpha-over zuletzt über Nebel und fernere Sterne gelegt. Eine konstante
  Querverteilung verhindert, dass der Raum nach den ersten nahen Sternen leer wirkt.
- Neue synthetische Tests prüfen tiefenabhängige Vorwärts- und Seitwärtsbewegung,
  die Abdeckung roter Nebelpixel durch nahe helle Kerne, richtige Tiefensortierung,
  Seed-Reproduzierbarkeit, endliche Projektion beim Recycling sowie expliziten
  Abbruch ohne erkennbare Sternkerne. Ein vollständiger FFmpeg-Test mit Ambient
  prüft nun auch den perspektivischen Renderpfad und decodiert jeden Frame.
- Aktuelle Testsuite: **34 passed in 2.72s** unter Linux/Python 3.12.
- Persönlicher Render mit getrenntem Nutzerfoto: 4.500 Sternpartikel; Stichproben
  bei 0/3/6/9/12 s zeigen 45–53 nahe sichtbare Sterne. In der Clipmitte beträgt
  die mediane Bewegung naher Sterne ca. 344 px/s, ferner Sterne ca. 54 px/s
  (1080 × 1920). Die Hintergrund-Kameramatrizen sind identisch.
- Nutzerfoto, StarNet-Ausgaben und daraus erzeugte persönliche Videos werden
  weiterhin nicht als Produktassets oder Testfixtures im Quellcode-ZIP verteilt.

Vollständiger persönlicher Export erfolgreich geprüft: 12,000 s, 1080 × 1920,
30 FPS / 360 Frames, H.264 yuv420p und AAC Stereo 48 kHz. FFmpeg decodierte
den gesamten Video-/Audiostream ohne Fehler (exit 0). Renderzeit 146,7 s;
Dateigröße 10.680.033 Bytes. Kontaktbogen aus den tatsächlich codierten Frames
0/90/180/270/359 betrachtet. Letzter Frame: 2.785 sichtbare Partikel, davon
54 nahe Sterne; Nebel bleibt stationär. Windows weiterhin nicht getestet.

## Nachtrag: 15-Sekunden-Varianten und Ambient-Harmonien

- Zwei neue Profile mit 450 Frames / 15 s bei 30 FPS. Kamerafahrt und Rotation
  pro Sekunde sind nominal um 5 % reduziert: travel 2,85 / 15 s statt 2,4 / 12 s;
  Rotation 4,75° / 15 s statt 4° / 12 s. Smootherstep und Tiefenverteilung bleiben
  erhalten. Einzelsterngeschwindigkeit hängt weiterhin von Position und Tiefe ab.
- Ambient-Varianten `floating` und `dusk` ändern Akkordmaterial und Tonlage;
  Phasen, Verstimmung und Stereo-Pan bleiben seeded. Keine Samples oder Dienste.
- Neuer synthetischer Test vergleicht die unterschiedlichen Harmonievarianten
  bei identischem Seed, prüft WAV-Dauer, Stereo, Fades, Abstand zu PCM-Clipping
  sowie Konfigurationsfehler. Gesamte Testsuite: **35 passed in 2.83s**.
- Zweites Nutzerfoto durch echte StarNet2-CLI mit `--upsample` verarbeitet:
  905 × 1536, 16-Bit-TIFF-Verarbeitung. Maximaler linearer Rekonstruktionsfehler
  ca. 1,19 × 10⁻⁷. Starless und Vorschau visuell geprüft; Nutzerassets werden
  nicht in das Quellcodepaket oder in synthetische Testfixtures übernommen.

- Ambient-WAV wird vor der Freigabe in eine temporäre Datei geschrieben, auf
  vollständige Samplezahl einschließlich des letzten Samples geprüft und atomar
  ersetzt. Ein zusätzlicher vollständiger 15-s-Test prüft 720.000 Stereo-Frames
  sowie den Erhalt einer bestehenden WAV bei Fehlern und die Bereinigung temporärer
  Dateien. Finale Testsuite: **36 passed** unter Linux/Python 3.12.
- Beide persönlichen Videos vollständig decodiert: FFmpeg exit 0 ohne Fehler;
  jeweils H.264 yuv420p, 1080 × 1920, 30 FPS / 450 Frames, 15,000 s Video und
  15,000 s AAC-Stereo bei 48 kHz. Kontaktbögen aus codierten Frames geprüft.
- Beide Musikquellen enthalten vollständig 720.000 Stereo-Frames (15 s), Start/
  Ende null und kein PCM-Clipping. Peak ca. 0,144 / 0,139; RMS ca. 0,033 / 0,032.
  Es sind unterschiedliche eigene Synthesen, keine bloße Wiederverwendung der
  vorherigen Musikdatei. Windows-Build weiterhin nicht hier getestet.

## Nachtrag: Sternprofile, wenige nahe Vorbeiflüge und Ambient-Akzente

- Neuer `starprofiles.py`-Modus: isolierte kleine RGB-Sternprofile aus der echten
  getrennten Sternebene statt einheitlicher Gaußpunkte. Voronoi-Zuordnung schließt
  andere erkannte Kerne aus. Weiche Ränder, premultipliziertes RGBA, Mipmaps und
  Subpixel-Projektion verhindern rechteckige Profilränder und dunkle Blur-Säume.
  Sehr kleine Sensor-/JPEG-Farbpixel werden lokal geglättet und an einer über
  mehrere Pixel integrierten Kernfarbe ausgerichtet. Formen und dezente Halos
  stammen aus dem Foto; begrenzte Eingabedetails werden nicht erfunden.
- Höchstens sechs einmalig ausgewählte reale Sterne pro Clip erhalten beim
  nahen Vorbeiflug am Rand sanft mehr Größe und Defokus. Kein Wechsel der Auswahl
  von Frame zu Frame. Grundbewegung, 15 Sekunden Länge und Nebelkamera unverändert.
- Eigenständige NumPy-Synthese um leise Glockenpartialtöne und hohe harmonische
  Klangflächen erweitert. Bei 15 Sekunden drei weich angeschlagene Glockenereignisse
  mit langen Ausklängen. Seed-Reproduzierbarkeit und saubere Fades bleiben erhalten.
- Neue synthetische Tests prüfen asymmetrische Sternform, sanften farbigen Halo,
  Ausschluss benachbarter Kerne, Defokus ohne dunkle Farbsäume, Unterdrückung bunter
  Einzelpixelblöcke, feste begrenzte Vordergrundauswahl, unterschiedliche reproduzierbare
  Ambient-Akzente und PCM-Clipping/Fades. Der vollständige FFmpeg-Test mit Ambient
  aktiviert zusätzlich Sternprofile, Vorbeiflüge und Akzente und decodiert jeden Frame.
- Gesamte Testsuite: **42 passed in 5.36s** unter Linux/Python 3.12.
- Persönliche Foto-/StarNet-Daten bleiben außerhalb des Quellcodepakets und der
  synthetischen Tests. Kein neuer StarNet-Lauf nötig; die zuvor geprüften echten
  Starless-Ergebnisse werden wiederverwendet. Windows-Build weiterhin ungetestet.

Finale persönliche Exporte: beide vollständigen Video-/Audiostreams mit FFmpeg
fehlerfrei decodiert (exit 0), jeweils 15,000 s, 1080 × 1920, 30 FPS / 450 Frames,
H.264 yuv420p + AAC Stereo 48 kHz. Sichtprüfung aus codierten Frames durchgeführt.
Beide Clips nutzen 4.500 Fotoprofile und je sechs ausgewählte nahe Vorbeiflüge.
Renderzeiten ca. 191,0 / 196,8 s. Musik-WAVs enthalten jeweils 720.000 Stereo-Frames,
weiche Fades, Peak ca. 0,152 / 0,145 und kein PCM-Clipping.

## Nachtrag: dezente Beschriftung und Annäherung

- Neues optionales Modul `captions.py`: vorbereitete kleine Textur, lokale
  skalierbare Schrift, sanfte Cosinus-Fades, feste Bildschirmposition.
  Konfigurationsgruppe `caption` sowie CLI-Optionen `--title` / `--subtitle`.
  Der normale Renderpfad setzt den Text nach der perspektivischen Sternkomposition.
- `configs/immersive_approach.yaml` vergrößert die Hintergrundebene um 4 Prozent
  über 15 Sekunden. Vordergrundprojektion und Sternflug bleiben unabhängig.
  Kameramatrizen für 31 Positionen auf vollständige Quellenabdeckung geprüft.
- Vier neue synthetische Tests: Fades und unveränderte Bildbereiche außerhalb
  der Schrift, Unicode/Zeilenanpassung, fehlender Font, Konfigurationsvalidierung
  und relative Fontpfade. Bestehender FFmpeg-End-to-End-Test mit Ambient aktiviert
  zusätzlich eine kurz sichtbare Beschriftung und decodiert jeden Frame.
- Gesamte Testsuite: **46 passed** unter Linux/Python 3.12.
- Persönliche Orion-Vorschau separat mit 4 Prozent Hintergrundannäherung und
  dezenter Beschriftung gerendert: 15 Sekunden, 450 Frames, 1080 × 1920,
  H.264 und AAC; vollständige Decodierung erfolgreich. Titel zwischen 2 und
  6,5 Sekunden sichtbar, Musik der vorherigen Fassung übernommen.
- Windows-Fontauswahl/StarNet-Windows-Build weiterhin nicht hier ausgeführt.
  Keine persönlichen Foto-/StarNet-Daten im Quellcodepaket.

## Nachtrag: stärkere Hintergrundannäherung

- Profil immersive_approach: 14 Prozent Hintergrundzoom und 2 Grad langsame
  Rotation über 15 Sekunden. Perspektivischer Sternflug weiterhin unabhängig.
- Beide aktualisierten Konfigurationen validiert; Quellenabdeckung aller vier
  Videoränder an 31 Kamerapositionen geprüft. Keine Programmcodeänderung.
- Persönlicher Orion-Render erneut vollständig decodiert: 15 Sekunden, 450 Frames,
  1080 x 1920, 30 FPS, H.264 und AAC-Stereo. Codierte Anfangs-, Titel- und
  Endframes visuell geprüft. Native CaptionOverlay verwendet.


## Nachtrag: konfigurierbare 30-Sekunden-Version und nahtloser Loop (09.10.2026)

- Version 1.1.0, neue Standarddauer 30 s. CLI `--duration` bzw. YAML/JSON
  `duration` weiterhin frei konfigurierbar; auf ganze Frames gerundet.
- Neues Profil `configs/immersive_loop.yaml`, CLI `--loop` / `--no-loop`,
  typgeprüfte Gruppe `loop`. Alte Konfigurationen behalten ihre explizite Dauer.
- Sternflug: ganzzahlige Volumendurchläufe mit konstanter Vorwärtsgeschwindigkeit;
  zyklische Seitwärtsfahrt/Rotation, periodische Nah-/Fernfades und Shutter.
  Kein Rückwärtsflug, keine Ganzbildüberblendung, kein doppelter Endpoint-Frame.
- Hintergrund: sanfter Zoom-/Rotations-/Pan-Zyklus hinein und zurück. 14 Prozent
  maximaler Zoom in der Mitte der Periode, 2 Grad Rotationsspanne im neuen Profil.
- Ambient: verlängerte NumPy-Synthese ohne Außenfades, eine Sekunde Warmup,
  anschließend Streaming-Overlap-Splice mit Smootherstep. Auch eigene MP3/WAV wird
  unterstützt. Speicherbedarf hängt vom Audioblock ab, nicht von der Videodauer.
- Neue Tests: periodische X/Y/Z-Projektion mit 1/2/5 Volumendurchläufen, echte
  Vorwärtsgeschwindigkeit auch am Übergang, gleiche vollständige Sternkomposition
  an den Perioden-Endpunkten inklusive Shutter/Defokus, Quellenabdeckung der
  zyklischen Kamera, periodisches Funkeln und geschlossene Kurzclip-Titelhülle.
- Audio-Tests: Seam-Sample folgt direkt auf den letzten Quellsample, deterministische
  Synthese, genau passende Samplezahl, keine Außenpause, atomarer Commit bei
  Fehlern. Eigene WAV tatsächlich mit FFmpeg dekodiert und in einen Loop gespliced.
- Zusätzlich vollständiger kurzer synthetischer End-to-End-Loop-Render mit
  Fotosternprofilen, Titel, Funkeln und Musik; alle Streams fehlerfrei dekodiert.
- Aktuelle Suite: **56 passed** unter Linux/Python 3.12 mit den gepinnten Paketen.
- H.264/AAC sind verlustbehaftet; der geschlossene Animations-/PCM-Zyklus bedeutet
  keine bitidentischen Endframes oder garantierte pausefreie Wiedergabe in jedem
  Player. Kein Windows- oder neuer StarNet-Test in dieser Erweiterung nötig bzw.
  durchgeführt: zuvor geprüfte echte StarNet-Ebenen werden wiederverwendet.
  Persönliche Bilder/StarNet-Ausgaben bleiben außerhalb des Produkt-Quellcode-ZIP.

### Fünf persönliche 30-Sekunden-Loop-Exporte

Alle fünf wurden vollständig mit FFmpeg fehlerfrei dekodiert (Video und Audio),
mit 900 Frames / 30 s / 30 FPS, H.264 yuv420p, BT.709 und AAC Stereo 48 kHz.
Dateien und persönliche Fotodaten werden separat vom Quellcodepaket bereitgestellt.

| Motiv | Auflösung | Unkomprimierter Perioden-Endpunktfehler | Decode |
|---|---|---:|---|
| 01_Pferdekopf_Flammennebel | 1920 × 1080 | 0 | bestanden |
| 02_Zauberernebel | 1080 × 1080 | 0 | bestanden |
| 03_Sichelnebel | 1080 × 1920 | 0 | bestanden |
| 04_Pacmannebel | 1080 × 1920 | 0 | bestanden |
| 05_Herznebel | 1080 × 1920 | 0 | bestanden |

- Jede Loop-WAV enthält genau 1.440.000 Stereo-Frames. Fünf unterschiedliche
  SHA-256-Hashes; kein PCM-Clipping und keine Außenpause. Der PCM-Sampleschritt
  vom Ende zum Anfang liegt jeweils unter dem 99. Perzentil normaler Schritte.
- Auch der dekodierte AAC-Übergang wurde quantitativ geprüft; Kompressions-
  abweichungen bleiben erhalten. H.264-End-/Startframe-Unterschiede wurden gegen
  benachbarte Frames verglichen. Der letzte Frame ist bewusst nicht identisch
  mit dem ersten: er liegt genau ein Frameintervall davor.
- Codierte letzte/erste Frames, Titelphase und maximaler Zoom als Kontaktbogen
  visuell geprüft. Hintergrundzoom sichtbar, keine schwarzen Randflächen.
- Exporte nutzen bereits zuvor erzeugte echte StarNet-Ebenen, ohne neue
  Sternentrennung oder Ersatzverfahren. Windows weiterhin ungetestet.


## Ergänzung: README-Demos und zufällige Musik (09.10.2026)

- 58 Tests bestanden unter Linux/Python 3.12, einschließlich FFmpeg-Exports, festem Seed, zufälligem Seed, Wiederholung einer Variante und Seed-Validierung.
- Standard und mitgelieferte Profile: neuer Ambient-Seed je Render; verwendeter Seed wird im Render-Bericht gespeichert, Eingabekonfiguration bleibt wiederverwendbar.
- Zwei eigene JPEG-Aufnahmen unverändert übernommen. Foto-Demos bewusst als 2D-Animation ohne StarNet, unabhängige Sternebene oder automatisches Farbgrading erzeugt.
- Beide Exporte: 30 Sekunden, 720 × 1280, 30 FPS, 900 Frames, H.264/AAC; vollständige Dekodierung mit FFmpeg ohne Fehler. Stichproben mit sichtbarer Objektbeschriftung visuell geprüft.
- GIF-Vorschauen: jeweils 216 × 384, 180 Frames, vollständiger 30-Sekunden-Zyklus; Originaldateien bytegleich mit Uploads, lokale README-Medienpfade geprüft.
- StarNet-Lizenzrevision 07.09.2026 aus dem offiziellen Linux-Paket gelesen. Programm/Gewichte werden nicht weitergegeben und wurden nicht für diese Foto-Demos verwendet.
- Neue Version weiterhin nicht auf Windows/macOS ausgeführt.
