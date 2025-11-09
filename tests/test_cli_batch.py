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
    例: tests/data/sample_result.json に保存しておく。
    """
    path = DATA_DIR / "image_pdf.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _patch_process_batch(monkeypatch, sample_api_result):
    """
    batch_command 内で呼ばれる process_batch を差し替える。
    本物の API には行かず、代わりに:
      - output_dir/raw/{basename}.json に sample_api_result を保存
      - output_dir/process_log.jsonl を書き出す
    という動作だけを行う。
    """

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
    ):
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

    # 入力ディレクトリとファイルを準備
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

    # 実際に使われる拡張子は get_format_ext に合わせて取得
    ext = batch_module.get_format_ext(file_format)

    # 入力ファイルに対応する出力があるはず
    for name in ["image.pdf"]:
        base = Path(name).stem
        expected = out_formatted / f"{base}.{ext}"
        assert expected.exists()


def test_batch_command_with_pages_split_and_visualize(
    monkeypatch,
    tmp_path: Path,
    runner,
    sample_api_result,
):
    """
    --pages / --split_mode / --ignore_line_break / --vis_mode などを指定したとき、
    - 処理が最後まで通る
    - formatted / visualization がそれぞれ出力される
    ことを確認するテスト。
    """

    _patch_process_batch(monkeypatch, sample_api_result)

    input_dir = DATA_DIR
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()

    result = runner.invoke(
        batch_command,
        [
            "--input_dir",
            str(input_dir),
            "--output_dir",
            str(output_dir),
            "--endpoint",
            "test-endpoint",
            "--file_format",
            "json",
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
        ],
    )

    assert result.exit_code == 0, result.output

    out_formatted = output_dir / "formatted"
    out_visualize = output_dir / "visualization"

    ext = batch_module.get_format_ext("json")
    for i in range(3):
        main_json = out_formatted / f"image_page_{i}.{ext}"
        assert main_json.exists()

        vis_img = out_visualize / f"image_ocr_page_{i}.jpg"
        assert vis_img.exists()

        vis_img = out_visualize / f"image_layout_page_{i}.jpg"
        assert vis_img.exists()
