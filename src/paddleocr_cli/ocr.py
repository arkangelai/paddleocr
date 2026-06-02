"""PaddleOCR wrapper with validated config from benchmark."""

import tempfile
from pathlib import Path

from PIL import Image

from paddleocr_cli.pdf import page_to_image

_ocr_instance = None


def _get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        from paddleocr import PaddleOCR
        _ocr_instance = PaddleOCR(lang="es", text_det_limit_side_len=960)
    return _ocr_instance


def ocr_image(image_path: str | Path) -> str:
    ocr = _get_ocr()

    img = Image.open(image_path)
    img_small = img.resize((img.width // 2, img.height // 2))

    tmp_path = Path(tempfile.gettempdir()) / "_paddleocr_resized.png"
    img_small.save(str(tmp_path))

    result = list(ocr.predict(str(tmp_path)))

    lines = []
    if result and "rec_texts" in result[0]:
        lines = result[0]["rec_texts"]

    return "\n".join(lines)


def ocr_pages(pdf_path: str, pages: list[int]) -> dict[int, str]:
    results = {}

    with tempfile.TemporaryDirectory(prefix="paddleocr_") as tmp_dir:
        for page_num in pages:
            img_path = page_to_image(pdf_path, page_num, dpi=300, output_dir=tmp_dir)
            text = ocr_image(img_path)
            results[page_num] = text

    return results
