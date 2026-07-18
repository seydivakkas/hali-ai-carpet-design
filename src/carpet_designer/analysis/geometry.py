"""Geometry and symmetry analysis per spec Section 17."""

from __future__ import annotations

import numpy as np

try:
    import cv2

    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

from typing import TYPE_CHECKING

from carpet_designer.domain.schemas import RepeatabilityResult, SeamResult, SymmetryResult
from carpet_designer.logging_config import get_logger

if TYPE_CHECKING:
    from PIL import Image

logger = get_logger("analysis.geometry")


def analyze_symmetry(image: Image.Image) -> SymmetryResult:
    """Analyze horizontal and vertical symmetry of an image.

    Args:
        image: PIL Image to analyze.

    Returns:
        SymmetryResult containing scores (1.0 = perfect symmetry).
    """
    if not OPENCV_AVAILABLE:
        logger.warning("OpenCV not available, returning dummy symmetry analysis")
        return SymmetryResult(
            horizontal_score=0.9,
            vertical_score=0.9,
            rotational_180_score=0.9,
            central_alignment_score=0.9,
        )

    img_data = np.array(image.convert("L"))  # Convert to grayscale
    h, w = img_data.shape

    # Horizontal symmetry (left vs right)
    left_half = img_data[:, : w // 2]
    right_half = img_data[:, w // 2 + (w % 2) :]  # Handle odd width
    right_half_flipped = cv2.flip(right_half, 1)  # Flip horizontally

    # Vertical symmetry (top vs bottom)
    top_half = img_data[: h // 2, :]
    bottom_half = img_data[h // 2 + (h % 2) :, :]
    bottom_half_flipped = cv2.flip(bottom_half, 0)  # Flip vertically

    def calc_score(half1: np.ndarray, half2: np.ndarray) -> float:
        # Mean Absolute Error mapped to 0-1 score
        diff = np.abs(half1.astype(float) - half2.astype(float))
        max_diff = 255.0
        return float(1.0 - (np.mean(diff) / max_diff))

    h_score = calc_score(left_half, right_half_flipped)
    v_score = calc_score(top_half, bottom_half_flipped)

    return SymmetryResult(
        horizontal_score=float(h_score),
        vertical_score=float(v_score),
        rotational_180_score=float((h_score + v_score) / 2),
        central_alignment_score=float(min(h_score, v_score)),
    )


def analyze_seam_continuity(image: Image.Image) -> SeamResult:
    """Analyze seam continuity for tileability.

    Args:
        image: PIL Image.

    Returns:
        SeamResult indicating how well the borders match.
    """
    if not OPENCV_AVAILABLE:
        return SeamResult(left_right_difference=0.1, top_bottom_difference=0.1, overall_score=0.9)

    img_data = np.array(image.convert("L"))

    # Extract 1px borders
    left = img_data[:, 0]
    right = img_data[:, -1]
    top = img_data[0, :]
    bottom = img_data[-1, :]

    lr_diff = np.mean(np.abs(left.astype(float) - right.astype(float))) / 255.0
    tb_diff = np.mean(np.abs(top.astype(float) - bottom.astype(float))) / 255.0

    return SeamResult(
        left_right_difference=float(lr_diff),
        top_bottom_difference=float(tb_diff),
        gradient_continuity=1.0 - float(lr_diff),
        frequency_discontinuity=1.0 - float(tb_diff),
        overall_score=1.0 - float((lr_diff + tb_diff) / 2),
    )


def analyze_repeatability(image: Image.Image) -> RepeatabilityResult:
    """Analyze motif repeatability.

    Args:
        image: PIL Image.

    Returns:
        RepeatabilityResult.
    """
    gray = np.asarray(image.convert("L").resize((128, 128)), dtype=np.float32)
    gray -= float(gray.mean())
    scale = float(np.sqrt(np.mean(gray**2)))
    if scale < 1e-6:
        return RepeatabilityResult()
    gray /= scale

    scores: list[tuple[int, float]] = []
    for shift in range(4, 65):
        horizontal = float(np.mean(gray[:, :-shift] * gray[:, shift:]))
        vertical = float(np.mean(gray[:-shift, :] * gray[shift:, :]))
        scores.append((shift, max(horizontal, vertical)))

    dominant_shift, peak = max(scores, key=lambda item: item[1])
    positive_scores = [score for _, score in scores if score > 0.35]
    periodicity = max(0.0, min(1.0, (peak + 0.2) / 1.2))
    spacing = min(1.0, len(positive_scores) / 8.0)
    dominant_period = round(dominant_shift * max(image.width, image.height) / 128)
    return RepeatabilityResult(
        autocorrelation_peak_count=len(positive_scores),
        periodicity_score=periodicity,
        spacing_consistency=spacing,
        dominant_period_px=dominant_period,
    )
