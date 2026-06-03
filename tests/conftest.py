import pytest
import pymupdf
from pathlib import Path
from unittest.mock import MagicMock

import paddleocr_cli.ocr as ocr_module


@pytest.fixture(autouse=True)
def _reset_ocr_singleton():
    ocr_module._ocr_instance = None
    ocr_module._init_lock = None
    yield
    ocr_module._ocr_instance = None
    ocr_module._init_lock = None


@pytest.fixture
def mock_ocr():
    mock = MagicMock()
    mock.predict.return_value = [{"rec_texts": ["mocked", "text"]}]
    ocr_module._ocr_instance = mock
    return mock


@pytest.fixture
def tiny_pdf(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    doc = pymupdf.open()
    for i in range(3):
        page = doc.new_page(width=200, height=200)
        page.insert_text((10, 50), f"Page {i + 1} content")
    doc.save(str(pdf_path))
    doc.close()
    return str(pdf_path)


@pytest.fixture
def sample_image(tmp_path):
    from PIL import Image
    img = Image.new("RGB", (200, 200), color="white")
    path = tmp_path / "test_image.png"
    img.save(str(path))
    return str(path)
