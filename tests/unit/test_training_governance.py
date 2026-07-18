"""Training governance tests."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from carpet_designer.training.trainer import Trainer

if TYPE_CHECKING:
    from pathlib import Path


def test_restricted_reference_manifest_cannot_train(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "status": "RESTRICTED_REFERENCE_ONLY",
                "training_use": "blocked_pending_written_permission",
                "permission_ref": "",
                "entries": [{"source_id": "90823-070"}],
            }
        ),
        encoding="utf-8",
    )
    trainer = Trainer(manifest, tmp_path / "training", dry_run=True)

    with pytest.raises(PermissionError, match="Training blocked"):
        trainer.train()

    assert not (tmp_path / "training" / "adapter_model.safetensors").exists()


def test_written_permission_allows_restricted_dry_run(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "status": "TRAINING_APPROVED",
                "training_use": "approved",
                "permission_ref": "COMPANY-LEGAL-2026-001",
                "files": [{"license": "company_owned"}],
            }
        ),
        encoding="utf-8",
    )
    trainer = Trainer(manifest, tmp_path / "training", dry_run=True)

    result = trainer.train()

    assert result.artifact_path == ""
    plan = json.loads((tmp_path / "training" / "dry_run_plan.json").read_text())
    assert plan["status"] == "DRY_RUN"
    assert plan["metrics"] is None
