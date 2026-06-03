# paddleocr

CLI for PDF text extraction using PP-OCRv5 models on ONNX Runtime. Runs 100% locally — no API keys, no network access, no PaddlePaddle dependency.

PP-OCRv5 is the #1 open-source OCR engine on [OmniDocBench (CVPR 2025)](https://arxiv.org/html/2412.07626v2) with only 5M parameters — beating models 100x larger.

## Why ONNX Runtime

This CLI uses the same PP-OCRv5 models as PaddleOCR but runs them on ONNX Runtime instead of PaddlePaddle. Same accuracy, dramatically lower resource usage:

| Metric | PaddlePaddle | ONNX Runtime | Improvement |
|--------|-------------|-------------|-------------|
| Peak RAM | 16 GB | 1.7 GB | **9.4x less** |
| Time per page | 26s | 3.4s | **7.7x faster** |
| RAM at load | 1.2 GB | 120 MB | **10x less** |

## Benchmark vs alternatives

Tested on 7 Colombian medical documents (SOAT, surgical records, anesthesia forms) against GPT-5.5 ground truth:

| Engine | Word Recall | Word F1 | RAM | Time/page |
|--------|------------|---------|-----|-----------|
| **This CLI (ONNX)** | **64.9%** | **67.8%** | **1.7 GB** | **3.4s** |
| PaddlePaddle (original) | 69.9% | 71.1% | 16 GB | 26s |
| Tesseract | 39.3% | 43.4% | ~300 MB | ~8s |

On standard documents (clean printed forms): **96-99% word recall** — identical to PaddlePaddle.

## Requirements

- Python 3.10+
- ~2 GB RAM
- ONNX model files (see [Model setup](#model-setup))

## Install

```bash
pip install -e .
```

## Model setup

Models are not included in the repo (92+ MB). The `paddleocr setup` command converts them automatically from PaddleOCR's cached PaddlePaddle models.

### Prerequisites

1. **paddle2onnx** (conversion tool, Python 3.12 recommended — 3.13 not yet supported):
   ```bash
   pip install paddle2onnx>=2.0.1
   ```
2. **PaddleX source models** cached at `~/.paddlex/official_models/`. If not present, run PaddleOCR once with PaddlePaddle to download them, or download manually from [PaddlePaddle's model hub](https://github.com/PaddlePaddle/PaddleOCR).

### Convert models

```bash
paddleocr setup
```

This converts 4 models (detection, recognition, two orientation classifiers) to ONNX format. The command is idempotent — it skips models that already exist. Use `--force` to reconvert all models.

```bash
# Reconvert all models (e.g. after a corrupted conversion)
paddleocr setup --force
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

# Parallel processing (2 workers)
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

## Models

4 PP-OCRv5 models converted to ONNX (installed via `paddleocr setup`):

| Model | Size | Function |
|-------|------|----------|
| PP-OCRv5_server_det | 84 MB | Text region detection |
| latin_PP-OCRv5_mobile_rec | 7.7 MB | Latin text recognition (836 chars, 45 languages) |
| PP-LCNet_x1_0_doc_ori | 6.5 MB | Document orientation (0/90/180/270) |
| PP-LCNet_x1_0_textline_ori | 6.5 MB | Text line orientation (0/180) |

## Performance

Benchmarked on Apple M4 (10 cores, 24 GB RAM) with Colombian medical documents (SOAT), 300 DPI.

| Metric | Value |
|--------|-------|
| Time per page | ~3.4s |
| Throughput | ~17 pages/min |
| RAM at load | ~120 MB |
| RAM peak | ~1.7 GB |

### Resource requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 4 GB | 8 GB |
| CPU | 2 cores | 4+ cores |
| Disk | ~200 MB | ~300 MB |
| GPU | Not required | Not required |

## OCR config

Validated on Spanish medical documents:

- Detection: PP-OCRv5 server, `resize_long=960`, stride 128, `box_thresh=0.5`, `unclip_ratio=1.5`
- Recognition: Latin PP-OCRv5 mobile, height 48px, 836-char dictionary
- Orientation: automatic document and text line rotation
- Input resize: 1/2 before OCR
