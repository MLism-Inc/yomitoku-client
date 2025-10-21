import asyncio
import json
import os

from yomitoku_client import YomitokuClient
from yomitoku_client.parsers.sagemaker_parser import parse_pydantic_model

# 入出力設定
target_dir = "notebooks/sample"
outdir = "output"

# SageMakerエンドポイント設定
ENDPOINT_NAME = "my-endpoint"
AWS_REGION = "ap-northeast-1"
MFA_SERIAL = "arn:aws:iam::025897765203:mfa/iphone"
MFA_TOKEN = "712732"


async def main():
    # バッチ解析の実行
    async with YomitokuClient(
        endpoint=ENDPOINT_NAME,
        region=AWS_REGION,
        mfa_serial=MFA_SERIAL,
        mfa_token=MFA_TOKEN,
    ) as client:
        await client.analyze_batch_async(
            input_dir=target_dir,
            output_dir=outdir,
        )

    # ログから成功したファイルを処理
    with open(os.path.join(outdir, "process_log.jsonl"), "r", encoding="utf-8") as f:
        logs = [json.loads(line) for line in f if line.strip()]

    out_markdown = os.path.join(outdir, "markdown")
    out_visualize = os.path.join(outdir, "visualization")

    os.makedirs(out_markdown, exist_ok=True)
    os.makedirs(out_visualize, exist_ok=True)

    for log in logs:
        if not log.get("success"):
            continue

        # 解析結果のJSONを読み込み
        with open(log["output_path"], "r", encoding="utf-8") as rf:
            result = json.load(rf)

        doc = parse_pydantic_model(result)

        # Markdown出力
        base = os.path.splitext(os.path.basename(log["file_path"]))[0]
        doc.to_markdown(output_path=os.path.join(out_markdown, f"{base}.md"))

        # 解析結果の可視化
        doc.visualize(
            image_path=log["file_path"],
            mode="ocr",
            output_directory=out_visualize,
            dpi=log.get("dpi", 200),
        )


if __name__ == "__main__":
    asyncio.run(main())
