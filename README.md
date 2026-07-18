# Halı AI Carpet Design

[![License](https://img.shields.io/badge/license-All%20Rights%20Reserved-red?style=flat-square)](LICENSE)

> Traceable Diffusion-Based Carpet Design Studio

## Overview

Halı AI Carpet Design is a local AI carpet design studio that:

- Generates carpet designs via SDXL with optional LoRA adaptation
- Manages dataset provenance and licensing rigorously
- Analyzes designs for color palette, symmetry, seam quality, repeatability
- Provides collection similarity/retrieval search
- Persists everything with full traceability

## Scope

See [HALI_AI_CARPET_DESIGN_MASTER_BUILD_SPEC.md](HALI_AI_CARPET_DESIGN_MASTER_BUILD_SPEC.md) for full scope.

### What This Is NOT

- This is NOT WeaveVision (anomaly/defect detection — separate product)
- This does NOT guarantee production manufacturability
- This does NOT establish legal originality or copyright safety
- This project is not affiliated with or endorsed by any catalog rights holder

## Quick Start

```bash
# Bootstrap (Python 3.11)
uv venv --python 3.11
uv sync --all-extras
uv run carpet-designer doctor

# Launch the working frontend + backend demo
uv run carpet-designer serve
```

Open `http://localhost:8501` and use **Design Studio**. The default CPU Demo engine needs
no model download and executes the complete workflow:

`Prompt recipe → deterministic render → color/geometry analysis → SQLite → PNG/JSON/HTML report`

The demo engine is explicitly marked `DEMO_ONLY`. To use SDXL, select the SDXL engine after
placing an approved model artifact in the configured model registry/cache.

### Verified Local SDXL + Carpet LoRA Pilot

The local RTX 4070 pilot is trained and registered as `ACTIVE_COMPANY_PILOT`. In Design Studio,
choose **SDXL + Carpet LoRA**; the backend loads the validated local SDXL/FP16 VAE package and the
active rank-4 adapter without requiring a model download. The `mrcpt` trigger is added automatically.

See [hali-ai-technical-review.md](hali-ai-technical-review.md) for the measured training and
end-to-end validation evidence, and [docs/DATASET_AND_LICENSE_REGISTER.md](docs/DATASET_AND_LICENSE_REGISTER.md)
for source/permission records.

### Public Repository Boundary

The public repository contains source code, documentation, generated examples, and auditable
metrics. Rights-restricted catalog images, private manifests, trained weights, local databases,
tokens, and generated evidence archives remain excluded by `.gitignore`. Renaming a source does
not change its copyright status; restricted assets remain private and retain their provenance.

### Backend CLI

```bash
# A recipe with an empty model_id automatically uses the local demo engine
uv run carpet-designer generate --recipe configs/demo_recipe.json

# Run the engineering checks
uv run ruff check .
uv run mypy src
uv run pytest -q
```

## Evaluation Metrics

<!-- AUTO-GENERATED — DO NOT EDIT MANUALLY -->
| Metric | Value | Status |
|--------|-------|--------|
| All metrics | — | NOT_RUN |

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

The first release is a modular monolith: Streamlit is the frontend, while
`DesignService` is the shared backend facade used by both Streamlit and Typer CLI.

## Limitations

- Generated designs are not production-approved
- Retrieval does not establish legal originality
- Open data does not establish company-specific style performance
- FID alone is not sufficient quality verdict
- Company name and claims require authorization
