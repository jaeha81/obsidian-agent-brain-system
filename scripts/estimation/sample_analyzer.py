"""
Step 3 sample analyzer.
- PDF: page count, drawing-number candidates, text-extractable ratio.
- XLS: sheets, rows/cols, header peek.
- MATERIAL LIST: detect by keyword frequency on each page.

Run once on the Chipotle samples and write a JSON + Markdown report.
"""
from __future__ import annotations
import json
import re
import sys
import time
from pathlib import Path
from collections import Counter, defaultdict

import fitz  # PyMuPDF
import pandas as pd

PDF_PATH = Path(r"G:\내 드라이브\견적시스템\temp_1782269609990.-1588570946.pdf")
XLS_PATH = Path(r"G:\내 드라이브\견적시스템\temp_1782269596641.2097014861.xls")
OUT_DIR = Path(r"G:\내 드라이브\obsidian-agent-brain-system\data\estimation_samples")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Drawing code pattern: P-101 / E-201 / K-301 / D-401 / F-501 / S-601 etc.
DRAWING_CODE_RE = re.compile(r"\b([A-Z]{1,3})-?(\d{3,4}[A-Z]?)\b")

# Category map based on prefix
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

MATERIAL_KEYWORDS = [
    "MATERIAL", "FINISH", "스펙", "SPEC", "SCHEDULE", "LEGEND",
    "F1", "F2", "F3", "W1", "W2", "CG1", "PT1",
]


def analyze_pdf(path: Path) -> dict:
    doc = fitz.open(path)
    n = doc.page_count
    result = {
        "path": str(path),
        "size_mb": round(path.stat().st_size / 1024 / 1024, 2),
        "page_count": n,
        "pages": [],
        "drawing_codes_total": Counter(),
        "category_count": Counter(),
        "material_pages": [],
        "text_extractable_pages": 0,
        "image_only_pages": 0,
    }

    for i in range(n):
        page = doc[i]
        text = page.get_text("text") or ""
        clean = text.strip()

        codes = DRAWING_CODE_RE.findall(clean)
        # Drop noise like "1-23" by requiring prefix in known categories OR length>=4 numeric
        kept = []
        cats = set()
        for prefix, num in codes:
            if prefix in CATEGORY_BY_PREFIX:
                code = f"{prefix}-{num}"
                kept.append(code)
                cats.add(CATEGORY_BY_PREFIX[prefix])
                result["drawing_codes_total"][code] += 1
                result["category_count"][CATEGORY_BY_PREFIX[prefix]] += 1

        upper = clean.upper()
        material_hits = sum(1 for k in MATERIAL_KEYWORDS if k.upper() in upper)
        is_material = material_hits >= 3

        if len(clean) >= 50:
            result["text_extractable_pages"] += 1
        else:
            result["image_only_pages"] += 1

        page_info = {
            "page_index": i,
            "text_len": len(clean),
            "drawing_codes": kept[:10],
            "categories": sorted(cats),
            "material_score": material_hits,
            "is_material_list": is_material,
        }
        result["pages"].append(page_info)
        if is_material:
            result["material_pages"].append(i)

    doc.close()
    result["drawing_codes_total"] = result["drawing_codes_total"].most_common(50)
    result["category_count"] = dict(result["category_count"])
    return result


def analyze_xls(path: Path) -> dict:
    # .xls (BIFF) — xlrd needed, but pandas 2.x dropped it. Try multiple engines.
    info = {
        "path": str(path),
        "size_kb": round(path.stat().st_size / 1024, 2),
        "sheets": [],
        "engine_used": None,
        "error": None,
    }
    for engine in ("xlrd", "openpyxl", "calamine", None):
        try:
            kw = {"engine": engine} if engine else {}
            xls = pd.ExcelFile(path, **kw)
            info["engine_used"] = engine or "auto"
            for s in xls.sheet_names:
                try:
                    df = pd.read_excel(path, sheet_name=s, header=None, **kw)
                    nrows, ncols = df.shape
                    head_rows = df.head(15).fillna("").astype(str).values.tolist()
                    info["sheets"].append({
                        "name": s,
                        "rows": int(nrows),
                        "cols": int(ncols),
                        "head_preview": head_rows,
                    })
                except Exception as e:
                    info["sheets"].append({"name": s, "error": str(e)})
            return info
        except Exception as e:
            info["error"] = f"{engine}: {e}"
            continue
    return info


def main() -> None:
    t0 = time.time()
    print("[1/2] PDF 분석 시작 ...", flush=True)
    pdf = analyze_pdf(PDF_PATH)
    print(f"  - {pdf['page_count']} pages, {pdf['text_extractable_pages']} text-extractable, "
          f"{pdf['image_only_pages']} image-only", flush=True)
    print(f"  - categories: {pdf['category_count']}", flush=True)
    print(f"  - material pages: {pdf['material_pages'][:10]}{'...' if len(pdf['material_pages'])>10 else ''}", flush=True)

    print("[2/2] XLS 분석 시작 ...", flush=True)
    xls = analyze_xls(XLS_PATH)
    print(f"  - engine: {xls.get('engine_used')}  sheets: {len(xls['sheets'])}", flush=True)

    out = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "pdf": pdf,
        "xls": xls,
    }
    json_path = OUT_DIR / "chipotle_sample_analysis.json"
    json_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {json_path}", flush=True)
    print(f"Elapsed: {time.time()-t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
