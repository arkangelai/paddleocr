# Changelog

## 0.3.0 — 2026-06-03

### Changed

- **Runtime migrado de PaddlePaddle a ONNX Runtime** — mismos modelos PP-OCRv5, 9.4x menos RAM, 7.7x mas rapido
- Dependencias: `paddleocr` y `paddlepaddle` eliminados, reemplazados por `onnxruntime`, `opencv-python-headless`, `pyclipper`, `shapely`
- RAM pico: 16 GB → 1.7 GB
- Tiempo por imagen: 26s → 3.4s
- Modelos .onnx no se commitean — se generan con `paddle2onnx` desde los modelos cacheados en `~/.paddlex/`

### Added

- Clasificador de orientacion de documento (`doc_ori`) — rota imagenes 0/90/180/270 grados automaticamente
- Clasificador de orientacion de linea (`textline_ori`) — corrige lineas invertidas 180 grados
- Archivo UVDoc.onnx presente para futura integracion de dewarping
- Modulo `onnx_ocr.py` con pipeline completo: det → crop → rec sobre ONNX Runtime

### Benchmark vs ground truth (Word Recall)

| Engine | Word Recall | Word F1 | RAM pico | Tiempo/img |
|--------|------------|---------|----------|------------|
| ONNX Runtime (este release) | 64.9% | 67.8% | 1.7 GB | 3.4s |
| PaddlePaddle (anterior) | 69.9% | 71.1% | 16 GB | 26s |
| Tesseract | 39.3% | 43.4% | ~300 MB | ~8s |

En documentos estandar (formularios limpios): 96-99% word recall, identico a PaddlePaddle.

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
