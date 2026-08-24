<div align="center">

# Halı AI Carpet Design

### Controlled Generative Design for Industrial Carpet Workflows

![Status](https://img.shields.io/badge/status-ACTIVE%20TECHNICAL%20PILOT-8b1e2d?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-2.8-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)
![SDXL](https://img.shields.io/badge/SDXL-LoRA-6F42C1?style=flat-square)
[![CI](https://github.com/seydivakkas/hali-ai-carpet-design/actions/workflows/ci.yml/badge.svg)](https://github.com/seydivakkas/hali-ai-carpet-design/actions/workflows/ci.yml)

**A provenance-aware SDXL + LoRA design studio for controlled carpet generation, reference-based variants, retrieval and analytical validation.**

`Generative AI` · `SDXL` · `LoRA` · `Diffusers` · `CIELAB / ΔE` · `Retrieval` · `Provenance`

</div>

---

## Why this project exists

Generative design becomes much more useful in an industrial workflow when the output is **controllable, comparable and traceable**.

Halı AI Carpet Design turns a structured design brief into reproducible carpet concepts while recording the model, LoRA adapter, seed, prompt recipe, analysis results and source provenance behind each run.

The goal is not to replace the designer. The goal is to provide a measurable **AI-assisted design workspace** for rapid exploration and engineering review.

---

## Minimum reproducible run

The fastest path to a validated local setup is:

```bash
git clone https://github.com/seydivakkas/hali-ai-carpet-design.git
cd hali-ai-carpet-design
uv venv --python 3.11
uv sync --all-extras
uv run pytest -q
uv run carpet-designer doctor
uv run carpet-designer serve
```

The CPU demo path does not require a GPU. SDXL / LoRA inference requires the corresponding local model and CUDA environment. Secrets, restricted catalog data, model weights and generated production artifacts are intentionally kept outside Git.

---

## Core capabilities

| Capability | Engineering approach |
|---|---|
| Controlled generation | Structured style, motif, composition, border, symmetry and palette contracts |
| Domain adaptation | Local **SDXL + Carpet LoRA** workflow |
| Reference variants | Controlled image-to-image variation with explicit preservation rules |
| Color validation | **CIELAB / ΔE** palette analysis |
| Geometry analysis | Symmetry, seam continuity and repeat-signal measurements |
| Retrieval | Similar-design search over permitted catalog content and prior runs |
| Provenance | Dataset/license records, manifests and SHA-256 artifact tracking |
| Evidence | PNG, JSON and standalone HTML evidence reports |
| Product interface | Multi-page Streamlit design workspace |

---

## Engineering evidence

| Signal | Current repository evidence |
|---|---|
| Automated validation | **52 tests passing** in the documented pilot validation |
| Live repository health | GitHub Actions `CI` workflow badge above |
| Runtime environment | Python 3.11 · PyTorch 2.8 · CUDA 12.6 |
| Training setup | SDXL LoRA optimized for an 8 GiB GPU environment |
| Governed training set | 386 normalized images across permitted/private and open sources |
| LoRA lifecycle | Registered adapter with artifact hash and pilot lifecycle state |
| System checks | GPU, libraries, disk, database and writable-path health checks |

> Metrics and pilot status describe the validated technical environment in this repository. They do not constitute manufacturing approval, legal originality certification or production authorization.

---

## System flow

```text
Design Brief
    ↓
Structured Prompt Recipe
    ↓
SDXL Base / SDXL + Carpet LoRA
    ↓
Generated Design
    ├── CIELAB / ΔE analysis
    ├── symmetry / seam / repeat analysis
    ├── catalog retrieval
    └── provenance + evidence record
    ↓
Streamlit Review Workspace
```

---

## Product views

| View | Purpose |
|---|---|
| Design Studio | Structured carpet generation with model / LoRA controls |
| Variant Laboratory | Reference-based controlled alternatives |
| Collection Search | Visual similarity exploration over permitted content |
| Model & LoRA Registry | Model lifecycle, hashes and training metadata |
| Evaluation Center | Run history and analytical evidence |
| System Health | Runtime and dependency validation |

Selected application screenshots are documented in **[docs/SCREENSHOTS.md](docs/SCREENSHOTS.md)**.

---

## Design principles

This repository is built around four constraints:

1. **Control before novelty** — important design variables are explicit rather than hidden inside free-form prompts.
2. **Evidence before claims** — every major output should have measurable or inspectable evidence.
3. **Provenance before training** — source permission and artifact lineage are part of the ML pipeline.
4. **Human review before production** — generated concepts remain candidates for design and manufacturing review.

---

## Technology stack

**Generative AI**  
`PyTorch` · `Diffusers` · `SDXL` · `LoRA` · `PEFT`

**Vision & analysis**  
`OpenCV` · `NumPy` · `CIELAB` · `Delta E` · `Similarity Retrieval`

**Product & governance**  
`Streamlit` · `SQLite` · `Pydantic` · `SHA-256 Provenance` · `pytest` · `Ruff` · `mypy`

---

## Documentation

The root README is intentionally concise and portfolio-oriented. The original full engineering document is preserved here:

### **[Full Technical Documentation →](docs/README_FULL.md)**

Additional evidence:

- [Application screenshots and technical walkthrough](docs/SCREENSHOTS.md)
- [Dataset and license register](docs/DATASET_AND_LICENSE_REGISTER.md)
- [Data card](docs/DATA_CARD.md)
- [Training protocol](docs/TRAINING_PROTOCOL.md)
- [Technical review](hali-ai-technical-review.md)

---

## Scope boundaries

This system does **not** independently certify:

- manufacturability,
- legal originality,
- copyright safety,
- commercial release readiness,
- or final production approval.

Those decisions remain human and organizational review steps.

---

<div align="center">

**Controlled generation · measurable analysis · traceable evidence**

[GitHub Profile](https://github.com/seydivakkas) · [Full Documentation](docs/README_FULL.md)

</div>
