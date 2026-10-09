"""Single-frame FFmpeg streaming, atomic final output, and ffprobe validation."""
from __future__ import annotations

import json
import logging
from pathlib import Path
import shutil
import subprocess
import uuid

import numpy as np

from .config import Config

LOG = logging.getLogger(__name__)


def resolve_binary(value: str) -> str:
    located = shutil.which(value)
    if not located and Path(value).is_file():
        located = str(Path(value).resolve())
    if not located:
        raise FileNotFoundError(f"Programm nicht gefunden: {value}. FFmpeg/FFprobe installieren und PATH prüfen.")
    return located


def probe(path: Path, ffprobe: str = "ffprobe") -> dict:
    result = subprocess.run([resolve_binary(ffprobe), "-v", "error", "-show_streams", "-show_format",
                             "-of", "json", str(path)], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError(f"FFprobe fehlgeschlagen: {result.stderr[-2000:]}")
    return json.loads(result.stdout)


def verify_video(path: Path, cfg: Config, has_audio: bool) -> dict:
    data = probe(path, cfg.encoding.ffprobe)
    videos = [s for s in data["streams"] if s["codec_type"] == "video"]
    audios = [s for s in data["streams"] if s["codec_type"] == "audio"]
    if len(videos) != 1:
        raise RuntimeError("Export enthält keinen eindeutigen Video-Stream.")
    v = videos[0]
    if (v["width"], v["height"]) != cfg.size or v["codec_name"] != "h264" or v["pix_fmt"] != "yuv420p":
        raise RuntimeError("Export: unerwartete Abmessungen/Codec/Pixelformat.")
    if "nb_frames" in v and int(v["nb_frames"]) != cfg.frame_count:
        raise RuntimeError("Export enthält eine unerwartete Framezahl.")
    numerator, denominator = map(int, v["avg_frame_rate"].split("/"))
    if abs(numerator / denominator - cfg.fps) > 1e-3:
        raise RuntimeError("Export hat eine unerwartete Bildrate.")
    if abs(float(v["duration"]) - cfg.actual_duration) > 1 / cfg.fps + .02:
        raise RuntimeError("Export hat eine unerwartete Videodauer.")
    if bool(audios) != has_audio:
        raise RuntimeError("Export: Audio-Stream fehlt oder ist unerwartet vorhanden.")
    if has_audio and (len(audios) != 1 or audios[0]["codec_name"] != "aac"):
        raise RuntimeError("Export enthält keinen gültigen AAC-Audiostream.")
    if has_audio and abs(float(audios[0].get("duration", data["format"]["duration"])) - cfg.actual_duration) > .12:
        raise RuntimeError("Audio- und Videodauer stimmen nicht überein.")
    return data


class VideoEncoder:
    def __init__(self, output: Path, cfg: Config, audio: Path | None, log_path: Path):
        self.output, self.cfg, self.has_audio = output, cfg, audio is not None
        self.log_path = log_path
        output.parent.mkdir(parents=True, exist_ok=True)
        self.partial = output.parent / f".{output.stem}.{uuid.uuid4().hex}.partial.mp4"
        self.log = log_path.open("w", encoding="utf-8")
        w, h = cfg.size
        cmd = [resolve_binary(cfg.encoding.ffmpeg), "-hide_banner", "-loglevel", "warning", "-y",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-video_size", f"{w}x{h}",
               "-framerate", str(cfg.fps), "-i", "pipe:0"]
        if audio:
            cmd += ["-stream_loop", "-1", "-i", str(audio.resolve())]
        cmd += ["-map", "0:v:0"]
        if audio:
            fade = min(cfg.audio.fade_seconds, cfg.actual_duration / 2)
            filters = f"volume={cfg.audio.gain},afade=t=in:st=0:d={fade},afade=t=out:st={cfg.actual_duration - fade}:d={fade}"
            if cfg.loop.enabled:
                filters = f"volume={cfg.audio.gain}"
            cmd += ["-map", "1:a:0", "-af", filters, "-c:a", "aac", "-b:a", "192k", "-ar", str(cfg.audio.sample_rate)]
        cmd += ["-t", str(cfg.actual_duration), "-c:v", "libx264", "-crf", str(cfg.encoding.crf),
                "-preset", cfg.encoding.preset, "-threads", str(cfg.encoding.threads or 4),
                "-filter_threads", "2", "-vf", "scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p",
                "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                "-movflags", "+faststart", str(self.partial)]
        self.frames = 0
        self.info: dict | None = None
        try:
            self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=self.log)
        except BaseException:
            self.log.close()
            raise

    def __enter__(self) -> VideoEncoder:
        return self

    def write(self, frame: np.ndarray) -> None:
        w, h = self.cfg.size
        if frame.shape != (h, w, 3) or frame.dtype != np.uint8:
            raise ValueError("Encoder erwartet ein RGB-uint8-Frame in Ausgabegröße.")
        try:
            assert self.process.stdin is not None
            self.process.stdin.write(np.ascontiguousarray(frame).tobytes())
            self.frames += 1
        except BrokenPipeError as exc:
            raise RuntimeError(f"FFmpeg hat abgebrochen: {self.log_path} prüfen.") from exc

    def __exit__(self, exc_type, exc, traceback) -> None:
        try:
            if exc_type:
                self.process.kill()
                self.process.wait(timeout=10)
                return
            assert self.process.stdin is not None
            self.process.stdin.close()
            code = self.process.wait(timeout=180)
            self.log.flush()
            if code:
                tail = self.log_path.read_text(encoding="utf-8", errors="replace")[-3000:]
                raise RuntimeError(f"FFmpeg fehlgeschlagen ({code}): {tail}")
            if self.frames != self.cfg.frame_count:
                raise RuntimeError("Nicht alle Frames wurden geschrieben.")
            if self.cfg.encoding.verify:
                self.info = verify_video(self.partial, self.cfg, self.has_audio)
            self.partial.replace(self.output)
        except BaseException:
            if self.process.poll() is None:
                self.process.kill()
                self.process.wait(timeout=10)
            raise
        finally:
            if self.process.stdin and not self.process.stdin.closed:
                try:
                    self.process.stdin.close()
                except BrokenPipeError:
                    pass
            self.log.close()
            self.partial.unlink(missing_ok=True)
