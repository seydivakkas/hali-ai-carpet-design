"""LoRA training orchestrator per spec Section 15."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import torch

from carpet_designer.data.ingest import compute_sha256
from carpet_designer.domain.enums import LoRAStatus
from carpet_designer.domain.schemas import LoRAManifest
from carpet_designer.logging_config import get_logger
from carpet_designer.settings import get_settings

logger = get_logger("training.trainer")


class Trainer:
    """Orchestrates LoRA training using Hugging Face Accelerate."""

    def __init__(self, dataset_path: Path, output_dir: Path, dry_run: bool = False) -> None:
        """Initialize trainer.

        Args:
            dataset_path: Path to dataset manifest.
            output_dir: Directory to save LoRA checkpoints.
            dry_run: If True, bypass actual PyTorch training loop.
        """
        self.dataset_path = dataset_path
        self.output_dir = output_dir
        self.dry_run = dry_run
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def train(self, config_overrides: dict[str, Any] | None = None) -> LoRAManifest:
        """Run the training loop.

        Args:
            config_overrides: Optional overrides for hyperparameters.

        Returns:
            A LoRAManifest for the newly trained adapter.
        """
        self._assert_training_allowed()
        logger.info("Initializing training run (Dry run: %s)", self.dry_run)

        if self.dry_run:
            logger.info("Dry-run mode activated. Validating and recording the training plan.")
            config = self._resolve_training_config(config_overrides or {})
            metrics = {
                "status": "DRY_RUN",
                "metrics": None,
                "config": config,
                "timestamp": datetime.now(tz=UTC).isoformat(),
            }
            metrics_path = self.output_dir / "dry_run_plan.json"
            metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
            logger.info("Validated training plan saved to %s", metrics_path)

            manifest = LoRAManifest(
                base_model_id="stabilityai/stable-diffusion-xl-base-1.0",
                artifact_path="",
                rank=int(config["rank"]),
                alpha=int(config["rank"]),
                metrics_path=str(metrics_path),
            )
            return manifest

        return self._train_sdxl_lora(config_overrides or {})

    def _train_sdxl_lora(self, overrides: dict[str, Any]) -> LoRAManifest:
        """Launch a pinned official Diffusers SDXL LoRA trainer."""
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA-enabled PyTorch is required for real LoRA training.")

        settings = get_settings()
        dataset_root = self.dataset_path.parent
        image_dir = self.dataset_path.parent / "images"
        if not image_dir.is_dir():
            raise FileNotFoundError(f"Training image directory not found: {image_dir}")

        config = self._resolve_training_config(overrides)
        if config["training_mode"] == "caption_aware":
            self._validate_caption_metadata(dataset_root)

        base_model_path = Path(str(config["base_model"]))
        if not base_model_path.is_dir():
            raise FileNotFoundError(
                "Local SDXL base model is missing. Download the approved ModelScope mirror to "
                f"{base_model_path} before training."
            )

        script_path = self._ensure_training_script(str(config["training_mode"]))

        self.output_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.output_dir / "training.log"
        command = self._build_training_command(config, script_path, dataset_root, image_dir)
        environment = os.environ.copy()
        environment["PYTHONUNBUFFERED"] = "1"
        environment["PYTHONIOENCODING"] = "utf-8"
        environment["HF_HOME"] = str(settings.resolve_path(settings.hf_home))
        environment["HF_HUB_OFFLINE"] = "1"
        environment["TRANSFORMERS_OFFLINE"] = "1"
        environment["DIFFUSERS_OFFLINE"] = "1"
        environment["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
        if settings.huggingface_token:
            environment["HF_TOKEN"] = settings.huggingface_token

        started_at = time.perf_counter()
        logger.info(
            "Starting SDXL LoRA training: steps=%s resolution=%s rank=%s",
            config["max_train_steps"],
            config["resolution"],
            config["rank"],
        )
        with log_path.open("w", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                command,
                cwd=settings.project_root,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if process.stdout is None:
                raise RuntimeError("Training process output stream was not created.")
            for line in process.stdout:
                log_file.write(line)
                log_file.flush()
                logger.info("trainer | %s", line.rstrip())
            return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(
                f"SDXL LoRA training failed with exit code {return_code}; see {log_path}"
            )

        adapter_path = self.output_dir / "pytorch_lora_weights.safetensors"
        if not adapter_path.is_file():
            raise RuntimeError(f"Training finished without LoRA weights: {adapter_path}")

        dataset_payload = json.loads(self.dataset_path.read_text(encoding="utf-8"))
        license_register = settings.project_root / "docs" / "DATASET_AND_LICENSE_REGISTER.md"
        metrics = {
            "completed_at": datetime.now(tz=UTC).isoformat(),
            "duration_seconds": round(time.perf_counter() - started_at, 3),
            "device": torch.cuda.get_device_name(0),
            "vram_bytes": torch.cuda.get_device_properties(0).total_memory,
            "dataset_count": dataset_payload.get("counts", {}).get("total", 0),
            "config": config,
            "training_log": str(log_path),
        }
        metrics_path = self.output_dir / "metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        manifest = LoRAManifest(
            adapter_name="carpet_domain_v1",
            base_model_id="sdxl_base_v1",
            training_run_id=f"train_{datetime.now(tz=UTC).strftime('%Y%m%d_%H%M%S')}",
            dataset_manifest_sha256=str(dataset_payload.get("manifest_sha256", "")),
            license_register_sha256=(
                compute_sha256(license_register) if license_register.is_file() else ""
            ),
            artifact_path=str(adapter_path),
            artifact_sha256=compute_sha256(adapter_path),
            rank=int(config["rank"]),
            alpha=int(config["rank"]),
            status=LoRAStatus.CANDIDATE,
            metrics_path=str(metrics_path),
        )
        (self.output_dir / "lora_manifest.json").write_text(
            manifest.model_dump_json(indent=2), encoding="utf-8"
        )
        return manifest

    def _resolve_training_config(self, overrides: dict[str, Any]) -> dict[str, Any]:
        """Merge and validate supported training parameters."""
        settings = get_settings()
        local_model_root = settings.resolved_artifacts_dir / "models" / "base"
        local_vae_model = local_model_root / "sdxl-vae-fp16-fix"
        config: dict[str, Any] = {
            "training_mode": "caption_aware",
            "base_model": str(local_model_root / "sdxl-base-1.0"),
            "vae_model": str(local_vae_model) if local_vae_model.is_dir() else None,
            "instance_prompt": (
                "a mrcpt carpet design, full rug view, detailed textile pattern"
            ),
            "resolution": 512,
            "max_train_steps": 100,
            "gradient_accumulation_steps": 4,
            "learning_rate": 1e-4,
            "rank": 4,
            "seed": 42,
            "snr_gamma": None,
            "validation_prompt": (
                "mrcpt carpet design, geometric central medallion, multi-band border, "
                "burgundy navy cream palette, flat full rug view"
            ),
            "num_validation_images": 2,
            "validation_epochs": 1,
            "checkpointing_steps": 25,
            "checkpoints_total_limit": 3,
            "resume_from_checkpoint": None,
            "lr_scheduler": "constant",
            "lr_warmup_steps": 0,
            "random_flip": False,
        }
        unknown = set(overrides) - set(config)
        if unknown:
            raise ValueError(f"Unknown training config keys: {', '.join(sorted(unknown))}")
        config.update(overrides)

        if config["training_mode"] not in {"caption_aware", "single_prompt"}:
            raise ValueError("training_mode must be 'caption_aware' or 'single_prompt'.")
        positive_ints = (
            "resolution",
            "max_train_steps",
            "gradient_accumulation_steps",
            "rank",
            "num_validation_images",
            "validation_epochs",
            "checkpointing_steps",
            "checkpoints_total_limit",
        )
        for key in positive_ints:
            if int(config[key]) < 1:
                raise ValueError(f"{key} must be at least 1.")
        if float(config["learning_rate"]) <= 0:
            raise ValueError("learning_rate must be greater than zero.")
        if config["snr_gamma"] is not None and float(config["snr_gamma"]) <= 0:
            raise ValueError("snr_gamma must be greater than zero when enabled.")
        if str(config["lr_scheduler"]) not in {
            "linear",
            "cosine",
            "cosine_with_restarts",
            "polynomial",
            "constant",
            "constant_with_warmup",
        }:
            raise ValueError("Unsupported lr_scheduler value.")
        return config

    def _ensure_training_script(self, training_mode: str) -> Path:
        """Resolve the pinned Diffusers example for the selected profile."""
        settings = get_settings()
        example_root = settings.resolved_artifacts_dir / "cache" / "diffusers-v0.39.0"
        relative_script = (
            Path("examples/text_to_image/train_text_to_image_lora_sdxl.py")
            if training_mode == "caption_aware"
            else Path("examples/dreambooth/train_dreambooth_lora_sdxl.py")
        )
        script_path = example_root / relative_script
        if not script_path.is_file():
            if example_root.exists():
                raise RuntimeError(f"Incomplete Diffusers example cache: {example_root}")
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    "v0.39.0",
                    "https://github.com/huggingface/diffusers.git",
                    str(example_root),
                ],
                check=True,
            )
        if training_mode == "single_prompt":
            self._apply_low_vram_script_patch(script_path)
        return script_path

    def _build_training_command(
        self,
        config: dict[str, Any],
        script_path: Path,
        dataset_root: Path,
        image_dir: Path,
    ) -> list[str]:
        """Build the argument-safe Accelerate command for one training run."""
        command = [
            sys.executable,
            "-m",
            "accelerate.commands.launch",
            "--mixed_precision=fp16",
            str(script_path),
            "--pretrained_model_name_or_path",
            str(config["base_model"]),
            "--output_dir",
            str(self.output_dir),
            "--resolution",
            str(config["resolution"]),
            "--train_batch_size",
            "1",
            "--gradient_accumulation_steps",
            str(config["gradient_accumulation_steps"]),
            "--learning_rate",
            str(config["learning_rate"]),
            "--lr_scheduler",
            str(config["lr_scheduler"]),
            "--lr_warmup_steps",
            str(config["lr_warmup_steps"]),
            "--max_train_steps",
            str(config["max_train_steps"]),
            "--rank",
            str(config["rank"]),
            "--seed",
            str(config["seed"]),
            "--mixed_precision",
            "fp16",
            "--variant",
            "fp16",
            "--gradient_checkpointing",
            "--use_8bit_adam",
            "--allow_tf32",
            "--center_crop",
            "--dataloader_num_workers",
            "0",
            "--checkpointing_steps",
            str(config["checkpointing_steps"]),
            "--checkpoints_total_limit",
            str(config["checkpoints_total_limit"]),
            "--report_to",
            "tensorboard",
        ]
        if config["training_mode"] == "caption_aware":
            command.extend(
                [
                    "--train_data_dir",
                    str(dataset_root),
                    "--image_column",
                    "image",
                    "--caption_column",
                    "text",
                ]
            )
        else:
            command.extend(
                [
                    "--instance_data_dir",
                    str(image_dir),
                    "--instance_prompt",
                    str(config["instance_prompt"]),
                ]
            )
        if config["vae_model"]:
            command.extend(
                ["--pretrained_vae_model_name_or_path", str(config["vae_model"])]
            )
        if config["snr_gamma"] is not None:
            command.extend(["--snr_gamma", str(config["snr_gamma"])])
        if config["validation_prompt"]:
            command.extend(
                [
                    "--validation_prompt",
                    str(config["validation_prompt"]),
                    "--num_validation_images",
                    str(config["num_validation_images"]),
                    "--validation_epochs",
                    str(config["validation_epochs"]),
                ]
            )
        if config["resume_from_checkpoint"]:
            command.extend(
                ["--resume_from_checkpoint", str(config["resume_from_checkpoint"])]
            )
        if config["random_flip"]:
            command.append("--random_flip")
        return command

    @staticmethod
    def _validate_caption_metadata(dataset_root: Path) -> None:
        """Validate ImageFolder caption rows before starting an expensive run."""
        metadata_path = dataset_root / "metadata.jsonl"
        if not metadata_path.is_file():
            raise FileNotFoundError(
                f"Caption-aware training requires ImageFolder metadata: {metadata_path}"
            )
        rows = 0
        for line_number, line in enumerate(
            metadata_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid metadata.jsonl row {line_number}: {error}"
                ) from error
            relative_path = str(row.get("file_name", ""))
            caption = str(row.get("text", "")).strip()
            if not relative_path or not caption:
                raise ValueError(
                    f"metadata.jsonl row {line_number} requires file_name and text."
                )
            if not (dataset_root / relative_path).is_file():
                raise FileNotFoundError(
                    f"Caption image does not exist for row {line_number}: {relative_path}"
                )
            rows += 1
        if rows == 0:
            raise ValueError("metadata.jsonl contains no caption rows.")

    @staticmethod
    def _apply_low_vram_script_patch(script_path: Path) -> None:
        """Apply audited Windows/offline changes to the pinned Diffusers trainer."""
        source = script_path.read_text(encoding="utf-8")
        changed = False

        memory_marker = "del tokenizer_one, tokenizer_two, text_encoder_one, text_encoder_two"
        if memory_marker not in source:
            expected = "        del tokenizers, text_encoders\n        gc.collect()"
            replacement = (
                "        del tokenizers, text_encoders\n"
                "        del tokenizer_one, tokenizer_two, text_encoder_one, text_encoder_two\n"
                "        gc.collect()"
            )
            if expected not in source:
                raise RuntimeError(
                    "Pinned Diffusers trainer changed; the audited 8 GB VRAM patch cannot be applied."
                )
            source = source.replace(expected, replacement, 1)
            changed = True

        offline_marker = 'weight_name="pytorch_lora_weights.safetensors"'
        if offline_marker not in source:
            expected = "        pipeline.load_lora_weights(args.output_dir)"
            replacement = (
                "        pipeline.load_lora_weights(\n"
                "            args.output_dir, weight_name=\"pytorch_lora_weights.safetensors\"\n"
                "        )"
            )
            if expected not in source:
                raise RuntimeError(
                    "Pinned Diffusers trainer changed; the audited offline patch cannot be applied."
                )
            source = source.replace(expected, replacement, 1)
            changed = True

        if changed:
            script_path.write_text(source, encoding="utf-8")

    def _assert_training_allowed(self) -> None:
        """Reject restricted manifests before any training artifact is produced."""
        try:
            payload = json.loads(self.dataset_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            raise PermissionError(f"Training manifest could not be audited: {error}") from error

        metadata = payload.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        training_use = str(
            payload.get("training_use") or metadata.get("training_use") or ""
        ).casefold()
        permission_ref = str(
            payload.get("permission_ref") or metadata.get("permission_ref") or ""
        ).strip()
        status = str(payload.get("status") or metadata.get("status") or "").casefold()
        permission_approved = training_use in {"approved", "allowed", "permitted"} and bool(
            permission_ref
        )

        if training_use.startswith("blocked") or (
            "restricted" in status and not permission_approved
        ):
            raise PermissionError(
                "Training blocked: this dataset is restricted and has no written permission reference."
            )

        files = payload.get("files", [])
        if isinstance(files, list):
            licenses = {
                str(item.get("license", "")).casefold()
                for item in files
                if isinstance(item, dict)
            }
            open_licenses = {"cc0", "public_domain", "public domain", "open"}
            if licenses and not licenses.issubset(open_licenses) and not permission_approved:
                raise PermissionError(
                    "Training blocked: non-open file licenses require an approved permission_ref."
                )
