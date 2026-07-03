"""
PDF text extraction helper.
Returns per-page text + simple metadata. OCR fallback only when a page is
image-only (text length < threshold).

Usage:
    from pdf_text_extractor import extract_pdf
    pages = extract_pdf(Path("file.pdf"))  # -> list[{index, text, is_image_only}]
"""
from __future__ import annotations
from pathlib import Path
from typing import Iterable

import fitz  # PyMuPDF

IMAGE_ONLY_THRESHOLD = 30  # chars


def extract_pdf(path: Path, *, ocr: bool = False, dpi: int = 200) -> list[dict]:
    doc = fitz.open(path)
    pages: list[dict] = []
    for i in range(doc.page_count):
        page = doc[i]
        text = (page.get_text("text") or "").strip()
        is_image_only = len(text) < IMAGE_ONLY_THRESHOLD
        ocr_used = False
        if is_image_only and ocr:
            text = _ocr_page(page, dpi=dpi)
            ocr_used = True
        pages.append({
            "index": i,
            "text": text,
            "char_count": len(text),
            "is_image_only": is_image_only,
            "ocr_used": ocr_used,
        })
    doc.close()
    return pages


def _ocr_page(page, *, dpi: int = 200) -> str:
    import pytesseract
    from PIL import Image
    import io
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    try:
        return pytesseract.image_to_string(img, lang="kor+eng").strip()
    except pytesseract.TesseractNotFoundError:
        return ""


def page_text(path: Path, index: int) -> str:
    doc = fitz.open(path)
    try:
        return (doc[index].get_text("text") or "").strip()
    finally:
        doc.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: pdf_text_extractor.py <pdf_path>")
        sys.exit(1)
    p = Path(sys.argv[1])
    pages = extract_pdf(p)
    print(f"{p.name}: {len(pages)} pages")
    for pg in pages[:3]:
        print(f"  [{pg['index']}] chars={pg['char_count']} image_only={pg['is_image_only']}")
        print("    " + pg["text"][:120].replace("\n", " "))
