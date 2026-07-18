#!/usr/bin/env python
"""Import an authorized company catalog as restricted internal reference material."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from carpet_designer.data.adapters.restricted_catalog import (  # noqa: E402
    RestrictedCatalogAdapter,
)
from carpet_designer.settings import get_settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download an authorized catalog for internal reference only."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "data" / "external" / "restricted_catalog",
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="Rights-holder-approved absolute catalog URL.",
    )
    parser.add_argument(
        "--collections",
        nargs="+",
        required=True,
        help="One or more collection path names authorized for import.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Global item cap; 0 imports every product found.",
    )
    parser.add_argument(
        "--limit-per-collection",
        type=int,
        default=0,
        help="Per-collection cap; 0 imports every product found.",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Write product records without downloading images.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.25,
        help="Delay in seconds between requests.",
    )
    parser.add_argument(
        "--permission-ref",
        default=None,
        help="Written rights-holder permission reference; defaults to project settings.",
    )
    args = parser.parse_args()
    permission_ref = args.permission_ref
    if permission_ref is None:
        permission_ref = get_settings().restricted_catalog_permission_ref

    adapter = RestrictedCatalogAdapter(
        collections=args.collections,
        base_url=args.base_url,
        limit_per_collection=args.limit_per_collection or None,
        metadata_only=args.metadata_only,
        request_delay_seconds=args.delay,
        permission_ref=permission_ref,
    )
    print("Restricted catalog reference import starting...")
    print(f"Policy: {adapter.dataset_status}; training_use={adapter.training_use}.")
    results = adapter.fetch_dataset(args.output_dir, limit=args.limit)
    downloaded = sum(item["download_status"] == "downloaded" for item in results)
    print(f"Completed: {len(results)} records, {downloaded} downloaded images.")
    print(f"Manifest: {args.output_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
