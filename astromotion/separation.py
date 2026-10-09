"""Explicit StarNet adapter, quality checks, and reconstructable star extraction."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import subprocess

import numpy as np

from .config import Separation
from .imaging import FloatImage, load_image, save_tiff, to_linear

LOG = logging.getLogger(__name__)


@dataclass
class Layers:
    nebula: FloatImage  # linear RGB
    stars: FloatImage  # screen fraction or additive radiance; linear RGB
    blend: str
    diagnostics: dict[str, float]

    def composite(self) -> FloatImage:
        return composite(self.nebula, self.stars, self.blend)


def composite(nebula: FloatImage, stars: FloatImage, blend: str = "screen") -> FloatImage:
    if blend == "screen":
        return nebula + (1 - nebula) * stars
    return np.clip(nebula + stars, 0, 1)


def extract_layers(original: FloatImage, starless: FloatImage, cfg: Separation) -> Layers:
    if original.shape != starless.shape:
        raise ValueError("Original und sternenloses Bild müssen exakt gleich groß/ausgerichtet sein.")
    if not np.isfinite(starless).all() or not np.isfinite(original).all():
        raise ValueError("Bild enthält ungültige Pixelwerte.")
    if float(starless.max()) < 1e-5:
        raise ValueError("Sternenloses Bild ist schwarz; keine zuverlässige Sternentrennung.")
    negative = float(np.maximum(starless - original, 0).mean())
    if negative > cfg.max_negative_error:
        raise ValueError(f"Sternenloses Bild passt nicht zum Original: mittlere negative Differenz {negative:.4f}. "
                         "Keine separate Farbkorrektur, Streckung oder Neuausrichtung verwenden.")
    if negative > .001:
        LOG.warning("Starless liegt lokal über dem Original (mittlere Differenz %.5f). "
                    "Diese Werte werden für eine rekonstruierbare Ebene begrenzt; Ebenen visuell prüfen.", negative)
    if cfg.foreground_cleanup:
        LOG.warning("foreground_cleanup wurde entfernt und wird ignoriert; keine Reparaturfilter.")
    orig = to_linear(original)
    base = np.minimum(to_linear(starless), orig)
    difference = np.maximum(orig - base, 0)
    if float(difference.max()) < 1e-5:
        raise ValueError("Keine separate Sternebene gefunden. Ist das sternenlose Bild das Original?")
    stars = difference / np.maximum(1 - base, 1e-6) if cfg.blend == "screen" else difference
    # Keep the measured RGB residual intact: no masks, channel normalization,
    # inpainting, or redistribution into the StarNet2 background. The minimum
    # above is only the non-negative decomposition bound, not a repair filter.
    layers = Layers(base, np.clip(stars, 0, 1), cfg.blend, {"negative_mean_srgb": negative})
    layers.diagnostics["reconstruction_max_error_linear"] = float(np.abs(layers.composite() - orig).max())
    layers.diagnostics["positive_residual_energy_fraction"] = float(difference.sum() / max(float(orig.sum()), 1e-6))
    layers.diagnostics["foreground_cleanup_enabled"] = 0.0
    layers.diagnostics["background_clamp_max_linear"] = float(np.max(to_linear(starless) - base))
    LOG.info("Ebenen rekonstruiert: max. linearer Fehler %.8f", layers.diagnostics["reconstruction_max_error_linear"])
    return layers


def starnet_command(cfg: Separation, input_path: Path, output_path: Path) -> list[str]:
    if not cfg.executable:
        raise ValueError("StarNet++ fehlt: --starnet EXE oder --starless BILD angeben.")
    exe = Path(cfg.executable).expanduser().resolve()
    if not exe.is_file():
        raise FileNotFoundError(f"StarNet-Programm nicht gefunden: {exe}")
    mode = cfg.mode
    if mode == "auto":
        mode = "modern" if exe.stem.lower() == "starnet2" else "legacy"
    if mode == "modern":
        args = [str(exe), "--input", str(input_path.resolve()), "--output", str(output_path.resolve()),
                "--stride", str(cfg.stride)]
    else:
        args = [str(exe), str(input_path.resolve()), str(output_path.resolve()), str(cfg.stride)]
    return args + cfg.extra_args


def run_starnet(image: FloatImage, cfg: Separation, workspace: Path) -> FloatImage:
    if min(image.shape[:2]) < 512:
        raise ValueError("StarNet benötigt hier mindestens 512 × 512 Pixel. Größeres Foto oder --starless verwenden.")
    input_path, output_path = workspace / "starnet_input.tif", workspace / "starnet_starless.tif"
    output_path.unlink(missing_ok=True)  # Never accept stale output from an earlier run.
    save_tiff(input_path, image)
    cmd = starnet_command(cfg, input_path, output_path)
    LOG.info("StarNet startet; Protokoll: %s", workspace / "starnet.log")
    # cwd must contain legacy DLLs and model weights. Absolute input/output paths
    # and shell=False also handle spaces and avoid shell injection.
    with (workspace / "starnet.log").open("w", encoding="utf-8") as log:
        try:
            result = subprocess.run(cmd, cwd=Path(cmd[0]).parent, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=cfg.timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("StarNet-Zeitlimit überschritten; Protokoll prüfen.") from exc
    if result.returncode != 0 or not output_path.is_file():
        raise RuntimeError(f"StarNet fehlgeschlagen (Code {result.returncode}); {workspace / 'starnet.log'} prüfen. "
                           "Es wird keine Ersatz-Sternentrennung verwendet.")
    starless = load_image(output_path)
    if starless.shape != image.shape:
        raise ValueError("StarNet-Ausgabe hat eine unerwartete Bildgröße.")
    return starless
