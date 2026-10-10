"""Strict, layered JSON/YAML configuration: defaults -> preset -> file -> CLI."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
import json
import math
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Motion:
    zoom: float = 0.065  # total nebula zoom at speed=1
    rotation_deg: float = 1.8  # total rotation, centered around zero
    pan_x: float = 0.018  # total displacement as fraction of output width
    pan_y: float = -0.012
    parallax: float = 1.0
    star_zoom_extra: float = 0.045
    star_rotation_deg: float = 0.5
    speed: float = 1.0
    overscan: float = 1.015
    center_x: float = 0.5  # focus position in source image
    center_y: float = 0.5


@dataclass
class Effects:
    bloom: float = 0.0
    glow: float = 0.0
    bloom_radius: float = 7.0  # pixels at 1080-short-edge; scales with resolution
    glow_radius: float = 24.0
    vignette: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    grade: float = 0.0
    twinkle: float = 0.0


@dataclass
class Separation:
    executable: str | None = None
    mode: str = "auto"  # modern starnet2 flags or legacy positional arguments
    stride: int = 256
    timeout: float = 3600.0
    extra_args: list[str] = field(default_factory=list)
    blend: str = "screen"  # screen in linear light, or additive
    max_negative_error: float = 0.035  # mean positive starless-original discrepancy
    foreground_cleanup: bool = False  # deprecated, accepted but ignored


@dataclass
class Audio:
    mode: str = "none"  # none, ambient, file
    file: str | None = None
    seed: int | None = None  # None: fresh music per render; integer: reproducible
    gain: float = 0.7
    fade_seconds: float = 2.0
    sample_rate: int = 48000
    harmony: str = "original"  # related ambient chord sets
    transpose: int = 0  # semitones
    accents: float = 0.0  # sparse bell and high shimmer; 0 disables both


@dataclass
class Encoding:
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"
    crf: int = 18
    preset: str = "medium"
    threads: int = 0
    verify: bool = True


@dataclass
class Starfield:
    """Perspective animation of star cores measured in the StarNet2 residual."""
    enabled: bool = False
    count: int = 4500
    seed: int = 2026
    near: float = 0.16
    far: float = 3.8
    travel: float = 2.4
    drift_x: float = 0.12
    drift_y: float = -0.035
    rotation_deg: float = 4.0
    farfield_gain: float = 0.18
    foreground_gain: float = 1.0
    color_strength: float = 0.6  # 0: neutral stars; 1: full residual color
    max_radius: float = 12.0  # sigma cap at a 1080-pixel short edge
    shutter: float = 0.6  # subframe motion trail in frame intervals
    photo_profiles: bool = False
    depth_mode: str = "random"  # random or adaptive; artistic brightness/depth correlation
    depth_correlation: float = 0.40  # 0..1; relative star brightness is not distance
    close_passes: int = 0  # number of featured real stars over the whole clip
    close_scale: float = 1.6
    close_blur: float = 2.4  # pixels at 1080-short-edge, only featured near stars


@dataclass
class Caption:
    enabled: bool = False
    title: str = ""
    subtitle: str = ""
    font: str | None = None
    title_size: int = 36  # pixels at 1080-pixel short edge
    subtitle_size: int = 22
    x: float = .067
    y: float = .8125
    opacity: float = .76
    start_seconds: float = 2.0
    fade_seconds: float = .9
    hold_seconds: float = 2.7


@dataclass
class Loop:
    enabled: bool = False
    star_cycles: int = 1  # whole depth-volume traversals per video period
    audio_crossfade_seconds: float = 4.0


@dataclass
class Cinematic:
    auto_focus: bool = False
    auto_color: bool = False
    focus_strength: float = 0.80
    color_strength: float = 0.85


@dataclass
class Config:
    preset: str = "cinematic"
    format: str = "vertical"
    resolution: str = "1080p"
    duration: float = 30.0
    fps: int = 30
    work_long_edge: int = 3200
    max_input_pixels: int = 120_000_000
    save_layers: bool = True
    motion: Motion = field(default_factory=Motion)
    cinematic: Cinematic = field(default_factory=Cinematic)
    effects: Effects = field(default_factory=Effects)
    separation: Separation = field(default_factory=Separation)
    audio: Audio = field(default_factory=Audio)
    encoding: Encoding = field(default_factory=Encoding)
    starfield: Starfield = field(default_factory=Starfield)
    caption: Caption = field(default_factory=Caption)
    loop: Loop = field(default_factory=Loop)

    @property
    def size(self) -> tuple[int, int]:
        short = {"720p": 720, "1080p": 1080, "4k": 2160}[self.resolution]
        long = short * 16 // 9
        return {"vertical": (short, long), "square": (short, short),
                "landscape": (long, short)}[self.format]

    @property
    def frame_count(self) -> int:
        return max(1, round(self.duration * self.fps))

    @property
    def actual_duration(self) -> float:
        return self.frame_count / self.fps

    def validate(self) -> None:
        if self.preset not in PRESETS or self.format not in ("vertical", "square", "landscape"):
            raise ValueError("Unbekanntes Preset oder Videoformat.")
        if self.resolution not in ("720p", "1080p", "4k") or self.fps not in (24, 30, 60):
            raise ValueError("Auflösung: 720p/1080p/4k; FPS: 24/30/60.")
        for key, value in _flatten(asdict(self)).items():
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"{key}: Zahlen müssen endlich sein.")
        if self.duration < 1 / self.fps or self.duration > 3600:
            raise ValueError("Dauer muss zwischen einem Frame und 3600 Sekunden liegen.")
        if not 512 <= self.work_long_edge <= 16384 or self.max_input_pixels <= 0:
            raise ValueError("work_long_edge: 512..16384; max_input_pixels > 0.")
        m = self.motion
        if not (0 <= m.zoom <= .5 and 0 <= m.star_zoom_extra <= .5 and 0 <= m.parallax <= 3):
            raise ValueError("Zoom/Star-Zoom: 0..0.5; Parallax: 0..3.")
        if not (0 <= m.speed <= 3 and abs(m.rotation_deg) <= 10 and abs(m.star_rotation_deg) <= 5):
            raise ValueError("Speed: 0..3; Rotation max. 10°, Sternrotation max. 5°.")
        if max(abs(m.pan_x), abs(m.pan_y)) > .15 or not 1 <= m.overscan <= 1.5:
            raise ValueError("Pan max. ±0.15; Overscan: 1..1.5.")
        if not (.1 <= m.center_x <= .9 and .1 <= m.center_y <= .9):
            raise ValueError("Bildzentrum: 0.1..0.9 (begrenzter Ausschnitt verhindert Randlücken).")
        if not (0 <= self.cinematic.focus_strength <= 1 and
                0 <= self.cinematic.color_strength <= 1):
            raise ValueError("Cinematic: focus_strength und color_strength müssen 0..1 sein.")
        e = self.effects
        if any(not 0 <= getattr(e, k) <= 1 for k in ("bloom", "glow", "vignette", "grade", "twinkle")):
            raise ValueError("Effektstärken: 0..1.")
        if not (.1 <= e.contrast <= 2 and 0 <= e.saturation <= 2):
            raise ValueError("Kontrast: 0.1..2; Sättigung: 0..2.")
        if not (0 < e.bloom_radius <= 100 and 0 < e.glow_radius <= 200):
            raise ValueError("Bloom-/Glow-Radius außerhalb des gültigen Bereichs.")
        s = self.separation
        if s.mode not in ("auto", "modern", "legacy") or s.blend not in ("screen", "additive"):
            raise ValueError("StarNet-Modus: auto/modern/legacy; Blend: screen/additive.")
        if not 2 <= s.stride <= 512 or s.stride % 2 or s.timeout <= 0:
            raise ValueError("StarNet-Stride muss gerade und 2..512 sein; Timeout > 0.")
        if not 0 <= s.max_negative_error <= .2 or not all(isinstance(x, str) for x in s.extra_args):
            raise ValueError("Ungültige StarNet-Argumente oder max_negative_error.")
        a = self.audio
        if a.mode not in ("none", "ambient", "file") or (a.mode == "file" and not a.file):
            raise ValueError("Audio: none/ambient/file; file benötigt audio.file.")
        if not 0 <= a.gain <= 2 or a.fade_seconds < 0 or a.sample_rate not in (44100, 48000):
            raise ValueError("Ungültige Audio-Einstellungen.")
        if a.seed is not None and (type(a.seed) is not int or not 0 <= a.seed < 2**32):
            raise ValueError("Audio-Seed: null (zufällig) oder 0..4294967295.")
        if a.harmony not in ("original", "floating", "dusk") or not -12 <= a.transpose <= 12:
            raise ValueError("Audio harmony: original/floating/dusk; transpose: -12..12 Halbtöne.")
        if not 0 <= a.accents <= 1:
            raise ValueError("Audio accents: 0..1.")
        if not 0 <= self.encoding.crf <= 35 or self.encoding.threads < 0:
            raise ValueError("CRF: 0..35; Threads >= 0.")
        if self.encoding.preset not in ("ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"):
            raise ValueError("Ungültiges x264-Preset.")
        f = self.starfield
        if not 1 <= f.count <= 20000 or not 0 <= f.seed < 2**32:
            raise ValueError("Starfield count: 1..20000; Seed: 0..4294967295.")
        if not (.05 <= f.near < f.far <= 20 and 0 <= f.travel <= 20):
            raise ValueError("Starfield: 0.05 <= near < far <= 20; travel: 0..20.")
        if max(abs(f.drift_x), abs(f.drift_y)) > .5 or abs(f.rotation_deg) > 15:
            raise ValueError("Starfield drift max. ±0.5; Rotation max. 15°.")
        if not (0 <= f.farfield_gain <= 1 and 0 <= f.foreground_gain <= 3 and 1 <= f.max_radius <= 30 and 0 <= f.shutter <= 2):
            raise ValueError("Ungültige Starfield-Helligkeit, Radius oder Shutter.")
        if not 0 <= f.color_strength <= 1:
            raise ValueError("Starfield color_strength: 0..1.")
        if f.depth_mode not in ("random", "adaptive") or not 0 <= f.depth_correlation <= 1:
            raise ValueError("Starfield: depth_mode random/adaptive, depth_correlation 0..1.")
        if not (0 <= f.close_passes <= 20 and 1 <= f.close_scale <= 2.5 and 0 <= f.close_blur <= 8):
            raise ValueError("Close passes: 0..20; Scale: 1..2.5; Blur: 0..8.")
        c = self.caption
        if c.enabled and not c.title.strip():
            raise ValueError("caption.title darf bei aktivierter Beschriftung nicht leer sein.")
        if any(len(text) > 100 or any(ord(char) < 32 for char in text) for text in (c.title, c.subtitle)):
            raise ValueError("Beschriftung: höchstens 100 Zeichen pro Zeile, keine Steuerzeichen.")
        if not (12 <= c.title_size <= 100 and 10 <= c.subtitle_size <= 80):
            raise ValueError("Beschriftung: title_size 12..100, subtitle_size 10..80.")
        if not (0 <= c.x <= .8 and 0 <= c.y <= .9 and 0 <= c.opacity <= 1):
            raise ValueError("Beschriftung: Position x 0..0.8, y 0..0.9, opacity 0..1.")
        if c.start_seconds < 0 or c.fade_seconds <= 0 or c.hold_seconds < 0:
            raise ValueError("Beschriftung: Start/Haltedauer >= 0, Fade > 0.")
        if type(self.loop.star_cycles) is not int or not 1 <= self.loop.star_cycles <= 5:
            raise ValueError("Loop star_cycles: 1..5 ganze Volumendurchläufe.")
        if not .05 <= self.loop.audio_crossfade_seconds <= 30:
            raise ValueError("Loop audio_crossfade_seconds: 0.05..30.")


PRESETS: dict[str, dict[str, Any]] = {
    "cinematic": {},
    "epic": {"motion": {"zoom": .10, "rotation_deg": 3.2, "pan_x": .035,
                         "pan_y": -.024, "parallax": 1.5, "star_zoom_extra": .055},
             "effects": {}},
    "calm": {"motion": {"zoom": .03, "rotation_deg": .65, "pan_x": .008,
                         "pan_y": -.005, "parallax": .6, "star_zoom_extra": .025},
             "effects": {}},
}


def _flatten(d: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result.update(_flatten(v, prefix + k + "."))
        else:
            result[prefix + k] = v
    return result


def _merge(target: Any, values: dict[str, Any]) -> None:
    known = {f.name for f in fields(target)}
    for key, value in values.items():
        if key not in known:
            raise ValueError(f"Unbekannter Konfigurationsschlüssel: {key}")
        current = getattr(target, key)
        if hasattr(current, "__dataclass_fields__"):
            if not isinstance(value, dict):
                raise ValueError(f"{key} muss ein Objekt sein.")
            _merge(current, value)
        else:
            if isinstance(target, Audio) and key == "seed":
                if value is not None and type(value) is not int:
                    raise ValueError("Audio-Seed: Ganzzahl oder null.")
            elif current is not None:
                # bool is a subclass of int, so reject accidental coercions explicitly.
                valid = (type(value) is type(current)) or (type(current) is float and type(value) is int)
                if not valid:
                    raise ValueError(f"{key}: erwartet {type(current).__name__}.")
            elif value is not None and not isinstance(value, str):
                raise ValueError(f"{key}: erwartet einen Pfad als String oder null.")
            setattr(target, key, value)


def load_config(path: Path | None = None, overrides: dict[str, Any] | None = None) -> Config:
    values: dict[str, Any] = {}
    if path:
        raw = path.read_text(encoding="utf-8-sig")
        values = json.loads(raw) if path.suffix.lower() == ".json" else yaml.safe_load(raw)
        if values is None:
            values = {}
        if not isinstance(values, dict):
            raise ValueError("Konfiguration muss ein YAML-/JSON-Objekt sein.")
    overrides = overrides or {}
    name = overrides.get("preset", values.get("preset", "cinematic"))
    if name not in PRESETS:
        raise ValueError(f"Unbekanntes Preset: {name}")
    cfg = Config(preset=name)
    _merge(cfg, PRESETS[name])
    _merge(cfg, values)
    _merge(cfg, overrides)
    cfg.validate()
    # Paths in a config file are relative to that file, not the process directory.
    if path:
        for obj, key in ((cfg.separation, "executable"), (cfg.audio, "file"), (cfg.caption, "font"),
                         (cfg.encoding, "ffmpeg"), (cfg.encoding, "ffprobe")):
            value = getattr(obj, key)
            if value and ("/" in value or "\\" in value) and not Path(value).is_absolute():
                setattr(obj, key, str((path.parent / value).resolve()))
    return cfg
