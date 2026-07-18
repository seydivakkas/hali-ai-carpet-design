#!/usr/bin/env python
"""
Import script for the Met Open Access API.
Downloads carpet/rug images from the public domain dataset.
"""

import argparse
import sys
from pathlib import Path

# Add src to sys.path so we can import our modules
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from carpet_designer.data.adapters.met_open_access import MetOpenAccessAdapter  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Fetch carpet dataset from Met Open Access API.")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(project_root / "data" / "external" / "met"),
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
        help="Fetch high-resolution primaryImage instead of primaryImageSmall.",
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    print("Starting Met Open Access import...")
    print(f"Query: '{args.query}' | Limit: {args.limit} | High-Res: {args.high_res}")
    print(f"Output Directory: {output_dir}")

    adapter = MetOpenAccessAdapter(query=args.query, use_high_res=args.high_res)
    results = adapter.fetch_dataset(output_dir=output_dir, limit=args.limit)

    print(f"Completed! Successfully imported {len(results)} items.")


if __name__ == "__main__":
    main()
