"""Random or reproducible stereo ambient synthesis without recorded samples."""
from __future__ import annotations

from dataclasses import dataclass, replace
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


@dataclass(frozen=True)
class _Note:
    onset: float
    frequency: float
    pan: float
    gain: float
    attack: float
    decay: float
    tail: float
    partials: tuple[tuple[float, float], ...]


def _styled_notes(chords, progression_time, duration, cfg, spacing, rng, evolution):
    """Chord-linked phrases with breathing room, and changing arpeggio/bell motifs."""
    notes = []
    strength = cfg.development
    if spacing:
        onset = .35 if cfg.style == 'pulse' else .65
        beat = 60 / float(rng.uniform(*spacing)) if cfg.style == 'pulse' else None
        pattern = rng.permutation([2, 3, 4, 5])
        motif = pattern.copy()
        step = 0
        while onset < duration:
            if strength and step % 4 == 0:
                motif = np.roll(pattern, int(evolution.integers(0, 4)))
                if evolution.random() < .5:
                    motif = motif[::-1]
            chord = int(onset / progression_time + (.5 if strength else 0)) % 4
            if strength:
                index = int(motif[step % 4])
            else:
                index = int(pattern[step % 4]) if beat else int(rng.integers(2, 6))
            midi = int(chords[chord, index]) + (0 if beat else 12)
            pan = float(rng.uniform(.25, .75))
            velocity = 1 + strength * float(evolution.uniform(-.30, .18)) if strength else 1
            rest = bool(beat and strength and step % 4 == 3 and evolution.random() < .30 * strength)
            if not rest:
                notes.append(_Note(onset, 440 * 2 ** ((midi - 69) / 12), pan,
                    (.060 if beat else .048) * velocity, .045 if beat else .08,
                    .45 if beat else 1.5, 2 if beat else 5,
                    ((1, 1), (2, .22), (3, .08)) if beat else ((1, 1), (2.01, .25), (2.8, .08))))
            onset += beat * float(rng.uniform(.97, 1.03)) if beat else float(rng.uniform(*spacing))
            step += 1
    elif strength:
        # Warm/deep previously had only sustained chords. Soft four-note ideas
        # now answer each other; each note follows the currently dominant chord.
        onset = float(evolution.uniform(.7, 1.3))
        motif = np.array([[2, 4, 3, 2], [3, 4, 5, 3], [4, 3, 2, 3]])[evolution.integers(3)]
        phrase = 0
        while onset < duration:
            indices = motif if phrase % 2 == 0 else np.roll(motif, 1)
            spacing_seconds = float(evolution.uniform(.7, 1.0) if cfg.style == 'warm' else evolution.uniform(.95, 1.25))
            for step, index in enumerate(indices):
                start = onset + step * spacing_seconds
                if start >= duration:
                    break
                chord = int(start / progression_time + .5) % 4
                midi = int(chords[chord, index]) + (12 if cfg.style == 'deep' else 0)
                notes.append(_Note(start, 440 * 2 ** ((midi - 69) / 12), float(evolution.uniform(.3, .7)),
                    (.052 if cfg.style == 'warm' else .035) * strength * float(evolution.uniform(.8, 1.15)),
                    .22 if cfg.style == 'warm' else .35, 1.0 if cfg.style == 'warm' else 1.4,
                    4 if cfg.style == 'warm' else 6, ((1, 1), (2, .12), (3, .035))))
            onset += 4 * spacing_seconds + float(evolution.uniform(1.2, 2.6)) / (.6 + .4 * strength)
            phrase += 1
    return sorted(notes, key=lambda note: note.onset)


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
    if not 0 <= cfg.development <= 1:
        raise ValueError("Audio development: 0..1.")
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
    strength = cfg.development
    evolution = np.random.default_rng(cfg.seed ^ 0xD3E10)
    minimum = 6.0 if cfg.style == 'deep' else 4.5
    target_time = min(progression_time, max(minimum, duration / 4))
    progression_time += strength * (target_time - progression_time)
    phases = rng.uniform(0, 2 * np.pi, (4, 6, 2))
    detune = rng.uniform(-.0016, .0016, (4, 6, 2))
    pans = rng.uniform(.2, .8, (4, 6))
    second, third, pad_gain = harmonics
    second *= float(rng.uniform(.85, 1.15))
    third *= float(rng.uniform(.85, 1.15))
    notes = _styled_notes(chords, progression_time, duration, cfg, spacing, rng, evolution)
    onsets = np.array([note.onset for note in notes])
    tail = max((note.tail for note in notes), default=0)
    textures = evolution.uniform(.35, 1.5, (5, 6))
    textures /= textures.mean(axis=1, keepdims=True)
    texture_seconds = float(evolution.uniform(5, 8))
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
            texture_position = t / texture_seconds
            texture_index = np.floor(texture_position).astype(int) % len(textures)
            texture_blend = .5 - .5 * np.cos(np.pi * (texture_position % 1))
            voicing = ((1 - texture_blend[:, None]) * textures[texture_index]
                       + texture_blend[:, None] * textures[(texture_index + 1) % len(textures)])
            for c in range(4):
                envelope = np.where(chord_index == c, 1 - blend, 0) + np.where((chord_index + 1) % 4 == c, blend, 0)
                if not envelope.any():
                    continue
                for v, midi in enumerate(chords[c]):
                    freq = 440 * 2 ** ((float(midi) - 69) / 12)
                    voice = np.zeros(n)
                    tone = 1 + .28 * strength * np.sin(2 * np.pi * t / (11 + v) + phases[c, v, 0])
                    for osc in range(2):
                        phase = 2 * np.pi * freq * (1 + detune[c, v, osc]) * t + phases[c, v, osc]
                        voice += (np.sin(phase) + second * tone * np.sin(2 * phase) + third * np.sin(3 * phase)) / 2
                    swell = .85 + .15 * np.sin(2 * np.pi * .04 * t + phases[c, v, 0])
                    voice *= envelope * pad_gain * swell * (1 + strength * (voicing[:, v] - 1))
                    block[:, 0] += voice * np.sqrt(1 - pans[c, v])
                    block[:, 1] += voice * np.sqrt(pans[c, v])
                if bass_gain:
                    freq = 440 * 2 ** ((float(chords[c, 0]) - 12 - 69) / 12)
                    bass_swell = 1 - .14 * strength + .14 * strength * np.sin(2 * np.pi * t / texture_seconds + phases[c, 0, 0])
                    bass = bass_gain * envelope * bass_swell * np.sin(2 * np.pi * freq * t + phases[c, 0, 0])
                    block += bass[:, None] / np.sqrt(2)
            # Only inspect notes whose tails overlap this block, even for long clips.
            first = int(np.searchsorted(onsets, t[0] - tail))
            last = int(np.searchsorted(onsets, t[-1], side="right"))
            for note in notes[first:last]:
                age = np.maximum(t - note.onset, 0)
                attack = np.sin(np.clip(age / note.attack, 0, 1) * np.pi / 2) ** 2
                end = np.clip((note.tail - age) / .25, 0, 1) ** 2
                envelope = attack * np.exp(-age / note.decay) * end * (t >= note.onset)
                voice = sum(gain * np.sin(2 * np.pi * note.frequency * ratio * age) for ratio, gain in note.partials)
                voice *= note.gain * envelope
                block[:, 0] += voice * np.sqrt(1 - note.pan)
                block[:, 1] += voice * np.sqrt(note.pan)
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
    parser.add_argument("--development", type=float, default=.65)
    parser.add_argument("--duration", type=float, default=12.0)
    parser.add_argument("--output", type=Path, default=Path("music_preview.wav"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        cfg = Audio(mode="ambient", style=args.style, seed=args.seed, development=args.development, fade_seconds=.4)
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
