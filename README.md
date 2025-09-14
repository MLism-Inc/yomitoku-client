# Yomitoku Client

<div align="center">

<button onclick="toggleLanguage()" style="background: linear-gradient(45deg, #007bff, #0056b3); color: white; border: none; padding: 10px 20px; border-radius: 25px; cursor: pointer; font-size: 16px; font-weight: bold; margin: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); transition: all 0.3s ease;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
  <span id="lang-button">🌐 日本語 / English</span>
</button>

</div>

<script>
let currentLang = 'en';

function toggleLanguage() {
  const englishSection = document.getElementById('english-section');
  const japaneseSection = document.getElementById('japanese-section');
  const langButton = document.getElementById('lang-button');
  
  if (currentLang === 'en') {
    englishSection.style.display = 'none';
    japaneseSection.style.display = 'block';
    langButton.textContent = '🌐 English / 日本語';
    currentLang = 'ja';
  } else {
    englishSection.style.display = 'block';
    japaneseSection.style.display = 'none';
    langButton.textContent = '🌐 日本語 / English';
    currentLang = 'en';
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
  const englishSection = document.getElementById('english-section');
  const japaneseSection = document.getElementById('japanese-section');
  
  if (englishSection && japaneseSection) {
    englishSection.style.display = 'block';
    japaneseSection.style.display = 'none';
  }
});
</script>

---

<div id="english-section">

## English

### Overview

Yomitoku Client is a Python library for processing SageMaker Yomitoku API outputs with comprehensive format conversion and visualization capabilities. It bridges the gap between Yomitoku Pro's OCR analysis and practical data processing workflows.

### Key Features

- **SageMaker Integration**: Seamlessly process Yomitoku Pro OCR results
- **Multiple Format Support**: Convert to CSV, Markdown, HTML, JSON, and PDF formats
- **Searchable PDF Generation**: Create searchable PDFs with OCR text overlay
- **Advanced Visualization**: Document layout analysis, element relationships, and confidence scores
- **Utility Functions**: Rectangle calculations, text processing, and image manipulation
- **Jupyter Notebook Support**: Ready-to-use examples and workflows

### Installation

```bash
# Install from PyPI (includes PDF support by default)
pip install yomitoku-client

# Install from GitHub (latest features)
pip install git+https://github.com/MLism-Inc/yomitoku-client.git@main
```

### Quick Start

#### Step 1: Get OCR Results from Yomitoku Pro

First, you need to deploy Yomitoku Pro and get OCR results. See the `yomitoku-pro-document-analyzer.ipynb` notebook for detailed instructions on:

1. **Deploying Yomitoku Pro** using CloudFormation or SageMaker Console
2. **Creating endpoints** and configuring permissions
3. **Running OCR analysis** on your documents
4. **Getting structured results** in JSON format

#### Step 2: Process Results with Yomitoku Client

Once you have OCR results from Yomitoku Pro, use Yomitoku Client to process and convert them:

```python
from yomitoku_client import YomitokuClient

# Initialize client
client = YomitokuClient()

# Parse SageMaker output (from Yomitoku Pro)
data = client.parse_file('sagemaker_output.json')

# Convert to different formats
csv_result = client.convert_to_format(data, 'csv')
html_result = client.convert_to_format(data, 'html')
markdown_result = client.convert_to_format(data, 'markdown')

# Save to files
client.convert_to_format(data, 'csv', 'output.csv')
client.convert_to_format(data, 'html', 'output.html')
```

#### Step 3: Advanced Processing and Visualization

```python
# Enhanced document visualization
from yomitoku_client.visualizers import DocumentVisualizer

doc_viz = DocumentVisualizer()

# Element relationships visualization
rel_img = doc_viz.visualize_element_relationships(
    image, results, 
    show_overlaps=True, 
    show_distances=True
)

# Element hierarchy visualization
hierarchy_img = doc_viz.visualize_element_hierarchy(
    image, results, 
    show_containment=True
)

# Confidence scores visualization
confidence_img = doc_viz.visualize_confidence_scores(
    image, ocr_results, 
    show_ocr_confidence=True
)
```

#### Step 4: Searchable PDF Generation

```python
from yomitoku_client.pdf_generator import SearchablePDFGenerator

# Create searchable PDF from images and OCR results
pdf_generator = SearchablePDFGenerator()
pdf_generator.create_searchable_pdf(images, ocr_results, 'output.pdf')
```

### Notebook Examples

#### 1. Yomitoku Pro Document Analyzer (`yomitoku-pro-document-analyzer.ipynb`)

This notebook shows how to:
- Deploy Yomitoku Pro service
- Configure SageMaker endpoints
- Run OCR analysis on documents
- Get structured JSON results

**Key sections:**
- Service deployment (CloudFormation/SageMaker Console)
- Endpoint configuration
- Document processing workflow
- Result extraction and validation

#### 2. Yomitoku Client Examples (`yomitoku-client-example.ipynb`)

This notebook demonstrates:
- Parsing SageMaker outputs
- Format conversion (CSV, HTML, Markdown, JSON)
- Document visualization
- Advanced processing workflows

**Key sections:**
- Client initialization and setup
- Sample data processing
- Multi-format conversion
- Visualization techniques
- Utility function usage

### Supported Formats

- **CSV**: Tabular data export with proper cell handling
- **Markdown**: Structured document format with tables and headings
- **HTML**: Web-ready format with proper styling
- **JSON**: Structured data export with full document structure
- **PDF**: Searchable PDF generation with OCR text overlay

### Command Line Interface

```bash
# Convert to different formats
yomitoku-client sagemaker_output.json --format csv --output result.csv
yomitoku-client sagemaker_output.json --format html --output result.html
yomitoku-client sagemaker_output.json --format markdown --output result.md
```

### Architecture

The library uses several design patterns:
- **Factory Pattern**: `RendererFactory` manages different format renderers
- **Strategy Pattern**: Different conversion strategies for each format
- **Adapter Pattern**: Handles different input formats from SageMaker

### Development

```bash
# Clone repository
git clone https://github.com/MLism-Inc/yomitoku-client
cd yomitoku-client

# Install dependencies
uv sync

# Run tests
uv run pytest
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### License

MIT License - see LICENSE file for details.

### Contact

For questions and support: support-aws-marketplace@mlism.com

</div>

---

<div id="japanese-section">

## 日本語

### 概要

Yomitoku Clientは、SageMaker Yomitoku APIの出力を処理し、包括的なフォーマット変換と可視化機能を提供するPythonライブラリです。Yomitoku ProのOCR分析と実用的なデータ処理ワークフローを橋渡しします。

### 主な機能

- **SageMaker統合**: Yomitoku Pro OCR結果のシームレスな処理
- **複数フォーマット対応**: CSV、Markdown、HTML、JSON、PDF形式への変換
- **検索可能PDF生成**: OCRテキストオーバーレイ付きの検索可能PDFの作成
- **高度な可視化**: 文書レイアウト分析、要素関係、信頼度スコア
- **ユーティリティ関数**: 矩形計算、テキスト処理、画像操作
- **Jupyter Notebook対応**: すぐに使える例とワークフロー

### インストール

```bash
# PyPIからインストール（PDFサポートはデフォルトで含まれます）
pip install yomitoku-client

# GitHubから最新機能をインストール
pip install git+https://github.com/MLism-Inc/yomitoku-client.git@main
```

### クイックスタート

#### ステップ1: Yomitoku ProからOCR結果を取得

まず、Yomitoku ProをデプロイしてOCR結果を取得する必要があります。詳細な手順は`yomitoku-pro-document-analyzer.ipynb`ノートブックを参照してください：

1. **Yomitoku Proのデプロイ**（CloudFormationまたはSageMaker Consoleを使用）
2. **エンドポイントの作成**と権限の設定
3. **文書のOCR分析**の実行
4. **構造化された結果**のJSON形式での取得

#### ステップ2: Yomitoku Clientで結果を処理

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

#### ステップ3: 高度な処理と可視化

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

#### ステップ4: 検索可能PDF生成

```python
from yomitoku_client.pdf_generator import SearchablePDFGenerator

# 画像とOCR結果から検索可能PDFを作成
pdf_generator = SearchablePDFGenerator()
pdf_generator.create_searchable_pdf(images, ocr_results, 'output.pdf')
```

### ノートブック例

#### 1. Yomitoku Pro Document Analyzer (`yomitoku-pro-document-analyzer.ipynb`)

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

#### 2. Yomitoku Client Examples (`yomitoku-client-example.ipynb`)

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

### サポート形式

- **CSV**: 適切なセル処理による表形式データのエクスポート
- **Markdown**: テーブルと見出しを含む構造化文書形式
- **HTML**: 適切なスタイリングを含むWeb対応形式
- **JSON**: 完全な文書構造を含む構造化データエクスポート
- **PDF**: OCRテキストオーバーレイ付きの検索可能PDF生成

### コマンドラインインターフェース

```bash
# 異なる形式に変換
yomitoku-client sagemaker_output.json --format csv --output result.csv
yomitoku-client sagemaker_output.json --format html --output result.html
yomitoku-client sagemaker_output.json --format markdown --output result.md
```

### アーキテクチャ

ライブラリはいくつかのデザインパターンを使用しています：
- **ファクトリーパターン**: `RendererFactory`が異なるフォーマットレンダラーを管理
- **ストラテジーパターン**: 各フォーマットの異なる変換戦略
- **アダプターパターン**: SageMakerからの異なる入力フォーマットを処理

### 開発

```bash
# リポジトリをクローン
git clone https://github.com/MLism-Inc/yomitoku-client
cd yomitoku-client

# 依存関係をインストール
uv sync

# テストを実行
uv run pytest
```

### コントリビューション

1. リポジトリをフォーク
2. フィーチャーブランチを作成
3. 変更を加える
4. 新機能のテストを追加
5. すべてのテストが通ることを確認
6. プルリクエストを送信

### ライセンス

MITライセンス - 詳細はLICENSEファイルを参照してください。

### お問い合わせ

ご質問やサポートについては：support-aws-marketplace@mlism.com

</div>