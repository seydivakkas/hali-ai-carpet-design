# Architecture Index

The detailed architecture is maintained in [`../ARCHITECTURE.md`](../ARCHITECTURE.md).

## High-level system flow

```text
Design Brief / Reference Image
        ↓
Structured Prompt / Variant Contract
        ↓
CPU Demo | SDXL Base | SDXL + LoRA
        ↓
Generated Design
   ├─ CIELAB / Delta E
   ├─ symmetry / seam / repeat
   ├─ retrieval
   └─ provenance / evidence record
        ↓
Streamlit Review Workspace
```

## Main engineering boundaries

- `../../src/carpet_designer/` — product package and orchestration.
- Generation engines are separated from shared result contracts so UI/analysis/persistence can remain stable across CPU demo, base SDXL and LoRA-backed modes.
- Provenance and permission records are part of the ML lifecycle, not post-hoc documentation.
- Analytical outputs support design review; they do not replace manufacturing validation.

For claim evidence, see [`../evidence/README.md`](../evidence/README.md). For boundaries, see [`../../KNOWN_LIMITATIONS.md`](../../KNOWN_LIMITATIONS.md).
