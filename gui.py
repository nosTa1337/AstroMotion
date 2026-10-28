"""Small Tk desktop launcher using the existing config, profiles and renderer."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import logging
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

from astromotion.config import CAMERA_TIMINGS, MUSIC_STYLES, PROFILES, RESOLUTIONS, load_config
from astromotion.preview import preview_config
import wizard


TABS = {
    'Video': [('duration', 'Dauer (Sekunden)', None), ('fps', 'Bilder pro Sekunde', (24, 30, 60)),
              ('resolution', 'Auflösung', RESOLUTIONS),
              ('format', 'Format', ('vertical', 'landscape', 'square')),
              ('loop.enabled', 'Nahtloser Loop', None),
              ('profile_variation', 'Zufällige Profilvariation', None),
              ('profile_seed', 'Profil-Seed (leer = zufällig)', None)],
    'Bewegung': [('motion.zoom', 'Hintergrundzoom (0.14 = 14 %)', None),
                 ('motion.rotation_deg', 'Hintergrunddrehung (Grad)', None),
                 ('motion.timing', 'Verlauf (steady = gleichmäßig)', CAMERA_TIMINGS),
                 ('motion.speed', 'Geschwindigkeit', None),
                 ('motion.pan_x', 'Kameraversatz X', None), ('motion.pan_y', 'Kameraversatz Y', None)],
    'Sterne': [('starfield.enabled', 'Einzelner Sternflug', None),
               ('starfield.count', 'Maximale Sternanzahl', None),
               ('starfield.rotation_deg', 'Sterndrehung (Grad)', None),
               ('starfield.drift_x', 'Seitliche Bewegung X', None),
               ('starfield.drift_y', 'Seitliche Bewegung Y', None),
               ('starfield.foreground_gain', 'Helligkeit', None),
               ('starfield.color_strength', 'Farbstärke (0 bis 1)', None),
               ('loop.star_cycles', 'Sternflüge pro Loop (1 bis 5)', None),
               ('starfield.travel', 'Flugstrecke ohne Loop', None)],
    'Text': [('caption.title', 'Titel (leer = keine Einblendung)', None),
             ('caption.subtitle', 'Untertitel', None), ('caption.title_size', 'Titelgröße bei 1080p', None),
             ('caption.subtitle_size', 'Untertitelgröße bei 1080p', None),
             ('caption.opacity', 'Deckkraft (0 bis 1)', None),
             ('caption.start_seconds', 'Einblenden ab Sekunde', None),
             ('caption.fade_seconds', 'Ein-/Ausblenddauer (Sekunden)', None),
             ('caption.hold_seconds', 'Lesedauer (Sekunden)', None)],
    'Musik': [('audio.mode', 'Musik', ('ambient', 'none', 'file')),
              ('audio.style', 'Musikstil', MUSIC_STYLES),
              ('audio.seed', 'Musik-Seed (leer = zufällig)', None),
              ('audio.gain', 'Lautstärke (0 bis 2)', None),
              ('audio.development', 'Musikalische Entwicklung (0 bis 1)', None),
              ('audio.file', 'Eigene MP3-/WAV-Datei', 'file')],
    'Programme': [('separation.executable', 'StarNet2-Programm', 'file'),
                  ('encoding.ffmpeg', 'FFmpeg', 'file'), ('encoding.ffprobe', 'FFprobe', 'file')],
}


def value_at(data, key):
    for part in key.split('.'):
        data = data[part]
    return data


def form_config(base, values):
    """Parse form values without losing settings absent from the small GUI."""
    data = asdict(base)
    for fields in TABS.values():
        for key, label, _ in fields:
            target = data
            parts = key.split('.')
            for part in parts[:-1]:
                target = target[part]
            current, raw = target[parts[-1]], values[key]
            try:
                if key in ('audio.seed', 'profile_seed'):
                    value = int(raw) if str(raw).strip() else None
                elif isinstance(current, bool):
                    if type(raw) is not bool:
                        raise ValueError('Bitte ein- oder ausschalten.')
                    value = raw
                elif isinstance(current, int):
                    value = int(raw)
                elif isinstance(current, float):
                    value = float(str(raw).replace(',', '.'))
                else:
                    value = str(raw).strip() or (None if current is None or key == 'audio.file' else '')
            except (ValueError, TypeError) as exc:
                raise ValueError(f'{label}: ungültiger Wert.') from exc
            target[parts[-1]] = value
    data['caption']['enabled'] = bool(data['caption']['title'])
    return load_config(overrides=data)


def validate_files(image: Path, output: Path, cfg, starless: Path | None):
    from astromotion.encoding import resolve_binary

    if not image.is_file() or image.suffix.lower() not in wizard.IMAGE_SUFFIXES:
        raise ValueError('Bitte ein vorhandenes JPG-, PNG- oder TIFF-Bild auswählen.')
    if output.suffix.lower() != '.mp4' or output == image or output == starless:
        raise ValueError('Bitte einen anderen Ausgabepfad mit Endung .mp4 auswählen.')
    if output.exists() and not output.is_file():
        raise ValueError('Der Video-Ausgabepfad ist ein Ordner.')
    if starless:
        if not starless.is_file() or starless.suffix.lower() not in wizard.IMAGE_SUFFIXES:
            raise ValueError('Das optionale Starless-Bild muss eine vorhandene Bilddatei sein.')
    elif not cfg.separation.executable or not Path(cfg.separation.executable).is_file():
        raise ValueError('Unter Programme das StarNet2-Programm auswählen oder ein Starless-Bild angeben.')
    resolve_binary(cfg.encoding.ffmpeg)
    if cfg.encoding.verify:
        resolve_binary(cfg.encoding.ffprobe)
    if cfg.audio.mode == 'file' and (not Path(cfg.audio.file).is_file()
                                    or Path(cfg.audio.file).suffix.lower() not in ('.mp3', '.wav')):
        raise ValueError('Bitte eine vorhandene MP3-/WAV-Datei auswählen.')


class RenderCancelled(Exception):
    pass


class RenderTask:
    """Worker sends events only; every Tk operation remains on the UI thread."""
    def __init__(self):
        self.events = queue.Queue()
        self.cancel = threading.Event()

    def run(self, image, output, cfg, starless, overwrite, cache):
        events, cancel = self.events, self.cancel

        class LogHandler(logging.Handler):
            def emit(self, record):
                events.put(('log', self.format(record)))

        handler = LogHandler()
        handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        logger = logging.getLogger()
        old_level = logger.level
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        last = 0.0

        def progress(done, total, elapsed):
            nonlocal last
            if cancel.is_set():
                raise RenderCancelled()
            if time.monotonic() - last >= .1 or done == total:
                events.put(('progress', (done, total, elapsed)))
                last = time.monotonic()

        try:
            from astromotion.pipeline import render
            if cancel.is_set():
                raise RenderCancelled()
            render(image, output, cfg, starless, progress, overwrite, starnet_cache=cache)
            events.put(('done', output))
        except RenderCancelled:
            events.put(('cancelled', None))
        except Exception as exc:
            logger.exception('Rendering fehlgeschlagen')
            events.put(('error', str(exc)))
        finally:
            logger.removeHandler(handler)
            logger.setLevel(old_level)
            handler.close()


class AstroMotionApp:
    def __init__(self, root, settings_path=wizard.SETTINGS, image=None):
        self.root, self.settings_path = root, settings_path
        self.settings = wizard.load_settings(settings_path)
        self.cfg = load_config(wizard.PRESET, self.settings.get('defaults', {}))
        paths = self.settings.get('paths', {})
        self.cfg.separation.executable = paths.get('starnet', self.cfg.separation.executable)
        self.cfg.encoding.ffmpeg = paths.get('ffmpeg', self.cfg.encoding.ffmpeg)
        self.cfg.encoding.ffprobe = paths.get('ffprobe', self.cfg.encoding.ffprobe)
        self.image = tk.StringVar(value=str(image) if image else '')
        self.output = tk.StringVar()
        self.starless = tk.StringVar()
        self.profile = tk.StringVar(value='Aktuelle Einstellungen')
        self.status = tk.StringVar(value='Bild auswählen und Programme prüfen. Bereit.')
        self.vars, self.profile_values = {}, {}
        self.task = self.worker = None
        self.cache = None
        self.last_video = None
        self.closing = False
        root.title('AstroMotion · Foto zu Sternflug')
        root.geometry('960x850')
        root.minsize(820, 760)
        root.protocol('WM_DELETE_WINDOW', self.close)
        self._build()
        self.fill(self.cfg)
        self.refresh_profiles()
        if image:
            self.set_image(image)
        root.after(100, self.poll)

    def _build(self):
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='AstroMotion', font=('Segoe UI', 22, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Astrofoto auswählen · Profil anpassen · Sternflug exportieren').pack(anchor='w', pady=(0, 12))
        self.editor = ttk.Frame(frame)
        self.editor.pack(fill='both', expand=True)
        files = ttk.LabelFrame(self.editor, text='Dateien', padding=10)
        files.pack(fill='x')
        for row, (label, variable, command) in enumerate([
                ('Originalfoto', self.image, self.choose_image),
                ('Video (.mp4)', self.output, self.choose_output),
                ('Starless (optional)', self.starless, self.choose_starless)]):
            ttk.Label(files, text=label).grid(row=row, column=0, sticky='w', padx=(0, 10), pady=3)
            ttk.Entry(files, textvariable=variable).grid(row=row, column=1, sticky='ew', pady=3)
            ttk.Button(files, text='Auswählen …', command=command).grid(row=row, column=2, padx=(8, 0))
        files.columnconfigure(1, weight=1)
        profiles = ttk.Frame(self.editor, padding=(0, 10))
        profiles.pack(fill='x')
        ttk.Label(profiles, text='Profil').pack(side='left', padx=(0, 10))
        self.profile_box = ttk.Combobox(profiles, textvariable=self.profile, state='readonly', width=48)
        self.profile_box.pack(side='left', fill='x', expand=True)
        ttk.Button(profiles, text='Laden', command=self.load_profile).pack(side='left', padx=8)
        ttk.Button(profiles, text='Als Profil speichern …', command=self.save_profile).pack(side='left')
        tabs = ttk.Notebook(self.editor)
        tabs.pack(fill='both', expand=True)
        for title, fields in TABS.items():
            page = ttk.Frame(tabs, padding=12)
            tabs.add(page, text=title)
            page.columnconfigure(1, weight=1)
            for row, (key, label, choices) in enumerate(fields):
                current = value_at(asdict(self.cfg), key)
                variable = tk.BooleanVar() if isinstance(current, bool) else tk.StringVar()
                self.vars[key] = variable
                if isinstance(current, bool):
                    ttk.Checkbutton(page, text=label, variable=variable).grid(row=row, column=0, columnspan=2, sticky='w', pady=5)
                    continue
                ttk.Label(page, text=label).grid(row=row, column=0, sticky='w', padx=(0, 16), pady=5)
                if choices and choices != 'file':
                    control = ttk.Combobox(page, textvariable=variable, values=choices, state='readonly')
                else:
                    control = ttk.Entry(page, textvariable=variable)
                control.grid(row=row, column=1, sticky='ew', pady=5)
                if choices == 'file':
                    ttk.Button(page, text='Auswählen …', command=lambda v=variable: self.choose_file(v)).grid(row=row, column=2, padx=(8, 0))
        actions = ttk.Frame(frame, padding=(0, 12))
        actions.pack(fill='x')
        self.preview_button = ttk.Button(actions, text='360p-Vorschau rendern', command=lambda: self.start(True))
        self.preview_button.pack(side='left')
        self.render_button = ttk.Button(actions, text='Video exportieren', command=lambda: self.start(False))
        self.render_button.pack(side='left', padx=8)
        self.cancel_button = ttk.Button(actions, text='Abbrechen', command=self.cancel, state='disabled')
        self.cancel_button.pack(side='left')
        self.open_button = ttk.Button(actions, text='Video öffnen', command=self.open_video, state='disabled')
        self.open_button.pack(side='right')
        self.progress = ttk.Progressbar(frame, maximum=100)
        self.progress.pack(fill='x')
        ttk.Label(frame, textvariable=self.status, wraplength=870).pack(anchor='w', pady=6)
        self.log = ScrolledText(frame, height=7, state='disabled', wrap='word')
        self.log.pack(fill='x')

    def fill(self, cfg):
        data = asdict(cfg)
        for key, variable in self.vars.items():
            value = value_at(data, key)
            variable.set('' if value is None else value)
        self.cfg = cfg

    def read_config(self):
        return form_config(self.cfg, {key: variable.get() for key, variable in self.vars.items()})

    def choose_file(self, variable):
        path = filedialog.askopenfilename(parent=self.root)
        if path:
            variable.set(path)

    def choose_image(self):
        path = filedialog.askopenfilename(parent=self.root, title='Astrofoto auswählen',
                                          initialdir=self.settings.get('paths', {}).get('input_dir', str(wizard.ROOT)),
                                          filetypes=[('Astrofotos', '*.jpg *.jpeg *.png *.tif *.tiff')])
        if path:
            self.set_image(Path(path))

    def set_image(self, image):
        self.image.set(str(image))
        folder = Path(self.settings.get('paths', {}).get('output_dir', str(wizard.ROOT / 'videos')))
        self.output.set(str(folder / (image.stem + '_astromotion.mp4')))
        self.cache = None
        self.starless.set('')
        self.vars['caption.title'].set('')
        self.vars['caption.subtitle'].set('')

    def choose_output(self):
        path = filedialog.asksaveasfilename(parent=self.root, title='Video speichern unter',
                                           defaultextension='.mp4', filetypes=[('MP4-Video', '*.mp4')])
        if path:
            self.output.set(path)

    def choose_starless(self):
        self.choose_file(self.starless)

    def refresh_profiles(self):
        self.profile_values = {'Aktuelle Einstellungen': self.settings.get('defaults', {})}
        for name in PROFILES:
            if name != 'custom':
                self.profile_values[f'Sternflug: {name}'] = {'builtin': name}
        for name, entry in self.settings.get('favorites', {}).items():
            self.profile_values[f'Gespeichert: {name}'] = entry['defaults']
        for i, entry in enumerate(self.settings.get('history', []), 1):
            self.profile_values[f'Zuletzt {i}: {entry["image"]} · {entry["saved_at"]}'] = entry['defaults']
        self.profile_box['values'] = tuple(self.profile_values)

    def load_profile(self):
        try:
            values = self.profile_values[self.profile.get()]
            if 'builtin' in values:
                from astromotion.config import apply_profile
                cfg = apply_profile(self.read_config(), values['builtin'])
            else:
                cfg = load_config(wizard.PRESET, values)
            # Object names and program paths belong to this session, not a profile.
            cfg.caption.title = self.vars['caption.title'].get()
            cfg.caption.subtitle = self.vars['caption.subtitle'].get()
            cfg.caption.enabled = bool(cfg.caption.title)
            for key in ('separation.executable', 'encoding.ffmpeg', 'encoding.ffprobe'):
                group, field = key.split('.')
                setattr(getattr(cfg, group), field, self.vars[key].get() or None)
            cfg.validate()
            self.fill(cfg)
            self.status.set('Profil geladen. Einstellungen können jetzt angepasst werden.')
        except (ValueError, KeyError) as exc:
            messagebox.showerror('Profil nicht geladen', str(exc), parent=self.root)

    def persist(self, cfg, image=None, exact_cfg=None):
        from copy import deepcopy
        settings = deepcopy(self.settings)
        paths = settings.setdefault('paths', {})
        paths.update(starnet=cfg.separation.executable or '', ffmpeg=cfg.encoding.ffmpeg,
                     ffprobe=cfg.encoding.ffprobe)
        paths.setdefault('input_dir', str(wizard.ROOT))
        paths.setdefault('output_dir', str(wizard.ROOT / 'videos'))
        if image:
            paths.update(input_dir=str(image.parent), output_dir=str(Path(self.output.get()).expanduser().resolve().parent))
            wizard.remember_recent_settings(settings, image, cfg, exact_cfg)
        settings.update(version=1, defaults=wizard.remembered_defaults(cfg))
        wizard.save_settings(self.settings_path, settings)
        self.settings = settings
        self.refresh_profiles()

    def save_profile(self):
        if self.worker:
            return
        try:
            cfg = self.read_config()
            name = simpledialog.askstring('Profil speichern', 'Profilname (1 bis 60 Zeichen):', parent=self.root)
            if name is None:
                return
            name = name.strip()
            if not wizard.valid_profile_name(name):
                raise ValueError('Bitte 1 bis 60 Zeichen ohne Steuerzeichen eingeben.')
            favorites = self.settings.get('favorites', {})
            existing = next((key for key in favorites if key.casefold() == name.casefold()), None)
            if existing and not messagebox.askyesno('Profil ersetzen?', f'„{existing}“ ersetzen?', parent=self.root):
                return
            from copy import deepcopy
            previous = deepcopy(self.settings)
            self.settings.setdefault('favorites', {})[existing or name] = {
                'defaults': wizard.remembered_defaults(cfg), 'music': 'unchanged'}
            try:
                self.persist(cfg)
            except OSError:
                self.settings = previous
                raise
            self.profile.set(f'Gespeichert: {existing or name}')
            self.status.set('Profil gespeichert. Leere Seeds erzeugen weiterhin neue Variationen.')
        except (ValueError, OSError) as exc:
            messagebox.showerror('Profil nicht gespeichert', str(exc), parent=self.root)

    def start(self, preview):
        if self.worker:
            return
        try:
            cfg = self.read_config()
            if not self.image.get().strip() or not self.output.get().strip():
                raise ValueError('Bitte Originalfoto und Video-Ausgabepfad auswählen.')
            image = Path(self.image.get()).expanduser().resolve()
            output = Path(self.output.get()).expanduser().resolve()
            starless = Path(self.starless.get()).expanduser().resolve() if self.starless.get().strip() else None
            destination = wizard.preview_output_path(output) if preview else output
            validate_files(image, destination, cfg, starless)
            overwrite = destination.exists()
            if overwrite and not messagebox.askyesno('Video ersetzen?', f'{destination}\n\nVorhandenes Video ersetzen?', parent=self.root):
                return
            resolved = wizard.paired_render_config(cfg)
            self.persist(cfg, image, resolved)
            # Keep resolved seeds in the form for matching preview/full exports.
            self.fill(resolved)
            render_cfg = preview_config(resolved) if preview else resolved
            cache = None if starless else self.cache
            if cache is None and not starless and not preview:
                candidate = wizard.preview_output_path(output)
                cache = candidate.parent / (candidate.stem + '_assets')
            self.task = RenderTask()
            self.worker = threading.Thread(target=self.task.run,
                args=(image, destination, render_cfg, starless, overwrite, cache))
            self.status.set('Vorbereitung / Sternentrennung … Der erste Frame kann etwas dauern.')
            self.progress['value'] = 0
            self.open_button['state'] = 'disabled'
            self.busy(True)
            self.worker.start()
        except (ValueError, OSError) as exc:
            messagebox.showerror('Rendering nicht gestartet', str(exc), parent=self.root)

    def busy(self, active):
        self.preview_button['state'] = self.render_button['state'] = 'disabled' if active else 'normal'
        self.cancel_button['state'] = 'normal' if active else 'disabled'
        for page in self.editor.winfo_children():
            self._disable(page, active)

    def _disable(self, widget, active):
        if isinstance(widget, (ttk.Entry, ttk.Button, ttk.Checkbutton, ttk.Combobox)):
            widget.state(['disabled'] if active else ['!disabled'])
        for child in widget.winfo_children():
            self._disable(child, active)

    def cancel(self):
        if self.task:
            self.task.cancel.set()
            # shortcut: StarNet separation finishes first; cancellation is checked at the next frame.
            self.status.set('Abbruch angefordert. Eine laufende Sternentrennung wird zuerst beendet.')
            self.cancel_button['state'] = 'disabled'

    def poll(self):
        if self.task:
            while True:
                try:
                    kind, value = self.task.events.get_nowait()
                except queue.Empty:
                    break
                if kind == 'log':
                    self.log['state'] = 'normal'
                    self.log.insert('end', value + '\n')
                    if int(self.log.index('end-1c').split('.')[0]) > 2000:
                        self.log.delete('1.0', '200.0')
                    self.log.see('end')
                    self.log['state'] = 'disabled'
                elif kind == 'progress':
                    done, total, elapsed = value
                    self.progress['value'] = done / total * 100
                    if not self.task.cancel.is_set():
                        self.status.set(f'{done / total:.0%} · {done}/{total} Frames · {elapsed:.0f} Sekunden')
                else:
                    self.worker.join()
                    self.worker = None
                    self.busy(False)
                    if kind == 'done':
                        self.last_video = value
                        self.cache = value.parent / (value.stem + '_assets') if not self.cache else self.cache
                        self.progress['value'] = 100
                        self.status.set(f'Fertig: {value}')
                        self.open_button['state'] = 'normal'
                    elif kind == 'cancelled':
                        self.status.set('Abgebrochen. Vorhandene Videos bleiben erhalten.')
                    else:
                        self.status.set('Rendering fehlgeschlagen. Details im Protokoll.')
                        messagebox.showerror('Rendering fehlgeschlagen', value, parent=self.root)
                    if self.closing:
                        self.root.destroy()
                        return
        self.root.after(100, self.poll)

    def open_video(self):
        if self.last_video and self.last_video.is_file():
            import os
            import subprocess
            import sys
            try:
                if os.name == 'nt':
                    os.startfile(self.last_video)
                else:
                    subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', str(self.last_video)])
            except OSError as exc:
                messagebox.showerror('Video nicht geöffnet', str(exc), parent=self.root)

    def close(self):
        if self.worker:
            if messagebox.askyesno('Rendering läuft', 'Rendering abbrechen und anschließend schließen?', parent=self.root):
                self.closing = True
                self.cancel()
        else:
            self.root.destroy()


def main(argv=None):
    parser = argparse.ArgumentParser(description='AstroMotion Desktop-GUI')
    parser.add_argument('--input', type=Path, help='Bild direkt auswählen')
    parser.add_argument('--settings', type=Path, default=wizard.SETTINGS)
    args = parser.parse_args(argv)
    root = tk.Tk()
    try:
        AstroMotionApp(root, args.settings.expanduser().resolve(), args.input)
    except (ValueError, OSError) as exc:
        messagebox.showerror('AstroMotion konnte nicht starten', str(exc), parent=root)
        root.destroy()
        return 1
    root.mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
