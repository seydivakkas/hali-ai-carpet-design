"""Evidence integrity tests for the benchmark orchestrator."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from carpet_designer.data.ingest import compute_sha256
from carpet_designer.evaluation.benchmark import BenchmarkOrchestrator

if TYPE_CHECKING:
    from pathlib import Path


def test_benchmark_is_not_run_without_locked_evidence(tmp_path: Path) -> None:
    config_path = tmp_path / "benchmark.yaml"
    config_path.write_text(
        """
benchmark:
  prompt_set_path: null
metrics:
  fid: true
  clip_score: true
  symmetry: false
""".strip(),
        encoding="utf-8",
    )

    result = BenchmarkOrchestrator(tmp_path / "reports").run(config_path)

    assert result.status == "NOT_RUN"
    assert result.metrics == {"fid": None, "clip_score": None}
    assert result.details["samples_processed"] == 0
    assert result.details["config_sha256"] == compute_sha256(config_path)
    report = json.loads((tmp_path / "reports" / f"{result.eval_id}.json").read_text())
    assert report["status"] == "NOT_RUN"
    assert report["metrics"]["fid"] is None


def test_benchmark_rejects_non_mapping_config(tmp_path: Path) -> None:
    config_path = tmp_path / "benchmark.yaml"
    config_path.write_text("just-a-string", encoding="utf-8")

    with pytest.raises(ValueError, match="YAML/JSON object"):
        BenchmarkOrchestrator(tmp_path / "reports").run(config_path)
