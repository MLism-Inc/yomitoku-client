# Python API

YomiToku-Client は、Python コードから直接利用することができます。

## サンプルNotebook

以下のリンクからGoogle Colab上ですぐに試せます

<https://colab.research.google.com/github/MLism-Inc/yomitoku-client/blob/main/notebooks/yomitoku-pro-document-analyzer.ipynb>

Table Semantic Parser 版のNotebookは以下から試せます。

<https://colab.research.google.com/github/MLism-Inc/yomitoku-client/blob/main/notebooks/yomitoku-pro-table-semantic-parser.ipynb>

---

## Document Analyzer

文書解析APIのレスポンスは`parse_pydantic_model()`で読み込みます。
Markdown、CSV、HTML、JSON、Searchable PDFへの変換と、OCR・レイアウトの可視化を利用できます。

### クイックスタート

最もシンプルな実行例です。PDF を入力し、解析結果を Markdown として保存します。

```python
from yomitoku_client import YomitokuClient, parse_pydantic_model

with YomitokuClient(endpoint="my-endpoint", region="ap-northeast-1") as client:
    result = client.analyze("notebooks/sample/image.pdf")

model = parse_pydantic_model(result)
model.to_markdown(output_path="output.md")
```

---

### 非同期実行

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

### バッチ処理

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

---

## Table Semantic Parser

帳票の表構造を取得する場合は、Table Semantic Parser のエンドポイントを利用します。
エンドポイントの呼び出し方はDocument Analyzerと共通ですが、レスポンスの変換には`parse_table_semantic_parser()`を使います。

### 解析結果の読み込み

```python
from yomitoku_client import YomitokuClient, parse_table_semantic_parser

with YomitokuClient(endpoint="yomitoku-tsp", region="ap-northeast-1") as client:
    result = client.analyze("notebooks/sample/table.jpg")

model = parse_table_semantic_parser(result)

table = model.pages[0].tables[0]
print(table.find_cell_by_id("r0c0").contents)  # セルのテキスト
print(table.kv_items[0].key, table.kv_items[0].value)  # いずれもセルID

# Python APIのto_json()はrawが既定
model.to_json(output_path="table.raw.json")
```

出力例:

```text
利用情報
['r0c0', 'r1c0'] r1c1
```

`model.pages`はページ番号をキー、`TableSemanticParserResult`を値とする辞書です。
各ページの`cells`、`kv_items`、`grids`はrawスキーマで、Key-ValueとグリッドはセルのテキストではなくセルIDを参照します。

| クラス | 内容 |
| --- | --- |
| `MultiPageTableSemanticParserResult` | 文書全体。`pages`にページ番号とページ結果を保持 |
| `TableSemanticParserResult` | 1ページ分の`tables`、`paragraphs`、`words`、`num_page` |
| `SemanticTable` | 1つの表の`cells`、`kv_items`、`grids`、`box`、`style` |
| `SemanticCell` | セルのテキスト、役割、座標、行列位置 |
| `KvItem` | キーセルIDの配列と値セルID |
| `TableGrid` | 列ヘッダーとデータセルをセルIDで表したグリッド |

### raw・structured・simple

Python APIでは、用途に応じて3種類の表現を取得できます。

| API | 戻り値 | 用途 |
| --- | --- | --- |
| `page.to_json()` | `dict` | セル・単語・セルID参照を保持するraw |
| `page.to_structured()` | `StructuredDocumentSchema` | テキストと由来セルのID・座標を持つstructured |
| `page.to_simple()` | `SimpleDocumentSchema` | 座標などを除いたテキストのみのsimple |
| `model.to_structured()` | `dict[int, StructuredDocumentSchema]` | 全ページのstructured |
| `model.to_simple()` | `dict[int, SimpleDocumentSchema]` | 全ページのsimple |

```python
page = model.pages[0]

# 値と、その由来になったセルのID・座標を取得
structured = page.to_structured()
entry = structured.tables[0].kv_items[0]
print(entry.key, entry.value)
print(entry.key_cells, entry.value_cells)

# Key-Valueとグリッドをテキストだけで取得
simple = page.to_simple()
print(simple.tables[0].kv_items)
print(simple.tables[0].grids[0].rows[0])

# 同じキーセルに結び付いた複数値の区切り文字を変更
simple_with_custom_separator = page.to_simple(separator=" / ")
```

出力例:

```text
['利用情報', '施設名称'] MLism株式会社
[StructuredCellRefSchema(id='r0c0', box=[150, 500, 1499, 550]), StructuredCellRefSchema(id='r1c0', box=[150, 550, 364, 645])] [StructuredCellRefSchema(id='r1c1', box=[365, 550, 1499, 645])]
{'利用情報': {'施設名称': 'MLism株式会社', '利用目的': 'セミナー', '実施内容': 'YomiTokuの利用方法に関する説明会'}}
{'日付': '2025年01月30日(月曜日)', '入室時刻': '10時00分', '退室時刻': '17時00分'}
```

`structured`と`simple`では、同じキーセルに複数の値セルが結び付く場合、値を画像上の順序で並べ、既定では改行で結合します。
`simple`の変換規則は次のとおりです。

- 親子見出しを入れ子の辞書にします。
- 同じ階層に同名の別キーセルがある場合は配列にします。
- 親見出し自身の値と子見出しが共存する場合、親の値を`_value`へ格納します。
- キーのない単独セルは`_unkeyed`の配列へ格納します。
- グリッド行に同名の列見出しがある場合、`日付_0`、`日付_1`のように連番を付けます。

各形式のJSON例は[CLIの出力モード](cli-usage.md#tsp-output-formats)を参照してください。

### JSONへの保存

`MultiPageTableSemanticParserResult.to_json()`の`output_mode`で保存形式を指定します。
後方互換性のため、Python APIでは`output_mode`を省略すると`raw`を保存します。CLIの既定値は`structured`です。

```python
# raw：後から別形式へ変換できるよう解析情報を保管
model.to_json("table.raw.json")

# structured：CLIの既定出力と同じ
model.to_json("table.structured.json", output_mode="structured")

# simple：テキストのみ
model.to_json("table.simple.json", output_mode="simple")

# ページごとに別ファイルへ保存
model.to_json(
    "table.json",
    output_mode="structured",
    mode="separate",
)
```

`mode="combine"`ではページをJSON配列にまとめ、`mode="separate"`ではページごとに別ファイルへ保存します。
`structured`と`simple`は`cells`や`words`を省略するため、別形式へ再変換する可能性がある場合は`raw`も保存してください。

### テンプレートの保存と適用 {#tsp-template}

YomiToku-Pro互換のテンプレートをページ単位または文書単位で保存し、取得済みの解析結果へ適用できます。

```python
page = model.pages[0]

# 1ページのテンプレート
page.save_template_json("page.template.json")
page.load_template_json("page.template.json")

# 複数ページのテンプレート
model.save_template_json("document.template.json")
model.load_template_json("document.template.json")

# 適用後の結果をsimpleで保存
model.to_json("corrected.json", output_mode="simple")
```

テンプレートは`meta`と`tables`を持つYomiToku-Pro互換形式です。表は座標の重なりで照合し、セルは`meta.match_policy`の`cell_id`（既定）または`bbox`で照合します。
セルの`contents` / `role`、表の`kv_items` / `grids`を補正できます。省略または`null`の項目は変更せず、空文字列や空配列は上書きとして扱います。


### YomiToku Studioテンプレートの適用 {#studio-template-python}

YomiToku Studioの帳票解析画面から保存した`kind: "form-template"`のテンプレートは、`apply_studio_template_to_document()`でTable Semantic Parserの解析結果へ適用できます。バージョン2と3に対応しています。

```python
from yomitoku_client import (
    YomitokuClient,
    apply_studio_template_to_document,
    parse_table_semantic_parser,
)

image_path = "notebooks/sample/application.pdf"

with YomitokuClient(endpoint="yomitoku-tsp", region="ap-northeast-1") as client:
    result = client.analyze(image_path)

model = parse_table_semantic_parser(result)
apply_studio_template_to_document(
    model,
    template_path="templates/application.template.json",
    image_path=image_path,
    dpi=200,
)
model.to_json("application.simple.json", output_mode="simple")
```

テンプレートに保存された表・セル・Key-Value・グリッド・段落の構造へ、APIレスポンスのOCR単語を割り当てます。PDFでは解析時と同じ`dpi`を指定してください。OCRできなかった見出し（`header` / `group`）にはテンプレート作成時の文字を補いますが、値セルには作成時の値を補わず空文字にします。

テンプレートの検証や1ページ単位の適用には、トップレベルAPIの`load_studio_form_template()`と`apply_studio_form_template()`を利用できます。
