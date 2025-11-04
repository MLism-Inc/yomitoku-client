import asyncio
import json
import os

import click

from yomitoku_client import YomitokuClient, parse_pydantic_model

from .utils import get_format_ext, parse_pages


async def process_batch(
    input_dir,
    output_dir,
    endpoint,
    region,
    page_index,
    dpi,
    profile,
    request_timeout,
    total_timeout,
):
    """Analyze a single file and save the result."""
    async with YomitokuClient(
        endpoint=endpoint,
        region=region,
        profile=profile,
    ) as client:
        await client.analyze_batch_async(
            input_dir=input_dir,
            output_dir=output_dir,
            page_index=page_index,
            dpi=dpi,
            request_timeout=request_timeout,
            total_timeout=total_timeout,
        )


@click.command("batch")
@click.option(
    "--input_dir",
    "-i",
    type=click.Path(exists=True),
    required=True,
    help="Path to the input directory containing files to analyze",
)
@click.option(
    "--output_dir",
    "-o",
    type=click.Path(),
    required=True,
    help="Path to save the analysis result",
)
@click.option(
    "--endpoint",
    "-e",
    type=str,
    required=True,
    help="SageMaker endpoint name",
)
@click.option(
    "--region",
    "-r",
    type=str,
    default=None,
    help="AWS region name",
)
@click.option(
    "--file_format",
    "-f",
    type=click.Choice(["json", "csv", "html", "md", "pdf"]),
    default="json",
    help="Output format for the analysis result",
)
@click.option(
    "--dpi",
    default=200,
    help="DPI for image processing",
)
@click.option(
    "--profile",
    "-p",
    default=None,
    type=str,
    help="AWS Profile",
)
@click.option(
    "--request_timeout",
    default=None,
    type=float,
    help="Timeout for each request",
)
@click.option(
    "--total_timeout",
    default=None,
    type=float,
    help="Total timeout for the whole operation",
)
@click.option(
    "--vis_mode",
    "-v",
    default="both",
    type=click.Choice(["both", "ocr", "layout", "none"]),
    help="Visualization mode for output images",
)
@click.option(
    "--split_mode",
    "-s",
    default="combine",
    type=click.Choice(["combine", "separate"]),
    help="Split mode for output files",
)
@click.option(
    "--ignore_line_break",
    is_flag=True,
    default=False,
    help="Ignore line breaks in text extraction",
)
@click.option(
    "--pages",
    default=None,
    type=str,
    help="Pages to analyze (e.g., '0,1,3-5')",
)
def batch_command(
    input_dir,
    output_dir,
    endpoint,
    region,
    dpi,
    profile,
    request_timeout,
    total_timeout,
    split_mode,
    file_format,
    ignore_line_break,
    pages,
    vis_mode,
):
    page_index = None
    if pages is not None:
        page_index = parse_pages(pages)

    # バッチ処理の実行
    asyncio.run(
        process_batch(
            input_dir=input_dir,
            output_dir=output_dir,
            endpoint=endpoint,
            region=region,
            page_index=page_index,
            dpi=dpi,
            profile=profile,
            request_timeout=request_timeout,
            total_timeout=total_timeout,
        )
    )

    out_formatted = os.path.join(output_dir, "formatted")
    out_visualize = os.path.join(output_dir, "visualization")

    os.makedirs(out_formatted, exist_ok=True)
    os.makedirs(out_visualize, exist_ok=True)

    # ログから成功したファイルを処理
    with open(os.path.join(output_dir, "process_log.jsonl"), encoding="utf-8") as f:
        logs = [json.loads(line) for line in f if line.strip()]

    for log in logs:
        if not log.get("success"):
            continue

        # 解析結果のJSONを読み込み
        with open(log["output_path"], encoding="utf-8") as rf:
            result = json.load(rf)

        model = parse_pydantic_model(result)

        ext = get_format_ext(file_format)
        input_path = log["file_path"]
        base = os.path.splitext(os.path.basename(log["file_path"]))[0]
        output_file_path = os.path.join(out_formatted, f"{base}.{ext}")

        if ext == "json":
            model.to_json(
                output_path=output_file_path,
                mode=split_mode,
                page_index=page_index,
                ignore_line_break=ignore_line_break,
            )
        elif ext == "csv":
            model.to_csv(
                output_path=output_file_path,
                mode=split_mode,
                page_index=page_index,
                ignore_line_break=ignore_line_break,
            )
        elif ext == "html":
            model.to_html(
                output_path=output_file_path,
                image_path=input_path,
                mode=split_mode,
                page_index=page_index,
                ignore_line_break=ignore_line_break,
            )
        elif ext == "md":
            model.to_markdown(
                output_path=output_file_path,
                image_path=input_path,
                mode=split_mode,
                page_index=page_index,
                ignore_line_break=ignore_line_break,
            )
        elif ext == "pdf":
            model.to_pdf(
                output_path=output_file_path,
                image_path=input_path,
                mode=split_mode,
                page_index=page_index,
            )

        # 解析結果の可視化
        if vis_mode in ["both", "ocr"]:
            model.visualize(
                image_path=input_path,
                mode="ocr",
                output_directory=out_visualize,
                dpi=dpi,
                page_index=page_index,
            )

        if vis_mode in ["both", "layout"]:
            model.visualize(
                image_path=input_path,
                mode="layout",
                output_directory=out_visualize,
                dpi=dpi,
                page_index=page_index,
            )
