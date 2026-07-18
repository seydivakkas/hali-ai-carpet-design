# Blockers

## Current status

| ID | Description | Type | Status |
|---|---|---|---|
| BLK-001 | Reproducible Python runtime | Environment | RESOLVED: uv-managed Python 3.11 |
| BLK-002 | SDXL base weights | Model | RESOLVED: local package validated, offline load passed |
| BLK-003 | restricted company catalog training authority | Data governance | RESOLVED: user-attested written permission reference recorded |
| BLK-004 | Hugging Face authentication | Auth | RESOLVED: token is configured only in ignored `.env` |
| BLK-005 | CUDA GPU for practical LoRA training | Infrastructure | RESOLVED: RTX 4070 Laptop GPU, 8 GiB, PyTorch 2.8.0+cu126 |
| BLK-006 | Direct Hugging Face static-file connection resets | Network | MITIGATED: local ModelScope mirror plus resumable range downloader |

`Trainer` enforces `training_use=approved` and a non-empty `permission_ref` before it creates a
training artifact. The merged manifest satisfies this gate. Local SDXL weights, a one-step CUDA
smoke run, the 100-step pilot run, and an SDXL+LoRA inference all passed on 2026-07-18.
