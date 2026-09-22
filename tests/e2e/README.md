# Table Semantic Parser (TSP) の E2E 検証

実際の SageMaker エンドポイントに対して `yomitoku-client` の CLI を実行し、
返ってきた JSON の構造を検証してレポートにまとめるスクリプトです。

pytest ではなくスクリプトにしているのは、**デプロイ〜実行〜検証〜後片付けを 1 本で再現でき、
成果物（実レスポンス・スキーマ・レポート）をそのままレビューに出せる**ようにするためです。
検証ロジックは `validate_tsp.py` に独立させてあるので、必要になれば pytest からも呼べます。

## 構成

| ファイル | 役割 |
| --- | --- |
| `run_tsp_e2e.sh` | ドライバ。デプロイ(任意) → CLI 実行 → 検証 → レポート → 後片付け(任意) |
| `validate_tsp.py` | 出力 JSON の構造検証（単体でも実行可） |

入力は `notebooks/sample/` の同梱サンプルを使い、Content-Type 別の確認用に PNG / TIFF だけ
実行時に生成します（リポジトリにファイルを増やしません）。

## 実行

認証は AWS CLI / boto3 の既定の解決順に従います。環境変数にセッションを読み込んでいる場合は
`--profile` を指定しません（指定したときだけ各コマンドに渡します）。

```bash
# 既存のエンドポイントに対して実行
./tests/e2e/run_tsp_e2e.sh --endpoint yomitoku-tsp

# プロファイルを使う場合
./tests/e2e/run_tsp_e2e.sh --endpoint yomitoku-tsp --profile my-profile --region ap-northeast-1

# デプロイから後片付けまで通す（既定は CPU インスタンス ml.c7i.2xlarge）
./tests/e2e/run_tsp_e2e.sh \
    --deploy --model-package-arn arn:aws:sagemaker:...:model-package/... \
    --endpoint yomitoku-tsp-e2e --cleanup

# GPU で確認する場合（起動に時間がかかります）
./tests/e2e/run_tsp_e2e.sh \
    --deploy --model-package-arn arn:... --instance-type ml.g4dn.xlarge \
    --endpoint yomitoku-tsp-e2e --cleanup

# API の OpenAPI 定義でも検証する（任意）
./tests/e2e/run_tsp_e2e.sh --endpoint yomitoku-tsp \
    --schema /path/to/openapi-table-semantic-parser.yaml
```

環境変数でも指定できます: `YOMITOKU_TSP_ENDPOINT` / `AWS_REGION` / `YOMITOKU_E2E_PROFILE` /
`YOMITOKU_TSP_MODEL_PACKAGE_ARN`。

`--deploy` の既定は CPU インスタンス（`ml.c7i.2xlarge`）です。GPU は起動に時間がかかるうえ、
CPU では常に lite 認識器で動くためレスポンスの構造は変わりません。GPU でも確認したい場合は
`--instance-type ml.g4dn.xlarge` を指定してください。

## 実行ケース

| ケース | 内容 |
| --- | --- |
| `table_jpg` / `table_png` / `table_tiff` | 表ありの帳票を Content-Type 別に解析 |
| `multipage_pdf` | 複数ページ PDF（全ページ） |
| `pdf_pages_option` | `--pages 0,2` でページを絞った場合に `num_page` が保たれること |
| `handwriting` | 表が無い文書（手書き） |

未対応フォーマットを弾くことは `tests/test_client.py` のユニットテストで担保しています。

## 検証内容

ERROR（満たすべき構造）

- API のスキーマに適合する（`--schema` 指定時）
  - Table Semantic Parser API の OpenAPI 定義（`components.schemas.TSPResponse`）を渡すと、
    API が定義しているスキーマそのもので実レスポンスを検証できます
  - client が付ける `num_page` は API のスキーマに無いため、検証前に除外します
  - `jsonschema` と `PyYAML` が必要です（未インストールなら WARN を出してスキップ）
- 生レスポンスと client の出力が一致する（＝ client がフィールドを取りこぼしていない）
  - pydantic は既定で未知フィールドを捨てるため、「API が返しているのに client のモデルに
    無いフィールド」はこの差分でしか検出できません。逆に client が既定値で補ったフィールドは
    WARN として報告します
- yomitoku-client の pydantic モデルでパースできる（＝スキーマ適合）
- `kv_items` / `grids` が参照する `cell_id` が `cells` に存在する
- `box` が `[x1, y1, x2, y2]` として妥当（`x1 < x2`, `y1 < y2`）
- `words.points` が 4 点
- `num_page` が想定どおり（ページ数指定時は連番、`--pages` 指定時はその番号）

WARN（壊れてはいないが確認したい差異）

- `grid` の `n_row` / `n_col` と `data` の実形状が一致しない
- `col_headers` の数と `n_col` が一致しない
- `box` が画像範囲からはみ出す
- スコアが 0〜1 の範囲外

認識されたテキストの内容は検証しません（モデル更新で変化し、インターフェースの保証という
目的から外れるため）。認識精度の回帰は API 側の責務とします。

## 出力

`tests/e2e/results/<timestamp>/`（`.gitignore` 済み）に次を出力します。

```
report.md                    ケース一覧・結果・所要時間・環境情報
inputs/                      実行時に生成した入力（PNG / TIFF）
cases/<case>/*.json          解析結果（エンドポイントのレスポンス + num_page）
cases/<case>/intermediate/   エンドポイントの生レスポンス（差分チェックに使用）
cases/<case>/validation.log  検証結果
cases/<case>/validation.json 検証結果（機械可読）
cases/<case>/cli.log         CLI のログ
```

レビューに出すのは `report.md` と代表ケースの解析結果 JSON です。
