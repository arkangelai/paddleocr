"""PDF operations using PyMuPDF: metadata, page-to-image conversion."""

import os
import tempfile
from pathlib import Path

import pymupdf


def get_info(pdf_path: str) -> dict:
    path = Path(pdf_path)
    doc = pymupdf.open(str(path))

    file_size = os.path.getsize(path)
    total_pages = len(doc)

    pages_with_text = []
    pages_without_text = []
    for i in range(total_pages):
        text = doc[i].get_text().strip()
        if text:
            pages_with_text.append(i + 1)
        else:
            pages_without_text.append(i + 1)

    doc.close()

    if file_size >= 1_000_000:
        size_str = f"{file_size / 1_000_000:.1f} MB"
    else:
        size_str = f"{file_size / 1_000:.1f} KB"

    return {
        "file": path.name,
        "pages": total_pages,
        "size": size_str,
        "size_bytes": file_size,
        "pages_with_text": len(pages_with_text),
        "pages_without_text": len(pages_without_text),
    }


def page_to_image(pdf_path: str, page_num: int, dpi: int = 300, output_dir: str | None = None) -> Path:
    doc = pymupdf.open(pdf_path)
    page_idx = page_num - 1

    if page_idx < 0 or page_idx >= len(doc):
        doc.close()
        raise ValueError(f"Page {page_num} out of range (document has {len(doc)} pages)")

    page = doc[page_idx]
    zoom = dpi / 72
    mat = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    if output_dir:
        out_path = Path(output_dir) / f"page_{page_num:02d}.png"
    else:
        out_path = Path(tempfile.gettempdir()) / f"_paddleocr_page_{page_num:02d}.png"

    pix.save(str(out_path))
    doc.close()
    return out_path


def pages_to_images(
    pdf_path: str,
    pages: list[int] | None = None,
    dpi: int = 300,
    output_dir: str | None = None,
) -> list[Path]:
    doc = pymupdf.open(pdf_path)
    total = len(doc)
    doc.close()

    if pages is None:
        pages = list(range(1, total + 1))

    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    result = []
    for page_num in pages:
        img_path = page_to_image(pdf_path, page_num, dpi=dpi, output_dir=output_dir)
        result.append(img_path)

    return result


def resolve_pages(pdf_path: str, pages_str: str | None) -> list[int]:
    doc = pymupdf.open(pdf_path)
    total = len(doc)
    doc.close()

    if not pages_str:
        return list(range(1, total + 1))

    pages = []
    for part in pages_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            pages.extend(range(int(start), int(end) + 1))
        else:
            pages.append(int(part))

    for p in pages:
        if p < 1 or p > total:
            raise ValueError(f"Page {p} out of range (document has {total} pages)")

    return pages
