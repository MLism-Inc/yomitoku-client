import json
from pathlib import Path

import click

from yomitoku_client.constants import (
    API_DOCUMENT_ANALYZER,
    API_TABLE_SEMANTIC_PARSER,
    SUPPORT_API,
)
from yomitoku_client.exceptions import DocumentAnalysisError

from .utils import (
    parse_formats,
    parse_model,
    parse_pages,
    resolve_tsp_options,
    tsp_options,
)

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
    api: str = API_DOCUMENT_ANALYZER,
    output_mode: str = "structured",
    template: str | None = None,
    studio_template: str | None = None,
) -> list[Path]:
    """Convert one YomiToku Batch Transform JSON output."""
    try:
        with input_path.open(encoding="utf-8") as f:
            raw_result = json.load(f)
        if api == API_TABLE_SEMANTIC_PARSER and (
            isinstance(raw_result, list)
            or isinstance(raw_result, dict)
            and "result" not in raw_result
        ):
            raw_result = {"result": raw_result}
        model = parse_model(raw_result, api)
    except (OSError, json.JSONDecodeError, DocumentAnalysisError) as e:
        raise click.ClickException(f"Failed to read {input_path}: {e}") from e

    output_dir.mkdir(parents=True, exist_ok=True)
    base = output_dir / _output_stem(input_path)
    source_path = _find_source(input_path, src)
    outputs = []

    if api == API_TABLE_SEMANTIC_PARSER:
        if formats != ["json"]:
            raise click.ClickException("table-semantic-parser supports only: json")
        output_path = Path(f"{base}.json")
        indices = list(model.pages) if page_index is None else page_index
        outputs = (
            [output_path]
            if split_mode == "combine"
            else [
                output_path.with_name(f"{output_path.stem}_page_{idx}.json")
                for idx in indices
            ]
        )
        for path in outputs:
            if path.resolve() == input_path.resolve():
                raise click.ClickException(
                    "Choose --output-dir to avoid replacing the input JSON."
                )
            if path.exists() and not overwrite:
                raise click.ClickException(
                    f"Output already exists: {path}. Use --overwrite to replace it."
                )
        try:
            if template:
                model.load_template_json(template)
            if studio_template:
                if source_path is None:
                    raise ValueError(
                        "--studio-template requires --src with the original document"
                    )
                from yomitoku_client.studio_form_template import (
                    apply_studio_template_to_document,
                )

                apply_studio_template_to_document(
                    model, studio_template, source_path, dpi=dpi
                )
            model.to_json(
                str(output_path),
                mode=split_mode,
                page_index=page_index,
                output_mode=output_mode,
            )
        except (ValueError, OSError, KeyError) as error:
            raise click.ClickException(
                f"Failed to export TSP result: {error}"
            ) from error
        return outputs

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
@tsp_options
@click.option(
    "--api",
    "-a",
    type=click.Choice(SUPPORT_API),
    default=API_DOCUMENT_ANALYZER,
    show_default=True,
)
@click.argument(
    "input_path",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--format",
    "formats",
    "-f",
    default=None,
    help="Output formats: md,csv,html (default: md); TSP: json (default).",
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
    api: str,
    raw: bool,
    simple: bool,
    template: str | None,
    studio_template: str | None,
):
    """Convert saved Batch Transform output or raw TSP JSON locally."""
    output_mode = resolve_tsp_options(api, raw, simple, template, studio_template)
    formats = formats or ("json" if api == API_TABLE_SEMANTIC_PARSER else "md")
    try:
        parsed_formats = parse_formats(formats)
    except ValueError as e:
        raise click.BadParameter(str(e), param_hint="--format") from e

    supported_formats = (
        {"json"} if api == API_TABLE_SEMANTIC_PARSER else CONVERT_FORMATS
    )
    unsupported = set(parsed_formats) - supported_formats
    if unsupported:
        supported = ", ".join(sorted(supported_formats))
        raise click.BadParameter(
            f"convert supports only: {supported}", param_hint="--format"
        )

    page_index = parse_pages(pages) if pages is not None else None
    if input_path.is_dir():
        inputs = sorted(input_path.rglob("*.out"))
        if api == API_TABLE_SEMANTIC_PARSER:
            inputs += sorted(input_path.rglob("*.json"))
        target_dir = output_dir or input_path / "converted"
        if api == API_TABLE_SEMANTIC_PARSER:
            target = target_dir.resolve()
            inputs = [
                path
                for path in inputs
                if (
                    target == input_path.resolve()
                    or target not in path.resolve().parents
                )
                and (template is None or path.resolve() != Path(template).resolve())
                and (
                    studio_template is None
                    or path.resolve() != Path(studio_template).resolve()
                )
            ]
    else:
        inputs = [input_path]
        target_dir = output_dir or input_path.parent

    if not inputs:
        extensions = ".out/.json" if api == API_TABLE_SEMANTIC_PARSER else ".out"
        raise click.ClickException(f"No {extensions} files found under {input_path}")

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
                api=api,
                output_mode=output_mode,
                template=template,
                studio_template=studio_template,
            )
        )

    for path in generated:
        click.echo(path)
