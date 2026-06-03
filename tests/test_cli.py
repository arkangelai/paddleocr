import pytest
from click.testing import CliRunner
from paddleocr_cli.cli import main, _get_total_ram_gb, _warn_ram


class TestWorkersValidation:
    def test_rejects_zero(self, tiny_pdf):
        runner = CliRunner()
        result = runner.invoke(main, ["ocr", "--path", tiny_pdf, "--workers", "0"])
        assert result.exit_code != 0

    def test_rejects_negative(self, tiny_pdf):
        runner = CliRunner()
        result = runner.invoke(main, ["ocr", "--path", tiny_pdf, "--workers", "-1"])
        assert result.exit_code != 0

    def test_accepts_one(self, tiny_pdf, mock_ocr):
        runner = CliRunner()
        result = runner.invoke(main, ["ocr", "--path", tiny_pdf, "--pages", "1", "--workers", "1"])
        assert result.exit_code == 0


class TestRamDetection:
    def test_get_total_ram_returns_positive(self):
        ram = _get_total_ram_gb()
        assert ram is not None
        assert ram > 0

    def test_warn_ram_says_total(self, capsys):
        _warn_ram(999)
        captured = capsys.readouterr()
        assert "total" in captured.err


class TestPdfValidation:
    def test_rejects_nonexistent(self):
        runner = CliRunner()
        result = runner.invoke(main, ["ocr", "--path", "/nonexistent.pdf"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "File not found" in result.output

    def test_rejects_non_pdf(self, tmp_path):
        txt = tmp_path / "test.txt"
        txt.write_text("not a pdf")
        runner = CliRunner()
        result = runner.invoke(main, ["ocr", "--path", str(txt)])
        assert result.exit_code != 0
