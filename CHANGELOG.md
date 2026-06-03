# Changelog

## 0.4.0 — 2026-06-03

### Added

- **`paddleocr setup` command** — automates PaddlePaddle to ONNX model conversion in a single step
- `--force` flag to reconvert existing models (recovery from corrupted files)
- Atomic writes: converts to `.onnx.tmp`, renames to `.onnx` on completion
- Prerequisite detection: checks for `paddle2onnx`, source models, and Python version
- Required models missing → clear error. Optional missing → warning and skip.
- Updated documentation: README, SKILL.md, docs.md reflect ONNX Runtime era + automated setup

## 0.3.0 — 2026-06-03

### Changed

- **Runtime migrated from PaddlePaddle to ONNX Runtime** — same PP-OCRv5 models, 9.4x less RAM, 7.7x faster
- Dependencies: `paddleocr` and `paddlepaddle` removed, replaced by `onnxruntime`, `opencv-python-headless`, `pyclipper`, `shapely`
- Peak RAM: 16 GB → 1.7 GB
- Time per page: 26s → 3.4s
- ONNX models are not committed — generated with `paddle2onnx` from cached models at `~/.paddlex/`

### Added

- Document orientation classifier (`doc_ori`) — automatically rotates images 0/90/180/270 degrees
- Text line orientation classifier (`textline_ori`) — corrects 180-degree inverted lines
- `onnx_ocr.py` module with full pipeline: det → crop → rec on ONNX Runtime

### Benchmark vs ground truth (GPT-5.5, Word Recall)

| Engine | Word Recall | Word F1 | Peak RAM | Time/page |
|--------|------------|---------|----------|-----------|
| ONNX Runtime (this release) | 64.9% | 67.8% | 1.7 GB | 3.4s |
| PaddlePaddle (previous) | 69.9% | 71.1% | 16 GB | 26s |
| Tesseract | 39.3% | 43.4% | ~300 MB | ~8s |

On standard documents (clean printed forms): 96-99% word recall, identical to PaddlePaddle.

## 0.2.0 — 2026-06-02

### Added

- `--workers N` flag for `paddleocr ocr` — parallel page processing using multiprocessing
- RAM warning on stderr when workers * 8 GB exceeds available system memory

## 0.1.0 — 2026-06-02

Initial release.

### Added

- `paddleocr ocr` — Extract text from PDF pages using PaddleOCR, output as markdown to stdout or files
- `paddleocr info` — Show PDF metadata (pages, size, embedded text detection)
- `paddleocr images` — Export PDF pages as PNG images
- Page selection via `--pages` flag (comma-separated or ranges)
- `--output-dir` flag for saving results to disk
- PaddleOCR config validated on Spanish medical documents: `lang='es'`, `text_det_limit_side_len=960`, resize 1/2
