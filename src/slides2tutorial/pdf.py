"""PDF page rendering helpers."""

from __future__ import annotations

import base64
from pathlib import Path

import fitz


def open_pdf(path: Path) -> fitz.Document:
    """Open a PDF and raise a clear error if it cannot be read."""

    try:
        return fitz.open(path)
    except Exception as exc:  # pragma: no cover - PyMuPDF exception types vary
        raise ValueError(f"Could not open PDF: {path}") from exc


def render_page_to_png_data_url(document: fitz.Document, page_index: int, dpi: int) -> str:
    """Render a PDF page as a PNG data URL for multimodal chat APIs."""

    page = document.load_page(page_index)
    pixmap = page.get_pixmap(dpi=dpi, alpha=False)
    png_bytes = pixmap.tobytes("png")
    encoded = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"
