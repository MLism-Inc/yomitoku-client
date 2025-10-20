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
- **タイムアウト制御**: connect_timeout, read_timeout, total_timeout により通信・処理全体を安全に制御。
- **再試行 & サーキットブレーカー機能**: 一時的な失敗を自動リトライし、連続失敗時は一時停止してエンドポイントを保護。
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
## ライセンス

Apache License 2.0 - 詳細はLICENSEファイルを参照してください。

## お問い合わせ

ご質問やサポートについては: support-aws-marketplace@mlism.com