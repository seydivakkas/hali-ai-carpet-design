# Release Readiness

Halı AI Carpet Design is currently an **active technical pilot**. A public `v1.0.0` release should represent a stable product/evidence contract, not merely a working pilot build.

## v1.0.0 gate

- [x] Live CI is exposed in the root README.
- [x] Minimum reproducible CPU/product path is documented.
- [x] Provenance, dataset/license and training documentation exist.
- [x] Known limitations and evidence index exist.
- [x] Root branch is already `main`.
- [ ] CI confirmed green on the exact release SHA.
- [ ] Broader evaluation plan completed or explicitly scoped out of 1.0.
- [ ] Human design-review evidence summarized.
- [ ] Public/private catalog and permission boundaries re-audited.
- [ ] Model / LoRA artifact distribution policy finalized.
- [ ] Product status intentionally promoted from technical pilot to stable release.

## Release notes must include

- CPU demo vs SDXL/LoRA operating modes,
- model/LoRA identity and provenance,
- dataset/license scope,
- test/CI evidence,
- analytical metrics and their interpretation boundaries,
- explicit statement that the system does not certify manufacturability or legal originality.

Until these gates are satisfied, a pre-1.0 pilot/release-candidate label is more accurate than `v1.0.0`.
