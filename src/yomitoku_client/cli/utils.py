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
