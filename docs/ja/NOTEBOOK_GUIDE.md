# ノートブック使用ガイド

## 概要

このガイドでは、このリポジトリの2つの主要なノートブックを使用して、Yomitoku ProからOCR結果を取得し、Yomitoku Clientで処理する方法を説明します。

## ワークフロー概要

```
文書 → Yomitoku Pro → OCR結果 → Yomitoku Client → 処理済み出力
  ↓         ↓           ↓            ↓            ↓
PDF/画像  SageMaker  JSON形式    フォーマット変換  CSV/HTML/PDF
```

## ステップ1: OCR結果の取得 (`yomitoku-pro-document-analyzer.ipynb`)

このノートブックでは、Yomitoku Proをデプロイして文書からOCR結果を取得する方法を示しています。

### 前提条件

1. **AWSアカウント**（適切な権限付き）
2. **SageMaker FullAccess**権限（AWSユーザー/ロール用）
3. **Yomitoku Proサブスクリプション**（AWS Marketplaceから）

### デプロイオプション

#### オプションA: CloudFormationを使用（推奨）

1. **Yomitoku Proをサブスクライブ**（AWS Marketplaceから）
2. **CloudFormationスタックを起動**（製品ページから）
3. **パラメータを設定**:
   - スタック名: `yomitoku-pro-stack`
   - インスタンスタイプ: `ml.g4dn.xlarge`（推奨）
   - インスタンス数: `1`
4. **デプロイ完了を待つ**（通常10-15分）
5. **エンドポイント名を取得**（CloudFormation出力から）

#### オプションB: SageMaker Consoleを使用

1. **モデルを作成**:
   - AWS Marketplace → サブスクライブした製品 → 設定
   - 起動方法として「SageMaker Console」を選択
   - モデル名を設定（例：`my-yomitoku-model`）
   - SageMaker権限を持つIAMロールを設定

2. **エンドポイントを作成**:
   - モデルページを開く → エンドポイントを作成
   - エンドポイント名を設定（例：`my-yomitoku-endpoint`）
   - インスタンスタイプを選択：`ml.g4dn.xlarge`または`ml.g5.xlarge`
   - インスタンス数を設定：`1`

### OCR分析の実行

```python
import boto3
import json
import base64

# SageMakerクライアントを初期化
sagemaker_client = boto3.client('sagemaker-runtime')

# 文書を準備（PDFまたは画像）
with open('your_document.pdf', 'rb') as f:
    document_data = base64.b64encode(f.read()).decode('utf-8')

# リクエストペイロードを作成
payload = {
    "inputs": document_data,
    "parameters": {
        "max_length": 1024,
        "temperature": 0.1
    }
}

# Yomitoku Proエンドポイントにリクエストを送信
response = sagemaker_client.invoke_endpoint(
    EndpointName='your-endpoint-name',
    ContentType='application/json',
    Body=json.dumps(payload)
)

# レスポンスをパース
result = json.loads(response['Body'].read().decode('utf-8'))

# 次のステップのために結果を保存
with open('sagemaker_output.json', 'w') as f:
    json.dump(result, f, indent=2)
```

### 期待される出力形式

Yomitoku Proの出力は以下の形式になります：

```json
{
  "result": [
    {
      "paragraphs": [
        {
          "contents": "サンプルテキスト内容",
          "box": [x1, y1, x2, y2],
          "order": 1,
          "role": "paragraph"
        }
      ],
      "tables": [
        {
          "cells": [...],
          "box": [x1, y1, x2, y2],
          "order": 2,
          "n_row": 2,
          "n_col": 2
        }
      ],
      "figures": [...],
      "words": [...],
      "preprocess": {...}
    }
  ]
}
```

## ステップ2: 結果の処理 (`yomitoku-client-example.ipynb`)

このノートブックでは、Yomitoku Clientを使用してYomitoku ProのOCR結果を処理する方法を実演しています。

### 基本的なセットアップ

```python
from yomitoku_client import YomitokuClient
from yomitoku_client.parsers.sagemaker_parser import SageMakerParser
import json

# クライアントとパーサーを初期化
client = YomitokuClient()
parser = SageMakerParser()

# Yomitoku ProのOCR結果を読み込み
with open('sagemaker_output.json', 'r') as f:
    sagemaker_output = json.load(f)

# 結果をパース
parsed_data = parser.parse_dict(sagemaker_output)
```

### フォーマット変換例

#### 1. CSVに変換

```python
# CSV形式に変換
csv_result = client.convert_to_format(parsed_data, 'csv')

# ファイルに保存
with open('output.csv', 'w', encoding='utf-8') as f:
    f.write(csv_result)

print("CSV変換完了！")
```

#### 2. HTMLに変換

```python
# HTML形式に変換
html_result = client.convert_to_format(parsed_data, 'html')

# ファイルに保存
with open('output.html', 'w', encoding='utf-8') as f:
    f.write(html_result)

print("HTML変換完了！")
```

#### 3. Markdownに変換

```python
# Markdown形式に変換
markdown_result = client.convert_to_format(parsed_data, 'markdown')

# ファイルに保存
with open('output.md', 'w', encoding='utf-8') as f:
    f.write(markdown_result)

print("Markdown変換完了！")
```

#### 4. JSONに変換

```python
# 構造化JSONに変換
json_result = client.convert_to_format(parsed_data, 'json')

# ファイルに保存
with open('processed_output.json', 'w', encoding='utf-8') as f:
    f.write(json_result)

print("JSON変換完了！")
```

### 高度な可視化

```python
from yomitoku_client.visualizers import DocumentVisualizer
import cv2
import numpy as np

# 元の画像を読み込み
image = cv2.imread('your_document.png')

# ビジュアライザーを初期化
doc_viz = DocumentVisualizer()

# 1. 基本的なレイアウト可視化
layout_img = doc_viz.visualize((image, parsed_data[0]), type='layout_detail')
cv2.imwrite('layout_visualization.png', layout_img)

# 2. 読み順可視化
reading_order_img = doc_viz.visualize((image, parsed_data[0]), type='reading_order')
cv2.imwrite('reading_order.png', reading_order_img)

# 3. 要素関係
rel_img = doc_viz.visualize_element_relationships(
    image, parsed_data[0], 
    show_overlaps=True, 
    show_distances=True
)
cv2.imwrite('element_relationships.png', rel_img)

# 4. 要素階層
hierarchy_img = doc_viz.visualize_element_hierarchy(
    image, parsed_data[0], 
    show_containment=True
)
cv2.imwrite('element_hierarchy.png', hierarchy_img)

# 5. 信頼度スコア
confidence_img = doc_viz.visualize_confidence_scores(
    image, parsed_data[0], 
    show_ocr_confidence=True
)
cv2.imwrite('confidence_scores.png', confidence_img)
```

### 検索可能PDF生成

```python
from yomitoku_client.pdf_generator import SearchablePDFGenerator

# PDFジェネレーターを初期化
pdf_generator = SearchablePDFGenerator()

# 検索可能PDFを作成
pdf_generator.create_searchable_pdf(
    images=[image],  # 画像のリスト
    ocr_results=parsed_data,  # OCR結果
    output_path='searchable_output.pdf'
)

print("検索可能PDF作成完了！")
```

### ユーティリティ関数

```python
from yomitoku_client.utils import (
    calc_overlap_ratio, calc_distance, is_contained,
    escape_markdown_special_chars, table_to_csv
)

# 例：2つの要素間の重複を計算
element1_box = [100, 100, 200, 200]
element2_box = [150, 150, 250, 250]

overlap_ratio, intersection = calc_overlap_ratio(element1_box, element2_box)
print(f"重複率: {overlap_ratio:.2f}")

# 例：テーブルデータを処理
if parsed_data[0].tables:
    table = parsed_data[0].tables[0]
    csv_string = table_to_csv(table)
    print("テーブルをCSVとして:")
    print(csv_string)
```

### 完全なワークフロー例

```python
# 文書から処理済み出力までの完全なワークフロー
def process_document_with_yomitoku(document_path, endpoint_name):
    """
    完全なワークフロー: 文書 → Yomitoku Pro → Yomitoku Client → 出力
    """
    
    # ステップ1: Yomitoku ProからOCR結果を取得
    print("ステップ1: Yomitoku ProからOCR結果を取得中...")
    ocr_results = get_ocr_from_yomitoku_pro(document_path, endpoint_name)
    
    # ステップ2: Yomitoku Clientで処理
    print("ステップ2: Yomitoku Clientで処理中...")
    client = YomitokuClient()
    parsed_data = client.parse_dict(ocr_results)
    
    # ステップ3: 複数形式に変換
    print("ステップ3: 複数形式に変換中...")
    formats = ['csv', 'html', 'markdown', 'json']
    for format_type in formats:
        result = client.convert_to_format(parsed_data, format_type)
        with open(f'output.{format_type}', 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"✓ {format_type.upper()}変換完了")
    
    # ステップ4: 可視化を作成
    print("ステップ4: 可視化を作成中...")
    create_visualizations(document_path, parsed_data)
    
    # ステップ5: 検索可能PDFを生成
    print("ステップ5: 検索可能PDFを生成中...")
    generate_searchable_pdf(document_path, parsed_data)
    
    print("✓ 完全なワークフロー完了！")

# ワークフローを実行
process_document_with_yomitoku('your_document.pdf', 'your-endpoint-name')
```

### トラブルシューティング

#### よくある問題

1. **エンドポイントが見つからない**: SageMakerエンドポイントが「InService」状態か確認
2. **権限エラー**: AWS認証情報にSageMaker FullAccessがあるか確認
3. **インポートエラー**: yomitoku-clientが正しくインストールされているか確認
4. **メモリ問題**: より小さなインスタンスタイプを使用するか、文書をバッチで処理

#### ヘルプの取得

- ノートブックの出力で詳細なエラーメッセージを確認
- AWS CloudWatchログでSageMakerエンドポイントの問題を確認
- すべての依存関係が正しくインストールされているか確認
