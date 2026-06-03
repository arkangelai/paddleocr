# paddleocr — Technical Documentation

## Architecture

```
paddleocr ocr --path doc.pdf --pages 1,3
        │
        ▼
    cli.py          Parse args, validate PDF path, resolve pages
        │
        ▼
    pdf.py          PyMuPDF converts each page to PNG (300 DPI, tempdir)
        │
        ▼
    onnx_ocr.py     Resize 1/2 → ONNX Runtime inference (det → crop → rec)
        │
        ▼
    output.py       Format as markdown → stdout or page_XX.md files
```

## Modules

### `cli.py`

Entry point. Click group with 4 subcommands: `setup`, `ocr`, `info`, `images`.

- `setup` — Converts PaddlePaddle models to ONNX format via `paddle2onnx` subprocess. Atomic writes (`.tmp` → `.onnx`), `--force` flag, required/optional model handling.
- Validates `--path` exists and is a `.pdf` file
- Parses `--pages` string into `list[int]` (supports `1,3,5` and `1-5`)
- Progress messages go to stderr, content goes to stdout

### `pdf.py`

PDF operations using PyMuPDF.

- `get_info(pdf_path) -> dict` — File name, page count, size, embedded text detection per page
- `page_to_image(pdf_path, page_num, dpi, output_dir) -> Path` — Single page to PNG
- `pages_to_images(pdf_path, pages, dpi, output_dir) -> list[Path]` — Batch export
- `resolve_pages(pdf_path, pages_str) -> list[int]` — Parse page spec, validate bounds

### `onnx_ocr.py`

ONNX Runtime OCR engine. Loads 4 PP-OCRv5 models converted from PaddlePaddle format.

- `OnnxOCR` class — Loads detection, recognition, and orientation models on init
- Detection: PP-OCRv5 server model, text region proposals
- Recognition: Latin PP-OCRv5 mobile model, 836-char dictionary
- Orientation: automatic document (0/90/180/270) and text line (0/180) correction
- Optional models (doc_ori, textline_ori) gracefully skipped if absent

### `ocr.py`

Orchestrator. Connects PDF → image → ONNX OCR → text pipeline.

- `ocr_image(image_path) -> str` — Resize 1/2, run ONNX inference, join recognized text
- `ocr_pages(pdf_path, pages) -> dict[int, str]` — Full pipeline: PDF → temp PNGs → OCR → text

### `output.py`

Markdown formatting and I/O.

- `format_ocr_markdown(results) -> str` — `# Page N` header per page
- `format_info_markdown(info) -> str` — Bullet list with metadata
- `write_pages(results, output_dir) -> list[Path]` — One `page_XX.md` per page
- `write_or_print(content, output_path)` — Stdout if no path, file otherwise

## OCR Configuration

Config validated by benchmark on 7 Colombian medical documents (SOAT, surgical records, anesthesia forms) against GPT-5.5 ground truth.

| Parameter | Value | Why |
|-----------|-------|-----|
| Detection model | PP-OCRv5 server | Best accuracy for printed medical documents |
| Recognition model | Latin PP-OCRv5 mobile | 836-char dictionary, 45 languages, handles accents and ñ |
| `resize_long` | `960` | Sweet spot: captures all printed text without memory explosion |
| Resize factor | `1/2` | 300 DPI scans are too large; halving keeps quality while fitting in RAM |

### Models (ONNX, converted via `paddleocr setup`)

| Model | Function | Size |
|-------|----------|------|
| PP-OCRv5_server_det | Text detection | 84 MB |
| latin_PP-OCRv5_mobile_rec | Latin text recognition | 7.7 MB |
| PP-LCNet_x1_0_doc_ori | Document orientation (optional) | 6.5 MB |
| PP-LCNet_x1_0_textline_ori | Text line orientation (optional) | 6.5 MB |

## Memory and Performance

| Metric | Value |
|--------|-------|
| RAM at load | ~120 MB |
| RAM peak | ~1.7 GB |
| CPU | 100% all cores during processing |
| Speed | ~3.4s/page |
| Throughput | ~17 pages/min |
| Disk | ~200 MB (models + dependencies) |

## What PP-OCRv5 handles well

- Printed tables (invoices, CUPS codes)
- Forms with complex layout (FURIPS, policies) — 28/31 fields captured
- Dense printed text (epicrisis, medical orders)
- Standard documents (clean printed forms): 96-99% word recall

## What PP-OCRv5 does NOT handle

- Handwritten text (produces gibberish)
- For handwritten content, use a vision LLM (GPT-5.5, Claude Opus) on the PNG output

## Dependencies

Only what's needed:

| Package | Purpose |
|---------|---------|
| click | CLI framework |
| pymupdf | PDF → PNG conversion + metadata |
| onnxruntime | ONNX model inference (replaces PaddlePaddle) |
| opencv-python-headless | Image preprocessing (detection pipeline) |
| pyclipper | Polygon clipping for text detection |
| shapely | Geometry operations for bounding boxes |
| Pillow | Image resize before OCR |

### Setup-only dependency

| Package | Purpose |
|---------|---------|
| paddle2onnx | Convert PaddlePaddle models to ONNX (not a runtime dep) |
