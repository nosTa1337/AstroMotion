"""Lower-resolution previews keep the full video's timing and animation settings."""
from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Config


def preview_config(cfg: Config) -> Config:
    """Change only output resolution; StarNet still processes the same input."""
    result = replace(cfg, resolution="360p")
    result.validate()
    return result


def photo_preview_frame(image, cfg: Config, progress: float, size: tuple[int, int]):
    """Show the renderer's camera on the photo without running star separation."""
    import cv2
    from .animation import Animator
    from .separation import Layers

    camera = Animator(Layers(image, image, 'screen', {}), cfg.size, cfg.motion)
    matrix = camera.matrix(progress)
    # Resize output pixel centers, keeping the full-resolution camera geometry.
    for axis in (0, 1):
        ratio = size[axis] / cfg.size[axis]
        matrix[axis] *= ratio
        matrix[axis, 2] += (ratio - 1) / 2
    return cv2.warpAffine(image, matrix, size, flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=0)
