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

# Parallel processing (2 workers, needs ~16 GB RAM)
paddleocr ocr --path document.pdf --workers 2 --output-dir ./output
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

## Performance

Benchmarked on Apple M4 (10 cores, 24 GB RAM) with a 50-page Colombian medical document (SOAT), 300 DPI scans. Each page measured 3 times.

| Metric | Value |
|--------|-------|
| Cold start (model load) | ~4.5s |
| Average time per page | ~26s |
| Throughput | ~2.3 pages/min |
| RAM (model load) | ~1.2 GB |
| RAM peak (during OCR) | ~7.5 GB |
| Chars extracted per page | ~2,200 avg |

### Resource requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 10 GB | 16 GB |
| CPU | 2 cores | 4+ cores |
| Disk | ~600 MB | ~1 GB |
| GPU | Not required | Not required |

Processing is CPU-bound at ~100% utilization during OCR. With `--workers 1` (default), a 50-page document takes ~22 minutes. Use `--workers 2` to cut that in half (~11 min) at the cost of ~16 GB RAM.

## PaddleOCR config

Validated configuration from benchmark testing on Spanish medical documents:

- Language: `es` (Latin recognition model)
- Detection limit: `960px` side length
- Input resize: 1/2 before OCR (reduces memory from 6GB+ to ~2.5GB stable)
- Average speed: ~26s/page on 2 CPU cores
