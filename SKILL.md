---
name: paddleocr
description: Extract text from PDF pages using PaddleOCR. Use when you need to OCR a PDF, get PDF metadata, or export PDF pages as images. Triggers — "extract text from this PDF", "OCR these pages", "what's in this document", "convert PDF to images".
version: 0.1.0
author: raul.escandon@arkangel.ai
platforms: [macos, linux]
metadata:
  hermes:
    tags: [ocr, pdf, paddleocr, text-extraction]
    category: document-processing
    requires_toolsets: [terminal]
---

# paddleocr

CLI for local PDF text extraction using PP-OCRv5 models on ONNX Runtime. No API keys, no network access — everything runs on the machine. Outputs markdown to stdout (pipe-friendly) or to files.

Built on PP-OCRv5 (ONNX Runtime) validated by benchmark on 7 Colombian medical documents (SOAT, surgical records, anesthesia forms) against GPT-5.5 ground truth. Handles printed text, forms, and tables well. Does NOT handle handwriting.

## When to Use

- When the user asks to extract text from a PDF.
- When you need to OCR specific pages of a scanned document.
- When you need metadata about a PDF (page count, size, embedded text detection).
- When you need PDF pages as PNG images for visual inspection or downstream processing.
- When you need OCR output as markdown for further LLM processing.

## Procedure

0. **Set up models (first time only)** — convert PaddlePaddle models to ONNX format:
   ```bash
   paddleocr setup
   ```
   Requires `paddle2onnx>=2.0.1` and PaddleX models cached at `~/.paddlex/official_models/`. Idempotent — skips models that already exist. Use `--force` to reconvert.

1. **Check the PDF first** — get page count and embedded text info before running OCR:
   ```bash
   paddleocr info --path /path/to/document.pdf
   ```

2. **Extract text from specific pages** — use `--pages` to avoid processing the entire document:
   ```bash
   paddleocr ocr --path /path/to/document.pdf --pages 1,3,5
   ```
   Output goes to stdout as markdown. Pipe or redirect as needed.

3. **Extract text to files** — use `--output-dir` to save one `page_XX.md` per page:
   ```bash
   paddleocr ocr --path /path/to/document.pdf --pages 1-10 --output-dir ./extracted
   ```

4. **Export pages as PNG images** — useful for visual inspection or sending to a vision LLM:
   ```bash
   paddleocr images --path /path/to/document.pdf --pages 1,3 --output-dir ./pages
   ```

5. **Process the full document** — omit `--pages` to process all pages (~3.4s/page):
   ```bash
   paddleocr ocr --path /path/to/document.pdf --output-dir ./full-output
   ```

6. **Speed up with parallel workers** — use `--workers` on machines with 4+ GB RAM:
   ```bash
   paddleocr ocr --path /path/to/document.pdf --workers 2 --output-dir ./output
   ```
   Each worker loads its own ONNX Runtime session (~1.7 GB each). A RAM warning is printed if the machine doesn't have enough.

### Command reference

| Command | Purpose | Key flags |
|---------|---------|-----------|
| `paddleocr setup` | Convert models to ONNX | `--force` |
| `paddleocr ocr` | Extract text via OCR | `--path`, `--pages`, `--output-dir`, `--workers` |
| `paddleocr info` | PDF metadata | `--path` |
| `paddleocr images` | Pages to PNG | `--path`, `--pages`, `--output-dir`, `--dpi` |

### Flag details

| Flag | Commands | Required | Default | Description |
|------|----------|----------|---------|-------------|
| `--path` | ocr, info, images | yes | — | Path to PDF file |
| `--pages` | ocr, images | no | all | Comma-separated pages or ranges (e.g. `1,3,5` or `1-10`) |
| `--output-dir` | ocr, images | ocr: no, images: yes | stdout (ocr) | Directory for output files |
| `--workers` | ocr | no | 1 | Parallel workers. Each needs ~1.7 GB RAM |
| `--dpi` | images | no | 300 | Image resolution |
| `--force` | setup | no | false | Reconvert models even if ONNX files exist |

## Pitfalls

- **Symptom:** `paddleocr ocr` fails with missing ONNX model errors. **Cause:** Models have not been converted yet. **Fix:** Run `paddleocr setup` first (requires `paddle2onnx` and PaddleX source models).

- **Symptom:** `paddleocr setup` fails with paddle2onnx errors on Python 3.13. **Cause:** `paddle2onnx` does not support Python 3.13+ yet. **Fix:** Use a Python 3.12 environment for the setup step.

- **Symptom:** OCR output is gibberish or mostly empty for a page. **Cause:** The page likely contains handwritten text, which PP-OCRv5 cannot read. **Fix:** Export the page as PNG with `paddleocr images` and send to a vision LLM (GPT-5.5, Claude Opus) instead.

- **Symptom:** `paddleocr: command not found`. **Cause:** The Python bin directory is not in PATH. **Fix:** Run `pip3 install -e /path/to/paddleocr/repo` or create a symlink: `ln -sf $(python3 -c "import sysconfig; print(sysconfig.get_path('scripts'))")/paddleocr ~/.local/bin/paddleocr`.

## Verification

- `paddleocr --version` returns `paddleocr, version 0.1.0`
- `paddleocr setup` converts models (or reports them already present)
- `paddleocr info --path <any-pdf>` prints markdown with page count, size, and embedded text stats
- `paddleocr ocr --path <pdf> --pages 1` prints extracted text as markdown to stdout within ~5s
- Output files in `--output-dir` are named `page_01.md`, `page_02.md`, etc.

## References

- Repo: https://github.com/arkangelai/paddleocr
- PaddleOCR config rationale: `docs.md` in the repo root
- Performance benchmarks: `README.md` — Performance section
- Benchmark raw data: https://github.com/arkangelai/paddleocr (from `extract-pdf` benchmark suite)
