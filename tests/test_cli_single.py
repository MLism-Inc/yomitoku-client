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
def sample_api_result():
    """
    API の中間 JSON（YomitokuClient.analyze の戻り値と同等）を読み込む。

    例: tests/data/image_pdf.json に保存しておく。
    """
    path = DATA_DIR / "image_pdf.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _patch_yomitoku_client(monkeypatch, sample_api_result):
    """
    single_command 内の YomitokuClient を、
    固定 JSON を返す FakeClient に差し替えるヘルパ。
    """

    sample = sample_api_result  # クロージャで capture

    class FakeClient:
        last_instance = None

        def __init__(
            self,
            endpoint,
            region=None,
            profile=None,
            max_workers: int = 4,
            request_config=None,
            circuit_config=None,
        ):
            self.endpoint = endpoint
            self.region = region
            self.profile = profile
            self.max_workers = max_workers
            self.request_config = request_config
            self.circuit_config = circuit_config
            self.analyze_calls = []
            FakeClient.last_instance = self

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def analyze(
            self,
            path_img,
            page_index=None,
            dpi=None,
            request_timeout=None,
            total_timeout=None,
        ):
            self.analyze_calls.append(
                {
                    "path_img": path_img,
                    "page_index": page_index,
                    "dpi": dpi,
                    "request_timeout": request_timeout,
                    "total_timeout": total_timeout,
                }
            )
            # 実際の SageMaker 呼び出しはせず、固定 JSON を返す
            return sample

    monkeypatch.setattr(single_module, "YomitokuClient", FakeClient)

    return FakeClient


@pytest.mark.parametrize(
    "file_format, ext",
    [
        ("json", "json"),
        ("csv", "csv"),
        ("html", "html"),
        ("md", "md"),
        ("pdf", "pdf"),
    ],
)
def test_single_command_each_format(
    monkeypatch,
    tmp_path: Path,
    runner,
    sample_api_result,
    file_format,
    ext,
):
    """
    file_format 別に single コマンドを叩き、
    - YomitokuClient.analyze が呼ばれる
    - 指定形式のファイルが出力される
    ことだけを確認する。
    """

    FakeClient = _patch_yomitoku_client(monkeypatch, sample_api_result)

    input_file = DATA_DIR / "image.pdf"
    output_dir = tmp_path / "out"

    result = runner.invoke(
        single_command,
        [
            str(input_file),
            "--endpoint",
            "test-endpoint",
            "--region",
            "ap-northeast-1",
            "--file_format",
            file_format,
            "--output_dir",
            str(output_dir),
            "--vis_mode",
            "none",
        ],
    )

    assert result.exit_code == 0, result.output

    # YomitokuClient.analyze が一度呼ばれていること
    client = FakeClient.last_instance
    assert client is not None
    assert client.endpoint == "test-endpoint"
    assert client.region == "ap-northeast-1"
    assert len(client.analyze_calls) == 1
    assert client.analyze_calls[0]["path_img"] == str(input_file)

    # 出力ファイルが存在すること
    expected_out = output_dir / f"{input_file.stem}.{ext}"
    assert expected_out.exists()


def test_single_command_with_pages_split_intermediate_and_advanced_options(
    monkeypatch,
    tmp_path: Path,
    runner,
    sample_api_result,
):
    """
    --pages / --split_mode / --ignore_line_break / --intermediate_save
    に加えて、各種タイムアウト・リトライ・サーキットブレーカ・workers が
    YomitokuClient に正しく渡されるかを検証する統合テスト。
    """

    FakeClient = _patch_yomitoku_client(monkeypatch, sample_api_result)

    input_file = DATA_DIR / "image.pdf"
    output_dir = tmp_path / "out"

    result = runner.invoke(
        single_command,
        [
            str(input_file),
            "--endpoint",
            "test-endpoint",
            "--region",
            "ap-northeast-1",
            "--file_format",
            "json,md,pdf,html,csv",
            "--output_dir",
            str(output_dir),
            "--split_mode",
            "separate",
            "--pages",
            "0-2",
            "--ignore_line_break",
            "--intermediate_save",
            "--vis_mode",
            "both",
            "--dpi",
            "150",
            "--request_timeout",
            "10",
            "--total_timeout",
            "30",
            "--workers",
            "8",
            "--read_timeout",
            "120",
            "--connect_timeout",
            "5",
            "--max_retries",
            "5",
            "--threthold_circuit",
            "3",
            "--cooldown_time",
            "60",
        ],
    )

    assert result.exit_code == 0, result.output

    client = FakeClient.last_instance
    assert client is not None
    assert len(client.analyze_calls) == 1
    analyze_kwargs = client.analyze_calls[0]

    # analyze に渡された値確認
    assert analyze_kwargs["path_img"] == str(input_file)
    assert analyze_kwargs["dpi"] == 150
    assert analyze_kwargs["request_timeout"] == 10
    assert analyze_kwargs["total_timeout"] == 30

    # YomitokuClient 生成時のパラメータ確認
    assert client.max_workers == 8
    assert client.request_config is not None
    assert client.circuit_config is not None

    # RequestConfig の中身を確認
    # ※ 型は実際の RequestConfig インスタンス
    assert client.request_config.read_timeout == 120
    assert client.request_config.connect_timeout == 5
    assert client.request_config.max_attempts == 5

    # CircuitConfig の中身を確認
    assert client.circuit_config.threshold == 3
    assert client.circuit_config.cooldown_sec == 60

    # CLI 内の intermediate_save ロジック:
    # output_dir/intermediate/{base_name}_{base_ext}.json
    base_name = input_file.stem  # image
    base_ext = input_file.suffix.lstrip(".")  # pdf
    intermediate_file = output_dir / "intermediate" / f"{base_name}_{base_ext}.json"
    assert intermediate_file.exists()

    # split_mode="separate" のときは base_name_page_{i}.{ext} が出力される想定
    for i in range(3):
        main_json = output_dir / f"{base_name}_page_{i}.json"
        assert main_json.exists()

        main_md = output_dir / f"{base_name}_page_{i}.md"
        assert main_md.exists()

        main_pdf = output_dir / f"{base_name}_page_{i}.pdf"
        assert main_pdf.exists()

        main_html = output_dir / f"{base_name}_page_{i}.html"
        assert main_html.exists()

        main_csv = output_dir / f"{base_name}_page_{i}.csv"
        assert main_csv.exists()

        vis_ocr = output_dir / f"{base_name}_ocr_page_{i}.jpg"
        assert vis_ocr.exists()

        vis_layout = output_dir / f"{base_name}_layout_page_{i}.jpg"
        assert vis_layout.exists()
