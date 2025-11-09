import asyncio
import json
from pathlib import Path

import pytest
from botocore.exceptions import BotoCoreError, ClientError

import yomitoku_client.client as client_module
from yomitoku_client.client import (
    CircuitConfig,
    InvokeResult,
    PagePayload,
    YomitokuClient,
    guess_content_type,
)
from yomitoku_client.exceptions import YomitokuInvokeError


def test_analyze_merges_pages_without_aws(monkeypatch, tmp_path: Path):
    """
    YomitokuClient.analyze / analyze_async を、
    実際の AWS API を一切叩かずにテストする。

    - _connect を無効化（boto3 を使わない）
    - load_image_bytes で 2 ページ分のダミー画像バイト列を返す
    - _ainvoke_one で InvokeResult を直接返す
    - 2 ページ分の結果が _merge_results でマージされて num_page が付くことを確認
    """

    # 1) AWS 接続処理を無効化（boto3.Session や describe_endpoint を呼ばせない）
    monkeypatch.setattr(YomitokuClient, "_connect", lambda self: None)

    # 2) 画像読み込み処理をモック
    #   path_img / content_type / dpi を受け取り、2 ページ分の bytes と content_type を返す
    def fake_load_image_bytes(path_img: str, content_type: str, dpi: int):
        # 2 ページ分のダミー画像バイト列
        return [b"page0-bytes", b"page1-bytes"], "image/png"

    monkeypatch.setattr(client_module, "load_image_bytes", fake_load_image_bytes)

    # 3) コンテントタイプ推定も簡単に固定
    monkeypatch.setattr(client_module, "guess_content_type", lambda path: "image/png")

    # 4) _ainvoke_one をモックして AWS を叩かない
    async def fake_ainvoke_one(self, payload, request_timeout=None):
        # analyze_async の中で使われるインタフェースに合わせて InvokeResult を返す
        raw = {
            "result": [
                {
                    "text": f"page{payload.index}",
                }
            ]
        }
        return InvokeResult(index=payload.index, raw_dict=raw)

    monkeypatch.setattr(YomitokuClient, "_ainvoke_one", fake_ainvoke_one)

    # 5) クライアント生成（AWS 接続はモックされているので安全）
    client = YomitokuClient(endpoint="dummy-endpoint", region="ap-northeast-1")

    # ダミーの入力ファイル（実際には読まれないが、存在だけさせておく）
    img_path = tmp_path / "dummy.png"
    img_path.write_bytes(b"dummy")

    # 6) 同期版 analyze() を叩く（内部で analyze_async が動く）
    result = client.analyze(str(img_path), dpi=200)

    # 7) マージ結果の検証
    assert "result" in result
    items = result["result"]
    assert len(items) == 2

    assert items[0]["text"] == "page0"
    assert items[0]["num_page"] == 0

    assert items[1]["text"] == "page1"
    assert items[1]["num_page"] == 1


def test_analyze_batch_async_without_aws(monkeypatch, tmp_path: Path):
    """
    analyze_batch_async を、実際の SageMaker / AWS API を呼ばずにテストする。

    - _connect を無効化
    - SUPPORT_INPUT_FORMAT をテスト用に絞る
    - analyze_async をモックして軽いダミー JSON を返す
    - バッチ実行後、output_dir に JSON と process_log.jsonl が生成されているか確認
    """

    # 1) AWS 接続を無効化
    monkeypatch.setattr(YomitokuClient, "_connect", lambda self: None)

    # 2) 対応拡張子をテストファイル用に制限
    monkeypatch.setattr(client_module, "SUPPORT_INPUT_FORMAT", ["pdf"])

    # 3) analyze_async をモック（AWS には行かない）
    async def fake_analyze_async(
        self,
        path_img: str,
        dpi: int = 200,
        page_index=None,
        request_timeout=None,
        total_timeout=None,
    ):
        # ここでは単純な JSON を返すだけ
        return {"file": path_img, "dpi": dpi}

    monkeypatch.setattr(YomitokuClient, "analyze_async", fake_analyze_async)

    # 4) 入力ディレクトリとファイルを準備
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    (input_dir / "a.pdf").write_text("dummy a")
    (input_dir / "b.pdf").write_text("dummy b")
    # 拾われない拡張子（念のため）
    (input_dir / "ignore.txt").write_text("ignored")

    output_dir = tmp_path / "outputs"
    output_dir.mkdir()

    # 5) クライアントを生成
    client = YomitokuClient(endpoint="dummy-endpoint", region=None)

    # 6) バッチ処理を実行（クラス内部の event loop で回す）
    client._loop.run_until_complete(
        client.analyze_batch_async(
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            dpi=150,
            overwrite=False,
        )
    )

    # 7) 出力ファイルの確認
    #   output_path = Path(output_dir) / f"{stem}_{ext}.json"
    out_a = output_dir / "a_pdf.json"
    out_b = output_dir / "b_pdf.json"
    assert out_a.exists()
    assert out_b.exists()

    # 中身も一応軽く確認
    data_a = json.loads(out_a.read_text(encoding="utf-8"))
    assert data_a["file"].endswith("a.pdf")
    assert data_a["dpi"] == 150

    # 8) ログの確認
    log_path = output_dir / "process_log.jsonl"
    assert log_path.exists()

    lines = log_path.read_text(encoding="utf-8").splitlines()
    # a.pdf, b.pdf の2行のはず
    assert len(lines) == 2

    records = [json.loads(line) for line in lines]
    paths = {Path(r["file_path"]).name for r in records}
    assert paths == {"a.pdf", "b.pdf"}
    for r in records:
        assert r["success"] is True
        assert r["executed"] is True
        assert r["error"] is None


@pytest.mark.asyncio
async def test_analyze_async_total_timeout(monkeypatch, tmp_path: Path):
    # boto3 接続をオフ
    monkeypatch.setattr(YomitokuClient, "_connect", lambda self: None)

    client = YomitokuClient(endpoint="dummy", region=None)

    # 画像読み込み → 1ページだけ返す
    def fake_load_image_bytes(path_img, content_type, dpi):
        return [b"page0"], "image/png"

    monkeypatch.setattr(client_module, "load_image_bytes", fake_load_image_bytes)
    monkeypatch.setattr(client_module, "guess_content_type", lambda p: "image/png")

    # _ainvoke_one を「遅いダミー」にする（1ページ処理に時間がかかる想定）
    async def slow_ainvoke_one(self, payload, request_timeout=None):
        await asyncio.sleep(0.05)
        return None

    monkeypatch.setattr(YomitokuClient, "_ainvoke_one", slow_ainvoke_one)

    # _record_failure をカウント
    failures = {"count": 0}

    def fake_record_failure(self):
        failures["count"] += 1

    monkeypatch.setattr(YomitokuClient, "_record_failure", fake_record_failure)

    img_path = tmp_path / "dummy.pdf"
    img_path.write_bytes(b"dummy")

    with pytest.raises(YomitokuInvokeError) as excinfo:
        await client.analyze_async(
            str(img_path),
            dpi=200,
            page_index=None,
            request_timeout=0.01,  # 各ページのタイムアウト
            total_timeout=0.02,  # 全体タイムアウト
        )

    msg = str(excinfo.value)
    assert "Analyze timeout" in msg
    assert failures["count"] == 1


@pytest.mark.asyncio
async def test_ainvoke_one_timeout_sets_failure_and_raises(monkeypatch):
    # boto3 接続は殺しておく
    monkeypatch.setattr(YomitokuClient, "_connect", lambda self: None)

    client = YomitokuClient(endpoint="dummy", region=None)

    # _record_failure が呼ばれたかをカウント
    failures = {"count": 0}

    def fake_record_failure(self):
        failures["count"] += 1

    monkeypatch.setattr(YomitokuClient, "_record_failure", fake_record_failure)

    # run_in_executor を「時間のかかるダミー」に差し替え
    def fake_run_in_executor(pool, func, arg):
        async def slow():
            # request_timeout より長く眠らせて、wait_for に timeout させる
            await asyncio.sleep(0.05)

        return asyncio.ensure_future(slow())

    monkeypatch.setattr(client._loop, "run_in_executor", fake_run_in_executor)

    payload = PagePayload(
        index=0,
        content_type="image/png",
        body=b"dummy",
        source_name="dummy.png",
    )

    # request_timeout=0.01s でタイムアウトさせる
    with pytest.raises(YomitokuInvokeError) as excinfo:
        await client._ainvoke_one(payload, request_timeout=0.01)

    msg = str(excinfo.value)
    assert "Request timeout for page 0" in msg
    assert failures["count"] == 1


@pytest.mark.parametrize(
    "path, expected",
    [
        ("document.pdf", "application/pdf"),
        ("image.PNG", "image/png"),
        ("photo.jpg", "image/jpeg"),
        ("photo.JPEG", "image/jpeg"),
        ("scan.tif", "image/tiff"),
        ("scan.TIFF", "image/tiff"),
    ],
)
def test_guess_content_type_valid_extensions(path, expected):
    """各拡張子で正しい Content-Type が返ることを確認"""
    assert guess_content_type(path) == expected


@pytest.mark.parametrize("path", ["unknown.txt", "data.bmp", "noext", "README"])
def test_guess_content_type_invalid_extensions(path):
    """未対応拡張子では ValueError が発生することを確認"""
    with pytest.raises(ValueError) as e:
        guess_content_type(path)
    assert "Unsupported file extension" in str(e.value)


def test_circuit_breaker_opens_after_threshold_and_blocks_requests(monkeypatch):
    # 1) _connect は殺して boto3 / describe_endpoint を呼ばせない
    monkeypatch.setattr(YomitokuClient, "_connect", lambda self: None)

    # 2) 時間を制御するために now_ms をモック
    fake_time = {"value": 0}

    def fake_now_ms():
        return fake_time["value"]

    monkeypatch.setattr(client_module, "now_ms", fake_now_ms)

    # 3) サーキット閾値を小さめ（3回）にしたクライアントを作る
    cfg = CircuitConfig(threshold=3, cooldown_time=10)
    client = YomitokuClient(
        endpoint="dummy-endpoint",
        region=None,
        circuit_config=cfg,
    )

    # 4) sagemaker_runtime.invoke_endpoint をモック
    class FakeRuntime:
        def __init__(self):
            self.calls = 0

        def invoke_endpoint(self, **kwargs):
            self.calls += 1
            # 毎回失敗させる
            raise BotoCoreError()

    fake_runtime = FakeRuntime()
    client.sagemaker_runtime = fake_runtime
    client.sagemaker = object()  # 使わないので適当でOK

    payload = PagePayload(
        index=0,
        content_type="image/png",
        body=b"dummy",
        source_name="dummy.png",
    )

    # 5) 閾値までは普通に invoke され、毎回 YomitokuInvokeError
    #   （内部では _record_failure が呼ばれ、3回目でサーキットオープン）
    for i in range(cfg.threshold):
        with pytest.raises(YomitokuInvokeError) as excinfo:
            client._invoke_one(payload)
        assert "AWS SDK error during invoke" in str(excinfo.value)

    # この時点で:
    # - invoke_endpoint は閾値回数だけ呼ばれている
    # - サーキットがオープンしている（_circuit_open_until > 現在時刻）
    assert fake_runtime.calls == cfg.threshold
    assert client._circuit_open_until > fake_time["value"]
    # 閾値到達後はカウンタリセット
    assert client._circuit_failures == 0

    # 6) サーキットオープン中のリクエストは _check_circuit で弾かれ、
    #    invoke_endpoint 自体は呼ばれない
    with pytest.raises(YomitokuInvokeError) as excinfo2:
        client._invoke_one(payload)

    msg = str(excinfo2.value)
    assert "Circuit open" in msg
    # サーキットオープン中なので、呼び出し回数は増えていないはず
    assert fake_runtime.calls == cfg.threshold
    # 失敗カウントも増えない
    assert client._circuit_failures == 0

    # 7) クールダウン時間後（時間を進める）に再度リクエストすると、
    #    ふたたび invoke_endpoint が呼ばれる（ただし今回も失敗する想定）
    fake_time["value"] = client._circuit_open_until + 1

    with pytest.raises(YomitokuInvokeError):
        client._invoke_one(payload)

    # インボーク回数が 1 回増えていること
    assert fake_runtime.calls == cfg.threshold + 1
    # 失敗カウントも 1 に戻っている（_record_failure が働いている）
    assert client._circuit_failures == 1


def _make_client_error(status_code: int) -> ClientError:
    return ClientError(
        error_response={
            "Error": {"Code": "xxx", "Message": "dummy"},
            "ResponseMetadata": {"HTTPStatusCode": status_code},
        },
        operation_name="InvokeEndpoint",
    )


@pytest.mark.parametrize(
    "status_code, should_count",
    [
        (429, True),
        (500, True),
        (502, True),
        (503, True),
        (504, True),
        (400, False),  # 4xx のうち 400 はカウントしない
        (403, False),
    ],
)
def test_record_failure_only_on_retryable_client_errors(
    monkeypatch, status_code, should_count
):
    monkeypatch.setattr(YomitokuClient, "_connect", lambda self: None)

    client = YomitokuClient(endpoint="dummy", region=None)

    # _record_failure をラップして呼び出し回数を見る
    calls = {"count": 0}

    def fake_record_failure(self):
        calls["count"] += 1

    monkeypatch.setattr(YomitokuClient, "_record_failure", fake_record_failure)

    class FakeRuntime:
        def invoke_endpoint(self, **kwargs):
            raise _make_client_error(status_code)

    client.sagemaker_runtime = FakeRuntime()
    client.sagemaker = object()

    payload = PagePayload(
        index=0,
        content_type="image/png",
        body=b"dummy",
        source_name="dummy.png",
    )

    with pytest.raises(YomitokuInvokeError) as excinfo:
        client._invoke_one(payload)

    # メッセージのフォーマットが想定通りか
    msg = str(excinfo.value)
    assert "SageMaker invoke failed" in msg

    # 429 / 5xx だけ _record_failure が呼ばれているか
    if should_count:
        assert calls["count"] == 1
    else:
        assert calls["count"] == 0
