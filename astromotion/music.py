"""Random or reproducible stereo ambient synthesis without recorded samples."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import secrets
import uuid
import wave

import numpy as np

from .config import Audio


def resolve_audio_seed(cfg: Audio) -> Audio:
    """Resolve randomness once, preserving the caller's reusable configuration."""
    return replace(cfg, seed=secrets.randbits(32)) if cfg.seed is None else cfg


def synthesize_ambient(path: Path, duration: float, cfg: Audio) -> None:
    """Commit a complete checked WAV atomically; preserve output on failure."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.stem}.{uuid.uuid4().hex}.wav"
    try:
        _synthesize_ambient_stream(temporary, duration, resolve_audio_seed(cfg))
        with wave.open(str(temporary), "rb") as wav:
            if (wav.getnframes() != round(duration * cfg.sample_rate) or
                    wav.getnchannels() != 2 or wav.getframerate() != cfg.sample_rate):
                raise RuntimeError("Ambient-WAV ist unvollständig oder hat ein falsches Format.")
            if wav.getnframes():
                wav.setpos(wav.getnframes() - 1)
                if len(wav.readframes(1)) != 4:
                    raise RuntimeError("Ambient-WAV enthält nicht alle Audiosamples.")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _synthesize_ambient_stream(path: Path, duration: float, cfg: Audio) -> None:
    sr = cfg.sample_rate
    count = round(duration * sr)
    rng = np.random.default_rng(cfg.seed)
    # Related minor/add9 voicings; no sampled sounds or pre-existing recordings.
    harmonies = {
        "original": [[45, 52, 57, 60, 64, 69], [41, 48, 53, 57, 60, 65],
                     [48, 55, 60, 64, 67, 74], [43, 50, 55, 58, 62, 69]],
        "floating": [[45, 52, 59, 60, 64, 69], [48, 55, 59, 62, 64, 67],
                     [41, 48, 52, 57, 60, 67], [43, 50, 57, 59, 62, 69]],
        "dusk": [[40, 47, 54, 55, 59, 64], [43, 50, 54, 57, 59, 62],
                 [38, 45, 52, 54, 57, 62], [45, 52, 55, 59, 60, 64]],
    }
    if cfg.harmony not in harmonies or not -12 <= cfg.transpose <= 12:
        raise ValueError("Ungültige Ambient-Harmonie oder Transposition.")
    chords = np.array(harmonies[cfg.harmony])[rng.permutation(4)] + cfg.transpose
    phases = rng.uniform(0, 2 * np.pi, (4, 6, 3))
    detune = rng.uniform(-.0018, .0018, (4, 6, 3))
    pans = rng.uniform(.15, .85, (4, 6))
    progression_time = max(7.0, duration / 3) * rng.uniform(.88, 1.12)
    accent_rng = np.random.default_rng(cfg.seed ^ 0xA57A)
    event_count = max(1, int(duration / 5))
    event_times = np.linspace(min(2.8, duration * .3), max(duration * .8, duration - 3), event_count)
    event_times = np.sort(np.clip(event_times + accent_rng.uniform(-.8, .8, event_count),
                                  min(.3, duration * .1), max(.3, duration - .35)))
    events = []
    for onset in event_times:
        chord = int(onset / progression_time) % 4
        midi = int(accent_rng.choice(chords[chord, 3:])) + 12
        events.append((float(onset), 440 * 2 ** ((midi - 69) / 12),
                       float(accent_rng.uniform(.2, .8)), float(accent_rng.uniform(3.5, 5.5))))
    # Multi-tap stereo delay. Each tap keeps only a previous block, not the song.
    delays = [round(sr * value) for value in (.173, .311, .487)]
    history = np.zeros((max(delays), 2), np.float64)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        for start in range(0, count, 8192):
            n = min(8192, count - start)
            t = (start + np.arange(n, dtype=np.float64)) / sr
            position = t / progression_time
            chord_index = np.floor(position).astype(int) % 4
            frac = position % 1
            u = frac * frac * (3 - 2 * frac)
            block = np.zeros((n, 2), np.float64)
            for c in range(4):
                envelope = np.where(chord_index == c, 1 - u, 0) + np.where((chord_index + 1) % 4 == c, u, 0)
                if not envelope.any():
                    continue
                for v, midi in enumerate(chords[c]):
                    freq = 440 * 2 ** ((float(midi) - 69) / 12)
                    voice = np.zeros(n, np.float64)
                    for osc in range(3):
                        phase = 2 * np.pi * freq * (1 + detune[c, v, osc]) * t + phases[c, v, osc]
                        voice += (np.sin(phase) + .15 * np.sin(phase * 2) + .035 * np.sin(phase * 3)) / 3
                    voice *= envelope * (.75 + .12 * np.sin(2 * np.pi * .067 * t + phases[c, v, 0])) / 16
                    pan = pans[c, v]
                    block[:, 0] += voice * np.sqrt(1 - pan)
                    block[:, 1] += voice * np.sqrt(pan)
                if cfg.accents:
                    # Quiet high harmonic cloud, slowly swelling with the same
                    # chord blend. No noise samples or third-party recordings.
                    freq = 440 * 2 ** ((float(chords[c, -1]) + 12 - 69) / 12)
                    swell = (.5 - .5 * np.cos(2 * np.pi * .085 * t + phases[c, 0, 0]))
                    shimmer = .006 * cfg.accents * envelope * swell
                    block[:, 0] += shimmer * np.sin(2 * np.pi * freq * t + phases[c, 0, 1])
                    block[:, 1] += shimmer * np.sin(2 * np.pi * freq * 1.0004 * t + phases[c, 0, 1])
            if cfg.accents:
                for onset, freq, pan, decay in events:
                    if t[-1] < onset or t[0] > onset + 12:
                        continue
                    age = np.maximum(t - onset, 0)
                    attack = np.sin(np.clip(age / .3, 0, 1) * np.pi / 2) ** 2
                    end = np.clip((12 - age) / 2, 0, 1) ** 2
                    envelope = attack * np.exp(-age / decay) * end * (t >= onset)
                    # Gentle bell-like additive partials; soft attack, long tail.
                    bell = sum(gain * np.sin(2 * np.pi * freq * ratio * age)
                               for ratio, gain in ((1., 1.), (2.01, .28), (2.8, .08), (4.12, .03)))
                    bell *= .04 * cfg.accents * envelope
                    block[:, 0] += bell * np.sqrt(1 - pan)
                    block[:, 1] += bell * np.sqrt(pan)
            joined = np.concatenate((history, block))
            wet = block.copy()
            for delay, gain in zip(delays, (.21, .14, .095)):
                wet += joined[len(history) - delay:len(history) - delay + n, ::-1] * gain
            history = joined[-len(history):].copy()
            fade = min(cfg.fade_seconds, duration / 2)
            env = np.ones(n)
            if fade:
                env = np.sin(np.clip(t / fade, 0, 1) * np.pi / 2) ** 2
                env *= np.sin(np.clip((duration - t - 1 / sr) / fade, 0, 1) * np.pi / 2) ** 2
            # Fixed gentle saturation: block-independent, no abrupt normalization.
            wet = np.tanh(wet * 1.8) * .65 * env[:, None]
            wav.writeframes(np.round(wet * 32767).astype("<i2").tobytes())
