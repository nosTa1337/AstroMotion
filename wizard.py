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

from astromotion.wizard_text import translate

ROOT = Path(__file__).resolve().parent
SETTINGS = ROOT / '.astromotion-wizard.json'
PRESET = ROOT / 'configs' / 'immersive_loop.yaml'
IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.tif', '.tiff'}
LANGUAGE = 'en'


def _t(message: str, **values) -> str:
    return translate(message, LANGUAGE, **values)


def select_language(settings: dict, supplied: str | None = None) -> None:
    global LANGUAGE
    LANGUAGE = supplied or ask_choice('Language / Sprache: en = English, de = Deutsch',
                                      ('en', 'de'), settings.get('language', 'en'))
    settings['language'] = LANGUAGE


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
        print(_t('Please enter one of the displayed values.'))


def ask_number(label: str, default, low: float, high: float, *, integer: bool = False):
    while True:
        try:
            raw = ask_text(label, str(default)).replace(',', '.')
            value = int(raw) if integer else float(raw)
            if math.isfinite(value) and low <= value <= high:
                return value
        except ValueError:
            pass
        print(_t('Please enter a {kind}number between {low} and {high}.',
                 kind=_t('whole ') if integer else '', low=low, high=high))


def ask_yes(label: str, default: bool = False) -> bool:
    yes = 'j' if LANGUAGE == 'de' else 'y'
    while True:
        value = ask_text(f'{label} ({yes} / n)', yes if default else 'n').lower()
        if value in ('y', 'yes', 'j', 'ja'):
            return True
        if value in ('n', 'no', 'nein'):
            return False
        print(_t('Please enter one of the displayed values.'))


def ask_seed(label: str, default: int | None) -> int | None:
    while True:
        random_word = _t('random')
        raw = ask_text(label + _t(' (random or integer)'), str(default) if default is not None else random_word)
        if raw.lower() in ('random', 'zufall') or not raw:
            return None
        try:
            seed = int(raw)
            if 0 <= seed < 2**32:
                return seed
        except ValueError:
            pass
        print(_t('Please enter random or an integer from 0 to 4294967295.'))


def ask_file(label: str, default: str = '', *, base: Path = ROOT, suffixes=None) -> Path:
    while True:
        value = ask_text(label, default)
        if value:
            path = path_value(value, base)
            if path.is_file() and (suffixes is None or path.suffix.lower() in suffixes):
                return path
        print(_t('Please specify an existing file{suffixes}, not a folder.',
                 suffixes=f' ({", ".join(sorted(suffixes))})' if suffixes else ''))


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
                print(_t('Folder unavailable: {error}', error=exc))
        print(_t('Please specify a valid folder.'))


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
        print(_t('Program not found. Enter a name on PATH or the full executable path.'))


def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('version') != 1:
            raise ValueError(_t('Unknown format'))
        if not isinstance(data.get('paths'), dict) or not isinstance(data.get('defaults', {}), dict):
            raise ValueError(_t('Paths or defaults are missing'))
        if not all(isinstance(data['paths'].get(k), str) for k in ('starnet', 'input_dir', 'output_dir', 'ffmpeg', 'ffprobe')):
            raise ValueError(_t('Invalid paths'))
        if data.get('language', 'en') not in ('en', 'de'):
            raise ValueError(_t('Unsupported wizard language'))
        return data
    except (ValueError, OSError) as exc:
        raise ValueError(_t('Cannot read settings: {error}. Run --setup to configure them again.', error=exc)) from exc


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
    print(_t('\nFirst-time setup: paths are saved for future runs.'))
    paths = old.get('paths', {})
    starnet = ask_file(_t('StarNet2: full path to the executable'), paths.get('starnet', ''))
    input_dir = ask_directory(_t('Folder containing astrophotos'), paths.get('input_dir', str(ROOT / 'examples' / 'real')))
    output_dir = ask_directory(_t('Folder for finished videos'), paths.get('output_dir', str(ROOT / 'videos')), create=True)
    ffmpeg = ask_binary('FFmpeg', paths.get('ffmpeg', 'ffmpeg'))
    ffprobe = ask_binary('FFprobe', paths.get('ffprobe', 'ffprobe'))
    return {'version': 1, 'paths': {'starnet': str(starnet), 'input_dir': str(input_dir),
                                  'output_dir': str(output_dir), 'ffmpeg': ffmpeg, 'ffprobe': ffprobe},
            'defaults': old.get('defaults', {}), 'language': LANGUAGE}


def validate_paths(settings: dict) -> None:
    paths = settings['paths']
    if not Path(paths['starnet']).is_file():
        raise ValueError(_t('Saved StarNet2 executable is missing. Run --setup to update the path.'))
    if not Path(paths['input_dir']).is_dir():
        raise ValueError(_t('Saved photo folder is missing. Run --setup to update the path.'))
    for key in ('ffmpeg', 'ffprobe'):
        if not shutil.which(paths[key]):
            raise ValueError(_t('{program} not found. Run --setup to update the path.', program=key))
    Path(paths['output_dir']).mkdir(parents=True, exist_ok=True)


def collect_render(settings: dict, supplied_input: Path | None = None):
    from astromotion.config import MUSIC_STYLES, PROFILES, apply_profile, load_config

    paths = settings['paths']
    cfg = load_config(PRESET, settings.get('defaults', {}))
    cfg.separation.executable = paths['starnet']
    cfg.encoding.ffmpeg, cfg.encoding.ffprobe = paths['ffmpeg'], paths['ffprobe']
    cfg.caption.enabled, cfg.caption.title, cfg.caption.subtitle = False, '', ''
    input_dir = Path(paths['input_dir'])
    print(_t('\nVideo settings. Enter = default, - = clear an optional field. Ctrl+C = cancel.'))
    if supplied_input:
        image = path_value(str(supplied_input), input_dir)
        if not image.is_file() or image.suffix.lower() not in IMAGE_SUFFIXES:
            raise ValueError(_t('The supplied image is not an existing JPG, PNG or TIFF file.'))
    else:
        image = ask_file(_t('Image filename or full image path'), base=input_dir, suffixes=IMAGE_SUFFIXES)
    print(_t('Profiles: relax = very calm, drift = lateral flight, explore = closer framing; custom = your own settings.'))
    profile = ask_choice(_t('Star-flight profile'), tuple(PROFILES), cfg.profile)
    if profile != cfg.profile:
        cfg = apply_profile(cfg, profile)
    cfg.duration = ask_number(_t('Video duration in seconds (longer = slower loop)'), cfg.duration, 1, 3600)
    cfg.fps = ask_choice('FPS', (24, 30, 60), cfg.fps)
    cfg.resolution = ask_choice(_t('Resolution'), ('720p', '1080p', '4k'), cfg.resolution)
    cfg.format = ask_choice('Format', ('vertical', 'square', 'landscape'), cfg.format)
    cfg.loop.enabled = ask_yes('Perfect Loop', cfg.loop.enabled)
    while True:
        title = ask_text(_t('Title (empty = no text)'))
        subtitle = ask_text(_t('Subtitle (optional)')) if title else ''
        if all(len(text) <= 100 and all(ord(c) >= 32 for c in text) for text in (title, subtitle)):
            cfg.caption.title, cfg.caption.subtitle, cfg.caption.enabled = title, subtitle, bool(title)
            break
        print(_t('Use at most 100 characters per text line and no control characters.'))
    cfg.audio.mode = ask_choice(_t('Music'), ('ambient', 'none', 'file'), cfg.audio.mode)
    if cfg.audio.mode == 'file':
        cfg.audio.file = str(ask_file(_t('Your own music file'), cfg.audio.file or '', suffixes={'.mp3', '.wav'}))
    elif cfg.audio.mode == 'ambient':
        print(_t('Music styles: warm = soft pads, deep = low drones, shimmer = bright bells, pulse = gentle arpeggio.'))
        cfg.audio.style = ask_choice(_t('Music style'), MUSIC_STYLES, cfg.audio.style)
        cfg.audio.seed = ask_seed(_t('Music seed'), cfg.audio.seed)
    if ask_yes(_t('Customize motion, volume and text appearance')):
        if cfg.profile != 'custom':
            cfg.profile_variation = ask_yes(_t('Subtle random profile variation'), cfg.profile_variation)
            if cfg.profile_variation:
                cfg.profile_seed = ask_seed(_t('Profile seed'), cfg.profile_seed)
        cfg.motion.zoom = ask_number(_t('Background zoom (0.14 = 14%)'), cfg.motion.zoom, 0, .5)
        cfg.motion.rotation_deg = ask_number(_t('Background rotation in degrees'), cfg.motion.rotation_deg, -10, 10)
        cfg.starfield.drift_x = ask_number(_t('Lateral star motion X'), cfg.starfield.drift_x, -.5, .5)
        cfg.starfield.drift_y = ask_number(_t('Lateral star motion Y'), cfg.starfield.drift_y, -.5, .5)
        cfg.starfield.rotation_deg = ask_number(_t('Star-flight rotation in degrees'), cfg.starfield.rotation_deg, -15, 15)
        cfg.starfield.count = ask_number(_t('Maximum star count'), cfg.starfield.count, 1, 20000, integer=True)
        cfg.starfield.foreground_gain = ask_number(_t('Flying-star brightness'), cfg.starfield.foreground_gain, 0, 3)
        cfg.starfield.color_strength = ask_number(_t('Star color strength (0 = neutral, 1 = full color)'), cfg.starfield.color_strength, 0, 1)
        if cfg.loop.enabled:
            cfg.loop.star_cycles = ask_number(_t('Star passes per loop (1 = calm)'), cfg.loop.star_cycles, 1, 5, integer=True)
        else:
            cfg.starfield.travel = ask_number(_t('Travel distance'), cfg.starfield.travel, 0, 20)
        cfg.audio.gain = ask_number(_t('Music volume'), cfg.audio.gain, 0, 2)
        if cfg.caption.enabled:
            cfg.caption.title_size = ask_number(_t('Title size'), cfg.caption.title_size, 12, 100, integer=True)
            cfg.caption.subtitle_size = ask_number(_t('Subtitle size'), cfg.caption.subtitle_size, 10, 80, integer=True)
            cfg.caption.opacity = ask_number(_t('Text opacity'), cfg.caption.opacity, 0, 1)
    cfg.validate()
    output_dir = Path(paths['output_dir'])
    while True:
        output = path_value(ask_text(_t('Output filename'), image.stem + '_astromotion.mp4'), output_dir)
        if output.suffix.lower() != '.mp4' or output == image:
            print(_t('Please choose a different output path ending in .mp4.'))
            continue
        if output.exists() and not output.is_file():
            print(_t('The output path is a folder. Please choose a filename.'))
            continue
        overwrite = output.exists() and ask_yes(_t('Video already exists. Replace it'))
        if output.exists() and not overwrite:
            print(_t('Please choose a different output filename.'))
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
    global LANGUAGE
    # Select CLI help/error language without importing any render dependencies.
    LANGUAGE = 'en'
    language_parser = argparse.ArgumentParser(add_help=False)
    language_parser.add_argument('--language')
    language_args, _ = language_parser.parse_known_args(argv)
    if language_args.language in ('en', 'de'):
        LANGUAGE = language_args.language
    parser = argparse.ArgumentParser(description=_t('AstroMotion: guided video launcher with saved paths'), add_help=False)
    options = parser.add_argument_group(_t('Options'))
    options.add_argument('-h', '--help', action='help', help=_t('Show this help message and exit'))
    options.add_argument('--language', choices=('en', 'de'),
                        help=_t('Wizard language; skips the language question and saves the selection'))
    options.add_argument('--setup', action='store_true', help=_t('Reconfigure saved paths'))
    options.add_argument('--input', type=Path, help=_t('Supply an image filename or path (also supports drag and drop)'))
    options.add_argument('--dry-run', action='store_true', help=_t('Show and save settings without rendering a video'))
    options.add_argument('--settings', type=Path, default=SETTINGS, help=_t('Local settings file'))
    args = parser.parse_args(argv)
    try:
        if sys.version_info < (3, 11):
            raise ValueError(_t('Python 3.11+ is required.'))
        settings_path = args.settings.expanduser().resolve()
        try:
            settings = load_settings(settings_path)
        except ValueError:
            if not args.setup:
                raise
            settings = {}
        needs_setup = args.setup or not settings
        select_language(settings, args.language)
        if needs_setup:
            settings = configure_paths(settings)
        save_settings(settings_path, settings)
        validate_paths(settings)
        image, output, cfg, overwrite = collect_render(settings, args.input)
        print(_t('\nImage: {image}\nVideo: {output}\n{duration:g} s, {fps} FPS, '
                 '{resolution}, {format}, Loop: {loop}, Profile: {profile}, Music: {music}',
                 image=image, output=output, duration=cfg.duration, fps=cfg.fps,
                 resolution=cfg.resolution, format=cfg.format,
                 loop=_t('on') if cfg.loop.enabled else _t('off'),
                 profile=cfg.profile, music=cfg.audio.mode))
        if cfg.audio.mode == 'ambient':
            print(_t('Music style: {style}', style=cfg.audio.style))
        if cfg.caption.enabled:
            print(_t('Text: {caption}', caption=cfg.caption.title + (f' / {cfg.caption.subtitle}' if cfg.caption.subtitle else '')))
        if not args.dry_run and not ask_yes(_t('Start rendering'), True):
            print(_t('Rendering cancelled.'))
            return 0
        settings['defaults'] = remembered_defaults(cfg)
        save_settings(settings_path, settings)
        if args.dry_run:
            print(json.dumps(asdict(cfg), indent=2, ensure_ascii=False))
            print(_t('Defaults saved. No video rendered.'))
            return 0
        with tempfile.TemporaryDirectory(prefix='astromotion-wizard-') as folder:
            config_path = Path(folder) / 'render.json'
            config_path.write_text(json.dumps(asdict(cfg), ensure_ascii=False), encoding='utf-8')
            return subprocess.run(render_command(image, output, config_path, overwrite), cwd=ROOT, check=False).returncode
    except (KeyboardInterrupt, EOFError):
        print(_t('\nCancelled.'))
        return 130
    except ImportError as exc:
        print(_t('Missing Python package: {error}. Run setup.bat and start with .venv/Scripts/python.exe.', error=exc), file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(_t('ERROR: {error}', error=exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
