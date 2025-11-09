from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import yomitoku_client.client as client_module
import yomitoku_client.utils as utils
from yomitoku_client.client import load_image_bytes
from yomitoku_client.utils import (
    load_image,
    load_pdf,
    load_pdf_to_bytes,
    load_tiff_to_bytes,
)


def test_load_image_bytes_pdf(monkeypatch, tmp_path: Path):
    """PDF の場合: load_pdf_to_bytes が呼ばれ、content_type が image/png になる"""

    called = {}

    def fake_load_pdf_to_bytes(path, dpi):
        called["path"] = path
        called["dpi"] = dpi
        return [b"page1", b"page2"]

    monkeypatch.setattr(client_module, "load_pdf_to_bytes", fake_load_pdf_to_bytes)

    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"dummy")

    img_bytes, ctype = load_image_bytes(str(pdf_path), "application/pdf", dpi=300)

    # 呼び出し確認
    assert called["path"] == str(pdf_path)
    assert called["dpi"] == 300

    # 戻り値確認
    assert img_bytes == [b"page1", b"page2"]
    assert ctype == "image/png"  # PDF → PNG に変換される


def test_load_image_bytes_tiff(monkeypatch, tmp_path: Path):
    """TIFF の場合: load_tiff_to_bytes が呼ばれ、content_type は変更されない"""

    called = {}

    def fake_load_tiff_to_bytes(path):
        called["path"] = path
        return [b"tiff-page"]

    monkeypatch.setattr(client_module, "load_tiff_to_bytes", fake_load_tiff_to_bytes)

    tiff_path = tmp_path / "scan.tiff"
    tiff_path.write_bytes(b"dummy")

    img_bytes, ctype = load_image_bytes(str(tiff_path), "image/tiff")

    assert called["path"] == str(tiff_path)
    assert img_bytes == [b"tiff-page"]
    assert ctype == "image/tiff"


def test_load_image_bytes_others(tmp_path: Path):
    """その他 (jpg/png など) は open() でファイル内容を読み取る"""

    img_path = tmp_path / "photo.jpg"
    img_path.write_bytes(b"image-bytes")

    img_bytes, ctype = load_image_bytes(str(img_path), "image/jpeg")

    # ファイル内容を1要素リストで返す
    assert img_bytes == [b"image-bytes"]
    # content_type は変わらない
    assert ctype == "image/jpeg"


def test_load_image_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_image("no_such_file.jpg")


def test_load_image_unsupported_extension(monkeypatch, tmp_path: Path):
    # サポート拡張子を明示的にセット
    monkeypatch.setattr(
        utils, "SUPPORT_INPUT_FORMAT", ["jpg", "png", "pdf", "tif", "tiff"]
    )

    img_path = tmp_path / "image.bmp"
    img_path.write_bytes(b"dummy")

    with pytest.raises(ValueError) as e:
        load_image(str(img_path))
    assert "Unsupported image format" in str(e.value)


def test_load_image_pdf_rejected(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        utils, "SUPPORT_INPUT_FORMAT", ["jpg", "png", "pdf", "tif", "tiff"]
    )

    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 dummy")

    with pytest.raises(ValueError) as e:
        load_image(str(pdf_path))
    assert "load_pdf()" in str(e.value)


def test_load_image_jpeg_success(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        utils, "SUPPORT_INPUT_FORMAT", ["jpg", "png", "pdf", "tif", "tiff"]
    )

    # 赤っぽい画像を生成 (R=10, G=20, B=30)
    img = Image.new("RGB", (2, 2), (10, 20, 30))
    img_path = tmp_path / "photo.jpg"
    img.save(img_path, format="JPEG")

    pages = load_image(str(img_path))
    assert len(pages) == 1

    arr = pages[0]
    assert isinstance(arr, np.ndarray)
    assert arr.shape == (2, 2, 3)

    # BGR になっているか (元は 10,20,30 → BGR では 30,20,10)
    assert (arr[0, 0] == np.array([30, 20, 10])).all()


def test_load_image_tiff_multipage(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        utils, "SUPPORT_INPUT_FORMAT", ["jpg", "png", "pdf", "tif", "tiff"]
    )

    img1 = Image.new("RGB", (2, 2), (10, 20, 30))
    img2 = Image.new("RGB", (2, 2), (40, 50, 60))

    tiff_path = tmp_path / "multi.tiff"
    img1.save(tiff_path, save_all=True, append_images=[img2], format="TIFF")

    pages = load_image(str(tiff_path))

    assert len(pages) == 2
    arr1, arr2 = pages
    assert arr1.shape == (2, 2, 3)
    assert arr2.shape == (2, 2, 3)

    # 1ページ目: (10,20,30) → BGR (30,20,10)
    assert (arr1[0, 0] == np.array([30, 20, 10])).all()
    # 2ページ目: (40,50,60) → BGR (60,50,40)
    assert (arr2[0, 0] == np.array([60, 50, 40])).all()


def test_load_image_invalid_image_data(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(utils, "SUPPORT_INPUT_FORMAT", ["png"])

    broken_path = tmp_path / "broken.png"
    broken_path.write_bytes(b"not an image")

    with pytest.raises(ValueError) as e:
        load_image(str(broken_path))
    assert "Invalid image data" in str(e.value)


def test_load_pdf_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_pdf("no_such_file.pdf")


def test_load_pdf_unsupported_extension(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(utils, "SUPPORT_INPUT_FORMAT", ["pdf"])

    txt_path = tmp_path / "doc.txt"
    txt_path.write_text("dummy")

    with pytest.raises(ValueError) as e:
        load_pdf(str(txt_path))
    assert "Unsupported image format" in str(e.value)


def test_load_pdf_non_pdf(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(utils, "SUPPORT_INPUT_FORMAT", ["pdf", "png"])

    img_path = tmp_path / "image.png"
    img_path.write_bytes(b"dummy")

    with pytest.raises(ValueError) as e:
        load_pdf(str(img_path))
    assert "Use load_image()" in str(e.value)


def test_load_pdf_success(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(utils, "SUPPORT_INPUT_FORMAT", ["pdf"])

    # フェイクの PdfDocument
    class FakePdfDoc:
        def __init__(self, path):
            self.path = path

        def render(self, converter, scale):
            # PDF 1ページを RGB(10,20,30) の小さい画像に見立てる
            img = Image.new("RGB", (2, 3), (10, 20, 30))
            return [img]

        def close(self):
            pass

    monkeypatch.setattr(utils.pypdfium2, "PdfDocument", FakePdfDoc)

    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 dummy")

    images = load_pdf(str(pdf_path), dpi=144)

    assert len(images) == 1
    arr = images[0]
    assert isinstance(arr, np.ndarray)
    assert arr.shape == (3, 2, 3)  # h, w, c

    # 元色 (10,20,30) → BGR (30,20,10)
    assert (arr[0, 0] == np.array([30, 20, 10])).all()


def test_load_pdf_to_bytes_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_pdf_to_bytes("no_such_file.pdf")


def test_load_pdf_to_bytes_not_pdf(tmp_path: Path):
    img_path = tmp_path / "image.png"
    img_path.write_bytes(b"dummy")

    with pytest.raises(ValueError) as e:
        load_pdf_to_bytes(str(img_path))
    assert "Only PDF files are supported" in str(e.value)


def test_load_pdf_to_bytes_success(monkeypatch, tmp_path: Path):
    class FakePdfDoc:
        def __init__(self, path):
            self.path = path

        def render(self, scale, converter):
            # 2ページの PDF を想定
            img1 = Image.new("RGB", (2, 2), (255, 0, 0))
            img2 = Image.new("RGB", (2, 2), (0, 255, 0))
            return [img1, img2]

        def close(self):
            pass

    monkeypatch.setattr(utils.pypdfium2, "PdfDocument", FakePdfDoc)

    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 dummy")

    pages = load_pdf_to_bytes(str(pdf_path), dpi=144)

    assert len(pages) == 2
    # PNG のマジックナンバー 0x89 0x50 'P' 'N' 'G'
    assert pages[0].startswith(b"\x89PNG")
    assert pages[1].startswith(b"\x89PNG")


def test_load_pdf_to_bytes_failure(monkeypatch, tmp_path: Path):
    class FakePdfDocError:
        def __init__(self, path):
            raise RuntimeError("pdf error")

    monkeypatch.setattr(utils.pypdfium2, "PdfDocument", FakePdfDocError)

    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 dummy")

    with pytest.raises(RuntimeError) as e:
        load_pdf_to_bytes(str(pdf_path))
    assert "Failed to convert PDF to images" in str(e.value)


def test_load_tiff_to_bytes_multipage(tmp_path: Path):
    img1 = Image.new("RGB", (2, 2), (255, 0, 0))
    img2 = Image.new("RGB", (2, 2), (0, 255, 0))

    tiff_path = tmp_path / "multi.tiff"
    img1.save(tiff_path, save_all=True, append_images=[img2], format="TIFF")

    pages = load_tiff_to_bytes(str(tiff_path))

    assert len(pages) == 2
    # TIFF のマジックナンバー (II / MM) が含まれているはず
    assert pages[0][:2] in (b"II", b"MM")
    assert pages[1][:2] in (b"II", b"MM")
