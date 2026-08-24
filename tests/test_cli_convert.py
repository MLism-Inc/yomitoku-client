import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from yomitoku_client.cli.convert import convert_command
from yomitoku_client.parser import parse_pydantic_model


@pytest.fixture
def batch_output():
    return {
        "result": [
            {
                "preprocess": {"angle": 0.0, "angle_score": 1.0},
                "paragraphs": [
                    {
                        "box": [0, 0, 100, 20],
                        "contents": "Test heading",
                        "direction": "horizontal",
                        "order": 0,
                        "role": "section_headings",
                        "indent_level": None,
                    }
                ],
                "tables": [],
                "words": [],
                "figures": [],
            }
        ]
    }


def test_parse_batch_output_without_num_page(batch_output):
    model = parse_pydantic_model(batch_output)
    assert model.pages[0].num_page == 0


def test_convert_batch_output_to_multiple_formats(tmp_path: Path, batch_output):
    input_path = tmp_path / "document.pdf.out"
    input_path.write_text(json.dumps(batch_output), encoding="utf-8")
    output_dir = tmp_path / "converted"

    result = CliRunner().invoke(
        convert_command,
        [
            str(input_path),
            "--format",
            "md,csv,html",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert (output_dir / "document.md").exists()
    assert (output_dir / "document.csv").exists()
    assert (output_dir / "document.html").exists()
    assert "Test heading" in (output_dir / "document.md").read_text()


def test_convert_does_not_overwrite_by_default(tmp_path: Path, batch_output):
    input_path = tmp_path / "document.pdf.out"
    input_path.write_text(json.dumps(batch_output), encoding="utf-8")
    output_path = tmp_path / "document.md"
    output_path.write_text("existing", encoding="utf-8")

    result = CliRunner().invoke(convert_command, [str(input_path)])

    assert result.exit_code != 0
    assert "--overwrite" in result.output
    assert output_path.read_text(encoding="utf-8") == "existing"
