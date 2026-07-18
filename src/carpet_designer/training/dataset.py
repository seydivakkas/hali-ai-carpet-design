"""Training dataset module per spec Section 15."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms

from carpet_designer.domain.schemas import DatasetManifest
from carpet_designer.logging_config import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger("training.dataset")


class CarpetDataset(Dataset):
    """PyTorch Dataset for carpet designer training.

    Reads a DatasetManifest and corresponding images/captions.
    """

    def __init__(self, manifest_path: Path, image_dir: Path, image_size: int = 1024) -> None:
        """Initialize dataset from a manifest.

        Args:
            manifest_path: Path to the JSON manifest.
            image_dir: Base directory containing the actual image files.
            image_size: Target square size for SDXL (default 1024).
        """
        self.manifest_path = manifest_path
        self.image_dir = image_dir
        self.image_size = image_size

        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.manifest = DatasetManifest.model_validate(manifest_data)

        # Filter for training split
        self.files = [f for f in self.manifest.files if f.split == "train"]

        self.transform = transforms.Compose(
            [
                transforms.Resize(
                    self.image_size, interpolation=transforms.InterpolationMode.BILINEAR
                ),
                transforms.CenterCrop(self.image_size),
                transforms.ToTensor(),
                transforms.Normalize([0.5], [0.5]),
            ]
        )

        logger.info("Initialized CarpetDataset with %d training examples", len(self.files))

    def __len__(self) -> int:
        return len(self.files)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        """Get dataset item for training.

        Returns:
            Dict containing pixel_values and text context.
        """
        entry = self.files[idx]
        img_path = self.image_dir / entry.relative_path

        try:
            image = Image.open(img_path).convert("RGB")
            pixel_values = self.transform(image)
        except Exception as e:
            logger.error("Failed to load image %s: %s", img_path, e)
            # Return a dummy tensor and text in case of corruption
            import torch

            pixel_values = torch.zeros((3, self.image_size, self.image_size))

        caption_text = ""
        if entry.caption_path:
            caption_path = self.image_dir / entry.caption_path
            try:
                caption_text = caption_path.read_text(encoding="utf-8").strip()
            except OSError as exc:
                logger.warning("Failed to load caption %s: %s", caption_path, exc)

        return {
            "pixel_values": pixel_values,
            "text": caption_text,
            "id": entry.relative_path,
        }
