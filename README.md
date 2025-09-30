# Yomitoku Client

<div align="center">

[![Language](https://img.shields.io/badge/🌐_English-blue?style=for-the-badge&logo=github)](docs/en/README.md) [![Language](https://img.shields.io/badge/🌐_日本語-red?style=for-the-badge&logo=github)](docs/ja/README.md)

**上記のボタンをクリックして、お好みの言語でドキュメントを表示してください**

</div>

---

## クイックリンク

- 📖 **[English Documentation](docs/en/README.md)** - 英語での完全ガイド
- 📖 **[日本語ドキュメント](docs/ja/README.md)** - 日本語での完全ガイド
- 📓 **[Notebook Guide (English)](docs/en/NOTEBOOK_GUIDE.md)** - ステップバイステップのノートブックチュートリアル（英語）
- 📓 **[ノートブックガイド (日本語)](docs/ja/NOTEBOOK_GUIDE.md)** - ステップバイステップのノートブックチュートリアル

Yomitoku Clientは、SageMaker Yomitoku APIの出力を処理し、包括的なフォーマット変換と可視化機能を提供するPythonライブラリです。Yomitoku ProのOCR分析と実用的なデータ処理ワークフローを橋渡しします。

## 主な機能

- **SageMaker統合**: Yomitoku Pro OCR結果のシームレスな処理
- **複数フォーマット対応**: CSV、Markdown、HTML、JSON、PDF形式への変換
- **検索可能PDF生成**: OCRテキストオーバーレイ付きの検索可能PDFの作成
- **高度な可視化**: 文書レイアウト分析、要素関係、信頼度スコア
- **ユーティリティ関数**: 矩形計算、テキスト処理、画像操作
- **Jupyter Notebook対応**: すぐに使える例とワークフロー

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
from yomitoku_client.parsers.sagemaker_parser import SageMakerParser

# SageMakerランタイムクライアントを初期化
sagemaker_runtime = boto3.client('sagemaker-runtime')
ENDPOINT_NAME = 'your-yomitoku-endpoint'

# パーサーを初期化
parser = SageMakerParser()

# 文書でSageMakerエンドポイントを呼び出し
with open('document.pdf', 'rb') as f:
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType='application/pdf',  # または 'image/png', 'image/jpeg'
        Body=f.read(),
    )

# レスポンスをパース
body_bytes = response['Body'].read()
sagemaker_result = json.loads(body_bytes)

# 構造化データに変換
data = parser.parse_dict(sagemaker_result)

print(f"ページ数: {len(data.pages)}")
print(f"ページ1の段落数: {len(data.pages[0].paragraphs)}")
print(f"ページ1のテーブル数: {len(data.pages[0].tables)}")
```

### ステップ2: データを異なる形式に変換

#### 単一ページ文書（画像）

```python
# 異なる形式に変換
data.pages[0].to_csv('output.csv')
data.pages[0].to_html('output.html')
data.pages[0].to_markdown('output.md')
data.pages[0].to_json('output.json')

# 画像から検索可能PDFを作成
data.to_pdf(output_path='searchable.pdf', img='document.png')
```

#### 複数ページ文書（PDF）

```python
# 全ページを変換（フォルダ構造を作成）
data.to_csv_folder('csv_output/')
data.to_html_folder('html_output/')
data.to_markdown_folder('markdown_output/')
data.to_json_folder('json_output/')

# 検索可能PDFを作成（既存のPDFに検索可能テキストを追加）
data.to_pdf(output_path='enhanced.pdf', pdf='original.pdf')

# または個別のページを変換
data.pages[0].to_csv('page1.csv')
data.pages[1].to_html('page2.html')
```

#### テーブルデータ抽出

```python
# 様々な形式でテーブルをエクスポート
data.pages[0].visualize_tables(
    output_folder='tables/',
    output_format='csv'    # または 'html', 'json', 'text'
)

# 複数ページ文書の場合
data.visualize_tables(
    output_folder='all_tables/',
    output_format='csv'
)
```

### ステップ3: 結果を可視化

#### OCRテキスト可視化

```python
# 検出されたテキストをバウンディングボックスで表示
result_img = data.pages[0].visualize(
    image_path='document.png',
    viz_type='ocr',
    output_path='ocr_visualization.png'
)
```

#### レイアウト分析可視化

```python
# 文書構造を表示（テキスト、テーブル、図）
result_img = data.pages[0].visualize(
    image_path='document.png',
    viz_type='layout_detail',
    output_path='layout_visualization.png'
)
```

#### PDF可視化

```python
# 特定のPDFページを可視化
result_img = data.pages[0].visualize(
    image_path='document.pdf',
    viz_type='layout_detail',
    output_path='pdf_visualization.png',
    page_index=0  # 可視化するページを指定
)
```

## サポート形式

- **CSV**: 適切なセル処理による表形式データのエクスポート
- **Markdown**: テーブルと見出しを含む構造化文書形式
- **HTML**: 適切なスタイリングを含むWeb対応形式
- **JSON**: 完全な文書構造を含む構造化データエクスポート
- **PDF**: OCRテキストオーバーレイ付きの検索可能PDF生成

## ライセンス

Apache License 2.0 - 詳細はLICENSEファイルを参照してください。

## お問い合わせ

ご質問やサポートについては: support-aws-marketplace@mlism.com