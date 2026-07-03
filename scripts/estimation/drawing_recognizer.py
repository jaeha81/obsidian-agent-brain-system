"""
Drawing recognizer.
Input: PDF path (architectural drawing set).
Output: per-page inventory — drawing codes, category, role guess, material-list flag.

Run:
    python -X utf8 scripts/estimation/drawing_recognizer.py <pdf_path> [--out <json>]
"""
from __future__ import annotations
import json
import re
import sys
from collections import Counter
from pathlib import Path

from pdf_text_extractor import extract_pdf

DRAWING_CODE_RE = re.compile(r"\b([A-Z]{1,3})-?(\d{3,4}[A-Z]?)\b")

CATEGORY_BY_PREFIX = {
    "P": "PLAN",
    "E": "ELECTRICAL",
    "K": "KITCHEN",
    "D": "DETAIL",
    "F": "FURNITURE",
    "S": "SIGNAGE",
    "M": "MECHANICAL",
    "FF": "FF&E",
    "CD": "CONSTRUCTION_DOC",
}

ROLE_KEYWORDS = {
    "PLAN_FLOOR": ["FLOOR PLAN", "평면도"],
    "PLAN_RCP": ["RCP", "REFLECTED CEILING", "천장도"],
    "PLAN_WALL_FINISH": ["WALL FINISH", "벽마감", "마감재"],
    "PLAN_FURNITURE": ["FURNITURE PLAN", "가구배치"],
    "PLAN_ELEC": ["POWER PLAN", "LIGHTING PLAN", "전기"],
    "ELEVATION": ["ELEVATION", "입면"],
    "SECTION": ["SECTION", "단면"],
    "DETAIL": ["DETAIL", "DTL"],
    "KITCHEN_SCHEDULE": ["KITCHEN SCHEDULE", "주방"],
    "SIGNAGE": ["SIGNAGE", "SIGN"],
    "FURNITURE_SCHEDULE": ["FURNITURE SCHEDULE"],
    "MATERIAL_LIST": ["MATERIAL LIST", "FINISH SCHEDULE", "마감재 리스트"],
    "COVER": ["COVER", "표지", "INDEX"],
}

MATERIAL_KEYWORDS = [
    "MATERIAL", "FINISH", "SCHEDULE", "LEGEND", "스펙", "SPEC",
    "F1", "F2", "F3", "W1", "W2", "CG1", "PT1",
]


def _category(prefix: str) -> str | None:
    return CATEGORY_BY_PREFIX.get(prefix.upper())


def _detect_codes(text: str) -> list[tuple[str, str]]:
    out = []
    for prefix, num in DRAWING_CODE_RE.findall(text):
        if _category(prefix):
            out.append((prefix.upper(), num))
    return out


def _guess_role(text: str) -> str | None:
    upper = text.upper()
    best = None
    best_score = 0
    for role, kws in ROLE_KEYWORDS.items():
        score = sum(1 for kw in kws if kw.upper() in upper)
        if score > best_score:
            best_score = score
            best = role
    return best if best_score > 0 else None


def _is_material_list(text: str) -> bool:
    upper = text.upper()
    hits = sum(1 for kw in MATERIAL_KEYWORDS if kw.upper() in upper)
    return hits >= 3


def recognize(pdf_path: Path, *, ocr: bool = False) -> dict:
    pages_text = extract_pdf(pdf_path, ocr=ocr)
    pages: list[dict] = []
    category_count: Counter = Counter()
    role_count: Counter = Counter()
    code_total: Counter = Counter()
    material_pages: list[int] = []

    for pg in pages_text:
        text = pg["text"]
        codes = _detect_codes(text)
        cats = sorted({_category(p) for p, _ in codes if _category(p)})
        role = _guess_role(text)
        material = _is_material_list(text)

        for prefix, num in codes:
            code_total[f"{prefix}-{num}"] += 1
        for c in cats:
            category_count[c] += 1
        if role:
            role_count[role] += 1
        if material:
            material_pages.append(pg["index"])

        pages.append({
            "page_index": pg["index"],
            "char_count": pg["char_count"],
            "image_only": pg["is_image_only"],
            "ocr_used": pg["ocr_used"],
            "drawing_codes": [f"{p}-{n}" for p, n in codes[:20]],
            "categories": cats,
            "role_guess": role,
            "is_material_list": material,
        })

    return {
        "pdf_path": str(pdf_path),
        "page_count": len(pages),
        "image_only_pages": sum(1 for p in pages if p["image_only"]),
        "category_count": dict(category_count),
        "role_count": dict(role_count),
        "drawing_code_top": code_total.most_common(50),
        "material_pages": material_pages,
        "pages": pages,
    }


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", default=None)
    ap.add_argument("--ocr", action="store_true")
    a = ap.parse_args()

    result = recognize(Path(a.pdf), ocr=a.ocr)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"Saved: {a.out}")
    else:
        print(text[:2000])
    print(f"\nSummary: {result['page_count']} pages, "
          f"image_only={result['image_only_pages']}, "
          f"categories={result['category_count']}, "
          f"material_pages={len(result['material_pages'])}")


if __name__ == "__main__":
    main()
