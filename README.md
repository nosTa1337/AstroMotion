<p align="center"><img src="assets/astromotion-logo.png" alt="AstroMotion" width="320"></p>

**English** · [Deutsch](README.de.md)

# AstroMotion

**Turn your astrophotograph into a calm flight through the stars.** StarNet2 separates stars from nebulosity. Stars from the photo move at individual depths in front of a gently moving background. The recommended setup creates a **30-second video with a seamless loop and randomly generated ambient music**. Motion, format, duration and music are configurable.

## TL;DR – get started on Windows

1. Install **Python 3.11+** (recommended: 3.12), **FFmpeg with FFprobe**, and the official [StarNet2 CLI](https://starnetastro.com/cli-tools/starnet/). FFmpeg and FFprobe must be on your PATH.
2. Clone the repository or extract it completely, then run **`setup.bat`**. It creates or reuses `.venv` and installs all dependencies.
3. Run this command from the repository folder:

```powershell
.\.venv\Scripts\python.exe main.py --input examples\real\pleiades.jpg --starnet "C:\Program Files\StarNet2\bin\starnet2.exe" --config configs\immersive_loop.yaml --output Pleiades_video.mp4
```

Replace the path after `--input` with your own photo.

## Guided launcher

On Windows, double-click **`start_wizard.bat`** or drag a photo onto it. Alternatively:

```powershell
.\.venv\Scripts\python.exe wizard.py
```

On the first run, the wizard asks for the **StarNet2 executable**, **photo folder**, **video folder**, and **FFmpeg/FFprobe**. After that, you can enter just a filename from the saved photo folder or a full image path. Wizard prompts are currently in German.

For each video, choose duration, FPS, resolution, format, seamless loop, title, subtitle and music. **Press Enter to accept a default**; video preferences are saved for the next run. Titles and subtitles are entered separately for each photo. `-` clears an optional field. Use `zufall` (random) to generate fresh ambient music for each render.

An optional menu controls background zoom, rotation, lateral star motion, star count, brightness, loop pace, volume and text size. Before rendering, the wizard shows your choices and asks whether to start. Replacing an existing video requires explicit confirmation.

Update saved paths: `start_wizard.bat --setup`. Check settings without rendering: `start_wizard.bat --dry-run`. On Linux/macOS, run `python wizard.py` with the project environment activated.

Local settings are stored in `.astromotion-wizard.json`, which Git ignores. The wizard uses the same StarNet2 pipeline and Python interpreter as the command-line launcher.

## Demos

My own photos, captured with **Seestar S50 Pro** and processed with **AstroWizard**. You may use the included photos and demo media.

| Orion Nebula · M42 | Pleiades · M45 |
|---|---|
| [![Orion](examples/real/orion_starnet_preview.gif)](examples/real/orion_starnet_demo.mp4) | [![Pleiades](examples/real/pleiades_starnet_preview.gif)](examples/real/pleiades_starnet_demo.mp4) |
| [Original photo](examples/real/orion.jpg) · [Video with music](examples/real/orion_starnet_demo.mp4) | [Original photo](examples/real/pleiades.jpg) · [Video with music](examples/real/pleiades_starnet_demo.mp4) |

Each video is 30 seconds, 1080 × 1920, 30 FPS, H.264/AAC. GIFs are silent previews with a reduced color palette; open the MP4s to assess image quality and hear the music.

## Installation

### Windows

`setup.bat` uses the same interpreter as `start_windows.bat`: **`.venv\Scripts\python.exe`**. It reuses an existing project environment, installs `requirements.txt`, checks package imports, and stops with a clear message if something fails. `setup_windows.bat` remains available as an alternative entry point.

For manual installation, skip the first line if `.venv` already exists:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, install directly with the project interpreter and use that interpreter to launch AstroMotion as well:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Linux / macOS

Install Python 3.11+, `venv`, FFmpeg/FFprobe, and the official StarNet2 CLI package for your platform.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py --input examples/real/pleiades.jpg --starnet "/path/to/starnet2" --config configs/immersive_loop.yaml --output Pleiades_video.mp4
```

If necessary, make the StarNet2 executable runnable with `chmod +x /path/to/starnet2`.

## Customize your video

Start with **[`configs/immersive_loop.yaml`](configs/immersive_loop.yaml)**. This setup provides the main effect shown in the demos: individual star flight, calm background movement and a seamless loop, without additional visual effects.

Append these options to your launch command:

| Goal | Option |
|---|---|
| Longer, slower loop video | `--duration 45` |
| Landscape / square format | `--format landscape` / `--format square` |
| Resolution | `--resolution 720p`, `1080p` or `4k` |
| Frame rate | `--fps 24`, `30` or `60` |
| Repeat the same music variation | `--seed 1234` |
| Your own music / no audio | `--audio "music.wav"` / `--music none` |
| Display an object name | `--title "Pleiades"` |
| Add a second line of text | `--subtitle "MESSIER 45"` |
| Disable looping | `--no-loop` |
| Replace an existing output file | `--overwrite` |

**Optional text overlay:** `--title` enables the caption; `--subtitle` adds a second line. For example, append:

```powershell
--title "Pleiades" --subtitle "MESSIER 45"
```

Without these options, text overlays remain disabled in the recommended setup.

**Loop pace:** With the same settings, movement is spread over the video duration. A 45-second loop feels slower than a 30-second loop; a 2-second test compresses the entire flight. `--speed` controls background movement, not the overall pace of individual star flight.

To customize motion, make a copy:

```powershell
Copy-Item configs\immersive_loop.yaml my_config.yaml
```

Edit the values in `my_config.yaml`, then launch with **`--config my_config.yaml`**:

| Setting | Recommended setup | Behavior |
|---|---|---|
| `motion.zoom` | `0.14` | Background zoom up to 14%; lower = calmer, `0` = no zoom |
| `motion.rotation_deg` | `2.0` | Background rotation range in degrees; `0` = no rotation |
| `starfield.drift_x` / `drift_y` | `0.12` / `-0.035` | Lateral star movement; smaller magnitudes = less drift |
| `starfield.rotation_deg` | `4.75` | Star-flight rotation range in degrees; `0` = no rotation |
| `starfield.count` | `4500` | Maximum number of animated stars actually detected in the photo |
| `starfield.foreground_gain` | `1.15` | Brightness of the flying stars |
| `starfield.seed` | `2026` | Reproducible artistic depth distribution |
| `audio.gain` | `0.7` | Audio volume |
| `audio.seed` | `null` | Fresh ambient music per render; an integer repeats a variation |

Star depths are assigned artistically, not measured astronomical distances. In a seamless loop, stars fly forward while the background moves gently in and out. Music is crossfaded at the seam. You can also set `star_cycles: 1` in the `loop` section: `2` gives two complete star traversals per video, increasing the pace. Keep it at `1` for a calm flight. `starfield.travel` affects star movement only when looping is disabled.

CLI options override the configuration file. Relative file paths inside a configuration are resolved from that file's folder. `--print-config` shows the effective settings without rendering.

## Photos and star separation

Use a finished, stretched RGB astrophotograph, such as JPG, PNG or TIFF. AstroMotion uses only **genuine StarNet2 separation**. If you already have a matching StarNet2 starless image, you can reuse it:

```powershell
.\.venv\Scripts\python.exe main.py --input photo.tif --starless photo_starless.tif --config configs\immersive_loop.yaml --output video.mp4
```

The original and starless images must have identical dimensions and orientation and come from the same processing state. Output quality depends on the StarNet2 result. Separation does not apply subsequent hole-repair filters or redistribute star colors into the nebula.

## Troubleshooting and development

- **`ModuleNotFoundError`, for example for `tifffile`:** Run `setup.bat` again and launch with `.venv\Scripts\python.exe`.
- **FFmpeg is missing:** Check `ffmpeg -version` and `ffprobe -version`; both must be accessible.
- **StarNet2 does not start:** Check the executable path and that the StarNet2 package is complete. Older CLI packages using positional arguments are supported through `--starnet-mode legacy`.

Logs, layer images and the render report are saved alongside the video under `<video>_assets/`.

For development, start with the small [StarNet2 demo test](examples/real/README.md) (German instructions). Manual runs of the [Actions workflow](.github/workflows/starnet-demos.yml) default to a 2-second M45 test; choose `gallery` explicitly for full demos. Run tests without video rendering:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q -m "not video_render"
```

The earlier issue analysis and checks are documented in the [pipeline report](CLEAN_PIPELINE_REPORT.md) (German).

## Licenses

AstroMotion: [MIT](LICENSE). External components: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) (German). StarNet2 and model weights are obtained and licensed separately. Ambient music is synthesized locally, without samples from other recordings.
