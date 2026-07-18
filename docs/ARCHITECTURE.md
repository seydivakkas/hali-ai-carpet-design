# Architecture

See `HALI_AI_CARPET_DESIGN_MASTER_BUILD_SPEC.md` Section 6 for full architecture.

## Overview

Halı AI Carpet Design is a modular monolith with the following layers:

- **UI**: Streamlit pages (thin layer)
- **CLI**: Typer commands
- **Services**: Application orchestration
- **Domain**: Typed schemas, enums, protocols
- **Models**: Diffusers pipeline adapter, device management
- **Training**: Accelerate/PEFT LoRA trainer
- **Analysis**: Color, symmetry, seam, repeatability
- **Retrieval**: Embedding index, duplicate detection
- **Evaluation**: Metrics, benchmarks, human review
- **Persistence**: SQLite, repositories
- **Data**: Manifest, provenance, adapters

## Executable demo path

```text
Streamlit / Typer CLI
        ↓
DesignService
        ├─ PromptBuilder
        ├─ GenerationPipeline
        │    ├─ ProceduralCarpetGenerator (default, CPU, deterministic)
        │    └─ StableDiffusionXLPipeline (optional model artifact)
        ├─ Color + symmetry + seam + repeatability analysis
        ├─ SQLite repositories
        └─ JSON + standalone HTML report writer
```

The procedural engine is a product-demonstration fallback, not a substitute for SDXL quality.
It exists so engineers can exercise the complete frontend/backend contract without downloading
multi-gigabyte weights. Both engines return the same `DesignRunResult` contract.
