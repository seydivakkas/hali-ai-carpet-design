"""Auditable background launcher for Streamlit training controls."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from carpet_designer.data.ingest import compute_sha256

if TYPE_CHECKING:
    from pathlib import Path


def build_training_cli_command(
    dataset_manifest: Path,
    output_dir: Path,
    config: dict[str, Any],
    *,
    dry_run: bool = False,
) -> list[str]:
    """Build the shell-free CLI command shared by preview and launch."""
    command = [
        sys.executable,
        "-m",
        "carpet_designer",
        "training",
        "train",
        "--dataset-manifest",
        str(dataset_manifest),
        "--output-dir",
        str(output_dir),
        "--training-mode",
        str(config["training_mode"]),
        "--max-train-steps",
        str(config["max_train_steps"]),
        "--resolution",
        str(config["resolution"]),
        "--rank",
        str(config["rank"]),
        "--learning-rate",
        str(config["learning_rate"]),
        "--gradient-accumulation-steps",
        str(config["gradient_accumulation_steps"]),
        "--validation-prompt",
        str(config["validation_prompt"]),
        "--num-validation-images",
        str(config["num_validation_images"]),
        "--validation-epochs",
        str(config["validation_epochs"]),
        "--checkpointing-steps",
        str(config["checkpointing_steps"]),
        "--checkpoints-total-limit",
        str(config["checkpoints_total_limit"]),
        "--lr-scheduler",
        str(config["lr_scheduler"]),
        "--lr-warmup-steps",
        str(config["lr_warmup_steps"]),
        "--seed",
        str(config["seed"]),
        "--random-flip" if config.get("random_flip") else "--no-random-flip",
    ]
    if config.get("snr_gamma") is not None:
        command.extend(["--snr-gamma", str(config["snr_gamma"])])
    if config.get("resume_from_checkpoint"):
        command.extend(
            ["--resume-from-checkpoint", str(config["resume_from_checkpoint"])]
        )
    if dry_run:
        command.append("--dry-run")
    return command


def save_training_plan(
    plans_dir: Path,
    dataset_manifest: Path,
    output_dir: Path,
    config: dict[str, Any],
) -> Path:
    """Persist a reproducible plan before starting any GPU process."""
    plans_dir.mkdir(parents=True, exist_ok=True)
    plan_id = f"plan_{datetime.now(tz=UTC).strftime('%Y%m%d_%H%M%S_%f')}"
    payload = {
        "schema_version": "1.0.0",
        "plan_id": plan_id,
        "status": "PLANNED",
        "created_at": datetime.now(tz=UTC).isoformat(),
        "dataset_manifest": str(dataset_manifest.resolve()),
        "dataset_manifest_sha256": (
            compute_sha256(dataset_manifest) if dataset_manifest.is_file() else None
        ),
        "output_dir": str(output_dir.resolve()),
        "config": config,
    }
    plan_path = plans_dir / f"{plan_id}.json"
    plan_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return plan_path


def launch_training_job(
    project_root: Path,
    plans_dir: Path,
    dataset_manifest: Path,
    output_dir: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Start one non-blocking training CLI process and record its PID/log."""
    plan_path = save_training_plan(plans_dir, dataset_manifest, output_dir, config)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "launcher.log"
    command = build_training_cli_command(dataset_manifest, output_dir, config)
    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with log_path.open("a", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            command,
            cwd=project_root,
            env=environment,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            shell=False,
            creationflags=creationflags,
        )
    job = {
        "plan_path": str(plan_path),
        "pid": process.pid,
        "log_path": str(log_path),
        "output_dir": str(output_dir),
        "started_at": datetime.now(tz=UTC).isoformat(),
        "config": config,
    }
    (output_dir / "job.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    return job


def tail_text(path: Path, line_count: int = 20) -> str:
    """Return a compact UTF-8 log tail for the registry page."""
    if not path.is_file():
        return "Log henüz oluşmadı."
    return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-line_count:])
