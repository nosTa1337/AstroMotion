"""Display-ready RGB photographs; preserve integer precision until video output."""
from __future__ import annotations

import io
import logging
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageCms, ImageOps
import tifffile

FloatImage = NDArray[np.float32]
LOG = logging.getLogger(__name__)


def _orient(image: NDArray, orientation: int) -> NDArray:
    if orientation == 2:
        return image[:, ::-1]
    if orientation == 3:
        return image[::-1, ::-1]
    if orientation == 4:
        return image[::-1]
    if orientation == 5:
        return image.swapaxes(0, 1)
    if orientation == 6:
        return np.rot90(image, -1)
    if orientation == 7:
        return image.swapaxes(0, 1)[::-1, ::-1]
    if orientation == 8:
        return np.rot90(image, 1)
    return image


def load_image(path: Path, max_pixels: int = 120_000_000) -> FloatImage:
    if not path.is_file():
        raise FileNotFoundError(f"Bild nicht gefunden: {path}")
    if path.suffix.lower() not in (".jpg", ".jpeg", ".png", ".tif", ".tiff"):
        raise ValueError("Unterstützt: JPG, PNG, TIFF (RGB oder Graustufen, 8/16 Bit).")
    # Metadata read before decoding gives a useful, configurable memory limit.
    with Image.open(path) as meta:
        if meta.width * meta.height > max_pixels:
            raise ValueError(f"Bild überschreitet max_input_pixels={max_pixels}.")
        icc = meta.info.get("icc_profile")
        orientation = int(meta.getexif().get(274, 1))
        if getattr(meta, "n_frames", 1) > 1:
            raise ValueError("Mehrseitige/animierte Bilder nicht unterstützt; ein einzelnes RGB-Bild exportieren.")
        if meta.mode in ("CMYK", "P") or (icc and path.suffix.lower() in (".jpg", ".jpeg")):
            im = ImageOps.exif_transpose(meta)
            if "transparency" in meta.info and np.asarray(im.convert("RGBA"))[..., 3].min() < 255:
                raise ValueError("Transparente Astrofotos werden nicht unterstützt; zuvor auf RGB reduzieren.")
            if icc:
                source = ImageCms.ImageCmsProfile(io.BytesIO(icc))
                im = ImageCms.profileToProfile(im, source, ImageCms.createProfile("sRGB"), outputMode="RGB")
            else:
                im = im.convert("RGB")
            return np.asarray(im).astype(np.float32) / 255.0
    # UNCHANGED preserves 16-bit PNG/TIFF and ignores orientation (applied below).
    data = np.fromfile(path, dtype=np.uint8)  # Unicode paths also work on Windows.
    arr = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if arr is None:
        raise ValueError(f"Bild kann nicht decodiert werden: {path}")
    if arr.dtype not in (np.uint8, np.uint16):
        raise ValueError("Nur 8-/16-Bit Integer-Bilder. Lineare FITS/Float-TIFF zuvor stretchen/exportieren.")
    if arr.ndim == 2:
        arr = np.repeat(arr[..., None], 3, axis=2)
    elif arr.ndim == 3 and arr.shape[2] == 4:
        if np.any(arr[..., 3] != np.iinfo(arr.dtype).max):
            raise ValueError("Transparente Astrofotos werden nicht unterstützt; zuvor auf RGB reduzieren.")
        arr = arr[..., :3]
    elif arr.ndim != 3 or arr.shape[2] != 3:
        raise ValueError("Erwartet wird ein RGB- oder Graustufenbild.")
    scale = float(np.iinfo(arr.dtype).max)
    arr = _orient(arr[..., ::-1], orientation)
    rgb = np.ascontiguousarray(arr, dtype=np.float32) / scale
    if icc:
        if scale == 255:
            im = Image.fromarray(np.round(rgb * 255).astype(np.uint8), "RGB")
            im = ImageCms.profileToProfile(im, ImageCms.ImageCmsProfile(io.BytesIO(icc)),
                                          ImageCms.createProfile("sRGB"), outputMode="RGB")
            rgb = np.asarray(im).astype(np.float32) / 255.0
        else:
            # Never silently reduce a 16-bit image to 8 bits for color conversion.
            profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            name = ImageCms.getProfileDescription(profile).lower()
            if "srgb" not in name:
                raise ValueError("16-Bit-Bild mit anderem ICC-Profil: zuerst verlustfrei nach sRGB konvertieren.")
    if min(rgb.shape[:2]) < 16:
        raise ValueError("Bild ist zu klein (mindestens 16 × 16 Pixel).")
    LOG.info("Bild %s: %dx%d, %d Bit", path.name, rgb.shape[1], rgb.shape[0], 16 if scale > 255 else 8)
    return rgb


def resize_work(image: FloatImage, long_edge: int) -> FloatImage:
    h, w = image.shape[:2]
    factor = min(1.0, long_edge / max(h, w))
    if factor == 1:
        return image
    return cv2.resize(image, (max(16, round(w * factor)), max(16, round(h * factor))),
                      interpolation=cv2.INTER_AREA)


def save_tiff(path: Path, image: FloatImage) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(path, np.round(np.clip(image, 0, 1) * 65535).astype(np.uint16), photometric="rgb")


def save_png(path: Path, image: FloatImage) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.round(np.clip(image, 0, 1)[..., ::-1] * 65535).astype(np.uint16)
    success, encoded = cv2.imencode(".png", data)
    if not success:
        raise RuntimeError("PNG-Encoding fehlgeschlagen.")
    encoded.tofile(path)


def to_linear(rgb: FloatImage) -> FloatImage:
    return np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4).astype(np.float32)


def to_srgb(rgb: FloatImage) -> FloatImage:
    rgb = np.clip(rgb, 0, 1)
    return np.where(rgb <= .0031308, rgb * 12.92, 1.055 * rgb ** (1 / 2.4) - .055).astype(np.float32)
