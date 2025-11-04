# 🖥️ CLI Usage

`YomiToku-Client` をインストールすると、専用の CLI コマンド `yomitoku-client` が使用できます。
SageMaker 上の YomiToku エンドポイントにアクセスし、ドキュメントの解析や結果変換を行います。

---

## 🚀　ファイル単体の処理

指定したファイルを解析するためのコマンド。
ファイルを処理し、解析結果を指定のフォーマットで出力します。

### クイックスタート

```bash
yomitoku-client single ${path_file} -e ${endpoint_name} -r ${region} -f md -o demo
```

| 引数             | 説明                                                         |
| -------------- | ---------------------------------------------------------- |
| `${path_file}` | 解析対象のファイルパスを指定します。 *(必須)*                                  |
| `-e`           | SageMaker のエンドポイント名を指定します。 *(必須)*                          |
| `-r`           | AWS のリージョン名を指定します。                                         |
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

### 🆘 ヘルプの参照

CLI の利用可能なオプションは、`--help` で確認できます。

```bash
yomitoku-client single --help
```

---

### ⚙️ オプション詳細

| オプション                 | 型 / 値                            | 説明                                   |
| --------------------- | -------------------------------- | ------------------------------------ |
| `-e, --endpoint`      | `TEXT`                           | SageMaker のエンドポイント名（必須）              |
| `-r, --region`        | `TEXT`                           | AWS リージョン名（例：`ap-northeast-1`）       |
| `-f, --file_format`   | `[json / csv / html / md / pdf]` | 解析結果の出力フォーマット                        |
| `-o, --output_dir`    | `PATH`                           | 解析結果を保存する出力ディレクトリ                    |
| `--dpi`               | `INTEGER`                        | 画像解析時の DPI（解像度）                      |
| `-p, --profile`       | `TEXT`                           | 使用する AWS CLI プロファイル名                 |
| `--request_timeout`   | `FLOAT`                          | 各リクエストのタイムアウト（秒）                     |
| `--total_timeout`     | `FLOAT`                          | 全体処理のタイムアウト（秒）                       |
| `-v, --vis_mode`      | `[both / ocr / layout / none]`   | 出力画像の可視化モード（OCR結果 / レイアウト / 両方 / なし） |
| `-s, --split_mode`    | `[combine / separate]`           | 出力ファイルの分割モード（1つにまとめる / ページごとに分割）     |
| `--ignore_line_break` | *(flag)*                         | テキスト抽出時に改行を無視する                      |
| `--pages`             | `TEXT`                           | 解析対象ページを指定（例：`0,1,3-5`）              |
| `--intermediate_save` | *(flag)*                         | 中間生成物（RAW JSON）を保存する                 |
| `--help`              | *(flag)*                         | ヘルプを表示して終了する                         |

---

### 💡 Tips

!!! tip "よく使う組み合わせ"
    - Markdown 形式で解析結果を保存する：
    `yomitoku-client single invoice.pdf -e yomitoku-endpoint -f md`
    - OCR 結果を PDF に埋め込み可視化する：
    `yomitoku-client single report.pdf -e yomitoku-endpoint -f pdf -v both`
    - 中間JSONも同時に保存する：
    `yomitoku-client single form.png -e yomitoku-endpoint -f csv --intermediate_save`
    - 特定ページのみを解析：
    `yomitoku-client single book.pdf -e yomitoku-endpoint --pages "1,2-5"`

---

### 🧾 補足

* AWS CLI の設定済み環境で実行することを推奨します。
* 出力ディレクトリ（`-o`）が存在しない場合、自動で作成されます。
* CLI の戻り値は解析結果ファイルのパスを返します。
* `--intermediate_save` を指定すると、内部処理のRAW JSONを同ディレクトリ内に保存します。
* 高解像度処理を行う場合は、`--dpi 300` などを指定することでOCR精度が向上します。

---

## 🚀　バッチ処理（ディレクトリ一括解析）

複数ファイルを一括解析するための バッチ処理コマンド。
指定したディレクトリ内のファイルを順次処理し、解析結果を指定のフォーマットで出力します。

### クイックスタート

```bash
yomitoku-client batch -i ${input_dir} -o ${output_dir} -e ${endpoint_name} -r ${region} -f md
```

| 引数                  | 説明                                                         |
| ------------------- | ---------------------------------------------------------- |
| `-i, --input_dir`   | 解析対象のファイルを含むディレクトリのパスを指定します。 *(必須)*                        |
| `-o, --output_dir`  | 解析結果を保存するディレクトリを指定します。 *(必須)*                              |
| `-e, --endpoint`    | SageMaker のエンドポイント名を指定します。 *(必須)*                          |
| `-r, --region`      | AWS のリージョン名を指定します。                                         |
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

### 🆘 ヘルプの参照

CLI の利用可能なオプションは、`--help` で確認できます。

```bash
yomitoku-client batch --help
```

---

### ⚙️ オプション詳細

| オプション                 | 型 / 値                            | 説明                             |
| --------------------- | -------------------------------- | ------------------------------ |
| `-i, --input_dir`     | `PATH`                           | 解析対象ファイルを含む入力ディレクトリのパス（必須）     |
| `-o, --output_dir`    | `PATH`                           | 解析結果を保存する出力先ディレクトリのパス（必須）      |
| `-e, --endpoint`      | `TEXT`                           | SageMaker のエンドポイント名（必須）        |
| `-r, --region`        | `TEXT`                           | AWS リージョン名（例：`ap-northeast-1`） |
| `-f, --file_format`   | `[json / csv / html / md / pdf]` | 出力フォーマット                       |
| `--dpi`               | `INTEGER`                        | 画像解析時の DPI（解像度）                |
| `-p, --profile`       | `TEXT`                           | 使用する AWS CLI プロファイル名           |
| `--request_timeout`   | `FLOAT`                          | 各リクエストのタイムアウト（秒）               |
| `--total_timeout`     | `FLOAT`                          | 全体処理のタイムアウト（秒）                 |
| `-v, --vis_mode`      | `[both / ocr / layout / none]`   | OCR 結果やレイアウト構造の可視化モード          |
| `-s, --split_mode`    | `[combine / separate]`           | 出力ファイルの分割モード（まとめる／ページごと）       |
| `--ignore_line_break` | *(flag)*                         | テキスト抽出時に改行を無視                  |
| `--pages`             | `TEXT`                           | 解析対象ページを指定（例：`0,1,3-5`）        |

---

### 💡 Tips

!!! tip "よく使う組み合わせ"
    - Markdown 形式で全ファイルを一括解析する：
    `yomitoku-client batch -i ./docs -o ./out -e yomitoku-endpoint -f md`
    - OCR 結果を PDF に可視化して出力する：
    `yomitoku-client batch -i ./input -o ./vis -e yomitoku-endpoint -f pdf -v both`
    - CSV 出力で構造化データとして保存する：
    `yomitoku-client batch -i ./forms -o ./csv -e yomitoku-endpoint -f csv`
    - 特定ページのみを対象に解析：
    `yomitoku-client batch -i ./pdfs -o ./out -e yomitoku-endpoint --pages 0,2-4`

---

### 🧾 補足

* 指定されたディレクトリ配下のすべての対応ファイル（`PDF`, `PNG`, `JPEG` など）が自動的に解析対象になります。
* `--vis_mode` により OCR / レイアウト枠付きの画像を生成できます。
* 並列処理（非同期実行）により複数ファイルを高速に処理します。
* AWS 認証は環境変数または `--profile` で指定されたプロファイルを使用します。

---