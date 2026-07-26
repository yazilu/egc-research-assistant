import logging
import os
import re

from fastapi import HTTPException

from service.core.deepdoc.parser import (
    DocxParser,
    ExcelParser,
    HtmlParser,
    JsonParser,
    PptParser,
    TxtParser,
)

logger = logging.getLogger(__name__)

SUPPORTED_FILE_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".pptx",
    ".html",
    ".htm",
    ".md",
    ".markdown",
    ".txt",
    ".csv",
    ".json",
}


def get_file_extension(file_name: str) -> str:
    return os.path.splitext(file_name)[1].lower()


def supported_extensions_message() -> str:
    return ", ".join(sorted(SUPPORTED_FILE_EXTENSIONS))


def validate_supported_extension(file_name: str) -> str:
    ext = get_file_extension(file_name)
    if ext not in SUPPORTED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext or '(无扩展名)'}，支持: {supported_extensions_message()}",
        )
    return ext


def extract_pdf_text(file_path: str, include_tables: bool = True) -> str:
    import pdfplumber

    texts = []
    with pdfplumber.open(file_path) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            page_parts = []
            try:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    page_parts.append(page_text.strip())
            except Exception as exc:
                logger.warning("Failed to extract PDF page %s text from %s: %s", page_index, file_path, exc)

            if include_tables:
                try:
                    tables = page.extract_tables()
                except Exception as exc:
                    logger.warning("Failed to extract PDF page %s tables from %s: %s", page_index, file_path, exc)
                    tables = []

                for table in tables:
                    if not table:
                        continue
                    rows = []
                    for row in table:
                        cells = [str(cell).strip() if cell else "" for cell in row]
                        if any(cells):
                            rows.append(" | ".join(cells))
                    if rows:
                        page_parts.append("[表格]\n" + "\n".join(rows))

            if page_parts:
                texts.append("\n\n".join(page_parts))

    return "\n\n".join(texts)


def extract_pdf_index_text(file_path: str) -> str:
    from pypdf import PdfReader

    reader = PdfReader(file_path)
    texts = []
    for page_index, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception as exc:
            logger.warning("Failed to extract PDF page %s with pypdf from %s: %s", page_index, file_path, exc)
            continue
        page_text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", page_text)
        page_text = re.sub(r"[ \t]{2,}", " ", page_text)
        if page_text.strip():
            texts.append(page_text.strip())
    return "\n\n".join(texts)


def _normalize_parser_result(result) -> list[str]:
    if isinstance(result, tuple):
        sections = result[0] if len(result) >= 1 else []
    elif isinstance(result, list):
        sections = result
    else:
        sections = [result] if result else []

    lines = []
    for item in sections:
        if isinstance(item, (list, tuple)) and len(item) >= 1:
            text = str(item[0])
        else:
            text = str(item)
        if text.strip():
            lines.append(text)
    return lines


def extract_text(file_path: str, ext: str | None = None) -> str:
    ext = ext or get_file_extension(file_path)

    if ext == ".pdf":
        return extract_pdf_text(file_path)

    parser_map = {
        ".docx": DocxParser,
        ".xlsx": ExcelParser,
        ".pptx": PptParser,
        ".html": HtmlParser,
        ".htm": HtmlParser,
        ".md": TxtParser,
        ".markdown": TxtParser,
        ".txt": TxtParser,
        ".csv": TxtParser,
        ".json": JsonParser,
    }

    parser_cls = parser_map.get(ext)
    if parser_cls is None:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext or '(无扩展名)'}，支持: {supported_extensions_message()}",
        )

    if ext == ".json":
        with open(file_path, "rb") as file:
            result = parser_cls()(file.read())
    else:
        result = parser_cls()(file_path)

    return "\n".join(_normalize_parser_result(result))
