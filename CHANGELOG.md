# Changelog

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
