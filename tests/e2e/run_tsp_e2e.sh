#!/bin/bash

# Table Semantic Parser (TSP) の E2E 検証スクリプト
#
# SageMaker エンドポイントに対して yomitoku-client の CLI を実行し、
# 出力 JSON の構造を検証してレポートにまとめる。
#
# 使用方法:
#   ./tests/e2e/run_tsp_e2e.sh --endpoint yomitoku-tsp
#   ./tests/e2e/run_tsp_e2e.sh --deploy --model-package-arn arn:... --cleanup
#
# 認証は AWS CLI / boto3 の既定の解決順に従う。環境変数でセッションを読み込んで
# いる場合は --profile を指定しない。指定した場合のみ各コマンドに渡す。
#
# 主なオプション（環境変数でも指定可）:
#   --endpoint NAME          エンドポイント名 (env: YOMITOKU_TSP_ENDPOINT)
#   --region REGION          リージョン (env: AWS_REGION。未指定なら既定の解決に任せる)
#   --profile NAME           AWS プロファイル (env: YOMITOKU_E2E_PROFILE。省略可)
#   --outdir DIR             出力先 (既定: tests/e2e/results/<timestamp>)
#   --schema PATH            API のスキーマで検証する
#                            (例: /path/to/openapi-table-semantic-parser.yaml)
#   --deploy                 実行前にエンドポイントを作成する
#   --model-package-arn ARN  --deploy 時の Model Package ARN (env: YOMITOKU_TSP_MODEL_PACKAGE_ARN)
#   --instance-type TYPE     --deploy 時のインスタンスタイプ
#                            (既定: ml.c7i.2xlarge。GPU は起動に時間がかかるため CPU を既定にする)
#   --cleanup                実行後にエンドポイントを削除する

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
E2E_DIR="${REPO_ROOT}/tests/e2e"
SAMPLE_DIR="${REPO_ROOT}/notebooks/sample"

ENDPOINT="${YOMITOKU_TSP_ENDPOINT:-}"
REGION="${AWS_REGION:-}"
PROFILE="${YOMITOKU_E2E_PROFILE:-}"
OUTDIR=""
SCHEMA=""
DEPLOY=false
CLEANUP=false
MODEL_PACKAGE_ARN="${YOMITOKU_TSP_MODEL_PACKAGE_ARN:-}"
# GPU インスタンスは起動に時間がかかるため、既定は CPU にする（CPU は常に lite 認識器で動く）
INSTANCE_TYPE="ml.c7i.2xlarge"

PYTHON_BIN="${PYTHON:-python3}"
CLIENT_BIN="${YOMITOKU_CLIENT_BIN:-yomitoku-client}"

usage() {
  sed -n '3,25p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
  --endpoint) ENDPOINT="$2"; shift 2 ;;
  --region) REGION="$2"; shift 2 ;;
  --profile) PROFILE="$2"; shift 2 ;;
  --outdir) OUTDIR="$2"; shift 2 ;;
  --schema) SCHEMA="$2"; shift 2 ;;
  --model-package-arn) MODEL_PACKAGE_ARN="$2"; shift 2 ;;
  --instance-type) INSTANCE_TYPE="$2"; shift 2 ;;
  --deploy) DEPLOY=true; shift ;;
  --cleanup) CLEANUP=true; shift ;;
  -h | --help) usage 0 ;;
  *) echo "❌ 不明なオプション: $1" >&2; usage 1 ;;
  esac
done

if [[ -z "${ENDPOINT}" ]]; then
  echo "❌ エンドポイント名を --endpoint か YOMITOKU_TSP_ENDPOINT で指定してください" >&2
  exit 1
fi

if ! command -v "${CLIENT_BIN}" >/dev/null 2>&1; then
  echo "❌ ${CLIENT_BIN} が見つかりません（YOMITOKU_CLIENT_BIN で上書きできます）" >&2
  exit 1
fi

# --profile / --region は指定された場合のみ渡す（環境変数のセッションをそのまま使えるように）
# NOTE: bash 3.2 では空配列の "${arr[@]}" が unbound になるため ${arr[@]+...} で展開する
CLIENT_AUTH_ARGS=()
[[ -n "${PROFILE}" ]] && CLIENT_AUTH_ARGS+=(--profile "${PROFILE}")
[[ -n "${REGION}" ]] && CLIENT_AUTH_ARGS+=(--region "${REGION}")

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
OUTDIR="${OUTDIR:-${E2E_DIR}/results/${TIMESTAMP}}"
INPUT_DIR="${OUTDIR}/inputs"
CASE_DIR="${OUTDIR}/cases"
REPORT="${OUTDIR}/report.md"
mkdir -p "${INPUT_DIR}" "${CASE_DIR}"

echo "=== TSP E2E 検証 ==="
echo "エンドポイント: ${ENDPOINT}"
echo "リージョン: ${REGION:-<default>}"
echo "プロファイル: ${PROFILE:-<環境変数の認証情報を使用>}"
echo "出力先: ${OUTDIR}"
echo ""

# --- 1. デプロイ（任意） ---
if [[ "${DEPLOY}" == true ]]; then
  if [[ -z "${MODEL_PACKAGE_ARN}" ]]; then
    echo "❌ --deploy には --model-package-arn が必要です" >&2
    exit 1
  fi
  echo "1. エンドポイントを作成中 (${INSTANCE_TYPE})..."
  "${CLIENT_BIN}" sagemaker deploy \
    --product table-semantic-parser \
    --endpoint-name "${ENDPOINT}" \
    --instance-type "${INSTANCE_TYPE}" \
    --model-package-arn "${MODEL_PACKAGE_ARN}" \
    ${CLIENT_AUTH_ARGS[@]+"${CLIENT_AUTH_ARGS[@]}"} || {
    echo "❌ デプロイに失敗しました" >&2
    exit 1
  }
else
  echo "1. デプロイはスキップ（既存のエンドポイントを使用）"
fi

# --- 2. 入力の準備（Content-Type 別の確認用に PNG / TIFF を生成する） ---
echo "2. 入力を準備中..."
"${PYTHON_BIN}" -c "
from PIL import Image
with Image.open('${SAMPLE_DIR}/table.jpg') as img:
    rgb = img.convert('RGB')
    rgb.save('${INPUT_DIR}/table.png')
    rgb.save('${INPUT_DIR}/table.tiff')
" || exit 1

# ケース定義: 名前|入力ファイル|追加オプション|想定ページ|説明
#   想定ページは「ページ数」(例: 9) か「num_page のカンマ区切り」(例: 0,2)。空なら検証しない。
CASES=(
  "table_jpg|${SAMPLE_DIR}/table.jpg||1|表あり（JPEG）"
  "table_png|${INPUT_DIR}/table.png||1|表あり（PNG）"
  "table_tiff|${INPUT_DIR}/table.tiff||1|表あり（TIFF）"
  "multipage_pdf|${SAMPLE_DIR}/image.pdf||9|複数ページ PDF（全ページ）"
  "pdf_pages_option|${SAMPLE_DIR}/image.pdf|--pages 0,2|0,2|ページ指定（--pages 0,2）"
  "handwriting|${SAMPLE_DIR}/tegaki.jpg||1|表なし文書（手書き）"
)

# --- 3. ケースの実行と検証 ---
echo "3. ケースを実行中..."
declare -a ROWS=()
FAILED=0

for case_def in "${CASES[@]}"; do
  IFS='|' read -r name input_path options expect_pages description <<<"${case_def}"
  case_out="${CASE_DIR}/${name}"

  if [[ ! -f "${input_path}" ]]; then
    echo "   ⏭  ${name}: 入力が無いためスキップ (${input_path})"
    ROWS+=("| ${name} | ${description} | SKIP | - | 入力ファイルなし |")
    continue
  fi

  mkdir -p "${case_out}"
  start=$(date +%s)

  # shellcheck disable=SC2086
  "${CLIENT_BIN}" single "${input_path}" \
    --api table-semantic-parser \
    --raw \
    --endpoint "${ENDPOINT}" \
    ${CLIENT_AUTH_ARGS[@]+"${CLIENT_AUTH_ARGS[@]}"} \
    --file_format json \
    --output_dir "${case_out}" \
    --vis_mode none \
    --intermediate_save \
    ${options} >"${case_out}/cli.log" 2>&1
  cli_status=$?

  elapsed=$(($(date +%s) - start))

  if [[ ${cli_status} -ne 0 ]]; then
    echo "   ❌ ${name}: CLI が失敗 (${elapsed}s) -> ${case_out}/cli.log"
    ROWS+=("| ${name} | ${description} | NG | ${elapsed}s | CLI が異常終了。[${name}/cli.log](./cases/${name}/cli.log) を参照 |")
    FAILED=$((FAILED + 1))
    continue
  fi

  json_path="$(find "${case_out}" -maxdepth 1 -name '*.json' | head -1)"
  if [[ -z "${json_path}" ]]; then
    echo "   ❌ ${name}: 出力 JSON が見つからない"
    ROWS+=("| ${name} | ${description} | NG | ${elapsed}s | 出力 JSON なし |")
    FAILED=$((FAILED + 1))
    continue
  fi

  VALIDATE_ARGS=("${json_path}" --input "${input_path}" --report-json "${case_out}/validation.json")

  # 生レスポンスと突き合わせて、client がフィールドを取りこぼしていないか確認する
  raw_path="$(find "${case_out}/intermediate" -maxdepth 1 -name '*.json' 2>/dev/null | head -1)"
  [[ -n "${raw_path}" ]] && VALIDATE_ARGS+=(--raw "${raw_path}")

  if [[ "${expect_pages}" == *,* ]]; then
    VALIDATE_ARGS+=(--expect-page-numbers "${expect_pages}")
  elif [[ -n "${expect_pages}" ]]; then
    VALIDATE_ARGS+=(--expect-pages "${expect_pages}")
  fi
  [[ -n "${SCHEMA}" ]] && VALIDATE_ARGS+=(--schema "${SCHEMA}")

  validation_log="${case_out}/validation.log"
  "${PYTHON_BIN}" "${E2E_DIR}/validate_tsp.py" "${VALIDATE_ARGS[@]}" >"${validation_log}" 2>&1
  validate_status=$?

  n_warnings=$(grep -c "WARN" "${validation_log}" || true)
  summary_line=$(head -1 "${validation_log}")

  if [[ ${validate_status} -eq 0 ]]; then
    echo "   ✅ ${name}: OK (${elapsed}s, warnings=${n_warnings})"
    ROWS+=("| ${name} | ${description} | OK | ${elapsed}s | ${summary_line#*: } (warnings=${n_warnings}) |")
  else
    echo "   ❌ ${name}: 検証エラー (${elapsed}s) -> ${validation_log}"
    ROWS+=("| ${name} | ${description} | NG | ${elapsed}s | 検証エラー。[${name}/validation.log](./cases/${name}/validation.log) を参照 |")
    FAILED=$((FAILED + 1))
  fi
done

# --- 4. 後片付け（任意） ---
if [[ "${CLEANUP}" == true ]]; then
  echo "4. エンドポイントを削除中..."
  "${CLIENT_BIN}" sagemaker delete --endpoint-name "${ENDPOINT}" \
    ${CLIENT_AUTH_ARGS[@]+"${CLIENT_AUTH_ARGS[@]}"} ||
    echo "   ⚠️  削除に失敗しました。手動で確認してください"
else
  echo "4. 後片付けはスキップ（エンドポイントは起動したままです）"
fi

# --- 5. レポート出力 ---
{
  echo "# TSP E2E 検証レポート"
  echo ""
  echo "- 実行日時: $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "- エンドポイント: \`${ENDPOINT}\`"
  echo "- リージョン: ${REGION:-<default>}"
  echo "- インスタンスタイプ: $([[ "${DEPLOY}" == true ]] && echo "${INSTANCE_TYPE}" || echo "既存エンドポイントの設定")"
  echo "- yomitoku-client: $(${PYTHON_BIN} -c 'import yomitoku_client; print(yomitoku_client.__version__)' 2>/dev/null || echo unknown)"
  echo ""
  echo "## 結果"
  echo ""
  echo "| ケース | 内容 | 結果 | 所要時間 | 備考 |"
  echo "| --- | --- | --- | --- | --- |"
  for row in ${ROWS[@]+"${ROWS[@]}"}; do echo "${row}"; done
  echo ""
  echo "## 検証項目"
  echo ""
  echo "- 生レスポンスと client の出力が一致すること（フィールドの取りこぼしが無いこと）"
  echo "- pydantic モデルでパースできること（スキーマ適合）"
  echo "- kv_items / grids が参照する cell_id が cells に存在すること"
  echo "- box が [x1, y1, x2, y2] として妥当で、画像範囲内にあること"
  echo "- words.points が 4 点であること"
  echo "- num_page が想定どおりであること"
  echo ""
  echo "認識テキストの内容は検証対象外（モデル更新で変化するため）。"
  echo "grid の n_row / n_col と実データの不一致、スコアの範囲外は WARN として記録する。"
} >"${REPORT}"

echo ""
if [[ ${FAILED} -eq 0 ]]; then
  echo "🎉 すべてのケースが成功しました"
else
  echo "❌ ${FAILED} 件のケースが失敗しました"
fi
echo "レポート: ${REPORT}"
exit $((FAILED > 0 ? 1 : 0))
