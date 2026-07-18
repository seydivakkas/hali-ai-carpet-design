"""Custom exception hierarchy per spec Section 39."""

from __future__ import annotations

from carpet_designer.domain.enums import ErrorCode


class CarpetDesignerError(Exception):
    """Base exception for all Carpet Designer errors."""

    def __init__(self, message: str, error_code: ErrorCode, detail: str = "") -> None:
        self.error_code = error_code
        self.detail = detail
        super().__init__(f"[{error_code.value}] {message}")


class ConfigError(CarpetDesignerError):
    """Configuration is invalid or missing."""

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message, ErrorCode.CD_CONFIG_INVALID, detail)


class DatasetError(CarpetDesignerError):
    """Dataset-related errors."""

    def __init__(
        self, message: str, error_code: ErrorCode = ErrorCode.CD_DATASET_NOT_FOUND, detail: str = ""
    ) -> None:
        super().__init__(message, error_code, detail)


class DatasetLicenseBlockedError(CarpetDesignerError):
    """Dataset license blocks training use."""

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message, ErrorCode.CD_DATASET_LICENSE_BLOCKED, detail)


class DataLeakageError(CarpetDesignerError):
    """Data leakage detected between splits."""

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message, ErrorCode.CD_DATA_LEAKAGE_DETECTED, detail)


class ModelNotReadyError(CarpetDesignerError):
    """Model is not available for inference."""

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message, ErrorCode.CD_MODEL_NOT_READY, detail)


class ModelHashMismatchError(CarpetDesignerError):
    """Model file hash does not match expected."""

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message, ErrorCode.CD_MODEL_HASH_MISMATCH, detail)


class LoRAError(CarpetDesignerError):
    """LoRA adapter errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.CD_LORA_NOT_FOUND,
        detail: str = "",
    ) -> None:
        super().__init__(message, error_code, detail)


class RecipeInvalidError(CarpetDesignerError):
    """Prompt recipe validation failed."""

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message, ErrorCode.CD_RECIPE_INVALID, detail)


class ImageInvalidError(CarpetDesignerError):
    """Image file is corrupt or invalid."""

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message, ErrorCode.CD_IMAGE_INVALID, detail)


class GenerationOOMError(CarpetDesignerError):
    """Out of memory during generation."""

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message, ErrorCode.CD_GENERATION_OOM, detail)


class GenerationFailedError(CarpetDesignerError):
    """Generation failed for non-OOM reasons."""

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message, ErrorCode.CD_GENERATION_FAILED, detail)


class AnalysisFailedError(CarpetDesignerError):
    """Design analysis failed."""

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message, ErrorCode.CD_ANALYSIS_FAILED, detail)


class IndexNotReadyError(CarpetDesignerError):
    """Retrieval index not available."""

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message, ErrorCode.CD_INDEX_NOT_READY, detail)


class DatabaseError(CarpetDesignerError):
    """Database operation failed."""

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message, ErrorCode.CD_DATABASE_FAILED, detail)


class GPUUnavailableError(CarpetDesignerError):
    """GPU is not available."""

    def __init__(self, message: str = "No CUDA GPU available", detail: str = "") -> None:
        super().__init__(message, ErrorCode.CD_GPU_UNAVAILABLE, detail)
