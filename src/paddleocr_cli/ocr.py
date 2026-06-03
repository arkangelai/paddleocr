"""ONNX Runtime OCR wrapper with validated config from benchmark."""

import tempfile
from multiprocessing import Lock, Pool
from pathlib import Path

import cv2

from paddleocr_cli.pdf import pages_to_images

_ocr_instance = None
_init_lock = None


def _pool_initializer(lock):
    global _init_lock
    _init_lock = lock


def _get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        if _init_lock is not None:
            with _init_lock:
                if _ocr_instance is None:
                    from paddleocr_cli.onnx_ocr import OnnxOCR
                    _ocr_instance = OnnxOCR(
                        models_dir=str(Path(__file__).parent / "models")
                    )
        else:
            from paddleocr_cli.onnx_ocr import OnnxOCR
            _ocr_instance = OnnxOCR(
                models_dir=str(Path(__file__).parent / "models")
            )
    return _ocr_instance


def ocr_image(image_path: str | Path, temp_dir: str) -> str:
    ocr = _get_ocr()
    img = cv2.imread(str(image_path))
    h, w = img.shape[:2]
    img_small = cv2.resize(img, (w // 2, h // 2))
    result = ocr(img_small)
    if result is None:
        return ""
    lines = [item[1] for item in result]
    return "\n".join(lines)


def _worker_ocr_page(args: tuple) -> tuple[int, str]:
    image_path, page_num, temp_dir = args
    text = ocr_image(image_path, temp_dir=temp_dir)
    return (page_num, text)


def ocr_pages(pdf_path: str, pages: list[int], workers: int = 1) -> dict[int, str]:
    with tempfile.TemporaryDirectory(prefix="paddleocr_") as tmp_dir:
        image_paths = pages_to_images(pdf_path, pages, dpi=300, output_dir=tmp_dir)
        work_items = [(str(p), num, tmp_dir) for p, num in zip(image_paths, pages)]

        if workers <= 1:
            return {num: ocr_image(img, temp_dir=tmp_dir) for img, num, _ in work_items}

        lock = Lock()
        with Pool(processes=workers, initializer=_pool_initializer, initargs=(lock,)) as pool:
            results_list = pool.map(_worker_ocr_page, work_items)

        return dict(results_list)
