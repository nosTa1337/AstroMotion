"""GUI workflow checks; no real StarNet process or user settings are touched."""
from dataclasses import asdict
from pathlib import Path
import queue
import shutil
import sys
import time

import pytest

tk = pytest.importorskip('tkinter')
import gui
import wizard
from astromotion.config import load_config
from astromotion import pipeline


def form_values(cfg):
    data = asdict(cfg)
    return {key: (value if isinstance(value, bool) else '' if value is None else str(value))
            for fields in gui.TABS.values() for key, _, _ in fields
            for value in [gui.value_at(data, key)]}


def test_form_keeps_unexposed_settings_and_parses_seeds_and_german_numbers():
    cfg = load_config(wizard.PRESET)
    cfg.separation.stride = 128
    cfg.motion.center_x = .3
    values = form_values(cfg)
    values.update({'motion.zoom': '0,25', 'caption.title': 'Orion', 'caption.subtitle': 'M42',
                   'profile_seed': '42', 'audio.seed': '', 'loop.enabled': False})
    result = gui.form_config(cfg, values)
    assert result.motion.zoom == .25 and result.motion.center_x == .3
    assert result.caption.enabled and result.caption.title == 'Orion'
    assert result.separation.stride == 128 and result.profile_seed == 42
    assert result.audio.seed is None and not result.loop.enabled
    assert cfg.motion.zoom != .25 and not cfg.caption.enabled


@pytest.mark.parametrize('key,value', [('fps', '25'), ('motion.zoom', 'nan'), ('motion.zoom', '1.1'),
                                      ('starfield.count', '2.5'), ('profile_seed', '-1'),
                                      ('audio.seed', '1.5'), ('caption.title', 'line\nbreak'),
                                      ('loop.enabled', 'false')])
def test_form_rejects_bad_values(key, value):
    cfg = load_config(wizard.PRESET)
    values = form_values(cfg)
    values[key] = value
    with pytest.raises(ValueError):
        gui.form_config(cfg, values)


def drain(task):
    events = []
    while True:
        try:
            events.append(task.events.get_nowait())
        except queue.Empty:
            return events


@pytest.mark.parametrize('outcome', ['done', 'error', 'cancelled'])
def test_worker_reports_completion_errors_and_cooperative_cancellation(monkeypatch, tmp_path, outcome):
    task = gui.RenderTask()
    output = tmp_path / 'old.mp4'
    output.write_bytes(b'previous video')

    def render(image, destination, cfg, starless, progress, overwrite, *, starnet_cache):
        assert starnet_cache == tmp_path / 'preview_assets'
        if outcome == 'error':
            raise RuntimeError('Test failure')
        if outcome == 'cancelled':
            task.cancel.set()
        progress(1, 2, .1)
        destination.write_bytes(b'completed')

    monkeypatch.setattr(pipeline, 'render', render)
    task.run(tmp_path / 'input.jpg', output, load_config(), None, True, tmp_path / 'preview_assets')
    events = drain(task)
    assert events[-1][0] == outcome
    assert output.read_bytes() == (b'completed' if outcome == 'done' else b'previous video')
    if outcome == 'error':
        assert events[-1][1] == 'Test failure'


@pytest.fixture
def app(tmp_path, monkeypatch):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip('Tk display unavailable')
    root.withdraw()
    errors = []
    monkeypatch.setattr(gui.messagebox, 'showerror', lambda *args, **kwargs: errors.append(args))
    application = gui.AstroMotionApp(root, tmp_path / 'settings.json')
    application.vars['separation.executable'].set(sys.executable)
    image = tmp_path / 'Photo with spaces.jpg'
    image.write_bytes(b'image decoded only by renderer')
    application.set_image(image)
    application.output.set(str(tmp_path / 'video.mp4'))
    yield application, errors
    if application.worker:
        application.task.cancel.set()
        application.worker.join(timeout=5)
    root.destroy()


def finish(app):
    deadline = time.monotonic() + 5
    while app.worker and time.monotonic() < deadline:
        app.root.update()
        time.sleep(.01)
    assert app.worker is None


def test_preview_full_export_share_seeds_cache_and_keep_full_resolution(app, monkeypatch):
    application, errors = app
    calls = []

    def render(image, output, cfg, starless, progress, overwrite, *, starnet_cache):
        calls.append((output, cfg, starnet_cache))
        progress(1, 1, .1)
        output.write_bytes(b'rendered')

    monkeypatch.setattr(pipeline, 'render', render)
    application.profile.set('Sternflug: explore')
    application.load_profile()  # Built-in profiles must not lose selected program paths.
    application.vars['caption.title'].set('M42')
    application.start(True)
    finish(application)
    assert not errors
    assert application.vars['resolution'].get() == '1080p'
    application.start(False)
    finish(application)
    assert not errors and len(calls) == 2
    preview, full = calls
    assert preview[0].name == 'video_preview.mp4' and full[0].name == 'video.mp4'
    assert preview[1].resolution == '360p' and full[1].resolution == '1080p'
    assert preview[1].audio.seed == full[1].audio.seed
    assert type(full[1].audio.seed) is int
    assert preview[1].profile_seed == full[1].profile_seed
    assert type(full[1].profile_seed) is int
    assert asdict(preview[1]) == {**asdict(full[1]), 'resolution': '360p'}
    assert full[2] == full[0].parent / 'video_preview_assets'
    saved = wizard.load_settings(application.settings_path)
    assert saved['defaults']['resolution'] == '1080p' and not saved['defaults']['caption']['title']
    assert saved['history'][0]['exact_defaults']['audio']['seed'] == full[1].audio.seed


def test_invalid_form_and_declined_overwrite_do_not_launch_or_save(app, monkeypatch):
    application, errors = app
    application.vars['motion.zoom'].set('oops')
    application.start(True)
    assert errors and application.worker is None and not application.settings_path.exists()
    application.vars['motion.zoom'].set('.14')
    output = Path(application.output.get())
    output.write_bytes(b'keep')
    monkeypatch.setattr(gui.messagebox, 'askyesno', lambda *a, **k: False)
    application.start(False)
    assert output.read_bytes() == b'keep'
    assert application.worker is None and not application.settings_path.exists()


def test_named_profile_roundtrip_preserves_current_title_and_paths(app, monkeypatch):
    application, errors = app
    monkeypatch.setattr(gui.simpledialog, 'askstring', lambda *a, **k: 'My flight')
    application.vars['motion.rotation_deg'].set('40')
    application.vars['caption.title'].set('Original photo title')
    application.save_profile()
    assert not errors
    application.vars['motion.rotation_deg'].set('10')
    application.vars['caption.title'].set('Different photo')
    application.load_profile()
    assert not errors
    assert application.vars['motion.rotation_deg'].get() == '40.0'
    assert application.vars['caption.title'].get() == 'Different photo'
    assert application.vars['separation.executable'].get() == sys.executable
    saved = wizard.load_settings(application.settings_path)
    assert saved['favorites']['My flight']['defaults']['motion']['rotation_deg'] == 40
    assert not saved['favorites']['My flight']['defaults']['caption']['title']


@pytest.mark.video_render
@pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'), reason='FFmpeg unavailable')
def test_gui_exports_verified_video_using_existing_starless(app):
    import numpy as np
    from astromotion.imaging import save_png, to_srgb
    from astromotion.separation import composite
    from astromotion.encoding import probe

    application, errors = app
    image = Path(application.image.get())
    starless = image.with_name('starless.png')
    base = np.full((120, 160, 3), [.05, .08, .1], np.float32)
    stars = np.zeros_like(base)
    for y in range(15, 110, 15):
        for x in range(15, 150, 15):
            stars[y, x] = [.9, .85, .8]
    image = image.with_suffix('.png')
    save_png(image, to_srgb(composite(base, stars)))
    save_png(starless, to_srgb(base))
    application.image.set(str(image))
    application.starless.set(str(starless))
    for key, value in {'duration': '.25', 'fps': '24', 'audio.mode': 'none',
                       'starfield.count': '30', 'caption.title': 'M42'}.items():
        application.vars[key].set(value)
    application.cfg.encoding.preset = 'ultrafast'
    application.start(True)
    finish(application)
    assert not errors
    assert application.last_video and application.last_video.is_file()
    result = probe(application.last_video, 'ffprobe')
    video = next(stream for stream in result['streams'] if stream['codec_type'] == 'video')
    assert (video['width'], video['height'], int(video['nb_frames'])) == (360, 640, 6)
