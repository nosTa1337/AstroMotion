# Synthetische Demo

Die Demo-Bilder werden mit `python scripts/create_demo.py` im Projektverzeichnis
erzeugt. Unter Windows übernimmt `render_demo_windows.bat` sowohl die Erstellung
der Bilder als auch das Rendering eines 30-Sekunden-Loops mit Ambient-Musik.

Der Generator erstellt `deep_sky.png`, `deep_sky_starless.png`,
`deep_sky_16bit.tif` und `deep_sky_preview.jpg`. Das Starless ist die bekannte
Nebelebene der synthetischen Aufnahme; es ersetzt keine echte Sternentrennung.

Die Bilddateien, Videos und Render-Assets sind reproduzierbar und werden nicht
in Git gespeichert. Eigene Astroaufnahmen können außerhalb des Repositories
liegen; ihre Pfade werden über `--input` und optional `--starless` übergeben.
