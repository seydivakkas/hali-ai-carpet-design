"""Multi-LoRA loading and weighting tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from carpet_designer.domain.errors import GenerationFailedError
from carpet_designer.models.pipeline import GenerationPipeline

if TYPE_CHECKING:
    from pathlib import Path


class _FakeDiffusersPipeline:
    def __init__(self) -> None:
        self.loaded: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self.set_calls: list[tuple[list[str], list[float]]] = []
        self.unload_calls = 0

    def unload_lora_weights(self) -> None:
        self.unload_calls += 1

    def load_lora_weights(self, *args: Any, **kwargs: Any) -> None:
        self.loaded.append((args, kwargs))

    def set_adapters(self, ids: list[str], *, adapter_weights: list[float]) -> None:
        self.set_calls.append((ids, adapter_weights))


def _pipeline() -> tuple[GenerationPipeline, _FakeDiffusersPipeline]:
    pipeline = GenerationPipeline.__new__(GenerationPipeline)
    fake = _FakeDiffusersPipeline()
    pipeline._pipe = fake
    pipeline._active_loras = set()
    return pipeline, fake


def test_multiple_loras_are_loaded_and_weighted_separately(tmp_path: Path) -> None:
    first = tmp_path / "first.safetensors"
    second = tmp_path / "second.safetensors"
    first.write_bytes(b"1")
    second.write_bytes(b"2")
    pipeline, fake = _pipeline()

    pipeline._apply_loras(
        ["geometric", "palette"],
        [0.8, 0.35],
        {"geometric": first, "palette": second},
    )

    assert [call[1]["adapter_name"] for call in fake.loaded] == ["geometric", "palette"]
    assert fake.set_calls == [(["geometric", "palette"], [0.8, 0.35])]
    assert pipeline._active_loras == {"geometric", "palette"}


def test_lora_mix_rejects_missing_scale() -> None:
    pipeline, _ = _pipeline()

    with pytest.raises(GenerationFailedError, match="exactly one scale"):
        pipeline._apply_loras(["one", "two"], [0.8], {})
