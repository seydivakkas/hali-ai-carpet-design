# Data Card: carpet_lora_v1

Status: **TRAINING_APPROVED**

- Total: 386 normalized 768×768 JPEG images with full-rug padding.
- Restricted company catalog: 235 products from 15 collections under recorded training permission.
- Kaggle: 143 original Safavid carpet images under MIT; 429 augmented derivatives excluded.
- The Met: 8 carpet/textile records marked public domain; 21 unrelated sample records excluded.
- Deduplication and validation: 0 SHA-256 duplicates, 0 invalid images.
- Trigger token: `mrcpt`.
- Manifest content hash: `[REDACTED_PUBLIC]`; full value is retained in the private manifest.
- Storage: `data/processed/carpet_lora_v1/`.
- Metadata: `manifest.json`, `metadata.jsonl`, and `ATTRIBUTION.md`.

The set is intended for an internal technical pilot, not for publication or redistribution.
Rights-holder approval is represented by the user-attested permission reference
`USER_ATTESTED_WRITTEN_PERMISSION_2026-07-18`; the signed source document should be retained in the
company's own document system.

Known limitations: the pilot set is small, catalog photography is not class-balanced, historic
Safavid imagery differs from modern product photography, and only eight relevant open-access museum
records were found in the existing local sample. Production training should add an approved,
balanced export of product attributes, palettes, constructions, and sales-independent design labels.
