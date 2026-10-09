# Lizenzen und externe Komponenten

Stand: 09.10.2026. Die Versionsangaben beziehen sich auf `requirements.txt` und `requirements-dev.txt`. Die Lizenznamen wurden mit den Metadaten und Lizenzdateien der hier installierten Pakete abgeglichen.

## AstroMotion

Der eigene AstroMotion-Quellcode steht unter [MIT](LICENSE). Bei Weitergabe des Codes sind der Copyright-Hinweis und der vollständige Lizenztext beizubehalten. Die MIT-Lizenz von AstroMotion erteilt keine zusätzlichen Rechte an externen Komponenten oder deinen Eingabedateien.

Dieses Repository enthält keine gebündelten Python-Wheels, keine FFmpeg-/StarNet-Programme und keine StarNet-Modellgewichte. Abhängigkeiten werden separat installiert. Neben dem synthetischen Testbildgenerator enthält es eigene, zur Verwendung freigegebene Aufnahmen und daraus erzeugte Demovideos (historische 2D-Version im Repository, neue Demo-Engine mit approximierter Sternbewegung); siehe [Medienhinweise](examples/real/README.md).

## Python-Pakete

| Komponente | Version | Hauptlizenz / Hinweis | Quelle |
|---|---|---|---|
| NumPy | 2.2.6 | BSD-3-Clause; Wheels enthalten zusätzliche Bibliotheken mit eigenen Hinweisen | [Projekt / Lizenz](https://github.com/numpy/numpy/blob/v2.2.6/LICENSE.txt) |
| opencv-python-headless | 4.12.0.88 | OpenCV: Apache-2.0; Python-Paketierungs-Code: MIT; weitere Bestandteile laut `LICENSE-3RD-PARTY.txt` des Wheels | [Paket und Lizenzhinweise](https://pypi.org/project/opencv-python-headless/4.12.0.88/) |
| Pillow | 11.3.0 | MIT-CMU; gebündelte Bildbibliotheken haben zusätzliche Lizenzen | [Paket / License expression](https://pypi.org/project/pillow/11.3.0/) |
| PyYAML | 6.0.2 | MIT | [Lizenz](https://github.com/yaml/pyyaml/blob/6.0.2/LICENSE) |
| tifffile | 2025.6.11 | BSD-3-Clause | [Paket](https://pypi.org/project/tifffile/2025.6.11/) |
| pytest (nur Entwicklung) | 8.4.2 | MIT | [Lizenz](https://github.com/pytest-dev/pytest/blob/8.4.2/LICENSE) |

Die Tabelle nennt die direkten Pakete. Weitere Laufzeit-/Testabhängigkeiten und Bibliotheken innerhalb eines Wheels behalten ihre eigenen Lizenzbedingungen. Bei Weiterverteilung eines Wheels dessen vollständige Lizenz-/Copyright-Dateien und Hinweise erhalten; diese Übersicht ersetzt sie nicht. Die konkrete Zusammenstellung kann sich zwischen Windows-, Linux- und macOS-Wheels unterscheiden.

Für die separat installierte Python-Laufzeit gelten die [Python-Lizenz und zugehörigen Hinweise](https://docs.python.org/3.12/license.html).

## FFmpeg / FFprobe und libx264

FFmpeg ist grundsätzlich LGPL-2.1-or-later; bestimmte Build-Optionen und Bibliotheken führen zu GPL-Builds. AstroMotion nutzt den Encoder `libx264`, dessen GPL-Einbindung einen entsprechenden FFmpeg-Build erfordert. FFprobe stammt ebenfalls aus FFmpeg.

AstroMotion startet die separat installierten Programme als Prozesse. FFmpeg-Binärdateien werden hier nicht weiterverteilt. Falls später ein Installer oder Download FFmpeg mitliefert, müssen die Bedingungen genau dieses Builds erfüllt werden, einschließlich der einschlägigen Lizenzhinweise und Quellcodepflichten. Die passende Lizenzinformation lässt sich mit `ffmpeg -L` und der Build-Konfiguration mit `ffmpeg -version` prüfen.

Quellen: [FFmpeg Legal](https://ffmpeg.org/legal.html), [FFmpeg: x264](https://ffmpeg.org/general.html#x264), [x264](https://www.videolan.org/developers/x264.html).

## StarNet ist eine separat lizenzierte Komponente

StarNet2/StarNet++ und Modellgewichte separat vom [offiziellen Anbieter](https://starnetastro.com/cli-tools/starnet/) beziehen. Maßgeblich sind `LICENSE.txt`, README und weitere Hinweise **genau der installierten Version**. Geprüft wurde `LICENSE.txt` im offiziellen Linux-Paket `starnet2_linux_2.6.2-0241_ORT_x64_cli.zip`, Lizenzrevision 07.09.2026.

Diese Revision erlaubt persönliche und kommerzielle Astrofotoverarbeitung sowie bedingt den Aufruf der mitgelieferten CLI als separaten Prozess. Integrationen müssen StarNet benennen, den vollständigen Vertrag zugänglich machen und vor Verwendung ausdrückliche Zustimmung erhalten; die Zustimmung im offiziellen Installer kann dafür genügen. Software-/Modellweitergabe erfordert schriftliche Erlaubnis. Für Ausgaben bestehen zusätzliche Beschränkungen, insbesondere für Modelltraining sowie Entwicklung, Tests und Produktassets anderer Software; die ausdrücklich erlaubten Integrationsaktivitäten sind ausgenommen.

Die hier versionierten Foto-Demos verwenden daher **kein StarNet**. Für normale 2,5D-Renderings kann mit `--starless` ein bereits vorhandenes, entsprechend verwendbares sternenloses Bild dienen. Bei StarNet zuerst den vollständigen mitgelieferten Vertrag prüfen und über den Anbieter akzeptieren; bei geänderten Bedingungen ist erneute Zustimmung erforderlich. AstroMotions MIT-Lizenz erweitert diese Rechte nicht. Der Vertrag wird hier nicht durch eine vereinfachte Zusammenfassung ersetzt.

Die historische Python-Implementierung im [Repository des Autors](https://github.com/nekitmm/starnet) nennt MIT für Code und CC BY-NC-SA 4.0 für Gewichte. Diese Angaben dürfen nicht pauschal auf aktuelle Binärpakete übertragen werden.

Offizielle Dokumentation: [CLI](https://starnetastro.com/documentation/starnet/command-line-tool/), [Installer und Paketstruktur](https://starnetastro.com/documentation/cli-installers/).

## Schriften, Fotos und Musik

DejaVu Sans ist eine optionale, separat installierte Schrift für Beschriftungen und Tests. Es gelten die [Bitstream-Vera-/Arev-Lizenzhinweise des DejaVu-Projekts](https://dejavu-fonts.github.io/License.html); DejaVu-Erweiterungen sind laut Projekt gemeinfrei. Bei Weitergabe von Fontdateien die zugehörigen Copyright- und Lizenzhinweise beilegen. Für andere Schriften, etwa eine vorhandene Arial-Datei, gelten deren eigene Bedingungen; Fontdateien werden hier nicht mitgeliefert.

Eigene oder fremde Fotos, Starless-Dateien und hochgeladene Musik behalten ihre bestehenden Rechte. Die Ambient-Musik wird allein durch AstroMotions Oszillatoren und Delay erzeugt; es gibt keine Samplebibliothek und keinen Online-Dienst. Eine Garantie gegen zufällige Ähnlichkeiten oder Plattform-Content-ID-Fehlalarme ist damit nicht verbunden.

Die enthaltenen Originalaufnahmen stammen von Philipp / nosTa1337, aufgenommen mit **Seestar S50 Pro**, bearbeitet mit **AstroWizard**. Die Fotos, ihre Demo-MP4s einschließlich synthetisierter Musik und die GIF-Vorschauen dürfen verwendet werden; eine Quellenangabe ist willkommen. Diese Freigabe gilt nur für die konkret enthaltenen Demo-Medien und erteilt keine Rechte an externen Programmen, Modellen oder sonstigen fremden Medien.
