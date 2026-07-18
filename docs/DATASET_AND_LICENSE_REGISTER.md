# Dataset and License Register

| dataset_id | source | license / authority | training use | permission reference | selected | excluded | manifest SHA-256 | status |
|---|---|---|---|---|---:|---:|---|---|
| `restricted_company_catalog_reference` | Private company catalog (not redistributed) | All rights reserved; rights-holder permission required | Internal model training | `USER_ATTESTED_WRITTEN_PERMISSION_2026-07-18` | 235 | 0 failed | `f6f29a930db39744a23ac78c28bfa316ea234ea7ba9c2065604dd953e76de149` | `TRAINING_APPROVED` |
| `kaggle_safavid_original_v1` | [Safavid Dynasty Iranian Carpet Dataset](https://www.kaggle.com/datasets/mahdisarbazi/safavid-dynasty-iranian-carpet-dataset) | MIT | Approved under dataset license | `KAGGLE_DATASET_LICENSE_MIT` | 143 originals | 429 augmented copies | `3c2ea0ae32a3e04d13de4542cdd14e6c6f1367a092c335c22a5cc64b4eba0b86` | `TRAINING_APPROVED` |
| `met_open_access_carpet_subset` | [The Met Open Access](https://www.metmuseum.org/hubs/open-access) | Public domain | Approved | `MET_OPEN_ACCESS_PUBLIC_DOMAIN` | 8 relevant objects | 21 non-carpet records | `1e758ac2f09f16fd77af64ca722d3e0e23a9d9e58c06a38c919263d51ab1c8bd` | `TRAINING_APPROVED` |
| `carpet_lora_v1` | Normalized merged dataset | Source-specific terms above | Approved | `MULTI_SOURCE_LICENSE_REGISTER_2026-07-18` | 386 | 0 duplicate, 0 invalid | `[REDACTED_PUBLIC]` | `TRAINING_APPROVED` |

The rights-holder permission reference records the user's attestation that written permission was granted
for this training use. The source approval document itself is not stored in this repository and has
not been independently verified by the application.

The Kaggle source contains 143 originals and 429 derived augmentation files. Only the originals are
used so that train-time transformations remain controlled and duplicate influence is avoided. The
previous V&A sample is excluded because its local manifest did not provide a sufficiently precise
training license.

Raw source files and normalized training images are intentionally excluded from Git. Rebuild the
audited local snapshot with:

```powershell
.\.venv\Scripts\python.exe scripts\import_restricted_catalog.py --delay 0
.\.venv\Scripts\python.exe scripts\import_kaggle_safavid.py
.\.venv\Scripts\python.exe scripts\build_training_dataset.py
```

Every normalized image has source URL, source object ID, license, permission reference, SHA-256,
caption, dimensions, and split recorded in `data/processed/carpet_lora_v1/manifest.json` and
`metadata.jsonl`.
