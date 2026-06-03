from unittest.mock import MagicMock

import pytest

from paddleocr_cli.ocr import ocr_image, ocr_pages
import paddleocr_cli.ocr as ocr_module


class TestOcrImage:
    def test_writes_resized_to_temp_dir(self, mock_ocr, sample_image, tmp_path):
        ocr_image(sample_image, temp_dir=str(tmp_path))
        resized = list(tmp_path.glob("_resized_*.png"))
        assert len(resized) == 1

    def test_resized_is_half_size(self, mock_ocr, sample_image, tmp_path):
        from PIL import Image
        ocr_image(sample_image, temp_dir=str(tmp_path))
        resized = list(tmp_path.glob("_resized_*.png"))[0]
        img = Image.open(resized)
        assert img.width == 100
        assert img.height == 100

    def test_returns_joined_text(self, mock_ocr, sample_image, tmp_path):
        result = ocr_image(sample_image, temp_dir=str(tmp_path))
        assert result == "mocked\ntext"

    def test_empty_result(self, sample_image, tmp_path):
        m = MagicMock()
        m.predict.return_value = [{}]
        ocr_module._ocr_instance = m
        result = ocr_image(sample_image, temp_dir=str(tmp_path))
        assert result == ""


class TestOcrPages:
    def test_sequential_returns_all_pages(self, mock_ocr, tiny_pdf):
        results = ocr_pages(tiny_pdf, [1, 2], workers=1)
        assert set(results.keys()) == {1, 2}
        assert all(isinstance(v, str) for v in results.values())

    def test_sequential_three_pages(self, mock_ocr, tiny_pdf):
        results = ocr_pages(tiny_pdf, [1, 2, 3], workers=1)
        assert len(results) == 3

    def test_single_page(self, mock_ocr, tiny_pdf):
        results = ocr_pages(tiny_pdf, [1], workers=1)
        assert results == {1: "mocked\ntext"}
