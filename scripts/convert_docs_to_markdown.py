#!/usr/bin/env python3
"""
document -> markdown converter using markitdown
takes files from raw_docs/ and outputs markdown to sample_docs/
"""

import argparse
import sys
from pathlib import Path

try:
    from markitdown import MarkItDown
except ImportError as e:
    print("error: markitdown missing")
    print("install with: pip install 'markitdown[all]'")
    print(f"details: {e}")
    sys.exit(1)


def convert_document_to_markdown(input_path: Path, output_path: Path) -> bool:
    """
    convert a single document file into markdown
    """
    try:
        print(f"converting: {input_path.name}")

        md = MarkItDown()
        result = md.convert(str(input_path))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.text_content, encoding="utf-8")

        print(f"  ✓ saved: {output_path.name}")
        return True

    except Exception as e:
        msg = str(e).lower()

        if "not supported" in msg:
            print(f"  ⚠ skipped {input_path.name}: unsupported format")
        elif "not a zip" in msg or "badzipfile" in msg:
            print(f"  ✗ corrupted or invalid file: {input_path.name}")
        else:
            print(f"  ✗ error converting {input_path.name}: {str(e)[:200]}")

        return False


def convert_all_documents(raw_docs_dir: Path, sample_docs_dir: Path, specific_file: str = None) -> tuple[int, int]:
    """
    batch-convert docs in raw_docs_dir into markdown
    """
    if not raw_docs_dir.exists():
        print(f"error: directory missing → {raw_docs_dir}")
        return 0, 0

    supported_extensions = [
        "*.pdf",
        "*.doc",
        "*.docx",
        "*.xls",
        "*.xlsx",
        "*.csv",
    ]

    if specific_file:
        doc_files = [raw_docs_dir / specific_file]
        if not doc_files[0].exists():
            print(f"error: file not found → {doc_files[0]}")
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

        if convert_document_to_markdown(doc_file, output_file):
            successful += 1
        else:
            failed += 1

    return successful, failed


def main():
    """
    cli entrypoint
    """
    parser = argparse.ArgumentParser(description="convert docs -> markdown")
    parser.add_argument("--file", type=str)
    parser.add_argument("--raw-docs-dir", type=Path, default=Path(__file__).parent.parent / "raw_docs")
    parser.add_argument("--sample-docs-dir", type=Path, default=Path(__file__).parent.parent / "sample_docs")

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
