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
    ocr.py          Resize 1/2 with Pillow → PaddleOCR predict → rec_texts
        │
        ▼
    output.py       Format as markdown → stdout or page_XX.md files
```

## Modules

### `cli.py`

Entry point. Click group with 3 subcommands: `ocr`, `info`, `images`.

- Validates `--path` exists and is a `.pdf` file
- Parses `--pages` string into `list[int]` (supports `1,3,5` and `1-5`)
- Progress messages go to stderr, content goes to stdout

### `pdf.py`

PDF operations using PyMuPDF.

- `get_info(pdf_path) -> dict` — File name, page count, size, embedded text detection per page
- `page_to_image(pdf_path, page_num, dpi, output_dir) -> Path` — Single page to PNG
- `pages_to_images(pdf_path, pages, dpi, output_dir) -> list[Path]` — Batch export
- `resolve_pages(pdf_path, pages_str) -> list[int]` — Parse page spec, validate bounds

### `ocr.py`

PaddleOCR wrapper. Singleton pattern for model reuse across pages.

- `_get_ocr()` — Lazy-loads PaddleOCR with `lang='es'`, `text_det_limit_side_len=960`
- `ocr_image(image_path) -> str` — Resize 1/2, predict, join `rec_texts` with newlines
- `ocr_pages(pdf_path, pages) -> dict[int, str]` — Full pipeline: PDF → temp PNGs → OCR → text

### `output.py`

Markdown formatting and I/O.

- `format_ocr_markdown(results) -> str` — `# Page N` header per page
- `format_info_markdown(info) -> str` — Bullet list with metadata
- `write_pages(results, output_dir) -> list[Path]` — One `page_XX.md` per page
- `write_or_print(content, output_path)` — Stdout if no path, file otherwise

## PaddleOCR Configuration

Config comes from benchmark testing on 7 pages of a 50-page Colombian SOAT medical document.

| Parameter | Value | Why |
|-----------|-------|-----|
| `lang` | `'es'` | Latin recognition model, handles accents and ñ |
| `text_det_limit_side_len` | `960` | Sweet spot: captures all printed text without memory explosion |
| Resize factor | `1/2` | 300 DPI scans are too large; halving keeps quality while fitting in RAM |

### Models loaded (cached in `~/.paddlex/official_models/`)

| Model | Function | Size |
|-------|----------|------|
| PP-LCNet_x1_0_doc_ori | Document orientation | 6.6 MB |
| UVDoc | Dewarping | 31 MB |
| PP-LCNet_x1_0_textline_ori | Text line orientation | 6.6 MB |
| PP-OCRv5_server_det | Text detection (server) | 84 MB |
| latin_PP-OCRv5_mobile_rec | Latin recognition (mobile) | 7.9 MB |

## Memory and Performance

| Metric | Value |
|--------|-------|
| RAM peak | ~5.7 GB |
| RAM stable | ~2.5 GB |
| CPU | 100% all cores during processing |
| Speed | ~26s/page (2 CPU cores) |
| Chars/page | ~2,200 average |
| Disk | ~600 MB (framework + models) |

## What PaddleOCR handles well

- Printed tables (invoices, CUPS codes)
- Forms with complex layout (FURIPS, policies) — 28/31 fields captured
- Dense printed text (epicrisis, medical orders)

## What PaddleOCR does NOT handle

- Handwritten text (produces gibberish)
- For handwritten content, use a vision LLM (GPT-5.5, Claude Opus) on the PNG output

## Dependencies

Only what's needed:

| Package | Purpose |
|---------|---------|
| click | CLI framework |
| pymupdf | PDF → PNG conversion + metadata |
| paddleocr + paddlepaddle | OCR engine |
| Pillow | Image resize before OCR |
