"""Periodic camera timing and streaming, overlap-spliced PCM audio loops."""
from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
import subprocess
import uuid
import wave

import numpy as np

from .config import Config
from .encoding import resolve_binary
from .music import synthesize_ambient


def camera_phase(phase: float) -> float:
    """One smooth approach/return cycle, with identical endpoint derivatives."""
    return .5 - .5 * math.cos(2 * math.pi * (phase % 1))


def splice_audio_loop(source: Path, output: Path, frame_count: int, overlap: int) -> None:
    """Crossfade source[N:N+C] into source[0:C], then append source[C:N].

    Sample zero continues source[N-1], so the seam is a regular sample step,
    not two forced equal endpoint samples. Uses two readers and 8192-frame blocks.
    Source must contain at least N+C stereo PCM16 frames. No gain normalization.
    """
    if frame_count < 2 or not 2 <= overlap <= frame_count:
        raise ValueError("Ungültige Audio-Loop-Länge oder Überblendung.")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.parent / f".{output.stem}.{uuid.uuid4().hex}.wav"
    try:
        with wave.open(str(source), "rb") as head, wave.open(str(source), "rb") as tail:
            if head.getnchannels() != 2 or head.getsampwidth() != 2 or head.getnframes() < frame_count + overlap:
                raise ValueError("Audio-Loop benötigt genügend Stereo-PCM16-Samples.")
            tail.setpos(frame_count)
            with wave.open(str(temporary), "wb") as target:
                target.setnchannels(2)
                target.setsampwidth(2)
                target.setframerate(head.getframerate())
                for start in range(0, frame_count, 8192):
                    size = min(8192, frame_count - start)
                    incoming = np.frombuffer(head.readframes(size), dtype="<i2").reshape(-1, 2)
                    block = incoming.copy()
                    fade_count = min(size, max(0, overlap - start))
                    if fade_count:
                        outgoing = np.frombuffer(tail.readframes(fade_count), dtype="<i2").reshape(-1, 2)
                        t = (start + np.arange(fade_count, dtype=np.float64)) / (overlap - 1)
                        alpha = t * t * t * (t * (t * 6 - 15) + 10)
                        block[:fade_count] = np.rint(outgoing * (1 - alpha[:, None]) +
                                                    incoming[:fade_count] * alpha[:, None]).astype("<i2")
                    target.writeframes(block.astype("<i2", copy=False).tobytes())
        with wave.open(str(temporary), "rb") as check:
            if check.getnframes() != frame_count:
                raise RuntimeError("Audio-Loop wurde nicht vollständig geschrieben.")
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


def prepare_audio_loop(output: Path, cfg: Config, source: Path | None = None) -> None:
    """Synthesize or decode an extended source, then splice its seamless period.

    Ambient skips a one-second delay-buffer warmup. External audio repeats to
    cover the requested duration; existing internal edits remain in that audio.
    """
    sr = cfg.audio.sample_rate
    count = round(cfg.actual_duration * sr)
    overlap = max(2, min(round(cfg.loop.audio_crossfade_seconds * sr), count // 3))
    warmup = sr if cfg.audio.mode == "ambient" else 0
    extended = output.parent / f".loop_source_{uuid.uuid4().hex}.wav"
    trimmed = output.parent / f".loop_trim_{uuid.uuid4().hex}.wav"
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        duration = (count + overlap + warmup) / sr
        if cfg.audio.mode == "ambient":
            synthesize_ambient(extended, duration, replace(cfg.audio, fade_seconds=0))
        else:
            if source is None:
                raise ValueError("Eigene Loop-Musik benötigt eine Audiodatei.")
            result = subprocess.run([resolve_binary(cfg.encoding.ffmpeg), "-hide_banner", "-v", "error",
                "-y", "-stream_loop", "-1", "-i", str(source), "-t", str(duration),
                "-vn", "-ac", "2", "-ar", str(sr), "-c:a", "pcm_s16le", str(extended)],
                capture_output=True, timeout=max(60, duration * 2))
            if result.returncode:
                raise RuntimeError(f"Loop-Musik konnte nicht dekodiert werden: {result.stderr.decode(errors='replace')[-1500:]}")
        with wave.open(str(extended), "rb") as wav, wave.open(str(trimmed), "wb") as target:
            wav.setpos(warmup)
            target.setparams((2, 2, sr, 0, "NONE", "not compressed"))
            remaining = count + overlap
            while remaining:
                block = wav.readframes(min(8192, remaining))
                if not block:
                    raise RuntimeError("Audioquelle ist zu kurz für den Loop.")
                target.writeframes(block)
                remaining -= len(block) // 4
        splice_audio_loop(trimmed, output, count, overlap)
    finally:
        extended.unlink(missing_ok=True)
        trimmed.unlink(missing_ok=True)
