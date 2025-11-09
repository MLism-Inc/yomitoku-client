from yomitoku_client.constants import SUPPORT_OUTPUT_FORMAT


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
