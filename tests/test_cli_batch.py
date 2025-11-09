# tests/test_cli_batch.py

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

import yomitoku_client.cli.batch as batch_module
from yomitoku_client.cli.batch import batch_command

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def sample_api_result():
    """
    API の中間 JSON（analyze / analyze_batch_async の出力と同じ構造）を読み込む。
    例: tests/data/image_pdf.json に保存しておく。
    """
    path = DATA_DIR / "image_pdf.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _patch_process_batch(monkeypatch, sample_api_result, record: dict | None = None):
    """
    batch_command 内で呼ばれる process_batch を差し替える。
    本物の API には行かず、代わりに:
      - output_dir/raw/{basename}.json に sample_api_result を保存
      - output_dir/process_log.jsonl を書き出す
    という動作だけを行う。

    record が与えられた場合は、CLI から渡ってきた引数を格納して検証に使う。
    """

    if record is None:
        record = {}

    async def fake_process_batch(
        input_dir,
        output_dir,
        endpoint,
        region,
        page_index,
        dpi,
        profile,
        request_timeout,
        total_timeout,
        workers,
        threthold_circuit,
        cooldown_time,
        read_timeout,
        connect_timeout,
        max_retries,
        overwrite,
    ):
        # 引数の内容を記録（高度なオプション検証用）
        record.update(
            dict(
                input_dir=input_dir,
                output_dir=output_dir,
                endpoint=endpoint,
                region=region,
                page_index=page_index,
                dpi=dpi,
                profile=profile,
                request_timeout=request_timeout,
                total_timeout=total_timeout,
                workers=workers,
                threthold_circuit=threthold_circuit,
                cooldown_time=cooldown_time,
                read_timeout=read_timeout,
                connect_timeout=connect_timeout,
                max_retries=max_retries,
                overwrite=overwrite,
            )
        )

        os.makedirs(output_dir, exist_ok=True)

        raw_dir = os.path.join(output_dir, "raw")
        os.makedirs(raw_dir, exist_ok=True)

        log_path = os.path.join(output_dir, "process_log.jsonl")

        with open(log_path, "w", encoding="utf-8") as log_f:
            file_path = os.path.join(input_dir, "image.pdf")
            base, _ = os.path.splitext(os.path.basename(file_path))
            raw_path = os.path.join(raw_dir, f"{base}.json")

            # 中間 JSON を保存
            with open(raw_path, "w", encoding="utf-8") as rf:
                json.dump(sample_api_result, rf)

            log = {
                "success": True,
                "output_path": raw_path,
                "file_path": file_path,
            }
            log_f.write(json.dumps(log) + "\n")

    # batch_command が参照している process_batch を差し替える
    monkeypatch.setattr(batch_module, "process_batch", fake_process_batch)

    return record


@pytest.mark.parametrize(
    "file_format",
    ["json", "csv", "html", "md", "pdf"],
)
def test_batch_command_each_format(
    monkeypatch, tmp_path: Path, runner, sample_api_result, file_format
):
    """
    batch コマンドを file_format ごとに叩き、
    - process_batch がモックとして中間結果＋ログを生成
    - その後の整形出力が output_dir/formatted/{base}.{ext} に出る
    ことを確認する。
    """

    _patch_process_batch(monkeypatch, sample_api_result)

    # 入力ディレクトリとファイルを準備（tests/data/image.pdf を想定）
    input_dir = DATA_DIR
    output_dir = tmp_path / "outputs"

    # CLI 実行（vis_mode=none にして visualize は無効化）
    result = runner.invoke(
        batch_command,
        [
            "--input_dir",
            str(input_dir),
            "--output_dir",
            str(output_dir),
            "--endpoint",
            "test-endpoint",
            "--region",
            "ap-northeast-1",
            "--file_format",
            file_format,
            "--vis_mode",
            "none",
        ],
    )

    assert result.exit_code == 0, result.output

    # batch_command 側で作られるディレクトリ
    out_formatted = output_dir / "formatted"
    out_visualize = output_dir / "visualization"

    assert out_formatted.exists()
    assert out_visualize.exists()

    # 実際の拡張子は file_format そのもの（json/csv/...）
    ext = file_format

    # 入力ファイルに対応する出力があるはず
    base = Path("image.pdf").stem
    expected = out_formatted / f"{base}.{ext}"
    assert expected.exists()


def test_batch_command_with_pages_split_visualize_and_advanced_options(
    monkeypatch,
    tmp_path: Path,
    runner,
    sample_api_result,
):
    """
    --pages / --split_mode / --ignore_line_break / --vis_mode に加えて、
    workers / timeout / retry / circuit / overwrite が
    process_batch に正しく渡されるかを確認するテスト。
    """

    record: dict = {}
    _patch_process_batch(monkeypatch, sample_api_result, record=record)

    input_dir = DATA_DIR
    output_dir = tmp_path / "outputs"

    result = runner.invoke(
        batch_command,
        [
            "--input_dir",
            str(input_dir),
            "--output_dir",
            str(output_dir),
            "--endpoint",
            "test-endpoint",
            "--region",
            "ap-northeast-1",
            "--file_format",
            "json,md,pdf,html,csv",
            "--split_mode",
            "separate",
            "--pages",
            "0-2",
            "--ignore_line_break",
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
            "--overwrite",
        ],
    )

    assert result.exit_code == 0, result.output

    # process_batch に渡されたパラメータを検証
    assert record["input_dir"] == str(input_dir)
    assert record["output_dir"] == str(output_dir)
    assert record["endpoint"] == "test-endpoint"
    assert record["region"] == "ap-northeast-1"
    assert record["dpi"] == 150
    assert record["request_timeout"] == 10
    assert record["total_timeout"] == 30
    assert record["workers"] == 8
    assert record["read_timeout"] == 120
    assert record["connect_timeout"] == 5
    assert record["max_retries"] == 5
    assert record["threthold_circuit"] == 3
    assert record["cooldown_time"] == 60
    assert record["overwrite"] is True

    out_formatted = output_dir / "formatted"
    out_visualize = output_dir / "visualization"

    assert out_formatted.exists()
    assert out_visualize.exists()

    base_name = "image"

    # split_mode="separate" のときは base_name_page_{i}.{ext} が出力される想定
    for i in range(3):
        main_json = out_formatted / f"{base_name}_page_{i}.json"
        assert main_json.exists()

        md_file = out_formatted / f"{base_name}_page_{i}.md"
        assert md_file.exists()

        pdf_file = out_formatted / f"{base_name}_page_{i}.pdf"
        assert pdf_file.exists()

        html_file = out_formatted / f"{base_name}_page_{i}.html"
        assert html_file.exists()

        csv_file = out_formatted / f"{base_name}_page_{i}.csv"
        assert csv_file.exists()

        vis_img = out_visualize / f"{base_name}_ocr_page_{i}.jpg"
        assert vis_img.exists()

        vis_img = out_visualize / f"{base_name}_layout_page_{i}.jpg"
        assert vis_img.exists()
