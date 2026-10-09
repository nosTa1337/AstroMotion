# Eigene Seestar-Aufnahmen und StarNet2-Demos

**Seestar S50 Pro + AstroWizard**, Originalfotos von Philipp / nosTa1337.
Die JPEG-Aufnahmen sind unverändert und dürfen verwendet werden; eine
Quellenangabe ist willkommen.

| Objekt | Originalfoto | StarNet2-Video (30 s, mit Musik) | GIF-Vorschau |
|---|---|---|---|
| Orionnebel · M42 | [orion.jpg](orion.jpg) | [orion_starnet_demo.mp4](orion_starnet_demo.mp4) | [orion_starnet_preview.gif](orion_starnet_preview.gif) |
| Plejaden · M45 | [pleiades.jpg](pleiades.jpg) | [pleiades_starnet_demo.mp4](pleiades_starnet_demo.mp4) | [pleiades_starnet_preview.gif](pleiades_starnet_preview.gif) |

**1080 × 1920, 30 FPS, H.264/AAC.** Die Sternentrennung erfolgte mit
der echten, separat installierten **StarNet2-CLI**, nicht mit einer
OpenCV-Approximation. Sterne und Nebel bewegen sich unabhängig;
die Sternentfernungen sind künstlerische Werte. Die Musik wurde
lokal synthetisiert, GIFs bleiben stumm.

Mit offizieller StarNet2-CLI und gültiger Lizenz neu rendern:

```bash
python scripts/render_starnet_examples.py --starnet "/pfad/zu/starnet2" --overwrite
```

Optional `--only pleiades`, `--duration 45`, `--seed 1234`.
Ohne festen Seed entsteht bei jedem Rendering neue Ambient-Musik.
Die Original-JPEGs werden nicht überschrieben.

Nach Mitteilung des Projektbetreibers besteht eine separate Freigabe für
die Demo-Nutzung der StarNet2-basierten Ergebnisse. Die StarNet2-Software
und Modelle sind davon nicht umfasst; siehe
[THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md).
