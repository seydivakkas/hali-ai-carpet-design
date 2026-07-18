#!/usr/bin/env python
"""Download only original images from the MIT-licensed Kaggle Safavid dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kaggle.api.kaggle_api_extended import KaggleApi

DATASET = "mahdisarbazi/safavid-dynasty-iranian-carpet-dataset"
SOURCE_URL = f"https://www.kaggle.com/datasets/{DATASET}"


def list_original_files(api: KaggleApi) -> list[Any]:
    """List files whose stem is numeric, excluding g/l/t augmentations."""
    files: list[Any] = []
    page_token: str | None = None
    while True:
        page = api.dataset_list_files(DATASET, page_token=page_token, page_size=200)
        files.extend(
            item for item in page.files if re.fullmatch(r"\d+", Path(item.name).stem.strip())
        )
        page_token = page.next_page_token
        if not page_token:
            break
    return sorted(files, key=lambda item: item.name)


def download_one(item: Any, output_dir: Path) -> dict[str, Any]:
    """Download one original image idempotently and return provenance metadata."""
    destination = output_dir / Path(item.name).name
    expected_size = int(item.total_bytes or 0)
    if not destination.is_file() or (expected_size and destination.stat().st_size != expected_size):
        api = KaggleApi()
        api.authenticate()
        succeeded = api.dataset_download_file(
            DATASET, item.name, path=str(output_dir), force=True, quiet=True
        )
        if not succeeded:
            raise RuntimeError(f"Kaggle download failed: {item.name}")
    return {
        "image_file": destination.name,
        "source_id": destination.stem,
        "source_path": item.name,
        "source_url": SOURCE_URL,
        "size_bytes": destination.stat().st_size,
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "license": "MIT",
        "training_use": "approved",
        "permission_ref": "KAGGLE_DATASET_LICENSE_MIT",
        "is_augmented": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/external/kaggle/safavid"),
    )
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    api = KaggleApi()
    api.authenticate()
    originals = list_original_files(api)
    print(f"Original Kaggle images selected: {len(originals)}")
    entries: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(download_one, item, args.output_dir): item for item in originals}
        for completed, future in enumerate(as_completed(futures), start=1):
            entry = future.result()
            entries.append(entry)
            print(f"[{completed}/{len(originals)}] {entry['image_file']}")
    entries.sort(key=lambda item: str(item["source_id"]))

    manifest = {
        "schema_version": 1,
        "dataset_id": "kaggle_safavid_original_v1",
        "source_url": SOURCE_URL,
        "retrieved_at": datetime.now(tz=UTC).isoformat(),
        "license": "MIT",
        "training_use": "approved",
        "permission_ref": "KAGGLE_DATASET_LICENSE_MIT",
        "status": "TRAINING_APPROVED",
        "original_count": len(entries),
        "excluded_augmented_count": 429,
        "entries": entries,
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Kaggle import complete: {len(entries)} originals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
