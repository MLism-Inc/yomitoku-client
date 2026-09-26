"""
Tests for the --api table-semantic-parser path of the CLI
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

import yomitoku_client.cli.single as single_module
from yomitoku_client.cli.single import single_command

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def tsp_api_result():
    with (DATA_DIR / "table_semantic.json").open(encoding="utf-8") as f:
        return json.load(f)


def _patch_yomitoku_client(monkeypatch, sample_api_result):
    """single_command の YomitokuClient を固定 JSON を返すダミーに差し替える"""

    class FakeClient:
        def __init__(self, endpoint, region=None, profile=None, **kwargs):
            self.endpoint = endpoint
            self.region = region

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def analyze(self, img=None, **kwargs):
            return sample_api_result

    monkeypatch.setattr(single_module, "YomitokuClient", FakeClient)


def test_single_command_saves_json(
    monkeypatch,
    tmp_path: Path,
    runner,
    tsp_api_result,
):
    _patch_yomitoku_client(monkeypatch, tsp_api_result)

    input_file = DATA_DIR / "image.pdf"
    output_dir = tmp_path / "out"

    result = runner.invoke(
        single_command,
        [
            str(input_file),
            "--endpoint",
            "tsp-endpoint",
            "--api",
            "table-semantic-parser",
            "--file_format",
            "json",
            "--output_dir",
            str(output_dir),
            "--vis_mode",
            "none",
        ],
    )

    assert result.exit_code == 0, result.output

    saved = json.loads((output_dir / f"{input_file.stem}.json").read_text("utf-8"))
    assert saved[0]["tables"][0]["cells"]["c0"]["contents"] == "氏 名"


@pytest.mark.parametrize("file_format", ["csv", "md", "html", "pdf"])
def test_single_command_rejects_other_formats(
    monkeypatch,
    tmp_path: Path,
    runner,
    tsp_api_result,
    file_format,
):
    """TSP はレスポンスの JSON 保存のみに対応する"""
    _patch_yomitoku_client(monkeypatch, tsp_api_result)

    result = runner.invoke(
        single_command,
        [
            str(DATA_DIR / "image.pdf"),
            "--endpoint",
            "tsp-endpoint",
            "--api",
            "table-semantic-parser",
            "--file_format",
            file_format,
            "--output_dir",
            str(tmp_path / "out"),
            "--vis_mode",
            "none",
        ],
    )

    assert result.exit_code != 0
    assert "table-semantic-parser supports only" in result.output


def test_single_command_skips_visualization(
    monkeypatch,
    tmp_path: Path,
    runner,
    tsp_api_result,
):
    """可視化は未対応なので、既定の --vis_mode でもスキップして正常終了する"""
    _patch_yomitoku_client(monkeypatch, tsp_api_result)

    output_dir = tmp_path / "out"
    result = runner.invoke(
        single_command,
        [
            str(DATA_DIR / "image.pdf"),
            "--endpoint",
            "tsp-endpoint",
            "--api",
            "table-semantic-parser",
            "--output_dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Visualization is not supported" in result.output
    assert not list(output_dir.glob("*.jpg"))
