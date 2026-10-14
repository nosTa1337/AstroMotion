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
