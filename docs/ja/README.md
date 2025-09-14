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

```bash
# PyPIからインストール（PDFサポートはデフォルトで含まれます）
pip install yomitoku-client

# GitHubから最新機能をインストール
pip install git+https://github.com/MLism-Inc/yomitoku-client.git@main
```

## クイックスタート

### ステップ1: Yomitoku ProからOCR結果を取得

まず、Yomitoku ProをデプロイしてOCR結果を取得する必要があります。詳細な手順は`yomitoku-pro-document-analyzer.ipynb`ノートブックを参照してください：

1. **Yomitoku Proのデプロイ**（CloudFormationまたはSageMaker Consoleを使用）
2. **エンドポイントの作成**と権限の設定
3. **文書のOCR分析**の実行
4. **構造化された結果**のJSON形式での取得

### ステップ2: Yomitoku Clientで結果を処理

Yomitoku ProからOCR結果を取得したら、Yomitoku Clientを使用して処理・変換します：

```python
from yomitoku_client import YomitokuClient

# クライアントを初期化
client = YomitokuClient()

# SageMaker出力をパース（Yomitoku Proから）
data = client.parse_file('sagemaker_output.json')

# 異なる形式に変換
csv_result = client.convert_to_format(data, 'csv')
html_result = client.convert_to_format(data, 'html')
markdown_result = client.convert_to_format(data, 'markdown')

# ファイルに保存
client.convert_to_format(data, 'csv', 'output.csv')
client.convert_to_format(data, 'html', 'output.html')
```

### ステップ3: 高度な処理と可視化

```python
# 強化された文書可視化
from yomitoku_client.visualizers import DocumentVisualizer

doc_viz = DocumentVisualizer()

# 要素関係の可視化
rel_img = doc_viz.visualize_element_relationships(
    image, results, 
    show_overlaps=True, 
    show_distances=True
)

# 要素階層の可視化
hierarchy_img = doc_viz.visualize_element_hierarchy(
    image, results, 
    show_containment=True
)

# 信頼度スコアの可視化
confidence_img = doc_viz.visualize_confidence_scores(
    image, ocr_results, 
    show_ocr_confidence=True
)
```

### ステップ4: 検索可能PDF生成

```python
from yomitoku_client.pdf_generator import SearchablePDFGenerator

# 画像とOCR結果から検索可能PDFを作成
pdf_generator = SearchablePDFGenerator()
pdf_generator.create_searchable_pdf(images, ocr_results, 'output.pdf')
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

MITライセンス - 詳細はLICENSEファイルを参照してください。

## お問い合わせ

ご質問やサポートについては：support-aws-marketplace@mlism.com
