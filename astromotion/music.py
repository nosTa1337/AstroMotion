"""Random or reproducible stereo ambient synthesis without recorded samples."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import secrets
import uuid
import wave

import numpy as np

from .config import Audio, MUSIC_STYLES


_STYLE_CHORDS = {
    "warm": [[48, 55, 60, 64, 67, 74], [53, 60, 65, 69, 72, 79],
             [45, 52, 57, 60, 64, 71], [43, 50, 55, 59, 62, 69]],
    "deep": [[33, 40, 45, 48, 52, 59], [29, 36, 41, 45, 48, 55],
             [36, 43, 48, 51, 55, 62], [31, 38, 43, 46, 50, 57]],
    "shimmer": [[62, 69, 74, 78, 81, 85], [59, 66, 71, 74, 78, 81],
                [55, 62, 67, 71, 74, 78], [57, 64, 69, 73, 76, 80]],
    "pulse": [[45, 52, 57, 60, 64, 69], [41, 48, 53, 57, 60, 65],
              [48, 55, 60, 64, 67, 74], [43, 50, 55, 58, 62, 69]],
}
# Chord duration, pad harmonics/gain, bass gain, echo times, note spacing.
_STYLE_SOUND = {
    "warm": ((10, 14), (.22, .08, .030), .024, (.31, .59, .97), None),
    "deep": ((15, 21), (.055, .015, .034), .040, (.37, .61, .89), None),
    "shimmer": ((8, 12), (.30, .16, .022), 0.0, (.17, .29, .53), (1.8, 3.4)),
    "pulse": ((8, 12), (.32, .10, .026), .018, (.23, .47, .71), (48, 66)),
}


def resolve_audio_seed(cfg: Audio) -> Audio:
    """Resolve the seed and random style once without modifying reusable settings."""
    if cfg.style not in MUSIC_STYLES:
        raise ValueError("Ungültiger Ambient-Stil.")
    seed = secrets.randbits(32) if cfg.seed is None else cfg.seed
    style = cfg.style
    if style == "random":
        style = str(np.random.default_rng(seed ^ 0x51A7).choice(tuple(_STYLE_CHORDS)))
    return replace(cfg, seed=seed, style=style)


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
    if cfg.harmony not in ("original", "floating", "dusk") or not -12 <= cfg.transpose <= 12:
        raise ValueError("Ungültige Ambient-Harmonie oder Transposition.")
    if cfg.style == "classic":
        _synthesize_classic_stream(path, duration, cfg)
    elif cfg.style in _STYLE_CHORDS:
        _synthesize_styled_stream(path, duration, cfg)
    else:
        raise ValueError("Ambient-Stil muss vor der Synthese aufgeloest sein.")


def _synthesize_styled_stream(path: Path, duration: float, cfg: Audio) -> None:
    """Distinct tonal palettes and instrumentation, streamed in small blocks."""
    sr, count = cfg.sample_rate, round(duration * cfg.sample_rate)
    rng = np.random.default_rng(cfg.seed)
    seconds, harmonics, bass_gain, echo_times, spacing = _STYLE_SOUND[cfg.style]
    # A new key/register, voicing order and tempo are audible composition changes,
    # rather than merely changing oscillator phases in the same arrangement.
    key = int(rng.choice([-5, -3, 0, 2, 4, 5])) + cfg.transpose
    chords = np.array(_STYLE_CHORDS[cfg.style])[rng.permutation(4)] + key
    progression_time = float(rng.uniform(*seconds))
    phases = rng.uniform(0, 2 * np.pi, (4, 6, 2))
    detune = rng.uniform(-.0016, .0016, (4, 6, 2))
    pans = rng.uniform(.2, .8, (4, 6))
    second, third, pad_gain = harmonics
    second *= float(rng.uniform(.85, 1.15))
    third *= float(rng.uniform(.85, 1.15))
    events = []
    if spacing:
        onset = .35 if cfg.style == "pulse" else .65
        beat = 60 / float(rng.uniform(*spacing)) if cfg.style == "pulse" else None
        pattern = rng.permutation([2, 3, 4, 5])
        step = 0
        while onset < duration:
            chord = int(onset / progression_time) % 4
            index = int(pattern[step % 4]) if beat else int(rng.integers(2, 6))
            midi = int(chords[chord, index]) + (0 if beat else 12)
            events.append((onset, 440 * 2 ** ((midi - 69) / 12), float(rng.uniform(.25, .75))))
            onset += beat * float(rng.uniform(.97, 1.03)) if beat else float(rng.uniform(*spacing))
            step += 1
    onsets = np.array([event[0] for event in events])
    delays = [round(sr * value) for value in echo_times]
    history = np.zeros((max(delays), 2), np.float64)
    with wave.open(str(path), "wb") as wav:
        wav.setparams((2, 2, sr, 0, "NONE", "not compressed"))
        for start in range(0, count, 8192):
            n = min(8192, count - start)
            t = (start + np.arange(n, dtype=np.float64)) / sr
            position = t / progression_time
            chord_index = np.floor(position).astype(int) % 4
            frac = position % 1
            blend = frac * frac * (3 - 2 * frac)
            block = np.zeros((n, 2), np.float64)
            for c in range(4):
                envelope = np.where(chord_index == c, 1 - blend, 0) + np.where((chord_index + 1) % 4 == c, blend, 0)
                if not envelope.any():
                    continue
                for v, midi in enumerate(chords[c]):
                    freq = 440 * 2 ** ((float(midi) - 69) / 12)
                    voice = np.zeros(n)
                    for osc in range(2):
                        phase = 2 * np.pi * freq * (1 + detune[c, v, osc]) * t + phases[c, v, osc]
                        voice += (np.sin(phase) + second * np.sin(2 * phase) + third * np.sin(3 * phase)) / 2
                    swell = .85 + .15 * np.sin(2 * np.pi * .04 * t + phases[c, v, 0])
                    voice *= envelope * pad_gain * swell
                    block[:, 0] += voice * np.sqrt(1 - pans[c, v])
                    block[:, 1] += voice * np.sqrt(pans[c, v])
                if bass_gain:
                    freq = 440 * 2 ** ((float(chords[c, 0]) - 12 - 69) / 12)
                    bass = bass_gain * envelope * np.sin(2 * np.pi * freq * t + phases[c, 0, 0])
                    block += bass[:, None] / np.sqrt(2)
            # Only inspect notes whose tails overlap this block, even for long clips.
            tail = 5.0 if cfg.style == "shimmer" else 2.0
            first = int(np.searchsorted(onsets, t[0] - tail))
            last = int(np.searchsorted(onsets, t[-1], side="right"))
            for onset, freq, pan in events[first:last]:
                age = np.maximum(t - onset, 0)
                attack_time = .08 if cfg.style == "shimmer" else .045
                attack = np.sin(np.clip(age / attack_time, 0, 1) * np.pi / 2) ** 2
                decay = 1.5 if cfg.style == "shimmer" else .45
                end = np.clip((tail - age) / .25, 0, 1) ** 2
                envelope = attack * np.exp(-age / decay) * end * (t >= onset)
                partials = ((1, 1), (2.01, .25), (2.8, .08)) if cfg.style == "shimmer" else ((1, 1), (2, .22), (3, .08))
                voice = sum(gain * np.sin(2 * np.pi * freq * ratio * age) for ratio, gain in partials)
                voice *= (.048 if cfg.style == "shimmer" else .060) * envelope
                block[:, 0] += voice * np.sqrt(1 - pan)
                block[:, 1] += voice * np.sqrt(pan)
            joined = np.concatenate((history, block))
            wet = block.copy()
            for delay, gain in zip(delays, (.20, .13, .08)):
                wet += joined[len(history) - delay:len(history) - delay + n, ::-1] * gain
            history = joined[-len(history):].copy()
            fade = min(cfg.fade_seconds, duration / 2)
            envelope = np.ones(n)
            if fade:
                envelope = np.sin(np.clip(t / fade, 0, 1) * np.pi / 2) ** 2
                envelope *= np.sin(np.clip((duration - t - 1 / sr) / fade, 0, 1) * np.pi / 2) ** 2
            wet = np.tanh(wet * 1.8) * .65 * envelope[:, None]
            wav.writeframes(np.round(wet * 32767).astype("<i2").tobytes())


def _synthesize_classic_stream(path: Path, duration: float, cfg: Audio) -> None:
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


def main(argv=None) -> int:
    """Listen to an ambient style without running StarNet or rendering video."""
    import argparse
    import sys
    from .config import Config

    parser = argparse.ArgumentParser(description="AstroMotion: kurze Ambient-Hoerprobe ohne Videorendering")
    parser.add_argument("--style", choices=MUSIC_STYLES, default="random")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--output", type=Path, default=Path("music_preview.wav"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        cfg = Audio(mode="ambient", style=args.style, seed=args.seed, fade_seconds=.4)
        Config(audio=cfg).validate()
        if not .1 <= args.duration <= 60:
            raise ValueError("Hoerproben: Dauer 0.1..60 Sekunden.")
        output = args.output.resolve()
        if output.suffix.lower() != ".wav":
            raise ValueError("Hoerprobe benoetigt eine .wav-Ausgabedatei.")
        if output.exists() and not args.overwrite:
            raise FileExistsError("Hoerprobe existiert bereits; --overwrite verwenden.")
        cfg = resolve_audio_seed(cfg)
        synthesize_ambient(output, args.duration, cfg)
        print(f"Ambient: {cfg.style}, Seed {cfg.seed}\n{output}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
