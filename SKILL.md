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

CLI for local PDF text extraction using PaddleOCR. No API keys, no network access — everything runs on the machine. Outputs markdown to stdout (pipe-friendly) or to files.

Built on a PaddleOCR configuration validated by benchmark on 50-page Colombian medical documents (SOAT). Handles printed text, forms, and tables well. Does NOT handle handwriting.

## When to Use

- When the user asks to extract text from a PDF.
- When you need to OCR specific pages of a scanned document.
- When you need metadata about a PDF (page count, size, embedded text detection).
- When you need PDF pages as PNG images for visual inspection or downstream processing.
- When you need OCR output as markdown for further LLM processing.

## Procedure

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

5. **Process the full document** — omit `--pages` to process all pages (slow for large docs, ~26s/page):
   ```bash
   paddleocr ocr --path /path/to/document.pdf --output-dir ./full-output
   ```

### Command reference

| Command | Purpose | Key flags |
|---------|---------|-----------|
| `paddleocr ocr` | Extract text via OCR | `--path`, `--pages`, `--output-dir` |
| `paddleocr info` | PDF metadata | `--path` |
| `paddleocr images` | Pages to PNG | `--path`, `--pages`, `--output-dir`, `--dpi` |

### Flag details

| Flag | Commands | Required | Default | Description |
|------|----------|----------|---------|-------------|
| `--path` | all | yes | — | Path to PDF file |
| `--pages` | ocr, images | no | all | Comma-separated pages or ranges (e.g. `1,3,5` or `1-10`) |
| `--output-dir` | ocr, images | ocr: no, images: yes | stdout (ocr) | Directory for output files |
| `--dpi` | images | no | 300 | Image resolution |

## Pitfalls

- **Symptom:** First run takes 30+ seconds before any output. **Cause:** PaddleOCR downloads ~136 MB of models on first use. **Fix:** This is expected. Subsequent runs use the cache at `~/.paddlex/official_models/`.

- **Symptom:** Process killed or system freezes during OCR. **Cause:** PaddleOCR peaks at ~7.5 GB RAM. Machines with less than 10 GB available will OOM. **Fix:** Close other applications or use a machine with 16+ GB RAM.

- **Symptom:** OCR output is gibberish or mostly empty for a page. **Cause:** The page likely contains handwritten text, which PaddleOCR cannot read. **Fix:** Export the page as PNG with `paddleocr images` and send to a vision LLM (GPT-5.5, Claude Opus) instead.

- **Symptom:** `paddleocr: command not found`. **Cause:** The Python bin directory is not in PATH. **Fix:** Run `pip3 install -e /path/to/paddleocr/repo` or create a symlink: `ln -sf $(python3 -c "import sysconfig; print(sysconfig.get_path('scripts'))")/paddleocr ~/.local/bin/paddleocr`.

## Verification

- `paddleocr --version` returns `paddleocr, version 0.1.0`
- `paddleocr info --path <any-pdf>` prints markdown with page count, size, and embedded text stats
- `paddleocr ocr --path <pdf> --pages 1` prints extracted text as markdown to stdout within ~30s
- Output files in `--output-dir` are named `page_01.md`, `page_02.md`, etc.

## References

- Repo: https://github.com/arkangelai/paddleocr
- PaddleOCR config rationale: `docs.md` in the repo root
- Performance benchmarks: `README.md` — Performance section
- Benchmark raw data: https://github.com/arkangelai/paddleocr (from `extract-pdf` benchmark suite)
