# RTX 4070 SDXL LoRA Training Protocol

## Inputs and governance

- Dataset manifest: `data/processed/carpet_lora_v1/manifest.json`
- Image directory: `data/processed/carpet_lora_v1/images/`
- Dataset count: 386
- Trigger token: `mrcpt`
- Base: Stable Diffusion XL Base 1.0, cached under `artifacts/models/base/`
- Authority: `docs/DATASET_AND_LICENSE_REGISTER.md`

The trainer fails closed when the manifest lacks approved training use or a permission reference.
Model files and source images remain local and Git-ignored.

## RTX 4070 laptop profile

The production pilot uses the pinned Diffusers v0.39.0 SDXL DreamBooth LoRA script with an audited
low-VRAM patch that releases the two frozen text encoders after the single shared prompt embedding is
computed. The run uses FP16, gradient checkpointing, 8-bit Adam, TF32, rank 4, batch size 1,
gradient accumulation 4, resolution 512, and 100 optimizer steps. The allocator uses expandable
segments to reduce fragmentation.

The separate fixed FP16 VAE is used when present; otherwise the local SDXL base VAE is used. Network
access is disabled inside the training subprocess, preventing accidental remote model substitution.

## Commands

One-step CUDA and artifact smoke test:

```powershell
.\.venv\Scripts\carpet-designer.exe training train `
  --dataset-manifest data/processed/carpet_lora_v1/manifest.json `
  --output-dir artifacts/models/lora_smoke_rtx4070 `
  --max-train-steps 1 --resolution 512 --rank 2
```

Approved pilot run:

```powershell
.\.venv\Scripts\carpet-designer.exe training train `
  --dataset-manifest data/processed/carpet_lora_v1/manifest.json `
  --output-dir artifacts/models/carpet_domain_v1 `
  --max-train-steps 100 --resolution 512 --rank 4
```

Each successful run writes `pytorch_lora_weights.safetensors`, `training.log`, `metrics.json`, and
`lora_manifest.json`. The adapter remains `CANDIDATE` until a generation smoke test succeeds; only
then may it be promoted to `ACTIVE_COMPANY_PILOT` in the LoRA Registry.

## Verified pilot result — 2026-07-18

- Training run: `train_20260718_063409`
- LoRA ID: `lora_07a6ab61f19c`
- Runtime: 587.223 seconds
- Artifact: 23,390,424 bytes / 1,120 tensors
- Artifact SHA-256: `66eadc5146cfbde5307e59a96c9562416fc241f9d2a8be59d5f52a0620d151d3`
- Inference: `gen_f40b1399e142`, 512×512, 15 steps, 23.070 seconds, `PASS`
- Lifecycle: `ACTIVE_COMPANY_PILOT`
