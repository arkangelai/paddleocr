import pytest
from paddleocr_cli.pdf import pages_to_images, resolve_pages


class TestResolvePages:
    def test_all_pages_when_none(self, tiny_pdf):
        pages = resolve_pages(tiny_pdf, None)
        assert pages == [1, 2, 3]

    def test_deduplicates(self, tiny_pdf):
        pages = resolve_pages(tiny_pdf, "1,1,2")
        assert pages == [1, 2]

    def test_sorts(self, tiny_pdf):
        pages = resolve_pages(tiny_pdf, "3,1,2")
        assert pages == [1, 2, 3]

    def test_deduplicates_and_sorts(self, tiny_pdf):
        pages = resolve_pages(tiny_pdf, "3,1,3,2,1")
        assert pages == [1, 2, 3]

    def test_range_syntax(self, tiny_pdf):
        pages = resolve_pages(tiny_pdf, "1-3")
        assert pages == [1, 2, 3]

    def test_out_of_range(self, tiny_pdf):
        with pytest.raises(ValueError, match="out of range"):
            resolve_pages(tiny_pdf, "5")


class TestPagesToImages:
    def test_requires_output_dir(self, tiny_pdf):
        with pytest.raises(ValueError, match="output_dir is required"):
            pages_to_images(tiny_pdf, [1], output_dir=None)

    def test_creates_all_files(self, tiny_pdf, tmp_path):
        out = tmp_path / "out"
        images = pages_to_images(tiny_pdf, [1, 2, 3], output_dir=str(out))
        assert len(images) == 3
        assert all(p.exists() for p in images)
        assert [p.name for p in images] == ["page_01.png", "page_02.png", "page_03.png"]

    def test_creates_output_dir(self, tiny_pdf, tmp_path):
        out = tmp_path / "nested" / "dir"
        pages_to_images(tiny_pdf, [1], output_dir=str(out))
        assert out.exists()

    def test_all_pages_when_none(self, tiny_pdf, tmp_path):
        out = tmp_path / "out"
        images = pages_to_images(tiny_pdf, None, output_dir=str(out))
        assert len(images) == 3
