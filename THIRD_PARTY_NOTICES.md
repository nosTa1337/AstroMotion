# Externe Komponenten

AstroMotion selbst steht unter MIT (LICENSE). Es werden weder externe Programme,
Modellgewichte noch fremde Musik-/Bildsamples mitgeliefert.

- NumPy: BSD-3-Clause; https://numpy.org/
- OpenCV/Python-Paket: Apache-2.0 für aktuelles OpenCV, weitere mitgelieferte
  Bestandteile nach den Hinweisen des installierten Wheels; https://opencv.org/license/
- Pillow: HPND; https://pillow.readthedocs.io/en/stable/about.html
- PyYAML: MIT; https://github.com/yaml/pyyaml
- tifffile: BSD-3-Clause; https://github.com/cgohlke/tifffile
- pytest (nur Entwicklung): MIT; https://github.com/pytest-dev/pytest
- FFmpeg: je nach Build LGPL/GPL und Bibliotheken. Für libx264 wird üblicherweise
  ein GPL-fähiger Build benötigt; https://ffmpeg.org/legal.html

## StarNet ist eine separat lizenzierte Komponente

Die aktuelle StarNet2/StarNet++-Distribution separat vom offiziellen Anbieter
beziehen. Maßgeblich sind LICENSE.txt, README und weitere Hinweise **genau der
installierten Version**. Ein kostenloser Download bedeutet nicht automatisch
Open Source oder uneingeschränkte kommerzielle Nutzbarkeit. AstroMotion erteilt
keine Rechte an StarNet, dessen Modellgewichten oder Ausgaben.

Die historische Python-Implementierung unter https://github.com/nekitmm/starnet
nennt MIT für Code und CC BY-NC-SA 4.0 für Gewichte; dies darf nicht pauschal auf
aktuelle Binärpakete übertragen werden. Vor kommerzieller/monetarisierter Nutzung
die jeweiligen Bedingungen prüfen; bei Unklarheit den Anbieter fragen.

Offizielle Einstiegsseiten (Dokumentation geprüft am 08.10.2026):

- https://starnetastro.com/cli-tools/starnet/
- https://starnetastro.com/documentation/starnet/command-line-tool/
- https://starnetastro.com/documentation/cli-installers/

Mit `--starless` kann eine bereits vorhandene, passend lizenzierte Sternenentfernung
verwendet werden. Die Ambient-Musik wird allein durch AstroMotions Oszillatoren
und Delay erzeugt. Es gibt keine Samplebibliothek und keinen Online-Dienst;
eine Garantie gegen zufällige Ähnlichkeiten oder Plattform-Content-ID-Fehlalarme
ist damit nicht verbunden.
