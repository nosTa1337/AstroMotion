"""Checked reuse of an unmodified, QA-validated StarNet2 working-size output."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np

from .config import Separation
from .imaging import FloatImage, load_image

MANIFEST = "starnet_cache.json"
STARLESS = "starnet_starless.tif"
MODEL_SUFFIXES = {".pb", ".onnx", ".h5", ".hdf5", ".pt", ".pth", ".weights", ".bin"}


def file_checksum(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def cache_identity(input_path: Path, image: FloatImage, cfg: Separation, work_long_edge: int) -> dict:
    executable = Path(cfg.executable).expanduser().resolve()
    settings = asdict(cfg)
    settings["executable"] = str(executable)
    models = {str(path.relative_to(executable.parent)): file_checksum(path)
              for path in sorted(executable.parent.rglob("*"))
              if path.is_file() and path.suffix.lower() in MODEL_SUFFIXES}
    # Extra CLI arguments can refer to model/config files outside the CLI folder.
    argument_files = {}
    for argument in cfg.extra_args:
        value = argument.split("=", 1)[1] if argument.startswith("-") and "=" in argument else argument
        path = Path(value).expanduser()
        path = (path if path.is_absolute() else executable.parent / path).resolve()
        if path.is_file():
            argument_files[str(path)] = file_checksum(path)
    return {"input_sha256": file_checksum(input_path), "work_long_edge": work_long_edge,
            "work_shape": list(image.shape), "work_dtype": str(image.dtype),
            "work_sha256": hashlib.sha256(memoryview(np.ascontiguousarray(image)).cast("B")).hexdigest(),
            "separation": settings, "executable_sha256": file_checksum(executable),
            "models": models, "argument_files": argument_files}


def load_cached_starless(workspace: Path, identity: dict) -> FloatImage | None:
    """An absent, mismatched, modified or unreadable cache is a miss."""
    try:
        manifest = json.loads((workspace / MANIFEST).read_text(encoding="utf-8"))
        if (not isinstance(manifest, dict) or manifest.get("version") != 1
                or manifest.get("source") != "StarNet2" or manifest.get("identity") != identity):
            return None
        path = workspace / STARLESS
        if file_checksum(path) != manifest.get("starless_sha256"):
            return None
        h, w, _ = identity["work_shape"]
        starless = load_image(path, max_pixels=h * w)
        if list(starless.shape) != identity["work_shape"]:
            return None
        return starless
    except (OSError, ValueError, TypeError, KeyError):
        return None


def save_cache_manifest(workspace: Path, identity: dict) -> None:
    """Called only after a fresh CLI result passes the existing layer QA."""
    manifest = {"version": 1, "source": "StarNet2", "identity": identity,
                "starless_sha256": file_checksum(workspace / STARLESS)}
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=workspace,
                                         prefix="starnet_cache.", suffix=".tmp", delete=False) as file:
            temporary = Path(file.name)
            file.write(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        temporary.replace(workspace / MANIFEST)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
