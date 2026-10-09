# Eigene Seestar-Aufnahmen und StarNet2-Demos

**Seestar S50 Pro + AstroWizard**, Originalfotos von nosTa1337.
Die JPEG-Aufnahmen sind unverändert und dürfen verwendet werden; eine
Quellenangabe ist willkommen.

| Objekt | Originalfoto | StarNet2-Video (30 s, mit Musik) | GIF-Vorschau |
|---|---|---|---|
| Orionnebel · M42 | [orion.jpg](orion.jpg) | [orion_starnet_demo.mp4](orion_starnet_demo.mp4) | [orion_starnet_preview.gif](orion_starnet_preview.gif) |
| Plejaden · M45 | [pleiades.jpg](pleiades.jpg) | [pleiades_starnet_demo.mp4](pleiades_starnet_demo.mp4) | [pleiades_starnet_preview.gif](pleiades_starnet_preview.gif) |

**1080 × 1920, 30 FPS, H.264/AAC.** Die Sternentrennung erfolgte mit
der echten, separat installierten **StarNet2-CLI**, nicht mit einer
OpenCV-Approximation. Sterne und Nebel bewegen sich unabhängig;
der Sternflug verwendet fotografische Profile aus dem StarNet2-Residuum. Die Musik wurde
lokal synthetisiert, GIFs bleiben stumm.

Die aktuellen Demos wurden im [erfolgreichen Actions-Lauf vom 9. Oktober 2026](https://github.com/nosTa1337/AstroMotion/actions/runs/37927064436) neu gerendert: individueller Sternflug mit fotografischen Sternprofilen, ruhige Hintergrundbewegung, Perfect Loop und zufällige Ambient-Musik. Cleanup, Lochfilter und zusätzliche Farbeffekte bleiben deaktiviert. Echte StarNet2-Trennung, aktiver Sternflug, 30 Sekunden, Auflösung, 900 Frames und vollständige Dekodierung wurden technisch geprüft; siehe [Prüfbericht](../../CLEAN_PIPELINE_REPORT.md).

Mit offizieller StarNet2-CLI und gültiger Lizenz zunächst die Ebenen prüfen:

```bash
python scripts/render_starnet_examples.py --starnet "/pfad/zu/starnet2" --check-only
```

Standardmäßig wird nur ein 2-Sekunden-M45-Test unter `test-renders/` erzeugt. Für beide vollständigen Demos nach Sichtprüfung:

```bash
python scripts/render_starnet_examples.py --starnet "/pfad/zu/starnet2" --only all --duration 30 --resolution 1080p --output-dir examples/real --overwrite
```

Optional `--duration 45` oder `--seed 1234`. Ohne festen Seed entsteht bei jedem Rendering neue Ambient-Musik. Die Original-JPEGs werden nicht überschrieben.

Nach Mitteilung des Projektbetreibers besteht eine separate Freigabe für
die Demo-Nutzung der StarNet2-basierten Ergebnisse. Die StarNet2-Software
und Modelle sind davon nicht umfasst; siehe
[THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md).
