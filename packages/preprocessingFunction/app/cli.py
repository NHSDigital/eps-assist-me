#!/usr/bin/env python3
"""local cli for testing document conversion without deploying lambda"""

import argparse
import sys
from pathlib import Path

from app.services.converter import (
    convert_document_to_markdown,
    EXCEL_SHEET_FILTER,
)
from app.config.config import CONVERTIBLE_FORMATS


def convert_all_documents(raw_docs_dir: Path, sample_docs_dir: Path, specific_file: str = None) -> tuple[int, int]:
    """batch converts documents from raw_docs_dir to sample_docs_dir"""
    if not raw_docs_dir.exists():
        print(f"error: directory missing -> {raw_docs_dir}")
        return 0, 0

    supported_extensions = [f"*{ext}" for ext in CONVERTIBLE_FORMATS]

    if specific_file:
        doc_files = [raw_docs_dir / specific_file]
        if not doc_files[0].exists():
            print(f"error: file not found -> {doc_files[0]}")
            return 0, 0
    else:
        doc_files = []
        for pattern in supported_extensions:
            doc_files.extend(raw_docs_dir.glob(pattern))

    if not doc_files:
        print(f"no supported docs in {raw_docs_dir}")
        return 0, 0

    print(f"\nfound {len(doc_files)} file(s)\n")

    successful = 0
    failed = 0

    for doc_file in doc_files:
        output_file = sample_docs_dir / doc_file.with_suffix(".md").name

        print(f"converting: {doc_file.name}")

        if convert_document_to_markdown(doc_file, output_file):
            if doc_file.suffix.lower() in [".xls", ".xlsx"]:
                print(f"  -> filtered to sheets: {', '.join(EXCEL_SHEET_FILTER)}")
                print("  -> removed last 4 columns from tables")
            print(f"  saved: {output_file.name}")
            successful += 1
        else:
            print(f"  ✗ failed: {doc_file.name}")
            failed += 1

    return successful, failed


def main():
    """cli entrypoint"""
    parser = argparse.ArgumentParser(description="convert docs -> markdown")
    parser.add_argument("--file", type=str, help="specific file to convert")
    parser.add_argument(
        "--raw-docs-dir",
        type=Path,
        default=Path(__file__).parent.parent.parent.parent / "raw_docs",
        help="directory containing raw documents",
    )
    parser.add_argument(
        "--sample-docs-dir",
        type=Path,
        default=Path(__file__).parent.parent.parent.parent / "sample_docs",
        help="directory for markdown output",
    )

    args = parser.parse_args()

    successful, failed = convert_all_documents(args.raw_docs_dir, args.sample_docs_dir, args.file)

    print("\n" + "=" * 50)
    print("conversion complete")
    print(f"  ok: {successful}")
    print(f"  failed: {failed}")
    print("=" * 50)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
