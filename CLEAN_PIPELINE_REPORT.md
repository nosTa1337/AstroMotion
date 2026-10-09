> Nachtrag: Der unten dokumentierte Fix entfernte den individuellen Sternflug zu weitgehend. `starfield.py` und `starprofiles.py` wurden deshalb wiederhergestellt; Cleanup und Lochreparatur bleiben entfernt. Die früheren Bildprüfungen betreffen die Ebenenanimation, nicht den wiederhergestellten Sternflug. Der Projektbetreiber hat dessen echten 2-Sekunden-M45-Clip inzwischen visuell freigegeben; danach wurde das Rendering der 30-Sekunden-Demos über GitHub Actions autorisiert. Der [Actions-Lauf 37927064436](https://github.com/nosTa1337/AstroMotion/actions/runs/37927064436) hat beide Demos erfolgreich gerendert und in Commit `f5dcf5b` im PR-Zweig gespeichert. StarNet2-Herkunft, aktiver Sternflug, 30 Sekunden, 1080 × 1920, 30 FPS, 900 Frames sowie die vollständige Video- und GIF-Dekodierung wurden geprüft. Der Projektbetreiber hat das aktuelle Animationsergebnis anschließend visuell freigegeben. Der folgende Bericht beschreibt weiterhin den historischen ersten Fix.

# Saubere StarNet2-Ebenen – Ursachenanalyse und Prüfung

Stand: 9. Oktober 2026. Ausgangspunkt: `f82e1681e6898ea05a3f6f1d07e48c80c4390231`.

## Was die Git-History tatsächlich zeigt

Ein separater v1.0-Quellcode oder Versions-Tag ist nicht enthalten. `5e8e6ae` enthält nur die README; der erste vollständige Code-Import ist `7ab0327` (v1.1). Ein exakter v1.0-Rollback lässt sich aus dieser History daher nicht rekonstruieren.

| Stand | Änderung und Befund |
|---|---|
| `7ab0327` – v1.1 | Enthält bereits `foreground_cleanup`, RGB-Neutralitätsmaske, Neuberechnung des Hintergrunds, `starfield.py` und `starprofiles.py`. |
| `cfc168d` bis `ef68c13` – v1.2 | Ergänzt Autofokus/Autofarbe und adaptive künstlerische Sterntiefen. `extract_layers()` bleibt gegenüber v1.1 unverändert. Das neue Preset aktiviert Cleanup und Sprites weiterhin. |
| `cfb0be5` | Bindet `repair_bright_star_holes()` ein und erweitert die Cleanup-Maske für farbige Sternkerne. |
| `88fb046` | Lässt zusätzlich stark gefärbte Sternkerne im Sprite-Detektor zu. Kann dadurch weitere farbige Restpixel vergrößern; verändert den Nebelhintergrund selbst nicht. |
| `11065f2` | Schränkt die Farbkernmaske wieder über zusammenhängende Komponenten ein; die schädliche Hintergrund-Neuberechnung bleibt. |
| `d5de771` | Entfernt die Umverteilung in den Nebel, behält aber den Lochreparaturfilter. |
| Dieser Fix | Entfernt Reparaturfilter und Sprite-Renderer vollständig. Ganze RGB-Sternebene, farbneutrale Presets und ruhige Ebenenkameras. |

`starprofiles.py` wurde nach dem v1.1-Import nicht mehr geändert. Es normalisierte kleine Stern-Patches, glättete/verschob deren Chromatizität und vergrößerte sie als Sprites. Das kann unnatürliche Sternfarben verstärken, ist aber **nicht** die Quelle der nachgewiesenen schwarzen Löcher im Hintergrund.

## Nachgewiesene Ursache

Die frühere Cleanup-Maske bewertet RGB-Neutralität und Helligkeit, reduziert damit Teile des Sternresiduums und berechnet anschließend den Hintergrund erneut über `(original - stars) / (1 - stars)`. Dadurch landen entfernte Teile insbesondere blauer Sterne im Nebel. Nebel und Sterne bewegen sich anschließend unabhängig: Die umverteilten farbigen Strukturen bleiben sichtbar zurück.

Der Vorher/Nachher-Vergleich verwendet **identische echte M45-StarNet2-Ausgangsdaten**, nicht eine simulierte Trennung:

![Original, rohe StarNet2-Ausgabe, alte Cleanup-Berechnung und einfache Trennung](qa/pleiades_before_after.jpg)

Anteil der Pixel mit einer Hintergrundänderung von mehr als 0,25 sRGB in mindestens einem Kanal:

| Ebenenberechnung | Stark veränderte Hintergrundpixel |
|---|---:|
| v1.1 `7ab0327` | 0,43987 % |
| v1.2 `ef68c13` | 0,43987 % |
| `cfb0be5` | 0,35067 % |
| `11065f2` | 0,41914 % |
| Erster Fix `d5de771` | 0,01010 % |
| Saubere Ebenen ohne Filter | **0,00000 %** |

Messwerte: [history_metrics.json](qa/history_metrics.json). Die alten Varianten rekonstruieren trotz der optisch beschädigten Ebenen das unbewegte Original mit einem Fehler unter 2,4e-7 in linearem Licht. **Ein Rekonstruktionstest allein erkennt diesen Fehler deshalb nicht.** Zusätzlich muss die Hintergrundebene gegen die rohe StarNet2-Ausgabe geprüft werden.

## Vereinfachte Pipeline

1. Gestrecktes RGB-Original und echte StarNet2-Starless-Ausgabe laden.
2. In lineares RGB umwandeln.
3. Hintergrund kanalweise auf das Original begrenzen; negatives Sternlicht vermeiden.
4. Vollständiges Sternresiduum durch inverse Screen-Komposition (oder explizit additive Komposition) bestimmen.
5. Beide Ebenen unabhängig, ohne Masken/Lochfilter/Sprite-Neuaufbau, transformieren und zusammenführen.
6. Gewählte Länge encodieren; vorhandene periodische Kamerafunktion und Audio-Überblendung beibehalten.

Alle mitgelieferten Presets deaktivieren zusätzliche Bildeffekte und automatische Farbeingriffe. Das empfohlene `clean_loop.yaml` verwendet 10 % Hintergrundzoom und 12,5 % Sternzoom. Die alten Konfigurationsfelder bleiben als ignorierte Kompatibilitätsfelder erhalten, damit gespeicherte Nutzerkonfigurationen weiter laden. Die entfernten Bildverarbeitungsmodule können nicht mehr durch einen alten Schalter aktiviert werden.

## Prüfungen und Grenzen

- 54 Tests bestanden, einschließlich fünf FFmpeg-Integrationstests. Neue Prüfungen schützen blaue Sternkerne und Halos, unveränderte Eingaben, den ausschließlich mathematischen Hintergrund-Clamp sowie neutrale Presets und periodische Bewegung.
- Echte M45- und M42-StarNet2-TIFFs aus einem protokollierten Lauf des offiziellen StarNet2 2.6.2 CLI mit `--upsample` wiederverwendet. Der gespeicherte Modell-Input stimmt pixelweise bis zur 16-Bit-Rundung mit dem jeweiligen Repository-JPEG überein. Keine neue oder ersatzweise OpenCV-Trennung.
- Bei beiden echten Bildern: maximaler Rekonstruktionsfehler `5.960464477539063e-08`, unerwartete Hintergrundänderung gegenüber dem mathematischen Clamp `0`, stark veränderte Hintergrundpixel `0`.
- Vor dem Encoding: volle Standbilder sowie vergrößerte helle Sternbereiche bei Phase 0, 0,25 und 0,5 visuell kontrolliert. Die gemeldeten M45-Farblöcher sind dort nicht mehr sichtbar.
- Bereits in der StarNet2-Starless-Ausgabe enthaltene Resthalos bleiben erhalten. Besonders bei Orion können sie bei unterschiedlichen Ebenenbewegungen noch leicht abdriften. Der Fix retuschiert sie bewusst nicht; die geringere relative Bewegung begrenzt den Effekt.
- 2,5D-Parallax ist eine künstlerische Darstellung, keine gemessene räumliche Sternentfernung. Ein Loop fährt weich vor und zurück.
- Linux/Python 3.12 geprüft. Windows-Batchdateien und macOS wurden hier nicht ausgeführt. `setup_windows.bat` installierte bereits requirements.txt; die README macht jetzt deutlich, dass anschließend derselbe `.venv`-Interpreter und der vollständige StarNet-EXE-Pfad erforderlich sind.

Die aktuelle Demo-Herkunft, Prüfsummen und Exportprüfung stehen in [qa/demo_verification.json](qa/demo_verification.json). Die Kontaktbögen dokumentieren die geprüften Sterne:

- [Plejaden](qa/pleiades_clean_review.jpg)
- [Orion](qa/orion_clean_review.jpg)

Der verbleibende GitHub-Workflow rendert ausschließlich mit echter StarNet2-CLI und bietet die Kandidaten zur Sichtprüfung als Artefakte an. Automatisches Überschreiben der Galerie wurde entfernt.
