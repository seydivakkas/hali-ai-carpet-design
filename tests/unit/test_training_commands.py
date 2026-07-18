"""Training profile and command construction tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from carpet_designer.training.jobs import build_training_cli_command
from carpet_designer.training.trainer import Trainer

if TYPE_CHECKING:
    from pathlib import Path


def _dataset(tmp_path: Path) -> tuple[Path, Path]:
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "sample.jpg").write_bytes(b"jpeg")
    (tmp_path / "metadata.jsonl").write_text(
        json.dumps({"file_name": "images/sample.jpg", "text": "mrcpt geometric carpet"})
        + "\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"training_use": "approved", "permission_ref": "TEST-1"}),
        encoding="utf-8",
    )
    return manifest, image_dir


def test_caption_command_uses_metadata_and_experiment_flags(tmp_path: Path) -> None:
    manifest, image_dir = _dataset(tmp_path)
    trainer = Trainer(manifest, tmp_path / "output")
    config = trainer._resolve_training_config(
        {
            "snr_gamma": 5.0,
            "resume_from_checkpoint": "latest",
            "random_flip": False,
        }
    )
    trainer._validate_caption_metadata(tmp_path)

    command = trainer._build_training_command(
        config, tmp_path / "train_text_to_image_lora_sdxl.py", tmp_path, image_dir
    )

    assert "--train_data_dir" in command
    assert "--caption_column" in command
    assert "--instance_data_dir" not in command
    assert command[command.index("--snr_gamma") + 1] == "5.0"
    assert command[command.index("--resume_from_checkpoint") + 1] == "latest"
    assert "--random_flip" not in command


def test_single_prompt_command_uses_low_vram_dataset_path(tmp_path: Path) -> None:
    manifest, image_dir = _dataset(tmp_path)
    trainer = Trainer(manifest, tmp_path / "output")
    config = trainer._resolve_training_config({"training_mode": "single_prompt"})

    command = trainer._build_training_command(
        config, tmp_path / "train_dreambooth_lora_sdxl.py", tmp_path, image_dir
    )

    assert "--instance_data_dir" in command
    assert "--instance_prompt" in command
    assert "--train_data_dir" not in command


def test_caption_metadata_rejects_missing_image(tmp_path: Path) -> None:
    (tmp_path / "metadata.jsonl").write_text(
        '{"file_name":"images/missing.jpg","text":"caption"}\n', encoding="utf-8"
    )

    with pytest.raises(FileNotFoundError, match="does not exist"):
        Trainer._validate_caption_metadata(tmp_path)


def test_streamlit_launcher_command_keeps_hybrid_parameters(tmp_path: Path) -> None:
    config = {
        "training_mode": "caption_aware",
        "max_train_steps": 250,
        "resolution": 512,
        "rank": 8,
        "learning_rate": 5e-5,
        "gradient_accumulation_steps": 4,
        "validation_prompt": "fixed prompt",
        "num_validation_images": 2,
        "validation_epochs": 1,
        "checkpointing_steps": 25,
        "checkpoints_total_limit": 3,
        "lr_scheduler": "constant",
        "lr_warmup_steps": 0,
        "seed": 3407,
        "random_flip": False,
        "snr_gamma": 5.0,
        "resume_from_checkpoint": "latest",
    }

    command = build_training_cli_command(
        tmp_path / "manifest.json", tmp_path / "out", config
    )

    assert command[command.index("--rank") + 1] == "8"
    assert command[command.index("--snr-gamma") + 1] == "5.0"
    assert command[command.index("--resume-from-checkpoint") + 1] == "latest"
    assert "--no-random-flip" in command
