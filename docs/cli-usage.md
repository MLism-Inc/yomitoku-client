# 🖥️ CLI Usage

`YomiToku-Client` をインストールすると、専用の CLI コマンド `yomitoku_client` が使用できます。
SageMaker 上の YomiToku エンドポイントにアクセスし、ドキュメントの解析や結果変換を行います。

---

## 🚀 クイックスタート

```bash
yomitoku_client ${path_file} -e ${endpoint_name} -r ${region} -f md -o demo
```

| 引数             | 説明                                                                 |
| -------------- | ------------------------------------------------------------------ |
| `${path_file}` | 解析対象のファイルパスを指定します。                                                 |
| `-e`           | SageMaker のエンドポイント名を指定します。 *(必須)*                                  |
| `-r`           | AWS のリージョン名を指定します。                                                 |
| `-f`           | 解析結果を変換したいフォーマットを指定します。<br>対応形式：`json`, `csv`, `html`, `md`, `pdf` |
| `-o`           | 出力先ディレクトリを指定します。                                                   |

> **例**
>
> ```bash
> yomitoku_client samples/demo.pdf -e yomitoku-endpoint -r ap-northeast-1 -f md -o output/
> ```

!!! note "補足"

    uv環境下でYomiToku-ClientのCLIコマンド`yomitoku_client`を実行する際は、コマンドの先頭に`uv run`を追加し、

    ```bash
     uv run yomitoku_client
    
    ```
    
    の形式で呼び出してください。

---

---

## 🆘 ヘルプの参照

CLI の利用可能なオプションは、`--help` で確認できます。

```bash
yomitoku_client --help
```

---

## ⚙️ オプション詳細

| オプション | 型 / 値 | 説明 |
|-------------|----------|------|
| `-e, --endpoint` | `TEXT` | SageMaker のエンドポイント名（必須） |
| `-r, --region` | `TEXT` | AWS リージョン名（例：`ap-northeast-1`） |
| `-f, --file_format` | `[csv / html / md / pdf]` | 解析結果の出力フォーマット |
| `-o, --output_dir` | `PATH` | 解析結果を保存する出力先パス |
| `--dpi` | `INTEGER` | 画像解析時の DPI 設定 |
| `--profile` | `TEXT` | 利用する AWS CLI プロファイル名 |
| `--request_timeout` | `FLOAT` | 各ページ単位のリクエストタイムアウト（秒） |
| `--total_timeout` | `FLOAT` | 全体処理のタイムアウト（秒） |
| `-v, --vis_mode` | `[both / ocr / layout / none]` | 可視化モード（OCR結果 / レイアウト / 両方 / なし） |
| `-s, --split_mode` | `[combine / separate]` | 出力ファイルの分割モード |
| `--ignore_line_break` | `FLAG` | テキスト抽出時に改行を無視する |

---

## 💡 Tips

!!! tip "よく使う組み合わせ"
    - Markdown 形式で解析結果を保存する：
    `yomitoku_client invoice.pdf -e yomitoku-endpoint -f md`
    - OCR 結果を PDF に埋め込み可視化する：
    `yomitoku_client report.pdf -e yomitoku-endpoint -f pdf -v both`
    - CSV形式と中間ファイルをとして保存：
    `yomitoku_client form.png -e yomitoku-endpoint -i -f csv`

---

## 🧾 補足

* AWS CLI の設定済み環境で実行することを推奨します。
* CLI の戻り値は解析結果ファイルのパスを返します。
* 出力先ディレクトリ（`-o`）が存在しない場合は自動で作成されます。
