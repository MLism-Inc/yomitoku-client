# Yomitoku Client

## 概要

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

## ノートブック例

### 1. Yomitoku Pro Document Analyzer (`yomitoku-pro-document-analyzer.ipynb`)

このノートブックでは以下を説明しています：
- Yomitoku Proサービスのデプロイ
- SageMakerエンドポイントの設定
- 文書のOCR分析の実行
- 構造化されたJSON結果の取得

**主要セクション:**
- サービスデプロイ（CloudFormation/SageMaker Console）
- エンドポイント設定
- 文書処理ワークフロー
- 結果抽出と検証

### 2. Yomitoku Client Examples (`yomitoku-client-example.ipynb`)

このノートブックでは以下を実演しています：
- SageMaker出力のパース
- フォーマット変換（CSV、HTML、Markdown、JSON）
- 文書可視化
- 高度な処理ワークフロー

**主要セクション:**
- クライアント初期化とセットアップ
- サンプルデータ処理
- マルチフォーマット変換
- 可視化技術
- ユーティリティ関数の使用

## データ変換と可視化

### フォーマット変換

Yomitoku Clientは包括的なフォーマット変換機能を提供します：

```python
# 単一ページの変換
data.pages[0].to_csv('output.csv')
data.pages[0].to_html('output.html')
data.pages[0].to_markdown('output.md')
data.pages[0].to_json('output.json')

# 複数ページドキュメントの変換（フォルダ構造を作成）
data.to_csv_folder('csv_output/')
data.to_html_folder('html_output/')
data.to_markdown_folder('markdown_output/')
data.to_json_folder('json_output/')
```

### 検索可能PDF生成

OCRテキストオーバーレイを含む検索可能PDFを作成：

```python
# 画像から
data.to_pdf(output_path='searchable.pdf', img='document.png')

# PDFから（既存のPDFに検索可能テキストを追加）
data.to_pdf(output_path='enhanced.pdf', pdf='original.pdf')
```

### 可視化

バウンディングボックスとレイアウト分析でOCR結果を可視化：

```python
# OCRテキスト可視化
result_img = data.pages[0].visualize(
    image_path='document.png',
    viz_type='ocr',
    output_path='ocr_visualization.png'
)

# レイアウト詳細可視化（テキスト、テーブル、図）
result_img = data.pages[0].visualize(
    image_path='document.png',
    viz_type='layout_detail',
    output_path='layout_visualization.png'
)

# PDF可視化（ページインデックスを指定）
result_img = data.pages[0].visualize(
    image_path='document.pdf',
    viz_type='layout_detail',
    output_path='pdf_visualization.png',
    page_index=0
)
```

### テーブル処理

複数の形式でテーブルデータを抽出・可視化：

```python
# 様々な形式でテーブルをエクスポート
data.pages[0].visualize_tables(
    output_folder='tables/',
    output_format='csv'    # または 'html', 'json', 'text'
)

# 複数ページドキュメントの場合
data.visualize_tables(
    output_folder='all_tables/',
    output_format='csv'
)
```

## サポート形式

- **CSV**: 適切なセル処理による表形式データのエクスポート
- **Markdown**: テーブルと見出しを含む構造化文書形式
- **HTML**: 適切なスタイリングを含むWeb対応形式
- **JSON**: 完全な文書構造を含む構造化データエクスポート
- **PDF**: OCRテキストオーバーレイ付きの検索可能PDF生成

## コマンドラインインターフェース

```bash
# 異なる形式に変換
yomitoku-client sagemaker_output.json --format csv --output result.csv
yomitoku-client sagemaker_output.json --format html --output result.html
yomitoku-client sagemaker_output.json --format markdown --output result.md
```

## アーキテクチャ

ライブラリはいくつかのデザインパターンを使用しています：
- **ファクトリーパターン**: `RendererFactory`が異なるフォーマットレンダラーを管理
- **ストラテジーパターン**: 各フォーマットの異なる変換戦略
- **アダプターパターン**: SageMakerからの異なる入力フォーマットを処理

## 開発

```bash
# リポジトリをクローン
git clone https://github.com/MLism-Inc/yomitoku-client
cd yomitoku-client

# 依存関係をインストール
uv sync

# テストを実行
uv run pytest
```

## コントリビューション

1. リポジトリをフォーク
2. フィーチャーブランチを作成
3. 変更を加える
4. 新機能のテストを追加
5. すべてのテストが通ることを確認
6. プルリクエストを送信

## ライセンス

Apache License 2.0 - 詳細はLICENSEファイルを参照してください。

## お問い合わせ

ご質問やサポートについては：support-aws-marketplace@mlism.com
