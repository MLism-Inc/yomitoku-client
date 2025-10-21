# Yomitoku Client

<div align="center">

[![Language](https://img.shields.io/badge/🌐_English-blue?style=for-the-badge&logo=github)](README.en.md) [![Language](https://img.shields.io/badge/🌐_日本語-red?style=for-the-badge&logo=github)](README.md)

</div>

---

## クイックリンク
- 📓 **[サンプルNotebook](notebooks/yomitoku-pro-document-analyzer.ipynb)** - AWS SageMakerエンドポイントとの接続とドキュメント解析のチュートリアル

Yomitoku Clientは、SageMaker Yomitoku APIの出力を処理し、包括的なフォーマット変換と可視化機能を提供するPythonライブラリです。Yomitoku ProのOCR分析と実用的なデータ処理ワークフローを橋渡しを行います。

## 主な機能
- **自動コンテンツタイプ判定**: PDF / TIFF / PNG / JPEG を自動認識し、最適な形式で処理。
- **ページ分割と非同期並列処理**: 複数ページで構成されるPDF・TIFFを自動でページ分割し、各ページを並列で推論。
- **タイムアウト・リトライ制御**: connect_timeout, read_timeout, total_timeout により通信・処理全体を安全に制御。一時的な失敗時は指数バックオフで自動リトライ。
- **再試行 & サーキットブレーカー機能**: 連続失敗時は一時停止してエンドポイントを保護。
- **堅牢なエラーハンドリング**: AWS通信エラー・JSONデコードエラー・タイムアウトなどを一元管理。
- **MFA対応の安全なAWS認証** : 一時セッショントークンによる安全なエンドポイント接続。
- **シンプルなインターフェース**: client("document.pdf") だけでページ分割・推論・結果統合を自動実行。
- **複数フォーマットへの変換対応**: CSV、Markdown、HTML、JSON、PDF形式への変換
- **検索可能PDF生成**: OCRテキストオーバーレイ付きの検索可能PDFの作成
- **可視化機能**: 文書レイアウト分析、OCRの読み取り結果のレンダリング
- **Jupyter Notebook対応**: 迅速に使えるサンプルコードとワークフロー

## インストール

### pipを使用
```bash
pip install yomitoku-client
```

### uvを使用（推奨）
```bash
uv add yomitoku-client
```

> **注意**: uvがインストールされていない場合は、以下でインストールできます：
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```

## クイックスタート

### Sagemaker Endpointの呼び出し
```python
from yomitoku_client import YomitokuClient

target_file = TARGET_FILE

with YomitokuClient(
    endpoint=ENDPOINT_NAME,
    region=AWS_REGION,
    mfa_serial=MFA_SERIAL,
    mfa_token=MFA_TOKEN,
) as client:
    result = client(target_file)
```

### 読み取り結果のフォーマット変換
```python
result.to_markdown(output_path="output.md")
result.to_csv(output_path="output.csv")
result.to_json(output_path='output.json')
result.to_html(output_path='output.html')
```

### 解析結果の可視化
```python
result.visualize(
    image_path=target_file,
    mode='ocr',
    page_index=None,
    output_directory="demo",
)

result.visualize(
    image_path=target_file,
    mode='layout',
    page_index=None,
    output_directory="demo",
)
```

## バッチ処理機能

YomiTokuClientはバッチ処理機能もサポートしており、安全かつ効率的に大量の文書を解析可能です。

### 機能の特長
- **フォルダ単位での一括解析** : 指定ディレクトリ内のPDF・画像ファイルを自動で検出し、並列処理を実行。
- **中間ログ出力（process_log.jsonl**: 各ファイルの処理結果・成功可否・処理時間・エラー内容を1行ごとに記録。（JSON Lines形式で出力され、後続処理や再実行管理に利用可能）
- **上書き制御**: 既に解析済みのファイルはスキップ（overwrite=False）設定で効率化。
- **ファイル名衝突防止**: 同一名で拡張子が異なるファイルも _pdf.json, _png.json として保存し、上書きを防止。
- **再実行対応**:  ログをもとに、失敗したファイルのみを再解析する運用が容易。
- **ログを利用した後処理**: process_log.jsonl を読み込み、成功ファイルのみMarkdown出力や可視化を自動実行可能

### サンプルコード
```python
import asyncio
import json
import os

from yomitoku_client import YomitokuClient
from yomitoku_client.parsers.sagemaker_parser import parse_pydantic_model

# 入出力設定
target_dir = "notebooks/sample"
outdir = "output"

# SageMakerエンドポイント設定
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

    # ログから成功したファイルを処理
    with open(os.path.join(outdir, "process_log.jsonl"), "r", encoding="utf-8") as f:
        logs = [json.loads(line) for line in f if line.strip()]

    out_markdown = os.path.join(outdir, "markdown")
    out_visualize = os.path.join(outdir, "visualization")

    os.makedirs(out_markdown, exist_ok=True)
    os.makedirs(out_visualize, exist_ok=True)

    for log in logs:
        if not log.get("success"):
            continue

        # 解析結果のJSONを読み込み
        with open(log["output_path"], "r", encoding="utf-8") as rf:
            result = json.load(rf)

        doc = parse_pydantic_model(result)

        # Markdown出力
        base = os.path.splitext(os.path.basename(log["file_path"]))[0]
        doc.to_markdown(output_path=os.path.join(out_markdown, f"{base}.md"))

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

## ライセンス

Apache License 2.0 - 詳細はLICENSEファイルを参照してください。

## お問い合わせ

ご質問やサポートについては: support-aws-marketplace@mlism.com