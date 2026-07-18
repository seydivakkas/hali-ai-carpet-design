"""Benchmark evaluation orchestrator per spec Section 19."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from carpet_designer.data.ingest import compute_sha256
from carpet_designer.domain.schemas import EvaluationResult
from carpet_designer.logging_config import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger("evaluation.benchmark")


class BenchmarkOrchestrator:
    """Runs automated evaluations to produce benchmark metrics."""

    def __init__(self, output_dir: Path) -> None:
        """Initialize BenchmarkOrchestrator.

        Args:
            output_dir: Directory to save evaluation reports.
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, config_path: Path) -> EvaluationResult:
        """Create an auditable benchmark record.

        Metric implementations and a locked reference set are not silently
        substituted with demo values. Until both are present, the record is
        intentionally emitted as ``NOT_RUN`` with nullable metrics.

        Args:
            config_path: Path to evaluation YAML/JSON config.

        Returns:
            EvaluationResult with honest execution status and evidence metadata.
        """
        logger.info("Starting evaluation from config: %s", config_path)
        try:
            import yaml

            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except Exception as error:
            raise ValueError(f"Evaluation config could not be parsed: {error}") from error
        if not isinstance(config, dict):
            raise ValueError("Evaluation config must contain a YAML/JSON object.")

        logger.info("Config loaded: %s", config)

        metric_config = config.get("metrics", {})
        if not isinstance(metric_config, dict):
            metric_config = {}
        requested_metrics = [
            name for name, enabled in metric_config.items() if enabled is True
        ]
        metrics: dict[str, float | None] = {name: None for name in requested_metrics}

        benchmark_config = config.get("benchmark", {})
        if not isinstance(benchmark_config, dict):
            benchmark_config = {}
        prompt_set = benchmark_config.get("prompt_set_path")
        missing_inputs = ["implemented_metric_runner", "locked_reference_dataset"]
        if not prompt_set:
            missing_inputs.append("locked_prompt_set")

        result = EvaluationResult(
            eval_id=f"eval_{datetime.now(tz=UTC).strftime('%Y%m%d_%H%M%S_%f')}",
            metrics=metrics,
            details={
                "mode": "not_run",
                "reason": (
                    "Real benchmark execution requires an implemented metric runner, "
                    "a locked reference dataset and a locked prompt/seed package."
                ),
                "missing_inputs": missing_inputs,
                "config": config,
                "config_path": str(config_path.resolve()),
                "config_sha256": compute_sha256(config_path),
                "samples_processed": 0,
            },
            status="NOT_RUN",
        )

        report_path = self.output_dir / f"{result.eval_id}.json"
        report_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        logger.warning("Evaluation not run. Evidence record saved to: %s", report_path)

        return result
