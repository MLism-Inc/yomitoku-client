# 📋 Table Semantic Parser

**YomiToku-Pro - Table Semantic Parser (TSP)** は、申込書・請求書・報告書といった帳票から**表の意味構造**を抽出するAPIです。
枠線の有無によらず表のセルを直接検出し、次の情報を返します。

| フィールド | 内容 |
| --- | --- |
| `document_name` | 文書から検出したタイトル |
| `tables[].cells` | 検出したセル（`cell_id` をキーにした辞書）。テキスト・役割(header / cell / empty / group)・行列位置を持ちます |
| `tables[].kv_items` | 「項目名 → 値」の組。キー・値はセルIDで参照します |
| `tables[].grids` | 行・列のグリッド。列ヘッダーと各セルの配置をセルIDで持ちます |
| `paragraphs` | 表の外にある段落 |
| `words` | 単語単位のOCR結果 |

!!! note "文書解析API(Document Analyzer)との違い"
    エンドポイントの呼び出し方(リクエスト形式・対応ファイル形式・課金単位=ページ数)は文書解析APIと共通です。
    異なるのは**レスポンスの構造**だけです。
    APIはコンテナイメージに焼き込まれているため、1つのエンドポイントはどちらか一方のAPIを提供します。
    文書解析のエンドポイントと同時に立ち上げて共存させることができます。

!!! info "現在の対応範囲"
    YomiToku-Client は現時点で、**エンドポイントの呼び出しとレスポンスの取得・JSON保存**に対応しています。
    セルIDを解決した構造化データの取得、CSV / Markdown / HTML への変換、可視化は今後の対応です。

---

## エンドポイントの作成

Table Semantic Parserは文書解析APIとは**別のモデルパッケージ**です。サブスクライブ後の手順は
[SageMakerエンドポイントのデプロイ](deploy-yomitoku-pro.md)と同じで、Table Semantic ParserのModel Package ARNを指定します。

```bash
yomitoku-client sagemaker deploy \
  --product table-semantic-parser \
  --endpoint-name yomitoku-tsp \
  --model-package-arn arn:aws:sagemaker:ap-northeast-1:xxxxxxxxxxxx:model-package/xxxxxxxx
```

Lite版は通常版とは別のMarketplace製品です。Lite版を使う場合は、Lite版製品のModel Package ARNを指定します。

```bash
yomitoku-client sagemaker deploy \
  --product table-semantic-parser-lite \
  --endpoint-name yomitoku-tsp-lite \
  --model-package-arn arn:aws:sagemaker:ap-northeast-1:xxxxxxxxxxxx:model-package/xxxxxxxx
```

| `--product` | 対象製品 |
| --- | --- |
| `table-semantic-parser` | YomiToku-Pro - Table Semantic Parser（通常版） |
| `table-semantic-parser-lite` | YomiToku-Pro Lite - Table Semantic Parser（Lite版） |

!!! info "Model Package ARNの設定"
    `yomitoku-client sagemaker configure --product table-semantic-parser` でARNを設定ファイルに保存しておくと、
    以降は `--model-package-arn` を省略できます。製品ごとに保存されるので、通常版とLite版を併用できます。

!!! note "レスポンスは通常版とLite版で同じです"
    Lite版は軽量な認識モデルを使いますが、返すフィールドの構造は通常版と同じです。
    クライアント側の扱いに違いはありません。

---

## Python API

`YomitokuClient` は文書解析APIと共通です。取得した生JSONを `parse_table_semantic_parser()` でpydanticモデルに変換します。

```python
from yomitoku_client import YomitokuClient, parse_table_semantic_parser

with YomitokuClient(endpoint="yomitoku-tsp", region="ap-northeast-1") as client:
    result = client.analyze("sample/table.jpg")

model = parse_table_semantic_parser(result)

# レスポンスの構造を確認する
page = model.pages[0]
table = page.tables[0]
print(table.id, table.style, len(table.cells))
print(table.cells["c0"].contents, table.cells["c0"].role)
print(table.kv_items[0].key, "->", table.kv_items[0].value)  # いずれもセルID

# JSON として保存する（mode="separate" でページごとに分割）
model.to_json(output_path="table.json")
```

### モデル

| クラス | 対応するレスポンス |
| --- | --- |
| `MultiPageTableSemanticParserResult` | ドキュメント全体（`pages`: ページ番号 → ページ結果） |
| `TableSemanticParserResult` | 1ページ（`tables` / `paragraphs` / `words` / `num_page`） |
| `SemanticTable` | 1つの表（`cells` / `kv_items` / `grids` / `box` / `style`） |
| `SemanticCell`, `KvItem`, `TableGrid` | セル・キーバリュー項目・グリッド |

`kv_items` と `grids` はセルの**テキストではなくセルID**を参照します。テキストは `cells[cell_id].contents` から引きます。

正確なスキーマは、Table Semantic Parser API の OpenAPI 定義を参照してください。

---

## CLI

`--api table-semantic-parser` を指定すると、TSPのエンドポイントを扱えます(省略時は文書解析API)。
出力はAPIレスポンスそのままのJSONです。

```bash
# 単一ファイルの解析
yomitoku-client single sample/table.jpg \
    --api table-semantic-parser \
    -e yomitoku-tsp \
    -r ap-northeast-1 \
    -f json \
    -o output/

# フォルダ単位のバッチ解析
yomitoku-client batch \
    --api table-semantic-parser \
    -i sample/ \
    -o output/ \
    -e yomitoku-tsp \
    -f json
```

| オプション | 説明 |
| --- | --- |
| `-a, --api` | `document-analyzer`(既定) / `table-semantic-parser` |
| `-f, --file_format` | TSPでは `json` のみ対応（`csv` / `html` / `md` / `pdf` は非対応） |
| `-v, --vis_mode` | TSPでは可視化に未対応のためスキップされます |

---

## サンプルNotebook

Google Colab上ですぐに試せます。

<https://colab.research.google.com/github/MLism-Inc/yomitoku-client/blob/main/notebooks/yomitoku-pro-table-semantic-parser.ipynb>
