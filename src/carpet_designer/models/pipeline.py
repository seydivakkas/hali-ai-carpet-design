"""Model pipeline orchestrator per spec Section 14."""

from __future__ import annotations

import hashlib
import time
from typing import TYPE_CHECKING, Any

import torch
from PIL import Image, ImageOps

from carpet_designer.domain.enums import Status
from carpet_designer.domain.errors import GenerationFailedError
from carpet_designer.domain.schemas import GenerationResult, PromptRecipe, TimingInfo
from carpet_designer.logging_config import get_logger
from carpet_designer.models.procedural import ProceduralCarpetGenerator
from carpet_designer.prompts.recipe import PromptBuilder
from carpet_designer.settings import Settings, get_settings

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger("models.pipeline")


class GenerationPipeline:
    """Wrapper for diffusers StableDiffusionXLPipeline."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the pipeline with settings."""
        self.settings = settings or get_settings()
        self.device = self._get_device()
        self.dtype = self._get_dtype()
        self._pipe: Any = None
        self._img2img_pipe: Any = None
        self._loaded_model_id: str | None = None
        self._active_loras: set[str] = set()

    def _get_device(self) -> str:
        if self.settings.device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
            return "cpu"
        return self.settings.device

    def _get_dtype(self) -> torch.dtype:
        if self.device == "cpu":
            return torch.float32
        return torch.float16

    def load_base_model(self, model_id: str, local_path: Path | None = None) -> None:
        """Load the base model into memory.

        Args:
            model_id: Registry ID of the model.
            local_path: Optional local path to weights.
        """
        if self._pipe is not None and self._loaded_model_id == model_id:
            return  # Already loaded

        import diffusers

        logger.info("Loading base model %s to %s", model_id, self.device)
        if local_path:
            model_path = str(local_path)
        elif "/" in model_id:
            model_path = model_id
        else:
            model_path = "stabilityai/stable-diffusion-xl-base-1.0"

        try:
            pipeline_options: dict[str, Any] = {
                "torch_dtype": self.dtype,
                "use_safetensors": True,
                "variant": "fp16" if self.dtype == torch.float16 else None,
                "token": self.settings.huggingface_token or None,
                "low_cpu_mem_usage": True,
                "local_files_only": bool(local_path),
            }
            local_vae = (
                self.settings.resolved_artifacts_dir
                / "models"
                / "base"
                / "sdxl-vae-fp16-fix"
            )
            if local_path and local_vae.is_dir():
                pipeline_options["vae"] = diffusers.AutoencoderKL.from_pretrained(
                    str(local_vae),
                    torch_dtype=self.dtype,
                    use_safetensors=True,
                    variant="fp16" if self.dtype == torch.float16 else None,
                    local_files_only=True,
                )
            self._pipe = diffusers.StableDiffusionXLPipeline.from_pretrained(
                model_path,
                **pipeline_options,
            )
            if self.device == "cuda" and torch.cuda.get_device_properties(0).total_memory < 12 * 2**30:
                self._pipe.enable_model_cpu_offload()
                self._pipe.enable_attention_slicing()
                self._pipe.vae.enable_tiling()
            else:
                self._pipe.to(self.device)
            self._loaded_model_id = model_id
            self._img2img_pipe = None
            self._active_loras.clear()
        except Exception as e:
            raise GenerationFailedError(
                message=f"Failed to load base model {model_id}: {e}",
                detail=str(e),
            ) from e

    def _apply_loras(
        self, lora_ids: list[str], lora_scales: list[float], lora_paths: dict[str, Path]
    ) -> None:
        """Apply requested LoRA adapters.

        Args:
            lora_ids: List of LoRA IDs to apply.
            lora_scales: Weights for the LoRAs.
            lora_paths: Mapping of LoRA ID to local file path.
        """
        if len(lora_ids) != len(lora_scales):
            raise GenerationFailedError("Each LoRA adapter must have exactly one scale.")
        if len(set(lora_ids)) != len(lora_ids):
            raise GenerationFailedError("A LoRA adapter can only appear once in a hybrid mix.")
        if any(scale < 0.0 or scale > 1.5 for scale in lora_scales):
            raise GenerationFailedError("LoRA scales must be between 0.0 and 1.5.")
        if not self._pipe:
            raise GenerationFailedError("Base model not loaded")

        current_set = set(lora_ids)
        if current_set == self._active_loras:
            # Maybe update scales, but skip reload if identical
            self._pipe.set_adapters(lora_ids, adapter_weights=lora_scales)
            return

        self._pipe.unload_lora_weights()
        self._active_loras.clear()

        if not lora_ids:
            return

        for l_id in lora_ids:
            path = lora_paths.get(l_id)
            if not path or not path.exists():
                raise GenerationFailedError(f"LoRA path not found for {l_id}")
            if path.is_file():
                self._pipe.load_lora_weights(
                    str(path.parent), weight_name=path.name, adapter_name=l_id
                )
            else:
                self._pipe.load_lora_weights(str(path), adapter_name=l_id)

        self._pipe.set_adapters(lora_ids, adapter_weights=lora_scales)
        self._active_loras = current_set

    def _compute_hash(self, image: Image.Image) -> str:
        """Compute SHA256 of PIL Image."""
        hasher = hashlib.sha256()
        hasher.update(image.tobytes())
        return hasher.hexdigest()

    def generate(
        self,
        recipe: PromptRecipe,
        base_model_path: Path | None = None,
        lora_paths: dict[str, Path] | None = None,
        palette: list[str] | None = None,
    ) -> GenerationResult:
        """Generate an image from a prompt recipe.

        Args:
            recipe: The prompt recipe.
            base_model_path: Optional path to local base model.
            lora_paths: Map of LoRA IDs to local paths.

        Returns:
            GenerationResult containing metadata and result image.
        """
        lora_paths = lora_paths or {}
        timing = TimingInfo()
        t0 = time.perf_counter()

        reference_image = None
        if recipe.reference_image_path:
            try:
                with Image.open(recipe.reference_image_path) as opened:
                    reference_image = ImageOps.fit(
                        opened.convert("RGB"),
                        (recipe.width, recipe.height),
                        method=Image.Resampling.LANCZOS,
                    )
            except (OSError, ValueError) as error:
                return GenerationResult(
                    recipe_id=recipe.recipe_id,
                    status=Status.FAIL,
                    warnings=[f"Reference image error: {error}"],
                )

        demo_mode = self.settings.generation_mode == "demo" or recipe.model_id in {
            "",
            "demo-procedural-v1",
            "hf-internal-testing/tiny-stable-diffusion-xl-pipe",
        }

        # 1. Load Model
        try:
            if demo_mode:
                logger.info("Using deterministic procedural demo renderer")
                demo_renderer = ProceduralCarpetGenerator()
                image = demo_renderer.generate(recipe, palette)
                if reference_image is not None:
                    image = Image.blend(
                        reference_image,
                        image,
                        alpha=recipe.variation_strength,
                    )
                    if "symmetry" in recipe.variation_targets:
                        image = demo_renderer.apply_symmetry(image, recipe.symmetry)
                self._loaded_model_id = "demo-procedural-v1"
            else:
                self.load_base_model(recipe.model_id or "sdxl_base_v1", base_model_path)
                if recipe.lora_ids:
                    self._apply_loras(recipe.lora_ids, recipe.lora_scales, lora_paths)
        except Exception as e:
            logger.error("Model load failed", exc_info=True)
            return GenerationResult(
                recipe_id=recipe.recipe_id,
                status=Status.FAIL,
                warnings=[f"Model load error: {e}"],
            )

        t1 = time.perf_counter()
        timing.load_ms = (t1 - t0) * 1000

        # 2. Build Prompts
        builder = PromptBuilder(recipe)
        prompt = builder.build_positive_prompt()
        negative_prompt = builder.build_negative_prompt()

        generator = torch.Generator(device=self.device).manual_seed(recipe.seed)

        # 3. Generation
        try:
            logger.info("Starting generation %s", recipe.recipe_id)
            if not demo_mode:
                generation_pipe = self._pipe
                generation_options: dict[str, Any] = {
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "num_inference_steps": recipe.steps,
                    "guidance_scale": recipe.guidance_scale,
                    "generator": generator,
                    "output_type": "pil",
                }
                if reference_image is not None:
                    if self._img2img_pipe is None:
                        import diffusers

                        self._img2img_pipe = diffusers.AutoPipelineForImage2Image.from_pipe(
                            self._pipe
                        )
                    generation_pipe = self._img2img_pipe
                    generation_options.update(
                        {
                            "image": reference_image,
                            "strength": recipe.variation_strength,
                        }
                    )
                else:
                    generation_options.update(
                        {
                            "width": recipe.width,
                            "height": recipe.height,
                        }
                    )
                result = generation_pipe(
                    **generation_options,
                )
                image = result.images[0]
        except torch.cuda.OutOfMemoryError:
            logger.error("OOM Error", exc_info=True)
            return GenerationResult(
                recipe_id=recipe.recipe_id,
                status=Status.FAIL,
                warnings=["CUDA Out of Memory"],
            )
        except Exception as e:
            logger.error("Generation failed", exc_info=True)
            return GenerationResult(
                recipe_id=recipe.recipe_id,
                status=Status.FAIL,
                warnings=[f"Generation error: {e}"],
            )

        t2 = time.perf_counter()
        timing.generation_ms = (t2 - t1) * 1000

        # 4. Save and Hash
        output_dir = self.settings.resolved_artifacts_dir / "generations"
        output_dir.mkdir(parents=True, exist_ok=True)

        gen_id = f"gen_{hashlib.md5(str(time.time()).encode()).hexdigest()[:12]}"
        image_path = output_dir / f"{gen_id}.png"
        image.save(image_path)

        image_hash = self._compute_hash(image)

        t3 = time.perf_counter()
        timing.total_ms = (t3 - t0) * 1000

        warnings = []
        if demo_mode:
            warnings.append(
                "DEMO_ONLY: Prosedürel motor kullanıldı; çıktı SDXL/LoRA kalite iddiası taşımaz."
            )
        if reference_image is not None:
            warnings.append(
                "REFERENCE_VARIATION: Yüklenen kaynak görsel kontrollü varyant girdisi olarak "
                f"kullanıldı; değişim gücü={recipe.variation_strength:.2f}."
            )

        return GenerationResult(
            generation_id=gen_id,
            recipe_id=recipe.recipe_id,
            model_id=self._loaded_model_id or "unknown",
            lora_adapters=recipe.lora_ids,
            seed=recipe.seed,
            scheduler=recipe.scheduler,
            steps=recipe.steps,
            guidance_scale=recipe.guidance_scale,
            width=recipe.width,
            height=recipe.height,
            device=self.device,
            dtype=str(self.dtype),
            timing=timing,
            image_sha256=image_hash,
            image_path=str(image_path),
            status=Status.PASS,
            warnings=warnings,
        )
