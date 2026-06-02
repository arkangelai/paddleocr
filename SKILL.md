# paddleocr — CLI Skill Reference

CLI para extracción de texto de PDFs usando PaddleOCR. Corre 100% local, sin API keys.

## Comandos

### `paddleocr ocr`

Extrae texto de páginas de un PDF usando PaddleOCR.

```bash
paddleocr ocr --path <pdf> [--pages 1,3,5] [--output-dir ./output]
```

| Flag | Requerido | Default | Descripción |
|------|-----------|---------|-------------|
| `--path` | si | — | Ruta al archivo PDF |
| `--pages` | no | todas | Páginas a procesar, separadas por coma o rango (1-5) |
| `--output-dir` | no | stdout | Directorio donde guardar `page_XX.md` por página |

Sin `--output-dir`, imprime markdown a stdout.

### `paddleocr info`

Muestra metadata del PDF sin ejecutar OCR.

```bash
paddleocr info --path <pdf>
```

Output: nombre, total de páginas, tamaño, páginas con/sin texto embebido.

### `paddleocr images`

Exporta páginas del PDF como imágenes PNG.

```bash
paddleocr images --path <pdf> [--pages 1,3,5] --output-dir ./pages [--dpi 300]
```

| Flag | Requerido | Default | Descripción |
|------|-----------|---------|-------------|
| `--path` | si | — | Ruta al archivo PDF |
| `--pages` | no | todas | Páginas a exportar |
| `--output-dir` | si | — | Directorio destino |
| `--dpi` | no | 300 | Resolución de las imágenes |

## Configuración PaddleOCR

Configuración validada por benchmark en documentos médicos colombianos:

- `lang='es'` — modelo de reconocimiento latino (soporta acentos y ñ)
- `text_det_limit_side_len=960` — lado máximo para detección
- Resize 1/2 antes de OCR — reduce memoria de 6GB+ a ~2.5GB estable

## Requisitos

- Python 3.10+
- ~8 GB RAM (PaddleOCR carga 5 modelos en memoria)
- ~600 MB disco (framework + modelos)
- No requiere GPU

## Rendimiento

- ~26s/página en 2 CPU cores
- ~2,200 caracteres/página promedio
- Primer ejecución descarga modelos (~136 MB), las siguientes usan cache

## Ejemplos de uso por agentes

```bash
# Obtener info rápida de un PDF
paddleocr info --path /path/to/document.pdf

# OCR de páginas específicas, resultado a stdout para procesar
paddleocr ocr --path /path/to/document.pdf --pages 1,3,5

# OCR de todo el documento, guardar en archivos
paddleocr ocr --path /path/to/document.pdf --output-dir ./extracted

# Extraer imágenes para inspección visual
paddleocr images --path /path/to/document.pdf --pages 1 --output-dir ./images
```
