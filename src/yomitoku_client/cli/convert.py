import json
from pathlib import Path

import click

from yomitoku_client import parse_pydantic_model
from yomitoku_client.exceptions import DocumentAnalysisError

from .utils import parse_formats, parse_pages

CONVERT_FORMATS = {"md", "csv", "html"}


def _output_stem(input_path: Path) -> str:
    """Return the original document stem from a Batch Transform output name."""
    name = input_path.name
    if name.endswith(".out"):
        name = name[: -len(".out")]
    return Path(name).stem


def _find_source(input_path: Path, src: Path | None) -> Path | None:
    if src is None or src.is_file():
        return src

    original_name = input_path.name
    if original_name.endswith(".out"):
        original_name = original_name[: -len(".out")]

    candidate = src / original_name
    return candidate if candidate.is_file() else None


def convert_file(
    input_path: Path,
    output_dir: Path,
    formats: list[str],
    src: Path | None = None,
    split_mode: str = "combine",
    page_index: list[int] | None = None,
    dpi: int = 200,
    ignore_line_break: bool = False,
    overwrite: bool = False,
) -> list[Path]:
    """Convert one YomiToku Batch Transform JSON output."""
    try:
        with input_path.open(encoding="utf-8") as f:
            raw_result = json.load(f)
        model = parse_pydantic_model(raw_result)
    except (OSError, json.JSONDecodeError, DocumentAnalysisError) as e:
        raise click.ClickException(f"Failed to read {input_path}: {e}") from e

    output_dir.mkdir(parents=True, exist_ok=True)
    base = output_dir / _output_stem(input_path)
    source_path = _find_source(input_path, src)
    outputs = []

    for output_format in formats:
        output_path = base.with_suffix(f".{output_format}")
        if output_path.exists() and not overwrite:
            raise click.ClickException(
                f"Output already exists: {output_path}. Use --overwrite to replace it."
            )

        common = {
            "output_path": str(output_path),
            "mode": split_mode,
            "page_index": page_index,
            "ignore_line_break": ignore_line_break,
        }
        if output_format == "md":
            model.to_markdown(
                **common,
                image_path=source_path,
                dpi=dpi,
                export_figure=source_path is not None,
            )
        elif output_format == "html":
            model.to_html(
                **common,
                image_path=source_path,
                dpi=dpi,
                export_figure=source_path is not None,
            )
        elif output_format == "csv":
            model.to_csv(**common, export_figure=False)
        outputs.append(output_path)

    return outputs


@click.command("convert")
@click.argument(
    "input_path",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--format",
    "formats",
    "-f",
    default="md",
    show_default=True,
    help="Comma-separated output formats: md,csv,html",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory. Defaults to the input directory.",
)
@click.option(
    "--src",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Original document, or its directory, used to export figure images.",
)
@click.option(
    "--split-mode",
    type=click.Choice(["combine", "separate"]),
    default="combine",
    show_default=True,
)
@click.option("--pages", default=None, help="Pages to convert, e.g. '0,1,3-5'.")
@click.option("--dpi", default=200, show_default=True, type=int)
@click.option("--ignore-line-break", is_flag=True, default=False)
@click.option("--overwrite", is_flag=True, default=False)
def convert_command(
    input_path: Path,
    formats: str,
    output_dir: Path | None,
    src: Path | None,
    split_mode: str,
    pages: str | None,
    dpi: int,
    ignore_line_break: bool,
    overwrite: bool,
):
    """Convert saved Batch Transform .out JSON to other formats."""
    try:
        parsed_formats = parse_formats(formats)
    except ValueError as e:
        raise click.BadParameter(str(e), param_hint="--format") from e

    unsupported = set(parsed_formats) - CONVERT_FORMATS
    if unsupported:
        supported = ", ".join(sorted(CONVERT_FORMATS))
        raise click.BadParameter(
            f"convert supports only: {supported}", param_hint="--format"
        )

    page_index = parse_pages(pages) if pages is not None else None
    if input_path.is_dir():
        inputs = sorted(input_path.rglob("*.out"))
        target_dir = output_dir or input_path / "converted"
    else:
        inputs = [input_path]
        target_dir = output_dir or input_path.parent

    if not inputs:
        raise click.ClickException(f"No .out files found under {input_path}")

    generated = []
    for path in inputs:
        generated.extend(
            convert_file(
                input_path=path,
                output_dir=target_dir,
                formats=parsed_formats,
                src=src,
                split_mode=split_mode,
                page_index=page_index,
                dpi=dpi,
                ignore_line_break=ignore_line_break,
                overwrite=overwrite,
            )
        )

    for path in generated:
        click.echo(path)
