import click
import json
import os

from pathlib import Path
from yomitoku_client import YomitokuClient, parse_pydantic_model


def parse_pages(pages_str):
    pages = set()
    for part in pages_str.split(","):
        if "-" in part:
            start, end = map(int, part.split("-"))
            pages.update(range(start, end + 1))
        else:
            pages.add(int(part))
    return sorted(pages)


@click.group()
def cli():
    pass


def get_format_ext(format: str) -> str:
    format = format.lower()
    if format in ["json"]:
        return "json"
    elif format in ["csv"]:
        return "csv"
    elif format in ["html", "htm"]:
        return "html"
    elif format in ["markdown", "md"]:
        return "md"
    elif format in ["pdf"]:
        return "pdf"
    else:
        raise ValueError(f"Unsupported format: {format}")


@cli.command()
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
    "--format",
    "-f",
    type=click.Choice(["json", "csv", "html", "md", "pdf"]),
    default="json",
    help="Output format for the analysis result",
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
    "-p",
    default=None,
    type=str,
    help="Pages to analyze (e.g., '0,1,3-5')",
)
@click.option(
    "--intermediate_save",
    "-i",
    is_flag=True,
    default=False,
    help="Save intermediate RAW JSON result",
)
def main(
    endpoint,
    region,
    input_path,
    output_dir,
    dpi,
    profile,
    request_timeout,
    total_timeout,
    split_mode,
    format,
    ignore_line_break,
    pages,
    vis_mode,
    intermediate_save,
):
    page_index = None
    if pages is not None:
        page_index = parse_pages(pages)

    """Analyze a single file and save the result."""
    with YomitokuClient(
        endpoint=endpoint,
        region=region,
        profile=profile,
    ) as client:
        result = client.analyze(
            path_img=input_path,
            page_index=page_index,
            dpi=dpi,
            request_timeout=request_timeout,
            total_timeout=total_timeout,
        )

    ext = get_format_ext(format)
    base_file_name = Path(input_path).stem
    base_ext = Path(input_path).suffix.lstrip(".")

    if output_dir is None:
        output_file_path = f"{base_file_name}.{ext}"
    else:
        output_file_path = Path(output_dir) / f"{base_file_name}.{ext}"

    if intermediate_save:
        intermediate_dir = (
            Path(output_dir) / "intermediate" if output_dir else Path("intermediate")
        )

        os.makedirs(intermediate_dir, exist_ok=True)

        intermediate_file_path = intermediate_dir / f"{base_file_name}_{base_ext}.json"

        with open(intermediate_file_path, "w") as f:
            json.dump(result, f, indent=4)

    model = parse_pydantic_model(result)

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
    main()
