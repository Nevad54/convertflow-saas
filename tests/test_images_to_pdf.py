from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from pypdf import PdfReader

import execution.pdf_tools as pdf_tools


@pytest.fixture(autouse=True)
def disable_ollama(monkeypatch):
    monkeypatch.setenv("OLLAMA_ENABLED", "false")


def _assert_pdf_file(path: Path, expected_pages: int) -> None:
    assert path.exists()
    assert path.stat().st_size > 0
    assert path.read_bytes().startswith(b"%PDF-")
    reader = PdfReader(str(path))
    assert len(reader.pages) == expected_pages


def _assert_pdf_bytes(data: bytes, expected_pages: int) -> None:
    assert data.startswith(b"%PDF-")
    reader = PdfReader(io.BytesIO(data))
    assert len(reader.pages) == expected_pages


def _make_rgba_png(path: Path) -> Path:
    image = Image.new("RGBA", (180, 120), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((12, 12, 168, 108), radius=18, fill=(40, 120, 220, 180))
    draw.line((20, 95, 160, 25), fill=(0, 40, 120, 255), width=6)
    image.save(path, format="PNG")
    image.close()
    return path


def _make_paletted_png(path: Path) -> Path:
    image = Image.new("P", (180, 120))
    palette: list[int] = []
    for index in range(256):
        palette.extend((index, 255 - index, (index * 3) % 256))
    image.putpalette(palette)
    for x in range(180):
        for y in range(120):
            image.putpixel((x, y), (x + y) % 256)
    image.save(path, format="PNG")
    image.close()
    return path


def _make_grayscale_png(path: Path) -> Path:
    image = Image.new("L", (180, 120), color=235)
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 18, 164, 102), outline=48, width=4)
    draw.ellipse((42, 30, 138, 94), fill=128)
    image.save(path, format="PNG")
    image.close()
    return path


def _make_tall_png(path: Path) -> Path:
    image = Image.new("RGB", (120, 420), color=(250, 246, 240))
    draw = ImageDraw.Draw(image)
    for index, top in enumerate(range(18, 390, 36), start=1):
        fill = (20 + index * 6, 90 + index * 3, 160)
        draw.rectangle((16, top, 104, top + 22), outline=(20, 40, 70), fill=fill)
    image.save(path, format="PNG")
    image.close()
    return path


@pytest.mark.parametrize(
    ("builder", "filename"),
    [
        (_make_rgba_png, "rgba.png"),
        (_make_paletted_png, "paletted.png"),
        (_make_grayscale_png, "grayscale.png"),
        (_make_tall_png, "tall.png"),
    ],
)
def test_images_to_pdf_handles_png_variants(tmp_path: Path, builder, filename: str):
    source = builder(tmp_path / filename)
    output = tmp_path / f"{source.stem}.pdf"

    pdf_tools.images_to_pdf([source], output)

    _assert_pdf_file(output, expected_pages=1)


def test_images_to_pdf_handles_multiple_images(tmp_path: Path):
    sources = [
        _make_rgba_png(tmp_path / "01_rgba.png"),
        _make_paletted_png(tmp_path / "02_paletted.png"),
        _make_tall_png(tmp_path / "03_tall.png"),
    ]
    output = tmp_path / "combined.pdf"

    pdf_tools.images_to_pdf(sources, output)

    _assert_pdf_file(output, expected_pages=len(sources))


def test_images_to_pdf_route_accepts_multiple_uploads(tmp_path: Path):
    import app_local

    client = TestClient(app_local.app, raise_server_exceptions=True)
    first = _make_rgba_png(tmp_path / "upload_rgba.png")
    second = _make_grayscale_png(tmp_path / "upload_grayscale.png")

    response = client.post(
        "/convert/images-to-pdf",
        files=[
            ("files", (first.name, first.read_bytes(), "image/png")),
            ("files", (second.name, second.read_bytes(), "image/png")),
        ],
    )

    assert response.status_code == 200
    assert response.headers["content-disposition"].endswith('filename="images.pdf"')
    _assert_pdf_bytes(response.content, expected_pages=2)
