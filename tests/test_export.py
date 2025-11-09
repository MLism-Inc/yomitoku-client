import json
from pathlib import Path

import pytest

from yomitoku_client import parse_pydantic_model

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def raw_response_json() -> dict:
    path = DATA_DIR / "image_pdf.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def model(raw_response_json):
    return parse_pydantic_model(raw_response_json)


@pytest.fixture
def target_file() -> str:
    """OCR 元の画像 / PDF のパス."""
    return str(DATA_DIR / "image.pdf")


def test_to_csv_variants(model, tmp_path: Path):
    # sample.csv として保存
    csv_path = tmp_path / "sample.csv"
    out = model.to_csv(output_path=str(csv_path))
    assert csv_path.exists()

    # demo フォルダ内に保存
    demo_dir = tmp_path / "demo"
    demo_dir.mkdir(exist_ok=True)
    demo_csv = demo_dir / "sample.csv"
    out = model.to_csv(output_path=str(demo_csv))
    assert demo_csv.exists()

    num_pages = len(model.pages)

    # ページごとに保存（mode="separate"）
    sep_csv = tmp_path / "separate.csv"
    out = model.to_csv(output_path=str(sep_csv), mode="separate")
    for i in range(num_pages):
        p = f"{tmp_path}/{sep_csv.stem}_page_{i}{sep_csv.suffix}"
        assert Path(p).exists()

    assert len(out) == num_pages

    # 指定ページのみ保存（リスト指定と int 指定の両方）
    specify_csv = tmp_path / "separate_spesify.csv"
    out = model.to_csv(
        output_path=str(specify_csv),
        mode="separate",
        page_index=[0],
    )
    p = f"{tmp_path}/{specify_csv.stem}_page_0{specify_csv.suffix}"
    assert Path(p).exists()
    assert len(out) == 1

    specify_csv = tmp_path / "separate_spesify_int.csv"
    out = model.to_csv(
        output_path=str(specify_csv),
        mode="separate",
        page_index=0,
    )
    p = f"{tmp_path}/{specify_csv.stem}_page_0{specify_csv.suffix}"
    assert Path(p).exists()
    assert len(out) == 1

    # 改行を無視して保存
    ignore_lb_csv = tmp_path / "ignore_lb.csv"
    out = model.to_csv(
        output_path=str(ignore_lb_csv),
        ignore_line_break=True,
    )
    assert ignore_lb_csv.exists()


def test_to_markdown_variants(model, target_file, tmp_path: Path):
    # demo フォルダ内に保存
    demo_dir = tmp_path / "demo"
    demo_dir.mkdir(exist_ok=True)
    md_path = demo_dir / "sample.md"
    out = model.to_markdown(
        output_path=str(md_path),
        image_path=target_file,
    )
    assert md_path.exists()

    # 通常パスに保存
    md_path2 = tmp_path / "sample.md"
    out = model.to_markdown(
        output_path=str(md_path2),
        image_path=target_file,
    )
    assert md_path2.exists()

    num_pages = len(model.pages)

    # ページごとに保存（mode="separate"）
    sep_md = tmp_path / "separate.md"
    out = model.to_markdown(
        output_path=str(sep_md),
        image_path=target_file,
        mode="separate",
    )

    for i in range(num_pages):
        p = f"{tmp_path}/{sep_md.stem}_page_{i}{sep_md.suffix}"
        assert Path(p).exists()

    assert len(out) == num_pages
    assert Path(tmp_path / "figures").exists()
    figure_files = list((tmp_path / "figures").glob("*.png"))
    assert len(figure_files) > 0

    # 指定ページのみ（リスト指定）
    specify_md = tmp_path / "separate_spesify.md"
    out = model.to_markdown(
        output_path=str(specify_md),
        image_path=target_file,
        mode="separate",
        page_index=[0],
    )
    p = f"{tmp_path}/{specify_md.stem}_page_0{specify_md.suffix}"
    assert Path(p).exists()
    assert len(out) == 1

    # 指定ページのみ（int 指定）
    specify_md = tmp_path / "separate_spesify_int.md"
    out = model.to_markdown(
        output_path=str(specify_md),
        image_path=target_file,
        mode="separate",
        page_index=0,
    )
    p = f"{tmp_path}/{specify_md.stem}_page_0{specify_md.suffix}"
    assert Path(p).exists()
    assert len(out) == 1

    # 改行を無視して保存
    ignore_lb_md = tmp_path / "ignore_lb.md"
    out = model.to_markdown(
        output_path=str(ignore_lb_md),
        image_path=target_file,
        ignore_line_break=True,
    )
    assert ignore_lb_md.exists()


def test_to_html_variants(model, target_file, tmp_path: Path):
    # 通常パスに保存
    html_path = tmp_path / "sample.html"
    out = model.to_html(
        output_path=str(html_path),
        image_path=target_file,
    )
    assert html_path.exists()

    # demo フォルダ内に保存
    demo_dir = tmp_path / "demo"
    demo_dir.mkdir(exist_ok=True)
    demo_html = demo_dir / "sample.html"
    out = model.to_html(
        output_path=str(demo_html),
        image_path=target_file,
    )
    assert demo_html.exists()
    assert Path(tmp_path / "figures").exists()
    figure_files = list((tmp_path / "figures").glob("*.png"))
    assert len(figure_files) > 0

    num_pages = len(model.pages)

    # ページごとに保存（mode="separate"）
    sep_html = tmp_path / "separate.html"
    out = model.to_html(
        output_path=str(sep_html),
        image_path=target_file,
        mode="separate",
    )

    for i in range(num_pages):
        p = f"{tmp_path}/{sep_html.stem}_page_{i}{sep_html.suffix}"
        assert Path(p).exists()

    assert len(out) == num_pages

    # 指定ページのみ（リスト指定）
    specify_html = tmp_path / "separate_spesify.html"
    out = model.to_html(
        output_path=str(specify_html),
        image_path=target_file,
        mode="separate",
        page_index=[0],
    )
    p = f"{tmp_path}/{specify_html.stem}_page_0{specify_html.suffix}"
    assert Path(p).exists()
    assert len(out) == 1

    # 指定ページのみ（int 指定）
    specify_html = tmp_path / "separate_spesify_int.html"
    out = model.to_html(
        output_path=str(specify_html),
        image_path=target_file,
        mode="separate",
        page_index=0,
    )
    p = f"{tmp_path}/{specify_html.stem}_page_0{specify_html.suffix}"
    assert Path(p).exists()
    assert len(out) == 1

    # 改行を無視して保存
    ignore_lb_html = tmp_path / "ignore_lb.html"
    out = model.to_html(
        output_path=str(ignore_lb_html),
        image_path=target_file,
        ignore_line_break=True,
    )
    assert ignore_lb_html.exists()


def test_to_json_variants(model, tmp_path: Path):
    # 通常パスに保存
    json_path = tmp_path / "sample.json"
    out = model.to_json(output_path=str(json_path))
    assert json_path.exists()

    # demo フォルダ内に保存
    demo_dir = tmp_path / "demo"
    demo_dir.mkdir(exist_ok=True)
    demo_json = demo_dir / "sample.json"
    out = model.to_json(output_path=str(demo_json))
    assert demo_json.exists()

    num_pages = len(model.pages)

    # ページごとに保存（mode="separate"）
    sep_json = tmp_path / "separate.json"
    out = model.to_json(output_path=str(sep_json), mode="separate")

    for i in range(num_pages):
        p = f"{tmp_path}/{sep_json.stem}_page_{i}{sep_json.suffix}"
        assert Path(p).exists()

    assert len(out) == num_pages

    # 指定ページのみ（リスト指定）
    specify_json = tmp_path / "separate_spesify.json"
    out = model.to_json(
        output_path=str(specify_json),
        mode="separate",
        page_index=[0],
    )
    p = f"{tmp_path}/{specify_json.stem}_page_0{specify_json.suffix}"
    assert Path(p).exists()
    assert len(out) == 1

    # 指定ページのみ（int 指定）
    specify_json = tmp_path / "separate_spesify_int.json"
    out = model.to_json(
        output_path=str(specify_json),
        mode="separate",
        page_index=0,
    )
    p = f"{tmp_path}/{specify_json.stem}_page_0{specify_json.suffix}"
    assert Path(p).exists()
    assert len(out) == 1

    # 改行を無視して保存
    ignore_lb_json = tmp_path / "ignore_lb.json"
    out = model.to_json(
        output_path=str(ignore_lb_json),
        ignore_line_break=True,
    )
    assert ignore_lb_json.exists()


def test_to_pdf_variants(model, target_file, tmp_path: Path):
    # 通常パスに保存
    pdf_path = tmp_path / "sample.pdf"
    model.to_pdf(
        output_path=str(pdf_path),
        image_path=target_file,
    )
    assert pdf_path.exists()

    # demo フォルダ内に保存
    demo_dir = tmp_path / "demo"
    demo_dir.mkdir(exist_ok=True)
    demo_pdf = demo_dir / "sample.pdf"
    model.to_pdf(
        output_path=str(demo_pdf),
        image_path=target_file,
    )
    assert demo_pdf.exists()

    num_pages = len(model.pages)

    # ページごとに保存（mode="separate"）
    sep_pdf = tmp_path / "separate.pdf"
    model.to_pdf(
        output_path=str(sep_pdf),
        image_path=target_file,
        mode="separate",
    )

    for i in range(num_pages):
        p = f"{tmp_path}/{sep_pdf.stem}_page_{i}{sep_pdf.suffix}"
        assert Path(p).exists()

    # 指定ページのみ（リスト指定）
    specify_pdf = tmp_path / "separate_spesify.pdf"
    model.to_pdf(
        output_path=str(specify_pdf),
        image_path=target_file,
        mode="separate",
        page_index=[0],
    )
    p = f"{tmp_path}/{specify_pdf.stem}_page_0{specify_pdf.suffix}"
    assert Path(p).exists()

    # 指定ページのみ（int 指定）
    specify_pdf = tmp_path / "separate_spesify_int.pdf"
    model.to_pdf(
        output_path=str(specify_pdf),
        image_path=target_file,
        mode="separate",
        page_index=0,
    )
    p = f"{tmp_path}/{specify_pdf.stem}_page_0{specify_pdf.suffix}"
    assert Path(p).exists()


def test_visualize_ocr(model, target_file, tmp_path: Path):
    """
    model.visualize の基本動作確認.
    - 例外が出ないこと
    - 画像配列を返していること
    - 返却された配列を np.ndarray に変換できること
    """
    demo_dir = tmp_path / "demo"
    demo_dir.mkdir(exist_ok=True)

    basename = Path(target_file).stem

    vis = model.visualize(
        image_path=target_file,
        mode="ocr",
        page_index=None,
        output_directory=str(demo_dir),
    )

    for i in range(len(model.pages)):
        assert Path(demo_dir / f"{basename}_ocr_page_{i}.jpg").exists()

    # 返り値が non-empty であること
    assert vis
    first = vis[0]

    # H x W x C の配列前提
    assert len(first.shape) == 3
    assert first.shape[2] in (3, 4)  # BGR or BGRA

    vis = model.visualize(
        image_path=target_file,
        mode="layout",
        page_index=None,
        output_directory=str(demo_dir),
    )

    for i in range(len(model.pages)):
        assert Path(demo_dir / f"{basename}_layout_page_{i}.jpg").exists()

        # 返り値が non-empty であること
    assert vis
    first = vis[0]

    # H x W x C の配列前提
    assert len(first.shape) == 3
    assert first.shape[2] in (3, 4)  # BGR or BGRA
