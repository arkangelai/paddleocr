"""CLI entry point for paddleocr-cli."""

import os
import shutil
import subprocess
import sys
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

RAM_PER_WORKER_GB = 8


def validate_pdf_path(ctx, param, value):
    path = Path(value)
    if not path.exists():
        raise click.BadParameter(f"File not found: {value}")
    if not path.is_file():
        raise click.BadParameter(f"Not a file: {value}")
    if path.suffix.lower() != ".pdf":
        raise click.BadParameter(f"Not a PDF: {value}")
    return str(path.resolve())


def _get_total_ram_gb() -> float | None:
    try:
        if hasattr(os, "sysconf"):
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            if pages > 0 and page_size > 0:
                return (pages * page_size) / (1024 ** 3)
    except Exception:
        pass
    return None


def _warn_ram(workers: int):
    needed = workers * RAM_PER_WORKER_GB
    total = _get_total_ram_gb()
    if total and needed > total:
        click.echo(
            f"Warning: {workers} workers need ~{needed} GB RAM, "
            f"but this machine has {total:.0f} GB total. Risk of OOM.",
            err=True,
        )


@click.group()
@click.version_option(version="0.1.0")
def main():
    """PDF text extraction using ONNX Runtime."""


@main.command()
@click.option("--path", required=True, callback=validate_pdf_path, help="Path to PDF file.")
@click.option("--pages", default=None, help="Pages to process (e.g. 1,3,5 or 1-5). Default: all.")
@click.option("--output-dir", default=None, help="Save page_XX.md files to this directory.")
@click.option("--workers", default=1, type=click.IntRange(min=1), help="Number of parallel workers. Default: 1.")
def ocr(path, pages, output_dir, workers):
    """Extract text from PDF pages using OCR."""
    page_list = resolve_pages(path, pages)

    if workers > 1:
        _warn_ram(workers)
        click.echo(f"Processing {len(page_list)} page(s) with {workers} workers...", err=True)
    else:
        click.echo(f"Processing {len(page_list)} page(s)...", err=True)

    results = ocr_pages(path, page_list, workers=workers)

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


# ---------------------------------------------------------------------------
# paddleocr setup
# ---------------------------------------------------------------------------

_SOURCE_BASE = Path.home() / ".paddlex" / "official_models"
_MODELS_DIR = Path(__file__).parent / "models"

_MODELS = [
    # (source_dir_name, onnx_filename, required)
    ("PP-OCRv5_server_det", "PP-OCRv5_server_det.onnx", True),
    ("latin_PP-OCRv5_mobile_rec", "latin_PP-OCRv5_mobile_rec.onnx", True),
    ("PP-LCNet_x1_0_doc_ori", "PP-LCNet_x1_0_doc_ori.onnx", False),
    ("PP-LCNet_x1_0_textline_ori", "PP-LCNet_x1_0_textline_ori.onnx", False),
]


@main.command()
@click.option("--force", is_flag=True, default=False, help="Reconvert models even if ONNX files already exist.")
def setup(force):
    """Convert PaddlePaddle models to ONNX format for local inference."""
    # Check paddle2onnx is installed
    if shutil.which("paddle2onnx") is None:
        click.echo(
            "paddle2onnx not found. Install it: pip install paddle2onnx>=2.0.1",
            err=True,
        )
        raise SystemExit(1)

    # Warn on Python >= 3.13
    if sys.version_info >= (3, 13):
        click.echo(
            "Warning: paddle2onnx may not support Python 3.13+. "
            "Use a Python 3.12 environment if conversion fails.",
            err=True,
        )

    # Ensure output directory exists
    _MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # Check source models and convert
    missing_required: list[str] = []
    converted = 0
    skipped = 0
    failed = 0

    for source_name, onnx_name, required in _MODELS:
        source_dir = _SOURCE_BASE / source_name
        onnx_path = _MODELS_DIR / onnx_name
        tmp_path = onnx_path.with_suffix(".onnx.tmp")

        # Check if source exists
        if not source_dir.exists():
            if required:
                missing_required.append(str(source_dir))
                continue
            else:
                click.echo(
                    f"Skipping optional model {source_name} (source not found)",
                    err=True,
                )
                skipped += 1
                continue

        # Skip if already converted (unless --force)
        if onnx_path.exists() and not force:
            click.echo(f"Skipping {onnx_name} (already exists)", err=True)
            skipped += 1
            continue

        click.echo(f"Converting {source_name}...", err=True)

        try:
            result = subprocess.run(
                [
                    "paddle2onnx",
                    "--model_dir", str(source_dir),
                    "--model_filename", "inference.json",
                    "--params_filename", "inference.pdiparams",
                    "--save_file", str(tmp_path),
                    "--opset_version", "17",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            click.echo(
                f"Failed to convert {source_name}: {exc.stderr.strip()}",
                err=True,
            )
            # Clean up partial tmp file
            if tmp_path.exists():
                tmp_path.unlink()
            failed += 1
            if required:
                missing_required.append(f"{source_name} (conversion failed)")
            continue

        # Validate output > 0 bytes
        if not tmp_path.exists() or tmp_path.stat().st_size == 0:
            click.echo(
                f"Failed to convert {source_name}: output file is empty",
                err=True,
            )
            if tmp_path.exists():
                tmp_path.unlink()
            failed += 1
            if required:
                missing_required.append(f"{source_name} (empty output)")
            continue

        # Atomic rename
        tmp_path.rename(onnx_path)
        click.echo(f"OK: {onnx_name}", err=True)
        converted += 1

    # Report missing required models
    if missing_required:
        click.echo("", err=True)
        click.echo(
            "Error: required models could not be set up:", err=True
        )
        for m in missing_required:
            click.echo(f"  - {m}", err=True)
        click.echo(
            "\nRun PaddleOCR once with PaddlePaddle to download models, "
            "or see README.",
            err=True,
        )
        raise SystemExit(1)

    click.echo("", err=True)
    click.echo(
        f"Setup complete: {converted} converted, {skipped} skipped, {failed} failed.",
        err=True,
    )
