import json
import os
from pathlib import Path

import click

from yomitoku_client import YomitokuClient, parse_pydantic_model
from yomitoku_client.client import CircuitConfig, RequestConfig

from .utils import parse_formats, parse_pages


@click.command("single")
@click.argument("input_path", type=click.Path(exists=True))
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
    "--output_dir",
    "-o",
    type=click.Path(),
    default=None,
    help="Path to save the analysis result",
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
    "--intermediate_save",
    is_flag=True,
    default=False,
    help="Save intermediate RAW JSON result",
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
def single_command(
    endpoint,
    region,
    input_path,
    output_dir,
    dpi,
    profile,
    request_timeout,
    total_timeout,
    split_mode,
    file_format,
    ignore_line_break,
    pages,
    vis_mode,
    intermediate_save,
    workers,
    threthold_circuit,
    cooldown_time,
    read_timeout,
    connect_timeout,
    max_retries,
):
    page_index = None
    if pages is not None:
        page_index = parse_pages(pages)

    extract_formats = parse_formats(file_format)

    """Analyze a single file and save the result."""
    with YomitokuClient(
        endpoint=endpoint,
        region=region,
        profile=profile,
        max_workers=workers,
        request_config=RequestConfig(
            read_timeout=read_timeout,
            connect_timeout=connect_timeout,
            max_attempts=max_retries,
        ),
        circuit_config=CircuitConfig(
            threshold=threthold_circuit,
            cooldown_sec=cooldown_time,
        ),
    ) as client:
        result = client.analyze(
            path_img=input_path,
            page_index=page_index,
            dpi=dpi,
            request_timeout=request_timeout,
            total_timeout=total_timeout,
        )

    base_file_name = Path(input_path).stem
    base_ext = Path(input_path).suffix.lstrip(".")

    if output_dir is None:
        output_file_base = f"{base_file_name}"
    else:
        output_file_base = Path(output_dir) / f"{base_file_name}"

    if intermediate_save:
        intermediate_dir = (
            Path(output_dir) / "intermediate" if output_dir else Path("intermediate")
        )

        os.makedirs(intermediate_dir, exist_ok=True)

        intermediate_file_path = intermediate_dir / f"{base_file_name}_{base_ext}.json"

        with open(intermediate_file_path, "w") as f:
            json.dump(result, f, indent=4)

    model = parse_pydantic_model(result)

    if "json" in extract_formats:
        output_file_path = output_file_base + ".json"
        model.to_json(
            output_path=output_file_path,
            mode=split_mode,
            page_index=page_index,
            ignore_line_break=ignore_line_break,
        )
    if "csv" in extract_formats:
        output_file_path = output_file_base + ".csv"
        model.to_csv(
            output_path=output_file_path,
            mode=split_mode,
            page_index=page_index,
            ignore_line_break=ignore_line_break,
        )
    if "html" in extract_formats:
        output_file_path = output_file_base + ".html"
        model.to_html(
            output_path=output_file_path,
            image_path=input_path,
            mode=split_mode,
            page_index=page_index,
            ignore_line_break=ignore_line_break,
        )
    if "md" in extract_formats:
        output_file_path = output_file_base + ".md"
        model.to_markdown(
            output_path=output_file_path,
            image_path=input_path,
            mode=split_mode,
            page_index=page_index,
            ignore_line_break=ignore_line_break,
        )
    if "pdf" in extract_formats:
        output_file_path = output_file_base + ".pdf"
        model.to_pdf(
            output_path=output_file_path,
            image_path=input_path,
            mode=split_mode,
            page_index=page_index,
        )

    if vis_mode in ["both", "ocr"]:
        model.visualize(
            image_path=input_path,
            mode="ocr",
            output_directory=output_dir,
            dpi=dpi,
            page_index=page_index,
        )

    if vis_mode in ["both", "layout"]:
        model.visualize(
            image_path=input_path,
            mode="layout",
            output_directory=output_dir,
            dpi=dpi,
            page_index=page_index,
        )


if __name__ == "__main__":
    single_command()
