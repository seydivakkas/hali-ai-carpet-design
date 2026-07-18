"""Color palette extraction per spec Section 16."""

from __future__ import annotations

import numpy as np

try:
    from sklearn.cluster import KMeans

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from typing import TYPE_CHECKING

from carpet_designer.domain.schemas import ColorAnalysisResult, DominantColor
from carpet_designer.logging_config import get_logger

if TYPE_CHECKING:
    from PIL import Image

logger = get_logger("analysis.color")


def extract_dominant_colors(image: Image.Image, num_colors: int = 5) -> ColorAnalysisResult:
    """Extract dominant colors from an image using KMeans.

    Args:
        image: PIL Image to analyze.
        num_colors: Number of colors to extract.

    Returns:
        ColorAnalysisResult containing dominant colors.
    """
    if not SKLEARN_AVAILABLE:
        logger.warning("scikit-learn not available, returning dummy color analysis")
        return ColorAnalysisResult(
            dominant_colors=[DominantColor(hex="#FF0000", proportion=1.0)],
            status="DESIGN_REFERENCE_ONLY",
        )

    # Resize for performance
    img = image.copy()
    img.thumbnail((100, 100))
    img_data = np.array(img.convert("RGB"))

    # Reshape to list of RGB pixels
    pixels = img_data.reshape(-1, 3)

    # Avoid asking KMeans for more clusters than the image actually contains.
    unique_colors = np.unique(pixels, axis=0)
    cluster_count = max(1, min(num_colors, len(unique_colors)))

    # Run KMeans deterministically.
    kmeans = KMeans(n_clusters=cluster_count, random_state=42, n_init=10)
    labels = kmeans.fit_predict(pixels)

    # Calculate proportions
    counts = np.bincount(labels)
    proportions = counts / len(pixels)

    dominant_colors = []
    for center, prop in zip(kmeans.cluster_centers_, proportions, strict=False):
        r, g, b = [int(c) for c in center]
        hex_code = f"#{r:02x}{g:02x}{b:02x}"
        dominant_colors.append(
            DominantColor(
                hex=hex_code,
                rgb=[r, g, b],
                lab=_rgb_to_lab(r, g, b),
                proportion=float(prop),
            )
        )

    # Sort by proportion descending
    dominant_colors.sort(key=lambda x: x.proportion, reverse=True)

    return ColorAnalysisResult(dominant_colors=dominant_colors, status="DESIGN_REFERENCE_ONLY")


def _rgb_to_lab(red: int, green: int, blue: int) -> list[float]:
    """Convert an sRGB color to CIE L*a*b* using a D65 white point."""
    rgb = np.array([red, green, blue], dtype=float) / 255.0
    linear = np.where(rgb > 0.04045, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
    x, y, z = (
        np.array(
            [
                [0.4124564, 0.3575761, 0.1804375],
                [0.2126729, 0.7151522, 0.0721750],
                [0.0193339, 0.1191920, 0.9503041],
            ]
        )
        @ linear
    )
    xyz = np.array([x / 0.95047, y, z / 1.08883])
    delta = 6 / 29
    transformed = np.where(
        xyz > delta**3,
        np.cbrt(xyz),
        xyz / (3 * delta**2) + 4 / 29,
    )
    lightness = 116 * transformed[1] - 16
    a_value = 500 * (transformed[0] - transformed[1])
    b_value = 200 * (transformed[1] - transformed[2])
    return [float(lightness), float(a_value), float(b_value)]
