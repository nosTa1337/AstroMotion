"""Small, fixed screen-space captions with smooth fades; no per-frame font work."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .config import Caption
from .imaging import FloatImage


class CaptionOverlay:
    def __init__(self, cfg: Caption, size: tuple[int, int]):
        self.cfg = cfg
        width, height = size
        scale = min(size) / 1080
        self.x, self.y = round(width * cfg.x), round(height * cfg.y)
        candidates = [cfg.font] if cfg.font else ["C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf"]

        def font_at(pixels: int) -> ImageFont.FreeTypeFont:
            for candidate in candidates:
                try:
                    return ImageFont.truetype(str(candidate), pixels)
                except OSError:
                    continue
            raise ValueError("Kein skalierbarer Schriftfont gefunden; caption.font auf lokale TTF/OTF setzen.")

        lines = [(cfg.title, round(cfg.title_size * scale))]
        if cfg.subtitle:
            lines.append((cfg.subtitle, round(cfg.subtitle_size * scale)))
        usable_width = width - self.x - max(4, round(width * .06))
        gap = max(3, round(12 * scale))
        rendered = []
        for text, pixels in lines:
            font = font_at(max(8, pixels))
            while font.getlength(text) > usable_width - 3 and pixels > 8:
                pixels -= 1
                font = font_at(pixels)
            if font.getlength(text) > usable_width - 3:
                raise ValueError("Beschriftung passt nicht in den gewählten Bildbereich.")
            bounds = font.getbbox(text)
            rendered.append((text, font, bounds))
        box_height = sum(b[3] - b[1] for _, _, b in rendered) + gap * (len(lines) - 1) + 4
        if self.y + box_height > height:
            raise ValueError("Beschriftung liegt außerhalb des Videos; caption.y reduzieren.")
        texture = Image.new("RGBA", (usable_width, box_height))
        draw = ImageDraw.Draw(texture)
        top = 0
        for text, font, bounds in rendered:
            baseline = top - bounds[1]
            draw.text((1, baseline + 1), text, font=font, fill=(0, 0, 0, 90))
            draw.text((0, baseline), text, font=font, fill=(240, 241, 244, 255))
            top += bounds[3] - bounds[1] + gap
        rgba = np.asarray(texture, np.float32) / 255
        self.rgb, self.alpha = rgba[..., :3], rgba[..., 3:]

    def opacity(self, seconds: float) -> float:
        elapsed = seconds - self.cfg.start_seconds
        fade, hold = self.cfg.fade_seconds, self.cfg.hold_seconds
        if elapsed <= 0 or elapsed >= 2 * fade + hold:
            return 0.0
        if elapsed < fade:
            amount = (1 - math.cos(math.pi * elapsed / fade)) / 2
        elif elapsed < fade + hold:
            amount = 1.0
        else:
            amount = (1 + math.cos(math.pi * (elapsed - fade - hold) / fade)) / 2
        return self.cfg.opacity * amount

    def apply(self, background: FloatImage, seconds: float, loop_duration: float | None = None) -> FloatImage:
        amount = self.opacity(seconds)
        if loop_duration:
            # Short loops may cut through the normal caption window. Close its
            # envelope at the seam as well, rather than leaving a title to pop.
            edge = min(self.cfg.fade_seconds, loop_duration / 4)
            elapsed = seconds % loop_duration
            margin = min(elapsed, loop_duration - elapsed)
            amount *= (1 - math.cos(math.pi * min(1, margin / edge))) / 2
        if amount <= 0:
            return background
        result = background.copy()
        h, w = self.alpha.shape[:2]
        region = result[self.y:self.y + h, self.x:self.x + w]
        alpha = self.alpha * amount
        region[:] = region * (1 - alpha) + self.rgb * alpha
        return result
