# 🖥️ CLI Usage

`YomiToku-Client` をインストールすると、専用の CLI コマンド `yomitoku-client` が使用できます。
SageMaker 上の YomiToku エンドポイントにアクセスし、ドキュメントの解析や結果変換を行います。

---

## Document Analyzer

文書解析APIを利用する場合は、`--api`を省略するか、`--api document-analyzer`を指定します。
JSONに加えて、CSV、HTML、Markdown、Searchable PDFへの変換と、OCR・レイアウトの可視化を利用できます。

### 🚀　ファイル単体の処理

指定したファイルを解析するためのコマンドです。
ファイルを処理し、解析結果を指定のフォーマットで出力します。

#### クイックスタート

```bash
yomitoku-client single ${path_file} -e ${endpoint_name} -r ${region} -f md -o demo
```

| 引数             | 説明                                                         |
| -------------- | ---------------------------------------------------------- |
| `${path_file}` | 解析対象のファイルパスを指定します。 *(必須)*                                  |
| `-e`           | SageMaker のエンドポイント名を指定します。 *(必須)*                          |
| `-r`           | AWS のリージョン名を指定します。                                         |
| `-a`           | エンドポイントが提供する API を指定します。<br>`document-analyzer`（既定） / `table-semantic-parser` |
| `-f`           | 出力フォーマットを指定します。<br>対応形式：`json`, `csv`, `html`, `md`, `pdf` |
| `-o`           | 解析結果を保存する出力先ディレクトリを指定します。                                  |

> **例**
>
> ```bash
> yomitoku-client single samples/demo.pdf \
>   -e yomitoku-endpoint \
>   -r ap-northeast-1 \
>   -f md \
>   -o output/
> ```

---

#### 🆘 ヘルプの参照

CLI の利用可能なオプションは、`--help` で確認できます。

```bash
yomitoku-client single --help
```

---

#### ⚙️ オプション詳細

| オプション                 | 型 / 値                                    | 説明                                                           |
| --------------------- | ---------------------------------------- | ------------------------------------------------------------ |
| `-e, --endpoint`      | `TEXT`                                   | **SageMaker のエンドポイント名（必須）**                                  |
| `-r, --region`        | `TEXT`                                   | AWS リージョン名（例：`ap-northeast-1`）                               |
| `-a, --api`           | `[document-analyzer / table-semantic-parser]` | エンドポイントが提供する API（既定：`document-analyzer`）<br>`table-semantic-parser` の出力は `json` のみ |
| `-f, --file_format`   | `TEXT（カンマ区切りで複数指定可）`<br>例：`json,csv,pdf` | 解析結果の出力フォーマット（`json` / `csv` / `html` / `md` / `pdf`）を複数指定可能 |
| `-o, --output_dir`    | `PATH`                                   | 解析結果を保存するディレクトリパス                                            |
| `--dpi`               | `INTEGER`                                | 画像解析時の解像度（DPI）                                               |
| `-p, --profile`       | `TEXT`                                   | 使用する AWS CLI プロファイル名                                         |
| `--request_timeout`   | `FLOAT`                                  | 各リクエスト単位のタイムアウト（秒）                                           |
| `--total_timeout`     | `FLOAT`                                  | 全体処理のタイムアウト（秒）                                               |
| `-v, --vis_mode`      | `[both / ocr / layout / none]`           | 出力画像の可視化モード<br>（OCR結果 / レイアウト / 両方 / なし）<br>`table-semantic-parser` では未対応のためスキップ |
| `-s, --split_mode`    | `[combine / separate]`                   | 出力ファイルの分割モード<br>（1つにまとめる / ページごとに分割）                         |
| `--ignore_line_break` | *(flag)*                                 | テキスト抽出時に改行を無視する                                              |
| `--pages`             | `TEXT`                                   | 解析対象ページを指定（例：`0,1,3-5`）                                      |
| `--intermediate_save` | *(flag)*                                 | 中間生成物（RAW JSON）を保存する                                         |
| `--workers`           | `INTEGER`                                | 並列処理に使用するワーカー数（デフォルト: 4）                                |
| `--threthold_circuit` | `INTEGER`                                | サーキットブレーカーの失敗閾値（例：5）                                         |
| `--cooldown_time`     | `INTEGER`                                | サーキットブレーカーのクールダウン時間（秒）                                       |
| `--read_timeout`      | `INTEGER`                                | HTTPリクエストの読み取りタイムアウト（秒）                                      |
| `--connect_timeout`   | `INTEGER`                                | HTTPリクエストの接続タイムアウト（秒）                                        |
| `--max_retries`       | `INTEGER`                                | HTTPリクエストの最大再試行回数                                            |
| `--help`              | *(flag)*                                 | ヘルプを表示して終了する                                                 |


---

#### 💡 Tips

!!! tip "よく使う組み合わせ"
    - Markdown 形式とCSVで解析結果を保存する：
    `yomitoku-client single invoice.pdf -e yomitoku-endpoint -f md,csv`
    - OCR 結果を PDF に埋め込み可視化する：
    `yomitoku-client single report.pdf -e yomitoku-endpoint -f pdf -v both`
    - 中間JSONも同時に保存する：
    `yomitoku-client single form.png -e yomitoku-endpoint -f csv --intermediate_save`
    - 特定ページのみを解析：
    `yomitoku-client single book.pdf -e yomitoku-endpoint --pages "1,2-5"`
---

#### 🧾 補足

* AWS CLI の設定済み環境で実行することを推奨します。
* 出力ディレクトリ（`-o`）が存在しない場合、自動で作成されます。
* CLI の戻り値は解析結果ファイルのパスを返します。
* `--intermediate_save` を指定すると、内部処理のRAW JSONを同ディレクトリ内に保存します。
* 高解像度処理を行う場合は、`--dpi 300` などを指定することでOCR精度が向上します。

---

### 🚀　バッチ処理（ディレクトリ一括解析）

複数ファイルを一括解析するための バッチ処理コマンドです。
指定したディレクトリ内のファイルを順次処理し、解析結果を指定のフォーマットで出力します。

#### クイックスタート

```bash
yomitoku-client batch -i ${input_dir} -o ${output_dir} -e ${endpoint_name} -r ${region} -f md
```

| 引数                  | 説明                                                         |
| ------------------- | ---------------------------------------------------------- |
| `-i, --input_dir`   | 解析対象のファイルを含むディレクトリのパスを指定します。 *(必須)*                        |
| `-o, --output_dir`  | 解析結果を保存するディレクトリを指定します。 *(必須)*                              |
| `-e, --endpoint`    | SageMaker のエンドポイント名を指定します。 *(必須)*                          |
| `-r, --region`      | AWS のリージョン名を指定します。                                         |
| `-a, --api`         | エンドポイントが提供する API を指定します。<br>`document-analyzer`（既定） / `table-semantic-parser` |
| `-f, --file_format` | 出力フォーマットを指定します。<br>対応形式：`json`, `csv`, `html`, `md`, `pdf` |

> **例**
>
> ```bash
> yomitoku-client batch \
>   -i ./samples \
>   -o ./results \
>   -e yomitoku-endpoint \
>   -r ap-northeast-1 \
>   -f md
> ```

---

#### 🆘 ヘルプの参照

CLI の利用可能なオプションは、`--help` で確認できます。

```bash
yomitoku-client batch --help
```

---

#### ⚙️ オプション詳細

| オプション                 | 型 / 値                                    | 説明                                                      |
| --------------------- | ---------------------------------------- | ------------------------------------------------------- |
| `-i, --input_dir`     | `PATH`                                   | **解析対象ファイルを含む入力ディレクトリのパス（必須）**                          |
| `-o, --output_dir`    | `PATH`                                   | **解析結果を保存する出力先ディレクトリのパス（必須）**                           |
| `-e, --endpoint`      | `TEXT`                                   | **SageMaker のエンドポイント名（必須）**                             |
| `-r, --region`        | `TEXT`                                   | AWS リージョン名（例：`ap-northeast-1`）                          |
| `-a, --api`           | `[document-analyzer / table-semantic-parser]` | エンドポイントが提供する API（既定：`document-analyzer`）<br>`table-semantic-parser` の出力は `json` のみ |
| `-f, --file_format`   | `TEXT（カンマ区切りで複数指定可）`<br>例：`json,csv,pdf` | 出力フォーマット（`json` / `csv` / `html` / `md` / `pdf`）を複数指定可能 |
| `--dpi`               | `INTEGER`                                | 画像解析時の DPI（解像度）                                         |
| `-p, --profile`       | `TEXT`                                   | 使用する AWS CLI プロファイル名                                    |
| `--request_timeout`   | `FLOAT`                                  | 各リクエスト単位のタイムアウト（秒）                                      |
| `--total_timeout`     | `FLOAT`                                  | 全体処理のタイムアウト（秒）                                          |
| `-v, --vis_mode`      | `[both / ocr / layout / none]`           | OCR 結果やレイアウト構造の可視化モード<br>`table-semantic-parser` では未対応のためスキップ |
| `-s, --split_mode`    | `[combine / separate]`                   | 出力ファイルの分割モード（1つにまとめる / ページごとに分割）                        |
| `--ignore_line_break` | *(flag)*                                 | テキスト抽出時に改行を無視する                                         |
| `--pages`             | `TEXT`                                   | 解析対象ページを指定（例：`0,1,3-5`）                                 |
| `--workers`           | `INTEGER`                                | 並列処理に使用するワーカー数（デフォルト: 4）                          |
| `--threthold_circuit` | `INTEGER`                                | サーキットブレーカーの失敗閾値（例：5）                                    |
| `--cooldown_time`     | `INTEGER`                                | サーキットブレーカーのクールダウン時間（秒）                                  |
| `--read_timeout`      | `INTEGER`                                | HTTP リクエストの読み取りタイムアウト（秒）                                |
| `--connect_timeout`   | `INTEGER`                                | HTTP リクエストの接続タイムアウト（秒）                                  |
| `--max_retries`       | `INTEGER`                                | HTTP リクエストの最大再試行回数                                      |
| `--help`              | *(flag)*                                 | ヘルプを表示して終了する                                            |


---

#### 💡 Tips

!!! tip "よく使う組み合わせ"
    - Markdown 形式とSearchable-PDFで全ファイルを一括解析する：
    `yomitoku-client batch -i ./docs -o ./out -e yomitoku-endpoint -f md,pdf`
    - OCR 結果を PDF に可視化して出力する：
    `yomitoku-client batch -i ./input -o ./vis -e yomitoku-endpoint -f pdf -v both`
    - CSV 出力で構造化データとして保存する：
    `yomitoku-client batch -i ./forms -o ./csv -e yomitoku-endpoint -f csv`
    - 特定ページのみを対象に解析：
    `yomitoku-client batch -i ./pdfs -o ./out -e yomitoku-endpoint --pages 0,2-4`

---

#### 🧾 補足

* 指定されたディレクトリ配下のすべての対応ファイル（`PDF`, `PNG`, `JPEG` など）が自動的に解析対象になります。
* `--vis_mode` により OCR / レイアウト枠付きの画像を生成できます。
* 並列処理（非同期実行）により複数ファイルを高速に処理します。
* AWS 認証は環境変数または `--profile` で指定されたプロファイルを使用します。

---

### Batch Transform出力の変換

保存済みのBatch Transform `.out`を、再推論せずにMarkdown、CSV、HTMLへ変換します。このコマンドはSageMakerエンドポイントやAWS認証を必要としません。

#### クイックスタート

```bash
yomitoku-client convert document.pdf.out --format md,csv,html --output-dir ./converted
```

出力先には元文書の拡張子と`.out`を除いた名前でファイルが生成されます。

```text
converted/document.md
converted/document.csv
converted/document.html
```

ディレクトリを指定すると、配下の`.out`を一括変換できます。

```bash
yomitoku-client convert ./batch-output --format md,csv --output-dir ./converted
```

#### 図の画像を出力する

MarkdownまたはHTMLへ図の切り出し画像を含める場合は、元画像または元PDFを`--src`で指定します。

```bash
yomitoku-client convert document.pdf.out \
  --format md,html \
  --src document.pdf \
  --output-dir ./converted
```

`--src`を省略した場合も変換できますが、図の画像は出力されません。段落、見出し、表などJSONだけで復元できる内容が出力されます。

#### オプション詳細

| オプション | 説明 |
| --- | --- |
| `-f, --format` | 出力形式。`md`, `csv`, `html`をカンマ区切りで指定（デフォルト: `md`） |
| `-o, --output-dir` | 出力ディレクトリ。省略時は単一ファイルなら入力元、ディレクトリなら`converted`配下 |
| `--src` | 図の切り出しに使用する元文書、または元文書を保存したディレクトリ |
| `--split-mode` | `combine`または`separate`（デフォルト: `combine`） |
| `--pages` | 変換するページ（例: `0,1,3-5`） |
| `--dpi` | 元PDFを読み込むDPI（デフォルト: `200`） |
| `--ignore-line-break` | 本文中の改行を除去 |
| `--overwrite` | 既存の出力ファイルを上書き |

!!! warning "既存ファイルはデフォルトで上書きしません"
    同名の出力が既に存在する場合はエラーになります。置き換える場合のみ`--overwrite`を指定してください。


---

## Table Semantic Parser

帳票解析APIを利用する場合は、`--api table-semantic-parser`を指定します。
Document Analyzerとはレスポンスの構造と対応する出力形式が異なり、出力はJSONのみです。既定では、セルIDをテキストと座標へ解決した`structured`形式を保存します。

### 単一ファイルとバッチ処理

```bash
# 単一ファイル
yomitoku-client single sample/table.jpg \
  --api table-semantic-parser \
  --endpoint yomitoku-tsp \
  --output_dir output/

# ディレクトリを一括処理
yomitoku-client batch \
  --api table-semantic-parser \
  --input_dir sample/ \
  --output_dir output/ \
  --endpoint yomitoku-tsp
```

### 出力モード {#tsp-output-formats}

| 指定 | 出力 | 用途 |
| --- | --- | --- |
| 指定なし | `structured` | 解決済みテキストと由来セルのID・座標を確認する |
| `--simple` | `simple` | 座標などを除き、Key-Valueや表の値だけを利用する |
| `--raw` | `raw` | セル・単語・参照を保持し、後から再変換する |

`--raw`と`--simple`は同時には指定できません。
後から出力形式を変える可能性がある場合は`raw`を保管してください。`structured`と`simple`は`cells`や`words`を省略するため、`raw`には戻せません。

```bash
# structured（既定）
yomitoku-client single sample/table.jpg -a table-semantic-parser -e yomitoku-tsp -o structured/

# simple
yomitoku-client single sample/table.jpg -a table-semantic-parser -e yomitoku-tsp --simple -o simple/

# raw
yomitoku-client single sample/table.jpg -a table-semantic-parser -e yomitoku-tsp --raw -o raw/
```

以下の例は1ページ分の内容です。既定の`combine`保存では、複数ページをJSON配列にまとめ、各ページに`num_page`を付けます。
`--split_mode separate`を指定すると、ページごとに別ファイルへ保存します。

#### raw：セルと参照を保持

APIレスポンスを正規化した形式です。セルのテキストや座標を`cells`に保持し、`kv_items`と`grids`はセルIDで参照します。`words`も残るため、解析結果の保管、テンプレート作成、後からの再変換に使用できます。

```json
{
  "num_page": 0,
  "document_name": "施設利用申込書",
  "tables": [
    {
      "id": "t0",
      "box": [10, 10, 400, 220],
      "style": "border",
      "cells": {
        "c0": {"id": "c0", "box": [10, 10, 100, 40], "contents": "氏名", "role": "header"},
        "c1": {"id": "c1", "box": [100, 10, 400, 40], "contents": "山田太郎", "role": "cell"},
        "c2": {"id": "c2", "box": [10, 60, 200, 90], "contents": "品名", "role": "header"},
        "c3": {"id": "c3", "box": [200, 60, 400, 90], "contents": "数量", "role": "header"},
        "c4": {"id": "c4", "box": [10, 90, 200, 120], "contents": "りんご", "role": "cell"},
        "c5": {"id": "c5", "box": [200, 90, 400, 120], "contents": "3", "role": "cell"},
        "c6": {"id": "c6", "box": [10, 120, 200, 150], "contents": "みかん", "role": "cell"},
        "c7": {"id": "c7", "box": [200, 120, 400, 150], "contents": "5", "role": "cell"}
      },
      "kv_items": [
        {"id": "kv0", "key": ["c0"], "value": "c1", "box": [10, 10, 400, 40]}
      ],
      "grids": [
        {
          "id": "g0",
          "box": [10, 60, 400, 150],
          "n_row": 3,
          "n_col": 2,
          "col_headers": [["c2"], ["c3"]],
          "data": [
            ["c2", "c3"],
            ["c4", "c5"],
            ["c6", "c7"]
          ]
        }
      ]
    }
  ],
  "paragraphs": [
    {
      "id": "p0",
      "box": [10, 170, 300, 200],
      "score": 0.98,
      "contents": "以上のとおり申請します。"
    }
  ],
  "words": []
}
```

この例では`kv_items[].key`の`c0`と`value`の`c1`が、`cells.c0`と`cells.c1`を参照します。APIが`cells`を配列で返すバージョンも読み込めますが、clientで保存する際はセルIDをキーにした辞書へ正規化します。

#### structured：テキストと由来セル

セルID参照をテキストへ解決し、`key_cells`と`value_cells`に由来セルのIDと座標を残します。値の確認画面や、画像上の位置との対応付けに適しています。

```json
{
  "num_page": 0,
  "document_name": "施設利用申込書",
  "tables": [
    {
      "id": "t0",
      "box": [10, 10, 400, 220],
      "style": "border",
      "kv_items": [
        {
          "key": ["氏名"],
          "value": "山田太郎",
          "key_cells": [{"id": "c0", "box": [10, 10, 100, 40]}],
          "value_cells": [{"id": "c1", "box": [100, 10, 400, 40]}]
        }
      ],
      "grids": [
        {
          "id": "g0",
          "box": [10, 60, 400, 150],
          "n_row": 3,
          "n_col": 2,
          "rows": [
            {
              "cells": [
                {
                  "key": ["品名"],
                  "value": "りんご",
                  "key_cells": [{"id": "c2", "box": [10, 60, 200, 90]}],
                  "value_cells": [{"id": "c4", "box": [10, 90, 200, 120]}]
                },
                {
                  "key": ["数量"],
                  "value": "3",
                  "key_cells": [{"id": "c3", "box": [200, 60, 400, 90]}],
                  "value_cells": [{"id": "c5", "box": [200, 90, 400, 120]}]
                }
              ]
            },
            {
              "cells": [
                {
                  "key": ["品名"],
                  "value": "みかん",
                  "key_cells": [{"id": "c2", "box": [10, 60, 200, 90]}],
                  "value_cells": [{"id": "c6", "box": [10, 120, 200, 150]}]
                },
                {
                  "key": ["数量"],
                  "value": "5",
                  "key_cells": [{"id": "c3", "box": [200, 60, 400, 90]}],
                  "value_cells": [{"id": "c7", "box": [200, 120, 400, 150]}]
                }
              ]
            }
          ]
        }
      ]
    }
  ],
  "paragraphs": [
    {
      "id": "p0",
      "box": [10, 170, 300, 200],
      "score": 0.98,
      "contents": "以上のとおり申請します。"
    }
  ]
}
```

同じキーセルに複数の値セルが結び付く場合、値を画像上の順序に並べて改行で結合し、結合元セルを同じ順序で`value_cells`に残します。同じ見出し文字列でもキーセルIDが異なる項目は別々に扱い、キーのない単独セルは`key: []`の独立した項目として残します。

#### simple：テキストのみ

座標、セルID、スコア、役割を除き、`kv_items`を見出し階層に沿った辞書、グリッド行を`{列見出し: 値}`、段落を文字列の配列として出力します。

```json
{
  "num_page": 0,
  "document_name": "施設利用申込書",
  "tables": [
    {
      "id": "t0",
      "kv_items": {"氏名": "山田太郎"},
      "grids": [
        {
          "id": "g0",
          "rows": [
            {"品名": "りんご", "数量": "3"},
            {"品名": "みかん", "数量": "5"}
          ]
        }
      ]
    }
  ],
  "paragraphs": ["以上のとおり申請します。"]
}
```

変換規則はYomiToku-Pro本体と同じです。

- 親見出しと子見出しは入れ子の辞書として保持します。
- 同じキーセルの複数値は画像上の順序に並べ、改行で結合します。
- 同じ階層に同名の別キーセルがある場合は配列にします。
- 親見出し自身の値と子見出しが共存する場合、親の値を`_value`へ格納します。
- キーのない単独セルは`_unkeyed`の配列へ格納します。
- グリッド行に同名の列見出しがある場合、`日付_0`、`日付_1`のように連番を付けます。

### 保存済みraw JSONの変換

`convert`を使うとAWSへ再リクエストせずに、保存済みの`raw`を`structured`または`simple`へ変換できます。
入力にはAPIレスポンスの`{"result": [...]}`、clientが保存したページ配列、1ページ分のJSONを使用できます。
`structured`と`simple`はセル情報を省略しているため、変換元には使用できません。

```bash
yomitoku-client convert raw/table.json -a table-semantic-parser -o structured/
yomitoku-client convert raw/table.json -a table-semantic-parser --simple -o simple/
```

入力ファイルを上書きしないよう、JSON変換では別の`--output-dir`を指定してください。既存の出力を置き換える場合は`--overwrite`を付けます。

### YomiToku-Proテンプレートの適用

`--template PATH`を指定すると、保存済みテンプレートを解析結果へ適用してから出力します。`single`、`batch`、`convert`で共通して利用できます。
テンプレートの作成には[Python APIの`save_template_json()`](module-usage.md#tsp-template)を使用します。
テンプレートは`meta`と`tables`を持つYomiToku-Pro互換形式です。表は座標の重なりで照合し、セルは`meta.match_policy`の`cell_id`（既定）または`bbox`で照合します。
セルの`contents` / `role`、表の`kv_items` / `grids`を補正できます。省略または`null`の項目は変更せず、空文字列や空配列は上書きとして扱います。
照合しない表・セルはスキップし、推論モデルの再実行やセルの新規検出は行いません。

```bash
yomitoku-client single sample/table.jpg \
  -a table-semantic-parser \
  -e yomitoku-tsp \
  --template templates/table.json \
  --simple \
  -o corrected/
```

### YomiToku Studioテンプレートの適用

YomiToku Studioの帳票解析画面から保存した`kind: "form-template"`のテンプレートには、`--studio-template PATH`を使用します。バージョン2と3に対応しています。

Batch CLIでは、入力ディレクトリ内の各画像・PDFをTable Semantic Parserで読み取り、APIレスポンスのOCR単語をStudioテンプレートの表・セル・段落へ割り当てます。表・セル・Key-Value・グリッドの構造はStudioテンプレート側の定義へ置き換わります。

```bash
yomitoku-client batch \
  --input_dir input/ \
  --output_dir output/ \
  --endpoint yomitoku-tsp \
  --api table-semantic-parser \
  --studio-template templates/application.template.json \
  --simple
```

テンプレート作成時の文字列は見出しセル（`header` / `group`）のOCR結果が空だった場合だけ補完に使います。値セルが読めなかった場合は、別帳票の値を誤って引き継がないよう空文字列を出力します。

`single`でも同じオプションを使用できます。保存済みraw JSONを`convert`する場合は、正規化座標を対象ページのピクセル座標へ戻すため、元の画像またはPDFを`--src`で指定します。

```bash
yomitoku-client convert raw/application.json \
  --api table-semantic-parser \
  --src input/application.pdf \
  --studio-template templates/application.template.json \
  --simple \
  --output-dir corrected/
```

`--template`と`--studio-template`はJSON形式と適用方法が異なり、同時には指定できません。
