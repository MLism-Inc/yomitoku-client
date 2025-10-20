# Yomitoku Client

<div align="center">

[![Language](https://img.shields.io/badge/🌐_English-blue?style=for-the-badge&logo=github)](README.en.md) [![Language](https://img.shields.io/badge/🌐_日本語-red?style=for-the-badge&logo=github)](README.md)

</div>

---

## クイックリンク
- 📓 **[AWS SageMakerの利用に関するサンプルNotebook](notebooks/yomitoku-pro-document-analyzer.ipynb)** - AWS SageMakerエンドポイントとの接続とドキュメント解析のチュートリアル
- 📓 **[結果のフォーマット変換と可視化に関するサンプルNotebook](notebooks/yomitoku-client-parser.ipynb)** - 処理結果の解析、フォーマット変換、可視化のチュートリアル

Yomitoku Clientは、SageMaker Yomitoku APIの出力を処理し、包括的なフォーマット変換と可視化機能を提供するPythonライブラリです。Yomitoku ProのOCR分析と実用的なデータ処理ワークフローを橋渡しを行います。

## 主な機能

- **SageMaker統合**: Yomitoku Pro OCR結果のシームレスな処理
- **複数フォーマット対応**: CSV、Markdown、HTML、JSON、PDF形式への変換
- **検索可能PDF生成**: OCRテキストオーバーレイ付きの検索可能PDFの作成
- **可視化機能**: 文書レイアウト分析、OCRの読み取り結果のレンダリング
- **Jupyter Notebook対応**: 迅速に使えるサンプルコードとワークフロー

## 変換のサポート形式

- **CSV**: 適切なセル処理による表形式データのエクスポート
- **Markdown**: テーブルと見出しを含む構造化文書形式
- **HTML**: 適切なスタイリングを含むWeb対応形式
- **JSON**: 完全な文書構造を含む構造化データエクスポート
- **PDF**: OCRテキストオーバーレイ付きの検索可能PDF生成

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

### ステップ1: SageMakerエンドポイントに接続

```python
import boto3
import json

# SageMakerランタイムクライアントを初期化
sagemaker_runtime = boto3.client('sagemaker-runtime')
ENDPOINT_NAME = 'your-yomitoku-endpoint'

# パーサーを初期化
parser = SageMakerParser()

# 文書でSageMakerエンドポイントを呼び出し
with open('document.png', 'rb') as f:
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType='image/png',  # または 'image/png', 'image/jpeg'
        Body=f.read(),
    )

# レスポンスをパース
body_bytes = response['Body'].read()
sagemaker_result = json.loads(body_bytes)
```

### ステップ2: データを異なる形式に変換

#### 単一ページ文書（画像）

```python
from yomitoku_client.parsers import parse_pydantic_model

# 構造化データに変換
data = parse_pydantic_model(sagemaker_result)

# 指定したファイル形式に変換
data.to_csv(output_path='output.csv')
data.to_html(output_path='output.html')
data.to_markdown(output_path='output.md')
data.to_json(output_path='output.json')
```

### ステップ3: 結果を可視化

#### 単一画像の可視化

```python
# OCRテキストの可視化
data.visualize(
    image_path='document.png',
    mode='ocr',
    page_index=None,
     utput_directory='demo'
)

# レイアウト詳細の可視化（テキスト、テーブル、図）
data.visualize(
    image_path='document.png',
    viz_type='layout',
    page_index=None,
    output_directory='demo'
)
```

#### 複数ページで構成されるPDFの一括可視化

```python
# 全ページのOCR結果を一括可視化
data.visualize(
    image_path="sample/image.pdf",
    mode='ocr',
    page_index=None,
    output_directory="demo",
    dpi=200
)

# 全ページのレイアウト解析情報を一括可視化
data.visualize(
    image_path="sample/image.pdf",
    mode='layout',
    page_index=None,
    output_directory="demo",
    dpi=200
)

# 特定のページのみ可視化
data.visualize(
    image_path="sample/image.pdf",
    mode='ocr',
    page_index=[0,1],
    output_directory="demo",
    dpi=200
)
```

## ライセンス

Apache License 2.0 - 詳細はLICENSEファイルを参照してください。

## お問い合わせ

ご質問やサポートについては: support-aws-marketplace@mlism.com