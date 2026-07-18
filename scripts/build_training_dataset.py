#!/usr/bin/env python
"""Build the governed multi-source carpet LoRA training dataset."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from carpet_designer.data.training_builder import TrainingDatasetBuilder  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--restricted-catalog-dir",
        type=Path,
        default=project_root / "data" / "external" / "restricted_catalog",
    )
    parser.add_argument(
        "--kaggle-dir",
        type=Path,
        default=project_root / "data" / "external" / "kaggle" / "safavid",
    )
    parser.add_argument(
        "--met-dir",
        type=Path,
        default=project_root / "data" / "external" / "met",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "data" / "processed" / "carpet_lora_v1",
    )
    parser.add_argument("--canvas-size", type=int, default=768)
    args = parser.parse_args()

    builder = TrainingDatasetBuilder(
        restricted_catalog_dir=args.restricted_catalog_dir,
        kaggle_dir=args.kaggle_dir,
        met_dir=args.met_dir,
        canvas_size=args.canvas_size,
    )
    manifest = builder.build(args.output_dir)
    print(f"Training dataset ready: {manifest['counts']['total']} images")
    for source in ("restricted_catalog", "kaggle_safavid", "met"):
        print(f"  {source}: {manifest['counts'].get(source, 0)}")
    print(f"Manifest: {args.output_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
