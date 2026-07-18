#!/usr/bin/env python
"""
Import script for the V&A Museum API.
Downloads carpet/rug images from the Victoria & Albert dataset.
"""

import argparse
import sys
from pathlib import Path

# Add src to sys.path so we can import our modules
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from carpet_designer.data.adapters.vna import VnaAdapter  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Fetch carpet dataset from V&A Museum API.")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(project_root / "data" / "external" / "vna"),
        help="Directory to save the downloaded images and manifest.",
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="Maximum number of items to download."
    )
    parser.add_argument(
        "--query", type=str, default="carpet", help="Search query to filter results."
    )
    parser.add_argument(
        "--high-res",
        action="store_true",
        help="Fetch high-resolution full size instead of 512x512.",
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    print("Starting V&A Museum import...")
    print(f"Query: '{args.query}' | Limit: {args.limit} | High-Res: {args.high_res}")
    print(f"Output Directory: {output_dir}")

    adapter = VnaAdapter(query=args.query, use_high_res=args.high_res)
    results = adapter.fetch_dataset(output_dir=output_dir, limit=args.limit)

    print(f"Completed! Successfully imported {len(results)} items.")


if __name__ == "__main__":
    main()
