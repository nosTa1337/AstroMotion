"""Read-only separation checks; never repair or recolor image data."""
from pathlib import Path

import numpy as np
import cv2
from PIL import Image, ImageDraw

from .animation import Animator
from .config import Config
from .effects import EffectProcessor
from .imaging import to_linear, to_srgb
from .looping import camera_phase
from .separation import Layers


def check_layers(original, starless, layers: Layers) -> dict[str, float]:
    expected = np.minimum(to_linear(original), to_linear(starless))
    background_error = float(np.max(np.abs(layers.nebula - expected)))
    reconstruction_error = float(np.max(np.abs(layers.composite() - to_linear(original))))
    changed = np.max(np.abs(to_srgb(layers.nebula) - starless), axis=2) > .25
    stats = {'background_error_linear': background_error,
             'reconstruction_error_linear': reconstruction_error,
             'strong_background_change_fraction': float(changed.mean())}
    if background_error > 2e-7 or reconstruction_error > 2e-6 or stats['strong_background_change_fraction'] >= .001:
        raise ValueError(f'StarNet2 layer QA failed; no demo render: {stats}')
    return stats


def save_contact_sheet(path: Path, original, starless, layers: Layers, cfg: Config) -> None:
    """Full images plus the brightest stellar regions at three camera phases."""
    camera = Animator(layers, cfg.size, cfg.motion)
    processor = EffectProcessor(cfg.effects, cfg.size, layers.blend)
    frames = [processor.apply(*camera.frame_layers(camera_phase(t) if cfg.loop.enabled else t, 0))
              for t in (0., .25, .5)]
    images = [original, starless, to_srgb(layers.nebula), *frames]
    names = ['Original', 'StarNet2 raw', 'Background', 'Phase 0', 'Phase .25', 'Phase .5']
    canvas = Image.new('RGB', (1500, 850), '#16191e'); draw = ImageDraw.Draw(canvas)
    # Rank integrated stellar flux, not single clipped/noisy pixels. Exclude
    # borders so the tracked crops stay visible through the full camera path.
    peak = cv2.GaussianBlur(layers.stars.max(axis=2), (0, 0), 3)
    h,w = peak.shape
    peak[:h//8] = peak[-h//8:] = 0
    peak[:, :w//8] = peak[:, -w//8:] = 0
    centers = []
    for _ in range(3):
        y, x = np.unravel_index(peak.argmax(), peak.shape)
        centers.append((x, y))
        peak[max(0,y-100):y+101, max(0,x-100):x+101] = 0
    for col, (name, array) in enumerate(zip(names, images)):
        im = Image.fromarray(np.uint8(np.clip(array, 0, 1)*255))
        thumb=im.copy(); thumb.thumbnail((245, 400)); canvas.paste(thumb, (col*250,25)); draw.text((col*250+5,5),name)
        for row, (x, y) in enumerate(centers):
            if col >= 3:
                t = (0., .25, .5)[col-3]
                x,y = camera.matrix(camera_phase(t) if cfg.loop.enabled else t, stars=True) @ [x,y,1]
            crop=im.crop((int(x)-35,int(y)-35,int(x)+35,int(y)+35)).resize((130,130))
            canvas.paste(crop,(col*250+55,435+row*137))
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)
