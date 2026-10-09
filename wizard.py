"""Interactive AstroMotion launcher; paths are saved locally, rendering uses main.py."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / '.astromotion-wizard.json'
PRESET = ROOT / 'configs' / 'immersive_loop.yaml'
IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.tif', '.tiff'}


def path_value(value: str, base: Path = ROOT) -> Path:
    value = value.strip().strip('\"').strip("'")
    path = Path(os.path.expandvars(value)).expanduser()
    return (path if path.is_absolute() else base / path).resolve()


def ask_text(label: str, default: str = '') -> str:
    value = input(f'{label}' + (f' [{default}]' if default else '') + ': ').strip()
    return '' if value == '-' else value or default


def ask_choice(label: str, choices: tuple, default):
    while True:
        value = ask_text(f'{label} ({" / ".join(map(str, choices))})', str(default)).lower()
        for choice in choices:
            if value == str(choice).lower():
                return choice
        print('Bitte einen der angezeigten Werte eingeben.')


def ask_number(label: str, default, low: float, high: float, *, integer: bool = False):
    while True:
        try:
            raw = ask_text(label, str(default)).replace(',', '.')
            value = int(raw) if integer else float(raw)
            if math.isfinite(value) and low <= value <= high:
                return value
        except ValueError:
            pass
        print(f'Bitte eine {"ganze " if integer else ""}Zahl von {low} bis {high} eingeben.')


def ask_yes(label: str, default: bool = False) -> bool:
    return ask_choice(label, ('j', 'n'), 'j' if default else 'n') == 'j'


def ask_file(label: str, default: str = '', *, base: Path = ROOT, suffixes=None) -> Path:
    while True:
        value = ask_text(label, default)
        if value:
            path = path_value(value, base)
            if path.is_file() and (suffixes is None or path.suffix.lower() in suffixes):
                return path
        print('Bitte eine vorhandene Datei' + (f' ({", ".join(sorted(suffixes))})' if suffixes else '') + ' angeben, keinen Ordner.')


def ask_directory(label: str, default: str, *, create: bool = False) -> Path:
    while True:
        value = ask_text(label, default)
        if value:
            path = path_value(value)
            try:
                if create:
                    path.mkdir(parents=True, exist_ok=True)
                if path.is_dir():
                    return path
            except OSError as exc:
                print(f'Ordner nicht verfuegbar: {exc}')
        print('Bitte einen gueltigen Ordner angeben.')


def ask_binary(label: str, default: str) -> str:
    while True:
        value = ask_text(label, default).strip('\"').strip("'")
        resolved = shutil.which(value) if value else None
        if resolved:
            return str(Path(resolved).resolve())
        if value:
            path = path_value(value)
            if path.is_file() and os.access(path, os.X_OK):
                return str(path)
        print('Programm nicht gefunden. Namen im PATH oder vollstaendigen EXE-Pfad angeben.')


def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('version') != 1:
            raise ValueError('Unbekanntes Format')
        if not isinstance(data.get('paths'), dict) or not isinstance(data.get('defaults', {}), dict):
            raise ValueError('Pfade oder Vorgaben fehlen')
        if not all(isinstance(data['paths'].get(k), str) for k in ('starnet', 'input_dir', 'output_dir', 'ffmpeg', 'ffprobe')):
            raise ValueError('Ungültige Pfade')
        return data
    except (ValueError, OSError) as exc:
        raise ValueError(f'Einstellungen nicht lesbar: {exc}. Mit --setup neu einrichten.') from exc


def save_settings(path: Path, settings: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Close the temporary file before replacement/cleanup (also on Windows).
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix=path.name + '.', suffix='.tmp', delete=False) as file:
            temporary = Path(file.name)
            file.write(json.dumps(settings, indent=2, ensure_ascii=False) + '\n')
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def configure_paths(old: dict) -> dict:
    print('\nEinmalige Einrichtung: Pfade werden fuer weitere Starts gespeichert.')
    paths = old.get('paths', {})
    starnet = ask_file('StarNet2: vollstaendiger Pfad zur EXE', paths.get('starnet', ''))
    input_dir = ask_directory('Ordner mit Astrofotos', paths.get('input_dir', str(ROOT / 'examples' / 'real')))
    output_dir = ask_directory('Ordner fuer fertige Videos', paths.get('output_dir', str(ROOT / 'videos')), create=True)
    ffmpeg = ask_binary('FFmpeg', paths.get('ffmpeg', 'ffmpeg'))
    ffprobe = ask_binary('FFprobe', paths.get('ffprobe', 'ffprobe'))
    return {'version': 1, 'paths': {'starnet': str(starnet), 'input_dir': str(input_dir),
                                  'output_dir': str(output_dir), 'ffmpeg': ffmpeg, 'ffprobe': ffprobe},
            'defaults': old.get('defaults', {})}


def validate_paths(settings: dict) -> None:
    paths = settings['paths']
    if not Path(paths['starnet']).is_file():
        raise ValueError('Gespeicherte StarNet2-EXE fehlt. Mit --setup den Pfad aktualisieren.')
    if not Path(paths['input_dir']).is_dir():
        raise ValueError('Gespeicherter Bilderordner fehlt. Mit --setup den Pfad aktualisieren.')
    for key in ('ffmpeg', 'ffprobe'):
        if not shutil.which(paths[key]):
            raise ValueError(f'{key} nicht gefunden. Mit --setup den Pfad aktualisieren.')
    Path(paths['output_dir']).mkdir(parents=True, exist_ok=True)


def collect_render(settings: dict, supplied_input: Path | None = None):
    from astromotion.config import load_config

    paths = settings['paths']
    cfg = load_config(PRESET, settings.get('defaults', {}))
    cfg.separation.executable = paths['starnet']
    cfg.encoding.ffmpeg, cfg.encoding.ffprobe = paths['ffmpeg'], paths['ffprobe']
    cfg.caption.enabled, cfg.caption.title, cfg.caption.subtitle = False, '', ''
    input_dir = Path(paths['input_dir'])
    print('\nVideo einstellen. Enter = Vorgabe, - = optionales Feld leeren. Strg+C = abbrechen.')
    if supplied_input:
        image = path_value(str(supplied_input), input_dir)
        if not image.is_file() or image.suffix.lower() not in IMAGE_SUFFIXES:
            raise ValueError('Das angegebene Bild ist keine vorhandene JPG-, PNG- oder TIFF-Datei.')
    else:
        image = ask_file('Bildname oder vollstaendiger Bildpfad', base=input_dir, suffixes=IMAGE_SUFFIXES)
    cfg.duration = ask_number('Videolaenge in Sekunden (laenger = langsamerer Loop)', cfg.duration, 1, 3600)
    cfg.fps = ask_choice('FPS', (24, 30, 60), cfg.fps)
    cfg.resolution = ask_choice('Aufloesung', ('720p', '1080p', '4k'), cfg.resolution)
    cfg.format = ask_choice('Format', ('vertical', 'square', 'landscape'), cfg.format)
    cfg.loop.enabled = ask_yes('Perfect Loop', cfg.loop.enabled)
    while True:
        title = ask_text('Titel (leer = ohne Text)')
        subtitle = ask_text('Untertitel (optional)') if title else ''
        if all(len(text) <= 100 and all(ord(c) >= 32 for c in text) for text in (title, subtitle)):
            cfg.caption.title, cfg.caption.subtitle, cfg.caption.enabled = title, subtitle, bool(title)
            break
        print('Pro Textzeile maximal 100 Zeichen und keine Steuerzeichen verwenden.')
    cfg.audio.mode = ask_choice('Musik', ('ambient', 'none', 'file'), cfg.audio.mode)
    if cfg.audio.mode == 'file':
        cfg.audio.file = str(ask_file('Eigene Musikdatei', cfg.audio.file or '', suffixes={'.mp3', '.wav'}))
    elif cfg.audio.mode == 'ambient':
        while True:
            raw = ask_text('Musik-Seed (zufall oder ganze Zahl)', str(cfg.audio.seed) if cfg.audio.seed is not None else 'zufall')
            if raw.lower() == 'zufall' or not raw:
                cfg.audio.seed = None
                break
            try:
                seed = int(raw)
                if 0 <= seed < 2**32:
                    cfg.audio.seed = seed
                    break
            except ValueError:
                pass
            print('Bitte zufall oder eine ganze Zahl von 0 bis 4294967295 eingeben.')
    if ask_yes('Bewegung, Lautstaerke und Textdarstellung anpassen'):
        cfg.motion.zoom = ask_number('Hintergrundzoom (0.14 = 14 %)', cfg.motion.zoom, 0, .5)
        cfg.motion.rotation_deg = ask_number('Hintergrunddrehung in Grad', cfg.motion.rotation_deg, -10, 10)
        cfg.starfield.drift_x = ask_number('Sternflug seitlich X', cfg.starfield.drift_x, -.5, .5)
        cfg.starfield.drift_y = ask_number('Sternflug seitlich Y', cfg.starfield.drift_y, -.5, .5)
        cfg.starfield.rotation_deg = ask_number('Sternflug Drehung in Grad', cfg.starfield.rotation_deg, -15, 15)
        cfg.starfield.count = ask_number('Maximale Sternanzahl', cfg.starfield.count, 1, 20000, integer=True)
        cfg.starfield.foreground_gain = ask_number('Helligkeit der fliegenden Sterne', cfg.starfield.foreground_gain, 0, 3)
        if cfg.loop.enabled:
            cfg.loop.star_cycles = ask_number('Sterndurchlaeufe pro Loop (1 = ruhig)', cfg.loop.star_cycles, 1, 5, integer=True)
        else:
            cfg.starfield.travel = ask_number('Flugstrecke', cfg.starfield.travel, 0, 20)
        cfg.audio.gain = ask_number('Musiklautstaerke', cfg.audio.gain, 0, 2)
        if cfg.caption.enabled:
            cfg.caption.title_size = ask_number('Titelgroesse', cfg.caption.title_size, 12, 100, integer=True)
            cfg.caption.subtitle_size = ask_number('Untertitelgroesse', cfg.caption.subtitle_size, 10, 80, integer=True)
            cfg.caption.opacity = ask_number('Textdeckkraft', cfg.caption.opacity, 0, 1)
    cfg.validate()
    output_dir = Path(paths['output_dir'])
    while True:
        output = path_value(ask_text('Ausgabename', image.stem + '_astromotion.mp4'), output_dir)
        if output.suffix.lower() != '.mp4' or output == image:
            print('Bitte einen anderen Ausgabepfad mit Endung .mp4 verwenden.')
            continue
        if output.exists() and not output.is_file():
            print('Der Ausgabepfad ist ein Ordner. Bitte einen Dateinamen waehlen.')
            continue
        overwrite = output.exists() and ask_yes('Video existiert bereits. Ersetzen')
        if output.exists() and not overwrite:
            print('Bitte einen anderen Ausgabenamen waehlen.')
            continue
        return image, output, cfg, overwrite


def remembered_defaults(cfg) -> dict:
    data = asdict(cfg)
    # Object names belong to the selected image, never to the next photo.
    data['caption'].update(enabled=False, title='', subtitle='')
    return data


def render_command(image: Path, output: Path, config_path: Path, overwrite: bool) -> list[str]:
    command = [sys.executable, str(ROOT / 'main.py'), '--input', str(image),
               '--config', str(config_path), '--output', str(output)]
    if overwrite:
        command.append('--overwrite')
    return command


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='AstroMotion: gefuehrter Video-Start mit gespeicherten Pfaden')
    parser.add_argument('--setup', action='store_true', help='Gespeicherte Grundpfade neu einrichten')
    parser.add_argument('--input', type=Path, help='Bildname oder Bildpfad vorgeben (auch Drag-and-drop)')
    parser.add_argument('--dry-run', action='store_true', help='Einstellungen anzeigen und speichern, kein Video rendern')
    parser.add_argument('--settings', type=Path, default=SETTINGS, help='Lokale Einstellungsdatei')
    args = parser.parse_args(argv)
    try:
        if sys.version_info < (3, 11):
            raise ValueError('Python 3.11+ erforderlich.')
        settings_path = args.settings.expanduser().resolve()
        try:
            settings = load_settings(settings_path)
        except ValueError:
            if not args.setup:
                raise
            settings = {}
        if args.setup or not settings:
            settings = configure_paths(settings)
            save_settings(settings_path, settings)
        validate_paths(settings)
        image, output, cfg, overwrite = collect_render(settings, args.input)
        print(f'\nBild: {image}\nVideo: {output}\n{cfg.duration:g} s, {cfg.fps} FPS, '
              f'{cfg.resolution}, {cfg.format}, Loop: {"an" if cfg.loop.enabled else "aus"}, Musik: {cfg.audio.mode}')
        if cfg.caption.enabled:
            print(f'Text: {cfg.caption.title}' + (f' / {cfg.caption.subtitle}' if cfg.caption.subtitle else ''))
        if not args.dry_run and not ask_yes('Rendering starten', True):
            print('Rendering abgebrochen.')
            return 0
        settings['defaults'] = remembered_defaults(cfg)
        save_settings(settings_path, settings)
        if args.dry_run:
            print(json.dumps(asdict(cfg), indent=2, ensure_ascii=False))
            print('Vorgaben gespeichert. Kein Video gerendert.')
            return 0
        with tempfile.TemporaryDirectory(prefix='astromotion-wizard-') as folder:
            config_path = Path(folder) / 'render.json'
            config_path.write_text(json.dumps(asdict(cfg), ensure_ascii=False), encoding='utf-8')
            return subprocess.run(render_command(image, output, config_path, overwrite), cwd=ROOT, check=False).returncode
    except (KeyboardInterrupt, EOFError):
        print('\nAbgebrochen.')
        return 130
    except ImportError as exc:
        print(f'Python-Paket fehlt: {exc}. setup.bat ausfuehren und mit .venv/Scripts/python.exe starten.', file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(f'FEHLER: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
