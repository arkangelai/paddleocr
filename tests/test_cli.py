import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
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


class TestSetupCommand:
    """Tests for the `paddleocr setup` command."""

    def test_fails_when_paddle2onnx_not_installed(self):
        runner = CliRunner()
        with patch("paddleocr_cli.cli.shutil.which", return_value=None):
            result = runner.invoke(main, ["setup"])
        assert result.exit_code != 0
        assert "paddle2onnx not found" in result.output

    def test_warns_python_313(self):
        runner = CliRunner()
        with patch("paddleocr_cli.cli.shutil.which", return_value="/usr/bin/paddle2onnx"), \
             patch("paddleocr_cli.cli.sys") as mock_sys, \
             patch("paddleocr_cli.cli._SOURCE_BASE") as mock_base:
            mock_sys.version_info = (3, 13, 0)
            # Make all source dirs missing so it fails on required models
            mock_base.__truediv__ = lambda self, x: Path("/nonexistent") / x
            result = runner.invoke(main, ["setup"])
        assert "Python 3.13" in result.output

    def test_skips_existing_onnx(self, tmp_path):
        """When ONNX files already exist, skip them (no --force)."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        source_base = tmp_path / "source"

        # Create all 4 source dirs and existing ONNX files
        for name, onnx_name, _ in [
            ("PP-OCRv5_server_det", "PP-OCRv5_server_det.onnx", True),
            ("latin_PP-OCRv5_mobile_rec", "latin_PP-OCRv5_mobile_rec.onnx", True),
            ("PP-LCNet_x1_0_doc_ori", "PP-LCNet_x1_0_doc_ori.onnx", False),
            ("PP-LCNet_x1_0_textline_ori", "PP-LCNet_x1_0_textline_ori.onnx", False),
        ]:
            (source_base / name).mkdir(parents=True)
            (models_dir / onnx_name).write_bytes(b"fake onnx data")

        runner = CliRunner()
        with patch("paddleocr_cli.cli._MODELS_DIR", models_dir), \
             patch("paddleocr_cli.cli._SOURCE_BASE", source_base), \
             patch("paddleocr_cli.cli.shutil.which", return_value="/usr/bin/paddle2onnx"):
            result = runner.invoke(main, ["setup"])

        assert result.exit_code == 0
        assert "already exists" in result.output
        assert "4 skipped" in result.output

    def test_converts_models_successfully(self, tmp_path):
        """Full happy-path: source dirs exist, no ONNX yet, conversion succeeds."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        source_base = tmp_path / "source"

        for name in [
            "PP-OCRv5_server_det",
            "latin_PP-OCRv5_mobile_rec",
            "PP-LCNet_x1_0_doc_ori",
            "PP-LCNet_x1_0_textline_ori",
        ]:
            (source_base / name).mkdir(parents=True)

        def fake_subprocess_run(cmd, **kwargs):
            """Write fake ONNX content to the --save_file path."""
            save_idx = cmd.index("--save_file") + 1
            save_path = Path(cmd[save_idx])
            save_path.write_bytes(b"fake onnx model content")
            return MagicMock(returncode=0)

        runner = CliRunner()
        with patch("paddleocr_cli.cli._MODELS_DIR", models_dir), \
             patch("paddleocr_cli.cli._SOURCE_BASE", source_base), \
             patch("paddleocr_cli.cli.shutil.which", return_value="/usr/bin/paddle2onnx"), \
             patch("paddleocr_cli.cli.subprocess.run", side_effect=fake_subprocess_run):
            result = runner.invoke(main, ["setup"])

        assert result.exit_code == 0
        assert "4 converted" in result.output
        # Verify final .onnx files exist (renamed from .tmp)
        assert (models_dir / "PP-OCRv5_server_det.onnx").exists()
        assert (models_dir / "latin_PP-OCRv5_mobile_rec.onnx").exists()

    def test_force_reconverts_existing(self, tmp_path):
        """With --force, reconvert even when ONNX files exist."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        source_base = tmp_path / "source"

        for name, onnx_name, _ in [
            ("PP-OCRv5_server_det", "PP-OCRv5_server_det.onnx", True),
            ("latin_PP-OCRv5_mobile_rec", "latin_PP-OCRv5_mobile_rec.onnx", True),
            ("PP-LCNet_x1_0_doc_ori", "PP-LCNet_x1_0_doc_ori.onnx", False),
            ("PP-LCNet_x1_0_textline_ori", "PP-LCNet_x1_0_textline_ori.onnx", False),
        ]:
            (source_base / name).mkdir(parents=True)
            (models_dir / onnx_name).write_bytes(b"old data")

        def fake_subprocess_run(cmd, **kwargs):
            save_idx = cmd.index("--save_file") + 1
            save_path = Path(cmd[save_idx])
            save_path.write_bytes(b"new onnx model content")
            return MagicMock(returncode=0)

        runner = CliRunner()
        with patch("paddleocr_cli.cli._MODELS_DIR", models_dir), \
             patch("paddleocr_cli.cli._SOURCE_BASE", source_base), \
             patch("paddleocr_cli.cli.shutil.which", return_value="/usr/bin/paddle2onnx"), \
             patch("paddleocr_cli.cli.subprocess.run", side_effect=fake_subprocess_run):
            result = runner.invoke(main, ["setup", "--force"])

        assert result.exit_code == 0
        assert "4 converted" in result.output
        # Verify content was replaced
        assert (models_dir / "PP-OCRv5_server_det.onnx").read_bytes() == b"new onnx model content"

    def test_fails_when_required_source_missing(self, tmp_path):
        """Missing required source model dirs should cause exit code 1."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        source_base = tmp_path / "source"
        source_base.mkdir(parents=True)

        runner = CliRunner()
        with patch("paddleocr_cli.cli._MODELS_DIR", models_dir), \
             patch("paddleocr_cli.cli._SOURCE_BASE", source_base), \
             patch("paddleocr_cli.cli.shutil.which", return_value="/usr/bin/paddle2onnx"):
            result = runner.invoke(main, ["setup"])

        assert result.exit_code != 0
        assert "required models" in result.output.lower()

    def test_skips_optional_source_missing(self, tmp_path):
        """Missing optional source models should warn and skip, not fail."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        source_base = tmp_path / "source"
        # Only create required source dirs
        (source_base / "PP-OCRv5_server_det").mkdir(parents=True)
        (source_base / "latin_PP-OCRv5_mobile_rec").mkdir(parents=True)

        def fake_subprocess_run(cmd, **kwargs):
            save_idx = cmd.index("--save_file") + 1
            save_path = Path(cmd[save_idx])
            save_path.write_bytes(b"fake onnx model content")
            return MagicMock(returncode=0)

        runner = CliRunner()
        with patch("paddleocr_cli.cli._MODELS_DIR", models_dir), \
             patch("paddleocr_cli.cli._SOURCE_BASE", source_base), \
             patch("paddleocr_cli.cli.shutil.which", return_value="/usr/bin/paddle2onnx"), \
             patch("paddleocr_cli.cli.subprocess.run", side_effect=fake_subprocess_run):
            result = runner.invoke(main, ["setup"])

        assert result.exit_code == 0
        assert "Skipping optional model" in result.output
        assert "2 converted" in result.output
        assert "2 skipped" in result.output

    def test_handles_conversion_failure(self, tmp_path):
        """When paddle2onnx fails for a required model, exit code 1."""
        import subprocess as real_subprocess

        models_dir = tmp_path / "models"
        models_dir.mkdir()
        source_base = tmp_path / "source"
        (source_base / "PP-OCRv5_server_det").mkdir(parents=True)
        (source_base / "latin_PP-OCRv5_mobile_rec").mkdir(parents=True)

        def fake_subprocess_run(cmd, **kwargs):
            raise real_subprocess.CalledProcessError(
                1, "paddle2onnx", stderr="conversion error"
            )

        runner = CliRunner()
        with patch("paddleocr_cli.cli._MODELS_DIR", models_dir), \
             patch("paddleocr_cli.cli._SOURCE_BASE", source_base), \
             patch("paddleocr_cli.cli.shutil.which", return_value="/usr/bin/paddle2onnx"), \
             patch("paddleocr_cli.cli.subprocess.run", side_effect=fake_subprocess_run):
            result = runner.invoke(main, ["setup"])

        assert result.exit_code != 0
        assert "Failed to convert" in result.output

    def test_cleans_up_tmp_on_failure(self, tmp_path):
        """Temp file should be cleaned up when conversion fails."""
        import subprocess as real_subprocess

        models_dir = tmp_path / "models"
        models_dir.mkdir()
        source_base = tmp_path / "source"
        (source_base / "PP-OCRv5_server_det").mkdir(parents=True)
        (source_base / "latin_PP-OCRv5_mobile_rec").mkdir(parents=True)

        def fake_subprocess_run(cmd, **kwargs):
            # Write a tmp file then raise to simulate partial write + failure
            save_idx = cmd.index("--save_file") + 1
            save_path = Path(cmd[save_idx])
            save_path.write_bytes(b"partial data")
            raise real_subprocess.CalledProcessError(
                1, "paddle2onnx", stderr="error"
            )

        runner = CliRunner()
        with patch("paddleocr_cli.cli._MODELS_DIR", models_dir), \
             patch("paddleocr_cli.cli._SOURCE_BASE", source_base), \
             patch("paddleocr_cli.cli.shutil.which", return_value="/usr/bin/paddle2onnx"), \
             patch("paddleocr_cli.cli.subprocess.run", side_effect=fake_subprocess_run):
            result = runner.invoke(main, ["setup"])

        # No .tmp files should remain
        tmp_files = list(models_dir.glob("*.tmp"))
        assert len(tmp_files) == 0
