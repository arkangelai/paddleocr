---
title: "feat: Add `paddleocr setup` command to automate ONNX model installation"
type: feat
status: active
date: 2026-06-03
---

# feat: Add `paddleocr setup` command

## Overview

Setting up the ONNX models requires 6 manual steps: installing paddle2onnx, running 5 separate conversion commands, and extracting a character dictionary. This blocks adoption and is error-prone. A single `paddleocr setup` command should automate the entire process.

## Problem Statement

The current model setup (README.md lines 43-98) requires users to:
1. Install `paddle2onnx>=2.0.1` separately (only works on Python ≤3.12)
2. Run `paddle2onnx` 5 times with specific flags for each model
3. Know the exact source paths at `~/.paddlex/official_models/`

If they skip this, `paddleocr ocr` fails with an opaque onnxruntime error about missing files.

## Proposed Solution

New Click subcommand `paddleocr setup` that:

1. Validates prerequisites (paddle2onnx installed, source models present)
2. Converts each missing model from PaddlePaddle format to ONNX
3. Reports progress and skip/success/failure per model
4. Is idempotent — safe to run multiple times

### Scope decisions

- **4 models, not 5**: Exclude UVDoc — `onnx_ocr.py` does not load it yet. Add when integration code exists.
- **Subprocess, not Python API**: Run `paddle2onnx` as a CLI subprocess for transparency and debuggability.
- **Editable install assumed**: Models write to `Path(__file__).parent / "models"` inside the package source. Non-editable installs from PyPI are out of scope.
- **No `--source-dir` in v1**: Hardcode `~/.paddlex/official_models/`. Add the option if requested.

### Models to convert

| Model | Size | Required | Source dir |
|-------|------|----------|------------|
| PP-OCRv5_server_det | 84 MB | Yes | `~/.paddlex/official_models/PP-OCRv5_server_det/` |
| latin_PP-OCRv5_mobile_rec | 7.7 MB | Yes | `~/.paddlex/official_models/latin_PP-OCRv5_mobile_rec/` |
| PP-LCNet_x1_0_doc_ori | 6.5 MB | No | `~/.paddlex/official_models/PP-LCNet_x1_0_doc_ori/` |
| PP-LCNet_x1_0_textline_ori | 6.5 MB | No | `~/.paddlex/official_models/PP-LCNet_x1_0_textline_ori/` |

All use the same conversion params: `--model_filename inference.json --params_filename inference.pdiparams --opset_version 17`.

## Acceptance Criteria

- [ ] `paddleocr setup` converts all 4 models from `~/.paddlex/official_models/` to `src/paddleocr_cli/models/*.onnx`
- [ ] Skips models whose ONNX file already exists (with message)
- [ ] `--force` flag reconverts even if ONNX files exist (recovery from corrupted files)
- [ ] If paddle2onnx is not installed: clear error with `pip install paddle2onnx>=2.0.1`
- [ ] If Python ≥3.13: warn that paddle2onnx may not work, suggest Python 3.12 venv
- [ ] If required source models missing: fail with clear message listing what's absent
- [ ] If optional source models missing: warn and skip, don't fail
- [ ] Atomic writes: convert to `.onnx.tmp`, rename to `.onnx` on success — prevents corrupted partial files
- [ ] Validate output file is >0 bytes after conversion
- [ ] Progress to stderr via `click.echo(..., err=True)` — no stdout output
- [ ] After successful setup, `paddleocr ocr --path doc.pdf` works immediately
- [ ] Update README.md: replace the manual "Model setup" section with `paddleocr setup`

## Technical Considerations

- **Where to add**: `src/paddleocr_cli/cli.py` as `@main.command()`, following existing pattern
- **Models dir**: Reuse `_MODELS_DIR` from `onnx_ocr.py` or compute the same path
- **paddle2onnx detection**: `shutil.which("paddle2onnx")` to check CLI availability
- **Conversion call**: `subprocess.run(["paddle2onnx", "--model_dir", ...], check=True)`
- **Dictionary**: `latin_v5_dict.txt` is already committed — no action needed
- **Tests**: Mock subprocess calls and file I/O in `tests/test_cli.py` using CliRunner

## Error messages

- No paddle2onnx: `"paddle2onnx not found. Install it: pip install paddle2onnx>=2.0.1"`
- Python ≥3.13 warning: `"Warning: paddle2onnx may not support Python 3.13+. Use a Python 3.12 environment if conversion fails."`
- Missing required source: `"Source model not found: ~/.paddlex/official_models/PP-OCRv5_server_det. Run PaddleOCR once with PaddlePaddle to download models, or see README."`
- Missing optional source: `"Skipping optional model PP-LCNet_x1_0_doc_ori (source not found)"`
- Conversion failure: `"Failed to convert PP-OCRv5_server_det: <paddle2onnx error>"`

## Follow-up (not in scope)

- Guard in `OnnxOCR.__init__` to suggest `paddleocr setup` when models are missing
- `--source-dir` option for custom PaddleX paths
- UVDoc model conversion (when integration code lands)
- Non-editable install support (models in `~/.paddleocr/models/`)

## Sources

- `src/paddleocr_cli/cli.py` — existing Click commands pattern
- `src/paddleocr_cli/onnx_ocr.py:14` — `_MODELS_DIR` definition
- `src/paddleocr_cli/onnx_ocr.py:332-357` — model loading, required vs optional logic
- `README.md:43-98` — current manual setup process
- `pyproject.toml:24-25` — entry point definition
- `.gitignore:13` — `*.onnx` already excluded
