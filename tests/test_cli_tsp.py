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


@pytest.mark.parametrize("cells_format", ["dict", "list"])
def test_single_command_saves_json(
    monkeypatch,
    tmp_path: Path,
    runner,
    tsp_api_result,
    cells_format,
):
    if cells_format == "list":
        table = tsp_api_result["result"][0]["tables"][0]
        table["cells"] = list(table["cells"].values())
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
            "--raw",
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
    cells = saved[0]["tables"][0]["cells"]
    if cells_format == "list":
        assert isinstance(cells, list)
        assert cells[0]["contents"] == "氏 名"
    else:
        assert cells["c0"]["contents"] == "氏 名"


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


@pytest.mark.parametrize(
    "options, mode",
    [
        ([], "structured"),
        (["--simple"], "simple"),
        (["--raw"], "raw"),
    ],
)
def test_single_output_modes(
    monkeypatch, tmp_path, runner, tsp_api_result, options, mode
):
    _patch_yomitoku_client(monkeypatch, tsp_api_result)
    result = runner.invoke(
        single_command,
        [
            str(DATA_DIR / "image.pdf"),
            "-e",
            "test",
            "--api",
            "table-semantic-parser",
            "-o",
            str(tmp_path),
            *options,
        ],
    )
    assert result.exit_code == 0, result.output
    saved = json.loads((tmp_path / "image.json").read_text())[0]
    if mode == "structured":
        assert saved["tables"][0]["kv_items"][0]["key"] == ["氏名"]
        assert saved["tables"][0]["kv_items"][0]["value_cells"][0]["id"] == "c1"
    elif mode == "simple":
        assert saved["tables"][0]["kv_items"]["氏名"] == "山田太郎"
        assert saved["paragraphs"] == ["以上のとおり申請します。"]
    else:
        assert saved["tables"][0]["cells"]["c0"]["contents"] == "氏 名"


def test_single_rejects_conflicting_modes_before_inference(monkeypatch, runner):
    def unexpected_client(**_kwargs):
        pytest.fail("Invalid options should not invoke AWS")

    monkeypatch.setattr(single_module, "YomitokuClient", unexpected_client)
    result = runner.invoke(
        single_command,
        [
            str(DATA_DIR / "image.pdf"),
            "-e",
            "test",
            "--api",
            "table-semantic-parser",
            "--raw",
            "--simple",
        ],
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


def test_single_applies_template(monkeypatch, tmp_path, runner, tsp_api_result):
    from yomitoku_client import parse_table_semantic_parser

    page = parse_table_semantic_parser(tsp_api_result).pages[0]
    template = page.to_template()
    template.tables[0].cells["c0"].contents = "名前"
    template_path = tmp_path / "template.json"
    template_path.write_text(template.model_dump_json())
    _patch_yomitoku_client(monkeypatch, tsp_api_result)
    result = runner.invoke(
        single_command,
        [
            str(DATA_DIR / "image.pdf"),
            "-e",
            "test",
            "--api",
            "table-semantic-parser",
            "--simple",
            "--template",
            str(template_path),
            "-o",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    saved = json.loads((tmp_path / "image.json").read_text())[0]
    assert saved["tables"][0]["kv_items"]["名前"] == "山田太郎"


@pytest.mark.parametrize("options", [[], ["--simple"], ["--raw"]])
def test_batch_tsp_modes(monkeypatch, tmp_path, tsp_api_result, options):
    from tests.test_cli_batch import _patch_process_batch
    from yomitoku_client.cli.batch import batch_command

    _patch_process_batch(monkeypatch, tsp_api_result)
    result = CliRunner().invoke(
        batch_command,
        [
            "-i",
            str(DATA_DIR),
            "-o",
            str(tmp_path),
            "-e",
            "test",
            "--api",
            "table-semantic-parser",
            *options,
        ],
    )
    assert result.exit_code == 0, result.output
    saved = json.loads((tmp_path / "formatted/image.json").read_text())[0]
    if not options:
        assert saved["tables"][0]["kv_items"][0]["value"] == "山田太郎"
    elif "--simple" in options:
        assert saved["tables"][0]["kv_items"]["氏名"] == "山田太郎"
    else:
        assert saved["tables"][0]["cells"]["c0"]["contents"] == "氏 名"
