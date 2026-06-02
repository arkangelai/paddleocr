"""Markdown formatting and output to stdout or files."""

import sys
from pathlib import Path


def format_ocr_markdown(results: dict[int, str]) -> str:
    sections = []
    for page_num in sorted(results.keys()):
        text = results[page_num]
        sections.append(f"# Page {page_num}\n\n{text}")
    return "\n\n".join(sections) + "\n"


def format_info_markdown(info: dict) -> str:
    lines = [
        "# Document Info",
        "",
        f"- **File**: {info['file']}",
        f"- **Pages**: {info['pages']}",
        f"- **Size**: {info['size']}",
        f"- **Pages with embedded text**: {info['pages_with_text']}",
        f"- **Pages without embedded text**: {info['pages_without_text']}",
    ]
    return "\n".join(lines) + "\n"


def write_pages(results: dict[int, str], output_dir: str) -> list[Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    written = []
    for page_num in sorted(results.keys()):
        file_path = out / f"page_{page_num:02d}.md"
        file_path.write_text(results[page_num], encoding="utf-8")
        written.append(file_path)

    return written


def write_or_print(content: str, output_path: str | None = None):
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    else:
        sys.stdout.write(content)
