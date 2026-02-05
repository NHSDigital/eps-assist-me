from pathlib import Path
import re
from markitdown import MarkItDown

try:
    from aws_lambda_powertools import Logger

    logger = Logger(child=True)
    USE_LAMBDA_LOGGER = True
except ImportError:
    # lambda powertools not available in local cli mode
    import logging

    logger = logging.getLogger(__name__)
    USE_LAMBDA_LOGGER = False

EXCEL_SHEET_FILTER = ["EPS Dispensing Requirements", "Technical Conformance"]


def remove_table_columns(markdown_content: str) -> str:
    """
    strips last 4 columns from scal tables
    (assessment method, actioned by, response fields)
    """
    lines = markdown_content.split("\n")
    processed_lines = []

    for line in lines:
        if line.strip().startswith("|"):
            cells = [cell.strip() for cell in line.split("|")]
            if cells and cells[0] == "":
                cells = cells[1:]
            if cells and cells[-1] == "":
                cells = cells[:-1]

            if len(cells) > 4:
                cells = cells[:-4]

            processed_lines.append("| " + " | ".join(cells) + " |")
        else:
            processed_lines.append(line)

    return "\n".join(processed_lines)


def filter_excel_sheets(markdown_content: str) -> str:
    """
    keeps only sheets matching EXCEL_SHEET_FILTER
    markitdown converts each sheet to markdown section
    """
    if not EXCEL_SHEET_FILTER:
        return markdown_content

    lines = markdown_content.split("\n")
    filtered_lines = []
    include_section = False

    for line in lines:
        if line.startswith("## "):
            sheet_name = line[3:].strip().replace("&amp;", "&")

            if sheet_name in EXCEL_SHEET_FILTER:
                include_section = True
                filtered_lines.append(line)
            else:
                include_section = False
        elif include_section:
            filtered_lines.append(line)

    return "\n".join(filtered_lines)


def convert_document_to_markdown(input_path: Path, output_path: Path) -> bool:
    """converts document to markdown, applies excel filtering if needed"""
    try:
        logger.info(f"Converting document: {input_path.name}")

        md = MarkItDown()
        result = md.convert(str(input_path))

        markdown_content = result.text_content
        if input_path.suffix.lower() in [".xls", ".xlsx"]:
            original_size = len(markdown_content)
            markdown_content = filter_excel_sheets(markdown_content)
            markdown_content = remove_table_columns(markdown_content)
            logger.info(f"Applied Excel filtering: {original_size} -> {len(markdown_content)} chars")
            logger.info(f"Filtered to sheets: {', '.join(EXCEL_SHEET_FILTER)}")

        # Create logical chunks based on code blocks and headings
        markdown_chunks = re.split(r"(`.*`\n+.*\n+## Overview)", markdown_content)
        if len(markdown_chunks) > 1:
            for i, chunk in enumerate(markdown_chunks):
                # name = chunk.split("\n", 1)[0]
                chunk_path = output_path.with_name(f"{output_path.stem}_{i + 1}{output_path.suffix}")
                chunk_path.write_text(chunk, encoding="utf-8")
                logger.info(f"Created chunk: {chunk_path.name} ({chunk_path.stat().st_size} bytes)")

                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(markdown_content, encoding="utf-8")

            logger.info(
                f"Conversion successful: {output_path.name} - in {len(markdown_chunks)} chunks"
                + f"({output_path.stat().st_size} bytes)"
            )
            return True

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown_content, encoding="utf-8")

        logger.info(f"Conversion successful: {output_path.name} ({output_path.stat().st_size} bytes)")
        return True

    except Exception as e:
        error_msg = str(e).lower()

        if "not supported" in error_msg:
            logger.warning(f"Skipped {input_path.name}: unsupported format")
        elif "not a zip" in error_msg or "badzipfile" in error_msg:
            logger.error(f"Corrupted or invalid file: {input_path.name}")
        else:
            logger.error(f"Error converting {input_path.name}: {str(e)[:200]}")

        return False


def is_convertible_format(file_extension: str) -> bool:
    from app.config.config import CONVERTIBLE_FORMATS

    return file_extension.lower() in CONVERTIBLE_FORMATS


def is_passthrough_format(file_extension: str) -> bool:
    from app.config.config import PASSTHROUGH_FORMATS

    return file_extension.lower() in PASSTHROUGH_FORMATS


def is_supported_format(file_extension: str) -> bool:
    from app.config.config import SUPPORTED_FILE_TYPES

    return file_extension.lower() in SUPPORTED_FILE_TYPES
