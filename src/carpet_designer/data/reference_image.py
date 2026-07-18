"""Validation and storage helpers for user-supplied carpet references."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING, cast

from PIL import Image, ImageOps

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class StoredReferenceImage:
    """Normalized local reference image plus auditable metadata."""

    path: Path
    sha256: str
    width: int
    height: int
    palette: list[str]


def store_reference_image(payload: bytes, output_dir: Path) -> StoredReferenceImage:
    """Validate, normalize and content-address an uploaded image."""
    if not payload:
        raise ValueError("Yüklenen referans görsel boş.")
    if len(payload) > 25 * 1024 * 1024:
        raise ValueError("Referans görsel 25 MB sınırını aşıyor.")

    try:
        with Image.open(BytesIO(payload)) as opened:
            opened.load()
            image = ImageOps.exif_transpose(opened).convert("RGB")
    except (OSError, ValueError) as error:
        raise ValueError("Dosya geçerli bir PNG, JPEG veya WEBP görseli değil.") from error
    if image.width < 64 or image.height < 64:
        raise ValueError("Referans görsel en az 64×64 piksel olmalı.")

    image.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
    sha256 = hashlib.sha256(payload).hexdigest()
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"reference_{sha256[:16]}.png"
    image.save(path, format="PNG", optimize=True)

    quantized = image.quantize(colors=5, method=Image.Quantize.MEDIANCUT).convert("RGB")
    color_counts = sorted(
        cast(
            "list[tuple[int, tuple[int, int, int]]]",
            quantized.getcolors(maxcolors=quantized.width * quantized.height) or [],
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    palette = [f"#{red:02X}{green:02X}{blue:02X}" for _, (red, green, blue) in color_counts[:5]]
    return StoredReferenceImage(
        path=path,
        sha256=sha256,
        width=image.width,
        height=image.height,
        palette=palette,
    )


def build_reference_guidance(variation_targets: list[str]) -> str:
    """Describe exactly which source-image attributes may change."""
    labels = {
        "style": "style family",
        "composition": "composition",
        "palette": "color palette",
        "motifs": "motifs",
        "border": "border structure",
        "symmetry": "symmetry intent",
        "resolution": "output resolution",
    }
    selected = [labels[target] for target in variation_targets if target in labels]
    preserved = [label for key, label in labels.items() if key not in variation_targets]
    change_text = ", ".join(selected) if selected else "seed-level surface details"
    preserve_text = ", ".join(preserved) if preserved else "overall carpet identity"
    return (
        f"Use the uploaded carpet as the visual reference; change only {change_text}; "
        f"preserve the source {preserve_text}, top-down orientation and complete rug framing"
    )


def fit_generation_size(
    source_width: int,
    source_height: int,
    target_long_edge: int,
    *,
    preserve_aspect_ratio: bool,
) -> tuple[int, int]:
    """Return SDXL-safe dimensions while optionally preserving source aspect ratio."""
    target = max(256, min(1024, target_long_edge))
    if not preserve_aspect_ratio:
        return target, target
    scale = target / max(source_width, source_height)
    width = max(256, round(source_width * scale / 8) * 8)
    height = max(256, round(source_height * scale / 8) * 8)
    return min(1024, width), min(1024, height)
