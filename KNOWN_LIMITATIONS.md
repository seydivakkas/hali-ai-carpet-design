# Known Limitations

Halı AI Carpet Design is an AI-assisted design and engineering review system. The following boundaries are intentional and should remain visible in portfolio, pilot and technical claims.

## 1. Not a manufacturing certificate

Symmetry, seam, repeat and color metrics are digital design-analysis signals. They do not prove that a generated design is physically manufacturable on a specific loom, yarn set or production line.

## 2. Not an originality or copyright guarantee

Similarity retrieval, provenance records and dataset/license governance improve traceability, but they do not independently certify legal originality, non-infringement or copyright safety.

## 3. Human review remains required

Generated designs are candidates for designer and production-team review. The system is not intended to autonomously approve a final commercial product.

## 4. LoRA results are domain- and data-dependent

The behavior of a LoRA adapter depends on the permitted training corpus, captions, hyperparameters, base model and inference recipe. A single pilot run does not establish general superiority over every style or prompt family.

## 5. Evaluation is incomplete

Repository evidence includes automated software tests, analytical design metrics, provenance and selected base-vs-LoRA comparisons. Broader human preference studies, systematic FID-style evaluation and physical production validation remain separate work.

## 6. GPU/model dependency

The CPU demo validates product flow without requiring a generative GPU model. Real SDXL / LoRA generation requires the documented model artifacts and a compatible runtime; degraded/demo operation must not be presented as equivalent to full model-backed inference.

## 7. Restricted/private data boundary

Permission references and provenance metadata may be recorded in the repository, while restricted catalog content, signed permission documents, private model artifacts and company-internal evidence should remain outside the public repository unless explicitly cleared for publication.

## Evidence policy

Portfolio claims should reference the repository's CI, dataset/license register, training protocol, screenshots and technical review. See `docs/evidence/README.md`.
