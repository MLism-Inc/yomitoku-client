import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from yomitoku_client import parse_table_semantic_parser
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


@pytest.mark.parametrize("envelope", ["api", "combined", "page"])
@pytest.mark.parametrize("mode", ["structured", "simple", "raw"])
def test_convert_tsp_saved_json(tmp_path, envelope, mode):
    data = json.loads((Path(__file__).parent / "data/table_semantic.json").read_text())
    if envelope == "combined":
        data = data["result"]
    elif envelope == "page":
        data = data["result"][0]
    source = tmp_path / "document.pdf.out"
    source.write_text(json.dumps(data))
    output_dir = tmp_path / "converted"
    mode_options = [] if mode == "structured" else [f"--{mode}"]
    result = CliRunner().invoke(
        convert_command,
        [
            str(source),
            "--api",
            "table-semantic-parser",
            *mode_options,
            "-o",
            str(output_dir),
        ],
    )
    assert result.exit_code == 0, result.output
    page = json.loads((output_dir / "document.json").read_text())[0]
    if mode == "structured":
        assert page["tables"][0]["kv_items"][0]["value"] == "山田太郎"
    elif mode == "simple":
        assert page["tables"][0]["kv_items"]["氏名"] == "山田太郎"
    else:
        assert page["tables"][0]["cells"]["c0"]["contents"] == "氏 名"


def test_convert_tsp_template_and_separate_overwrite_protection(tmp_path):
    data = json.loads((Path(__file__).parent / "data/table_semantic.json").read_text())
    data["result"][0]["num_page"] = 3
    source = tmp_path / "document.out"
    source.write_text(json.dumps(data))
    template = (
        parse_table_semantic_parser(data)
        .pages[3]
        .to_template()
        .model_dump(exclude_none=True)
    )
    template["tables"][0]["cells"]["c0"]["contents"] = "名前"
    template_path = tmp_path / "template.json"
    template_path.write_text(json.dumps(template))
    output_dir = tmp_path / "converted"
    args = [
        str(source),
        "--api",
        "table-semantic-parser",
        "--split-mode",
        "separate",
        "--simple",
        "--template",
        str(template_path),
        "-o",
        str(output_dir),
    ]
    runner = CliRunner()
    result = runner.invoke(convert_command, args)
    assert result.exit_code == 0, result.output
    path = output_dir / "document_page_3.json"
    assert str(path) in result.output
    result = runner.invoke(convert_command, args)
    assert result.exit_code != 0
    assert "--overwrite" in result.output
    result = runner.invoke(convert_command, [*args, "--overwrite"])
    assert result.exit_code == 0, result.output
    assert json.loads(path.read_text())["tables"][0]["kv_items"]["名前"] == "山田太郎"


def test_convert_tsp_does_not_replace_source(tmp_path):
    source = tmp_path / "document.json"
    original = (Path(__file__).parent / "data/table_semantic.json").read_text()
    source.write_text(original)
    result = CliRunner().invoke(
        convert_command, [str(source), "--api", "table-semantic-parser", "--overwrite"]
    )
    assert result.exit_code != 0
    assert "--output-dir" in result.output
    assert source.read_text() == original


def test_convert_tsp_directory_skips_output_and_template(tmp_path):
    source = tmp_path / "document.json"
    source.write_text((Path(__file__).parent / "data/table_semantic.json").read_text())
    runner = CliRunner()
    args = [str(tmp_path), "--api", "table-semantic-parser"]
    result = runner.invoke(convert_command, args)
    assert result.exit_code == 0, result.output
    # A second run must not parse its own structured output as raw input.
    result = runner.invoke(convert_command, [*args, "--overwrite"])
    assert result.exit_code == 0, result.output
    assert result.output.count("document.json") == 1


def test_convert_reports_invalid_template(tmp_path):
    source = tmp_path / "document.out"
    source.write_text((Path(__file__).parent / "data/table_semantic.json").read_text())
    template = tmp_path / "template.json"
    template.write_text('{"meta": {"match_policy": "wrong"}, "tables": []}')
    result = CliRunner().invoke(
        convert_command,
        [
            str(source),
            "--api",
            "table-semantic-parser",
            "--template",
            str(template),
            "-o",
            str(tmp_path / "converted"),
        ],
    )
    assert result.exit_code != 0
    assert "Failed to export TSP result" in result.output
    assert "match_policy" in result.output
