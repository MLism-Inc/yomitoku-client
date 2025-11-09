import asyncio
import json
import os

import click

from yomitoku_client import YomitokuClient, parse_pydantic_model
from yomitoku_client.client import CircuitConfig, RequestConfig

from .utils import parse_formats, parse_pages


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
    workers,
    threthold_circuit,
    cooldown_time,
    read_timeout,
    connect_timeout,
    max_retries,
    overwrite,
):
    """Analyze a single file and save the result."""
    async with YomitokuClient(
        endpoint=endpoint,
        region=region,
        profile=profile,
        max_workers=workers,
        request_config=RequestConfig(
            read_timeout=read_timeout,
            connect_timeout=connect_timeout,
            max_retries=max_retries,
        ),
        circuit_config=CircuitConfig(
            threshold=threthold_circuit,
            cooldown_time=cooldown_time,
        ),
    ) as client:
        await client.analyze_batch_async(
            input_dir=input_dir,
            output_dir=output_dir,
            page_index=page_index,
            dpi=dpi,
            request_timeout=request_timeout,
            total_timeout=total_timeout,
            overwrite=overwrite,
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
    type=str,
    default="json",
    help="Output format for the analysis result (json, csv, html, md, pdf)",
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
@click.option(
    "--workers",
    default=4,
    type=int,
    help="Number of workers for multiprocessing",
)
@click.option(
    "--threthold_circuit",
    default=0.5,
    type=int,
    help="Threshold for circuit breaker",
)
@click.option(
    "--cooldown_time",
    default=30,
    type=int,
    help="Cooldown time for circuit breaker in seconds",
)
@click.option(
    "--read_timeout",
    default=60,
    type=int,
    help="Read timeout for HTTP requests in seconds",
)
@click.option(
    "--connect_timeout",
    default=10,
    type=int,
    help="Connect timeout for HTTP requests in seconds",
)
@click.option(
    "--max_retries",
    default=3,
    type=int,
    help="Maximum number of retries for HTTP requests",
)
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="Overwrite existing output files",
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
    workers,
    threthold_circuit,
    cooldown_time,
    read_timeout,
    connect_timeout,
    max_retries,
    overwrite,
):
    page_index = None
    if pages is not None:
        page_index = parse_pages(pages)

    extract_formats = parse_formats(file_format)

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
            workers=workers,
            threthold_circuit=threthold_circuit,
            cooldown_time=cooldown_time,
            read_timeout=read_timeout,
            connect_timeout=connect_timeout,
            max_retries=max_retries,
            overwrite=overwrite,
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

        input_path = log["file_path"]
        base = os.path.splitext(os.path.basename(log["file_path"]))[0]

        if "json" in extract_formats:
            output_file_path = os.path.join(out_formatted, f"{base}.json")
            model.to_json(
                output_path=output_file_path,
                mode=split_mode,
                page_index=page_index,
                ignore_line_break=ignore_line_break,
            )
        if "csv" in extract_formats:
            output_file_path = os.path.join(out_formatted, f"{base}.csv")
            model.to_csv(
                output_path=output_file_path,
                mode=split_mode,
                page_index=page_index,
                ignore_line_break=ignore_line_break,
            )
        if "html" in extract_formats:
            output_file_path = os.path.join(out_formatted, f"{base}.html")
            model.to_html(
                output_path=output_file_path,
                image_path=input_path,
                mode=split_mode,
                page_index=page_index,
                ignore_line_break=ignore_line_break,
            )
        if "md" in extract_formats:
            output_file_path = os.path.join(out_formatted, f"{base}.md")
            model.to_markdown(
                output_path=output_file_path,
                image_path=input_path,
                mode=split_mode,
                page_index=page_index,
                ignore_line_break=ignore_line_break,
            )
        if "pdf" in extract_formats:
            output_file_path = os.path.join(out_formatted, f"{base}.pdf")
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
