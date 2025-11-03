# Module Usage

YomiToku-Client は、Python コードから直接利用することができます。

## サンプルNoteBook
以下のリンクからGoogle Colab上ですぐに試せます
- https://colab.research.google.com/github/MLism-Inc/yomitoku-client/blob/main/notebooks/yomitoku-pro-document-analyzer.ipynb

## クイックスタート

最もシンプルな実行例です。PDF を入力し、解析結果を Markdown として保存します。

```python
from yomitoku_client import YomitokuClient, parse_pydantic_model

with YomitokuClient(endpoint="my-endpoint", region="ap-northeast-1") as client:
    result = client.analyze("notebooks/sample/image.pdf")

model = parse_pydantic_model(result)
model.to_markdown(output_path="output.md")
```

---

## 非同期実行

YomiToku-Client は **非同期処理** にも対応しており、エンドポイント呼び出しからフォーマット変換・保存までを非同期で実行できます。

内部では主に次のような処理を行っています。

* **自動コンテンツタイプ判定**：PDF / TIFF / PNG / JPEG を自動判別し、最適な形式で処理
* **ページ分割と非同期並列処理**：複数ページで構成される PDF・TIFF を自動的にページ分割し、各ページを並列推論
* **タイムアウト制御**：リクエスト単位・全体処理単位のタイムアウトと自動リトライ
* **サーキットブレーカー機能**：連続失敗時に一時停止し、エンドポイントを保護

```python
import asyncio
from yomitoku_client import YomitokuClient, parse_pydantic_model

ENDPOINT_NAME = "my-endpoint"
AWS_REGION = "ap-northeast-1"

target_file = "notebooks/sample/image.pdf"

async def main():
    async with YomitokuClient(
        endpoint=ENDPOINT_NAME,
        region=AWS_REGION,
    ) as client:
        result = await client.analyze_async(target_file)

    # フォーマット変換
    model = parse_pydantic_model(result)

    # CSV として保存
    model.to_csv(output_path="output.csv")

    # Markdown で保存（画像付き）
    model.to_markdown(
        output_path="output.md",
        image_path=target_file,
    )

    # ページごとに JSON を分割して保存
    model.to_json(
        output_path="output.json",
        mode="separate",
    )

    # 一部ページのみ HTML で保存（例：0ページ目と2ページ目）
    model.to_html(
        output_path="output.html",
        image_path=target_file,
        page_index=[0, 2],
    )

    # Searchable PDF の出力
    model.to_pdf(
        output_path="output.pdf",
        image_path=target_file,
    )

    # OCR 結果の可視化
    model.visualize(
        image_path=target_file,
        mode="ocr",
        page_index=None,
        output_directory="demo",
    )

    # レイアウト解析結果の可視化
    model.visualize(
        image_path=target_file,
        mode="layout",
        page_index=None,
        output_directory="demo",
    )

if __name__ == "__main__":
    asyncio.run(main())
```

---

## バッチ処理

YomiToku-Client は **バッチ処理** もサポートしており、安全かつ効率的に大量の文書を解析できます。

主な特徴：

* **フォルダ単位での一括解析**：指定ディレクトリ内の PDF・画像ファイルを自動検出し、並列処理を実行
* **中間ログ出力（`process_log.jsonl`）**：各ファイルの処理結果・成功可否・処理時間・エラー内容を 1 行ごとの JSON Lines 形式で記録
  → 後続処理や再実行管理に利用可能
* **上書き制御**：`overwrite=False` 設定で、既に解析済みのファイルをスキップ可能
* **再実行対応**：ログをもとに、失敗したファイルのみ再解析する運用が容易
* **ログを利用した後処理**：`process_log.jsonl` を読み込み、成功ファイルのみ Markdown 出力や可視化を自動実行

```python
import asyncio
import json
import os

from yomitoku_client import YomitokuClient, parse_pydantic_model

# 入出力設定
target_dir = "notebooks/sample"
outdir = "output"

# SageMaker エンドポイント設定
ENDPOINT_NAME = "my-endpoint"
AWS_REGION = "ap-northeast-1"

async def main():
    # バッチ解析の実行
    async with YomitokuClient(
        endpoint=ENDPOINT_NAME,
        region=AWS_REGION,
    ) as client:
        await client.analyze_batch_async(
            input_dir=target_dir,
            output_dir=outdir,
        )

    # ログから成功したファイルのみを処理
    log_path = os.path.join(outdir, "process_log.jsonl")
    with open(log_path, "r", encoding="utf-8") as f:
        logs = [json.loads(line) for line in f if line.strip()]

    out_markdown = os.path.join(outdir, "markdown")
    out_visualize = os.path.join(outdir, "visualization")

    os.makedirs(out_markdown, exist_ok=True)
    os.makedirs(out_visualize, exist_ok=True)

    for log in logs:
        if not log.get("success"):
            continue

        # 解析結果の JSON を読み込み
        with open(log["output_path"], "r", encoding="utf-8") as rf:
            result = json.load(rf)

        doc = parse_pydantic_model(result)

        # Markdown 出力
        base = os.path.splitext(os.path.basename(log["file_path"]))[0]
        doc.to_markdown(
            output_path=os.path.join(out_markdown, f"{base}.md"),
        )

        # 解析結果の可視化
        doc.visualize(
            image_path=log["file_path"],
            mode="ocr",
            output_directory=out_visualize,
            dpi=log.get("dpi", 200),
        )

if __name__ == "__main__":
    asyncio.run(main())
```