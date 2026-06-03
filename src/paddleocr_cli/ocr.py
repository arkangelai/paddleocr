"""PaddleOCR wrapper with validated config from benchmark."""

import tempfile
from multiprocessing import Lock, Pool
from pathlib import Path

from PIL import Image

from paddleocr_cli.pdf import page_to_image

_ocr_instance = None
_init_lock = None


def _pool_initializer(lock):
    global _init_lock
    _init_lock = lock


def _get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        if _init_lock is not None:
            _init_lock.acquire()
            try:
                from paddleocr import PaddleOCR
                _ocr_instance = PaddleOCR(lang="es", text_det_limit_side_len=960)
            finally:
                _init_lock.release()
        else:
            from paddleocr import PaddleOCR
            _ocr_instance = PaddleOCR(lang="es", text_det_limit_side_len=960)
    return _ocr_instance


def ocr_image(image_path: str | Path) -> str:
    ocr = _get_ocr()

    img = Image.open(image_path)
    img_small = img.resize((img.width // 2, img.height // 2))

    tmp_path = Path(tempfile.gettempdir()) / f"_paddleocr_resized_{Path(image_path).stem}.png"
    img_small.save(str(tmp_path))

    result = list(ocr.predict(str(tmp_path)))

    lines = []
    if result and "rec_texts" in result[0]:
        lines = result[0]["rec_texts"]

    return "\n".join(lines)


def _worker_ocr_page(args: tuple) -> tuple[int, str]:
    pdf_path, page_num = args
    with tempfile.TemporaryDirectory(prefix=f"paddleocr_w{page_num}_") as tmp_dir:
        img_path = page_to_image(pdf_path, page_num, dpi=300, output_dir=tmp_dir)
        text = ocr_image(img_path)
    return (page_num, text)


def ocr_pages(pdf_path: str, pages: list[int], workers: int = 1) -> dict[int, str]:
    if workers <= 1:
        results = {}
        with tempfile.TemporaryDirectory(prefix="paddleocr_") as tmp_dir:
            for page_num in pages:
                img_path = page_to_image(pdf_path, page_num, dpi=300, output_dir=tmp_dir)
                text = ocr_image(img_path)
                results[page_num] = text
        return results

    lock = Lock()
    work_items = [(pdf_path, p) for p in pages]
    with Pool(processes=workers, initializer=_pool_initializer, initargs=(lock,)) as pool:
        results_list = pool.map(_worker_ocr_page, work_items)

    return dict(results_list)
