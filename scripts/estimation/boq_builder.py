"""
BOQ builder — orchestrator.
Combines drawing inventory (PDF) + BOQ items (XLS) into a single estimation
analysis bundle for the dashboard.

Outputs:
  data/estimation_samples/{project_slug}/
    - drawing_inventory.json
    - boq_workbook.json
    - bundle.json   <- consumed by docs/estimation-dashboard.html

Run:
    python -X utf8 scripts/estimation/boq_builder.py \
        --pdf "G:/내 드라이브/견적시스템/...pdf" \
        --xls "G:/내 드라이브/견적시스템/...xls" \
        --slug chipotle-shinsegae
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

# Allow running as a script
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from drawing_recognizer import recognize as recognize_drawings  # type: ignore
from excel_recognizer import recognize_workbook  # type: ignore

ROOT = Path(r"G:\내 드라이브\obsidian-agent-brain-system")
SAMPLES_DIR = ROOT / "data" / "estimation_samples"
DOCS_DATA_DIR = ROOT / "docs" / "data" / "estimation"


def build_bundle(pdf: Path | None, xls: Path | None, slug: str) -> dict:
    out: dict = {
        "slug": slug,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "drawings": None,
        "boq": None,
        "summary": {},
    }

    if pdf and pdf.exists():
        print(f"[1] PDF 인식: {pdf.name}", flush=True)
        out["drawings"] = recognize_drawings(pdf)
    if xls and xls.exists():
        print(f"[2] XLS 인식: {xls.name}", flush=True)
        out["boq"] = recognize_workbook(xls)

    summary = {}
    if out["drawings"]:
        d = out["drawings"]
        summary["drawing_page_count"] = d["page_count"]
        summary["drawing_category_count"] = d["category_count"]
        summary["material_pages"] = len(d.get("material_pages", []))
        summary["unique_drawing_codes"] = len(d.get("drawing_code_top", []))
    if out["boq"]:
        b = out["boq"]
        summary["project_meta"] = b.get("project_meta", {})
        summary["sheet_count"] = b["sheet_count"]
        summary["total_items"] = b["total_items"]
        # Sum totals where possible
        total_amount = 0.0
        priced_items = 0
        unit_counter: Counter = Counter()
        wg_counter: Counter = Counter()
        for s in b["sheets"]:
            for it in s.get("items", []):
                amt = it.get("amount")
                if isinstance(amt, (int, float)) and amt:
                    total_amount += amt
                    priced_items += 1
                if it.get("unit"):
                    unit_counter[it["unit"]] += 1
                if it.get("work_group"):
                    wg_counter[it["work_group"]] += 1
        summary["priced_items"] = priced_items
        summary["amount_total"] = round(total_amount, 0)
        summary["unit_distribution"] = dict(unit_counter.most_common(15))
        summary["work_group_distribution"] = dict(wg_counter.most_common(15))

    out["summary"] = summary
    return out


def save_bundle(bundle: dict) -> dict:
    slug = bundle["slug"]
    target = SAMPLES_DIR / slug
    target.mkdir(parents=True, exist_ok=True)

    paths = {}
    if bundle.get("drawings"):
        p = target / "drawing_inventory.json"
        p.write_text(json.dumps(bundle["drawings"], ensure_ascii=False, indent=2), encoding="utf-8")
        paths["drawings"] = str(p)
    if bundle.get("boq"):
        p = target / "boq_workbook.json"
        p.write_text(json.dumps(bundle["boq"], ensure_ascii=False, indent=2), encoding="utf-8")
        paths["boq"] = str(p)

    # Lightweight bundle for the dashboard (drop full per-page items)
    light = {
        "slug": slug,
        "generated_at": bundle["generated_at"],
        "summary": bundle["summary"],
        "drawing_category_count": bundle["summary"].get("drawing_category_count", {}),
        "material_pages": bundle["drawings"].get("material_pages", []) if bundle.get("drawings") else [],
        "drawing_role_count": bundle["drawings"].get("role_count", {}) if bundle.get("drawings") else {},
        "drawing_code_top": bundle["drawings"].get("drawing_code_top", [])[:25] if bundle.get("drawings") else [],
        "boq_sheets": [
            {
                "sheet": s["sheet"],
                "item_count": s.get("item_count", 0),
                "work_groups": s.get("work_groups", []),
                "sample_items": s.get("items", [])[:10],
            }
            for s in (bundle["boq"]["sheets"] if bundle.get("boq") else [])
            if "item_count" in s
        ],
    }
    p = target / "bundle.json"
    p.write_text(json.dumps(light, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["bundle"] = str(p)

    # Also copy bundle to docs/data so GitHub Pages dashboard can fetch it
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    docs_p = DOCS_DATA_DIR / f"{slug}.json"
    docs_p.write_text(json.dumps(light, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["docs_bundle"] = str(docs_p)

    return paths


def update_dashboard_index() -> Path:
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    index_path = DOCS_DATA_DIR / "index.json"
    bundles = []
    for p in sorted(DOCS_DATA_DIR.glob("*.json")):
        if p.name == "index.json":
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            bundles.append({
                "slug": data.get("slug", p.stem),
                "generated_at": data.get("generated_at"),
                "summary": data.get("summary", {}),
                "file": p.name,
            })
        except Exception:
            continue
    index_path.write_text(json.dumps({"bundles": bundles}, ensure_ascii=False, indent=2), encoding="utf-8")
    return index_path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default=None)
    ap.add_argument("--xls", default=None)
    ap.add_argument("--slug", required=True)
    a = ap.parse_args()

    bundle = build_bundle(
        Path(a.pdf) if a.pdf else None,
        Path(a.xls) if a.xls else None,
        a.slug,
    )
    paths = save_bundle(bundle)
    index = update_dashboard_index()

    print("\n=== 저장 완료 ===")
    for k, v in paths.items():
        print(f"  {k}: {v}")
    print(f"  index: {index}")
    print("\n=== Summary ===")
    print(json.dumps(bundle["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
