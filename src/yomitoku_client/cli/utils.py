import click

from yomitoku_client import parse_pydantic_model, parse_table_semantic_parser
from yomitoku_client.constants import (
    API_TABLE_SEMANTIC_PARSER,
    SUPPORT_OUTPUT_FORMAT,
    SUPPORT_TSP_OUTPUT_FORMAT,
)


def tsp_options(command):
    """Shared local TSP output/template options."""
    options = [
        click.option("--raw", is_flag=True, help="Save raw TSP cells and references."),
        click.option("--simple", is_flag=True, help="Save text-only TSP structure."),
        click.option(
            "--template",
            type=click.Path(exists=True, dir_okay=False),
            help="Apply a TSP template locally before export.",
        ),
        click.option(
            "--studio-template",
            type=click.Path(exists=True, dir_okay=False),
            help="Apply a YomiToku Studio form-template (v2/v3).",
        ),
    ]
    for option in reversed(options):
        command = option(command)
    return command


def resolve_tsp_options(api, raw, simple, template, studio_template):
    if raw and simple:
        raise click.UsageError("--raw and --simple are mutually exclusive")
    selected = "raw" if raw else "simple" if simple else "structured"
    if template and studio_template:
        raise click.UsageError(
            "--template and --studio-template are mutually exclusive"
        )
    if api != API_TABLE_SEMANTIC_PARSER and (
        selected != "structured" or template or studio_template
    ):
        raise click.UsageError(
            "TSP output/template options require --api table-semantic-parser"
        )
    return selected


def parse_pages(pages_str):
    pages = set()
    for part in pages_str.split(","):
        if "-" in part:
            start, end = map(int, part.split("-"))
            pages.update(range(start, end + 1))
        else:
            pages.add(int(part))
    return sorted(pages)


def get_format_ext(file_format: str) -> str:
    file_format = file_format.lower()
    if file_format in ["json"]:
        return "json"
    elif file_format in ["csv"]:
        return "csv"
    elif file_format in ["html", "htm"]:
        return "html"
    elif file_format in ["markdown", "md"]:
        return "md"
    elif file_format in ["pdf"]:
        return "pdf"
    else:
        raise ValueError(f"Unsupported format: {file_format}")


def parse_formats(formats):
    formats = formats.lower()
    formats = formats.split(",")

    parsed_formats = []
    for file_format in formats:
        if file_format not in SUPPORT_OUTPUT_FORMAT:
            raise ValueError(f"Unsupported format: {file_format}")

        if file_format == "markdown":
            file_format = "md"

        parsed_formats.append(file_format)

    if len(parsed_formats) == 0:
        raise ValueError("At least one format must be specified.")

    return parsed_formats


def parse_model(result: dict, api: str):
    """Parse a SageMaker response with the model matching the API"""
    if api == API_TABLE_SEMANTIC_PARSER:
        return parse_table_semantic_parser(result)
    return parse_pydantic_model(result)


def validate_formats(formats: list[str], api: str) -> list[str]:
    """Reject output formats the API cannot produce"""
    if api != API_TABLE_SEMANTIC_PARSER:
        return formats

    unsupported = set(formats) - set(SUPPORT_TSP_OUTPUT_FORMAT)
    if unsupported:
        supported = ", ".join(SUPPORT_TSP_OUTPUT_FORMAT)
        raise ValueError(
            f"{API_TABLE_SEMANTIC_PARSER} supports only: {supported} "
            f"(got: {', '.join(sorted(unsupported))})",
        )
    return formats


def export_model(
    model,
    api: str,
    output_base: str,
    formats: list[str],
    image_path: str | None = None,
    split_mode: str = "combine",
    page_index: list | None = None,
    dpi: int = 200,
    ignore_line_break: bool = False,
    output_mode: str = "structured",
    template: str | None = None,
    studio_template: str | None = None,
) -> None:
    """
    Save a parsed result in every requested format

    Args:
        model: MultiPageDocumentResult or MultiPageTableSemanticParserResult
        api: API that produced the result
        output_base: Output path without its extension
        formats: Output formats (json, csv, html, md, pdf)
        image_path: Original document, used for figures and searchable PDF
        split_mode: 'combine' or 'separate'
        page_index: Pages to export
        dpi: DPI used when the original document is a PDF
        ignore_line_break: Whether to drop line breaks (document analyzer only)
        template: YomiToku-Pro table correction template
        studio_template: YomiToku Studio form-template (v2/v3)
    """
    if api == API_TABLE_SEMANTIC_PARSER:
        try:
            if template:
                model.load_template_json(template)
            if studio_template:
                if image_path is None:
                    raise ValueError(
                        "Studio template application requires the source document"
                    )
                from yomitoku_client.studio_form_template import (
                    apply_studio_template_to_document,
                )

                apply_studio_template_to_document(
                    model, studio_template, image_path, dpi=dpi
                )
            model.to_json(
                output_path=f"{output_base}.json",
                mode=split_mode,
                page_index=page_index,
                output_mode=output_mode,
            )
        except (ValueError, OSError, KeyError) as error:
            raise click.ClickException(
                f"Failed to export TSP result: {error}"
            ) from error
        return

    common = {
        "mode": split_mode,
        "page_index": page_index,
        "ignore_line_break": ignore_line_break,
    }
    if "json" in formats:
        model.to_json(output_path=f"{output_base}.json", **common)
    if "csv" in formats:
        model.to_csv(output_path=f"{output_base}.csv", **common)
    if "html" in formats:
        model.to_html(
            output_path=f"{output_base}.html",
            image_path=image_path,
            dpi=dpi,
            **common,
        )
    if "md" in formats:
        model.to_markdown(
            output_path=f"{output_base}.md",
            image_path=image_path,
            dpi=dpi,
            **common,
        )
    if "pdf" in formats:
        model.to_pdf(
            output_path=f"{output_base}.pdf",
            image_path=image_path,
            mode=split_mode,
            dpi=dpi,
            page_index=page_index,
        )


def visualize_model(
    model,
    api: str,
    image_path: str,
    vis_mode: str,
    output_directory: str | None = None,
    page_index: list | None = None,
    dpi: int = 200,
) -> None:
    """
    Save the visualizations selected with --vis_mode

    The Table Semantic Parser has no visualization yet, so its results are
    skipped.
    """
    if vis_mode == "none":
        return

    if api == API_TABLE_SEMANTIC_PARSER:
        click.echo(
            f"Visualization is not supported for {API_TABLE_SEMANTIC_PARSER}; skipped.",
        )
        return

    modes = {"both": ["ocr", "layout"]}.get(vis_mode, [vis_mode])
    for mode in modes:
        model.visualize(
            image_path=image_path,
            mode=mode,
            output_directory=output_directory,
            dpi=dpi,
            page_index=page_index,
        )
