from pathlib import Path
from markitdown import MarkItDown
from aws_lambda_powertools import Logger

logger = Logger(child=True)

# Excel sheets to include in conversion
EXCEL_SHEET_FILTER = ["EPS Dispensing Requirements", "Technical Conformance"]


def remove_table_columns(markdown_content: str) -> str:
    """
    Remove specified columns from markdown tables.
    Removes the last 4 columns: "How the requirement may be assessed", "Actioned By",
    "Response: Yes / No", and "Response Details".

    Args:
        markdown_content: Markdown content with tables

    Returns:
        Markdown with columns removed
    """
    lines = markdown_content.split("\n")
    processed_lines = []

    for line in lines:
        # Check if this is a table row (starts with |)
        if line.strip().startswith("|"):
            # Split by | and remove empty first/last elements
            cells = [cell.strip() for cell in line.split("|")]
            # Filter out empty cells from start/end
            if cells and cells[0] == "":
                cells = cells[1:]
            if cells and cells[-1] == "":
                cells = cells[:-1]

            # Remove the last 4 columns if we have more than 4 columns
            if len(cells) > 4:
                cells = cells[:-4]

            # Reconstruct the row
            processed_lines.append("| " + " | ".join(cells) + " |")
        else:
            processed_lines.append(line)

    return "\n".join(processed_lines)


def filter_excel_sheets(markdown_content: str) -> str:
    """
    Filter Excel markdown output to only include specified sheets.

    Args:
        markdown_content: Full markdown content from Excel conversion

    Returns:
        Filtered markdown with only the specified sheets
    """
    if not EXCEL_SHEET_FILTER:
        return markdown_content

    lines = markdown_content.split("\n")
    filtered_lines = []
    include_section = False

    for line in lines:
        # Check if this is a sheet header (## Sheet Name)
        if line.startswith("## "):
            sheet_name = line[3:].strip()
            # Remove &amp; HTML entities
            sheet_name = sheet_name.replace("&amp;", "&")

            if sheet_name in EXCEL_SHEET_FILTER:
                include_section = True
                filtered_lines.append(line)
            else:
                include_section = False
        elif include_section:
            filtered_lines.append(line)

    return "\n".join(filtered_lines)


def convert_document_to_markdown(input_path: Path, output_path: Path) -> bool:
    """
    Convert a single document file into markdown using MarkItDown.

    Args:
        input_path: Path to the input document
        output_path: Path where markdown output should be saved

    Returns:
        True if conversion successful, False otherwise
    """
    try:
        logger.info(f"Converting document: {input_path.name}")

        md = MarkItDown()
        result = md.convert(str(input_path))

        # Apply sheet filtering and column removal for Excel files
        markdown_content = result.text_content
        if input_path.suffix.lower() in [".xls", ".xlsx"]:
            original_size = len(markdown_content)
            markdown_content = filter_excel_sheets(markdown_content)
            markdown_content = remove_table_columns(markdown_content)
            logger.info(f"Applied Excel filtering: {original_size} -> {len(markdown_content)} chars")
            logger.info(f"Filtered to sheets: {', '.join(EXCEL_SHEET_FILTER)}")

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
    """
    Check if a file extension requires conversion to markdown.

    Args:
        file_extension: File extension (e.g., ".pdf", ".docx")

    Returns:
        True if file should be converted, False otherwise
    """
    from app.config.config import CONVERTIBLE_FORMATS

    return file_extension.lower() in CONVERTIBLE_FORMATS


def is_passthrough_format(file_extension: str) -> bool:
    """
    Check if a file extension should be passed through without conversion.

    Args:
        file_extension: File extension (e.g., ".md", ".txt")

    Returns:
        True if file should be passed through, False otherwise
    """
    from app.config.config import PASSTHROUGH_FORMATS

    return file_extension.lower() in PASSTHROUGH_FORMATS


def is_supported_format(file_extension: str) -> bool:
    """
    Check if a file extension is supported at all.

    Args:
        file_extension: File extension (e.g., ".pdf", ".md")

    Returns:
        True if file is supported, False otherwise
    """
    from app.config.config import SUPPORTED_FILE_TYPES

    return file_extension.lower() in SUPPORTED_FILE_TYPES
