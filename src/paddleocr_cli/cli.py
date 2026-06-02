"""CLI entry point for paddleocr."""

from pathlib import Path

import click

from paddleocr_cli.pdf import get_info, pages_to_images, resolve_pages
from paddleocr_cli.ocr import ocr_pages
from paddleocr_cli.output import (
    format_info_markdown,
    format_ocr_markdown,
    write_or_print,
    write_pages,
)


def validate_pdf_path(ctx, param, value):
    path = Path(value)
    if not path.exists():
        raise click.BadParameter(f"File not found: {value}")
    if not path.is_file():
        raise click.BadParameter(f"Not a file: {value}")
    if path.suffix.lower() != ".pdf":
        raise click.BadParameter(f"Not a PDF: {value}")
    return str(path.resolve())


@click.group()
@click.version_option(version="0.1.0")
def main():
    """PDF text extraction using PaddleOCR."""


@main.command()
@click.option("--path", required=True, callback=validate_pdf_path, help="Path to PDF file.")
@click.option("--pages", default=None, help="Pages to process (e.g. 1,3,5 or 1-5). Default: all.")
@click.option("--output-dir", default=None, help="Save page_XX.md files to this directory.")
def ocr(path, pages, output_dir):
    """Extract text from PDF pages using PaddleOCR."""
    page_list = resolve_pages(path, pages)
    click.echo(f"Processing {len(page_list)} page(s)...", err=True)

    results = ocr_pages(path, page_list)

    if output_dir:
        written = write_pages(results, output_dir)
        for f in written:
            click.echo(f"Saved: {f}", err=True)
    else:
        content = format_ocr_markdown(results)
        write_or_print(content)


@main.command()
@click.option("--path", required=True, callback=validate_pdf_path, help="Path to PDF file.")
def info(path):
    """Show PDF metadata without running OCR."""
    doc_info = get_info(path)
    content = format_info_markdown(doc_info)
    write_or_print(content)


@main.command()
@click.option("--path", required=True, callback=validate_pdf_path, help="Path to PDF file.")
@click.option("--pages", default=None, help="Pages to export (e.g. 1,3,5 or 1-5). Default: all.")
@click.option("--output-dir", required=True, help="Directory to save PNG files.")
@click.option("--dpi", default=300, type=int, help="Resolution in DPI. Default: 300.")
def images(path, pages, output_dir, dpi):
    """Export PDF pages as PNG images."""
    page_list = resolve_pages(path, pages)
    click.echo(f"Exporting {len(page_list)} page(s) at {dpi} DPI...", err=True)

    exported = pages_to_images(path, page_list, dpi=dpi, output_dir=output_dir)

    for f in exported:
        click.echo(f"Saved: {f}", err=True)
