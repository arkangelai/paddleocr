# paddleocr

CLI for PDF text extraction using PaddleOCR. Runs 100% locally — no API keys, no network access.

## Requirements

- Python 3.10+
- ~8 GB RAM (PaddleOCR loads 5 models into memory)

## Install

```bash
pip install -e .
```

## Usage

### Extract text from PDF pages

```bash
# All pages to stdout
paddleocr ocr --path document.pdf

# Specific pages to stdout
paddleocr ocr --path document.pdf --pages 1,3,5

# Page range to files
paddleocr ocr --path document.pdf --pages 1-10 --output-dir ./output
```

### PDF metadata

```bash
paddleocr info --path document.pdf
```

### Export pages as images

```bash
paddleocr images --path document.pdf --pages 1,3 --output-dir ./pages
paddleocr images --path document.pdf --output-dir ./pages --dpi 150
```

## Output

All text output is markdown. When using `--output-dir`, each page is saved as `page_01.md`, `page_02.md`, etc.

## PaddleOCR config

Validated configuration from benchmark testing on Spanish medical documents:

- Language: `es` (Latin recognition model)
- Detection limit: `960px` side length
- Input resize: 1/2 before OCR (reduces memory from 6GB+ to ~2.5GB stable)
- Average speed: ~26s/page on 2 CPU cores
