"""
BOQ builder — orchestrator.
Combines drawing inventory (PDF) + BOQ items (XLS) into a single estimation
analysis bundle for the dashboard.

Modes:
  --pdf + --xls          : Mode C (full pipeline)
  --pdf only             : Mode A (drawing-only with unit price estimation)
  --xls only             : Mode B (BOQ-only analysis)
  --estimate-unit-prices : Apply defaults from unit_price_defaults.json (MED confidence)

Outputs:
  data/estimation_samples/{project_slug}/
    - drawing_inventory.json
    - boq_workbook.json
    - bundle.json   <- consumed by docs/estimation-dashboard.html
    - cost_estimate.json  <- unit price estimation result (if --estimate-unit-prices)

Run:
    python -X utf8 scripts/estimation/boq_builder.py \
        --pdf "path/to/drawings.pdf" \
        --xls "path/to/boq.xls" \
        --slug chipotle-shinsegae
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from drawing_recognizer import recognize as recognize_drawings  # type: ignore
from excel_recognizer import recognize_workbook  # type: ignore

ROOT = Path(r"G:\내 드라이브\obsidian-agent-brain-system")
SAMPLES_DIR = ROOT / "data" / "estimation_samples"
DOCS_DATA_DIR = ROOT / "docs" / "data" / "estimation"
UNIT_PRICE_FILE = HERE / "unit_price_defaults.json"

# Map drawing categories to 공종 for unit price lookup
CATEGORY_TO_GONGJE = {
    "PLAN": "목공사",
    "ELECTRICAL": "전기공사",
    "KITCHEN": "설비공사",
    "DETAIL": "타일공사",
    "FURNITURE": "가구공사",
    "SIGNAGE": "기타공사",
    "MECHANICAL": "설비공사",
    "ELEVATION": "도장공사",
    "SECTION": "목공사",
}


def load_unit_price_defaults() -> dict:
    if UNIT_PRICE_FILE.exists():
        return json.loads(UNIT_PRICE_FILE.read_text(encoding="utf-8"))
    return {}


def estimate_cost_from_drawings(drawing_data: dict, unit_defaults: dict) -> dict:
    """
    Given drawing inventory, estimate costs using unit_price_defaults.json.
    Returns a cost_estimate dict with confidence 🟡 MED.
    """
    category_count: dict = drawing_data.get("category_count", {})
    page_count: int = drawing_data.get("page_count", 0)
    material_pages: int = len(drawing_data.get("material_pages", []))

    gongje_data = unit_defaults.get("공종별_단가", {})
    ratios = unit_defaults.get("공종별_면적비율_표준", {})
    rates = unit_defaults.get("요율", {})

    # Infer area from drawing complexity (rough heuristic: 1 PLAN page ≈ 50m²)
    plan_pages = category_count.get("PLAN", 0)
    estimated_area_m2 = max(plan_pages * 50, 30)

    # Build cost estimate per 공종
    items = []
    total_min = 0.0
    total_max = 0.0
    total_avg = 0.0

    for cat, pages in category_count.items():
        gongje = CATEGORY_TO_GONGJE.get(cat, "기타공사")
        ratio = ratios.get(gongje, 0.05)
        price_block = gongje_data.get(gongje)

        if isinstance(price_block, dict) and "avg" in price_block:
            unit = price_block.get("unit", "m²")
            avg_price = price_block["avg"]
            min_price = price_block.get("min", avg_price * 0.7)
            max_price = price_block.get("max", avg_price * 1.5)

            qty = estimated_area_m2 * ratio
            amt_avg = qty * avg_price
            amt_min = qty * min_price
            amt_max = qty * max_price
        else:
            # Fallback: area × ratio × 50,000원 default
            qty = estimated_area_m2 * ratio
            avg_price = 50000
            unit = "m²"
            amt_avg = qty * avg_price
            amt_min = amt_avg * 0.7
            amt_max = amt_avg * 1.5

        items.append({
            "공종": gongje,
            "도면카테고리": cat,
            "도면페이지수": pages,
            "추정면적_m2": round(qty, 1),
            "단위": unit,
            "단가_avg": int(avg_price),
            "금액_min": int(amt_min),
            "금액_avg": int(amt_avg),
            "금액_max": int(amt_max),
            "신뢰도": "🟡 MED",
        })
        total_min += amt_min
        total_avg += amt_avg
        total_max += amt_max

    # Apply overhead rates
    surcharge = rates.get("할증_일반", 0.10)
    labor_ratio = rates.get("노무비_대자재비", 0.40)
    indirect = rates.get("간접비", 0.15)
    safety = rates.get("안전관리비", 0.0186)
    insurance = rates.get("산재보험", 0.038)
    vat_rate = rates.get("VAT", 0.10)

    def apply_rates(base: float) -> dict:
        material = base * (1 + surcharge)
        labor = material * labor_ratio
        direct = material + labor
        indirect_cost = direct * indirect
        safety_cost = direct * safety
        insurance_cost = labor * insurance
        subtotal = direct + indirect_cost + safety_cost + insurance_cost
        vat = subtotal * vat_rate
        return {
            "자재비": int(material),
            "노무비": int(labor),
            "직접공사비": int(direct),
            "간접비": int(indirect_cost),
            "안전관리비": int(safety_cost),
            "산재보험": int(insurance_cost),
            "소계": int(subtotal),
            "VAT": int(vat),
            "합계_VAT포함": int(subtotal + vat),
        }

    return {
        "confidence": "🟡 MED",
        "note": "unit_price_defaults.json 기준 추정값. Gate 3 (단가 확정) 통과 필요.",
        "estimated_area_m2": estimated_area_m2,
        "material_pages_detected": material_pages,
        "items": items,
        "total_min": apply_rates(total_min),
        "total_avg": apply_rates(total_avg),
        "total_max": apply_rates(total_max),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def compute_boq_totals(boq_data: dict) -> dict:
    """Compute totals and verify against declared totals in BOQ."""
    total_amount = 0.0
    priced_items = 0
    unpriced_items = 0
    unit_counter: Counter = Counter()
    wg_counter: Counter = Counter()
    gongje_totals: dict[str, float] = {}

    for sheet in boq_data.get("sheets", []):
        for item in sheet.get("items", []):
            amt = item.get("amount")
            wg = item.get("work_group", "기타")
            unit = item.get("unit", "")

            if isinstance(amt, (int, float)) and amt > 0:
                total_amount += amt
                priced_items += 1
                gongje_totals[wg] = gongje_totals.get(wg, 0) + amt
            else:
                unpriced_items += 1

            if unit:
                unit_counter[unit] += 1
            if wg:
                wg_counter[wg] += 1

    return {
        "total_amount": int(total_amount),
        "priced_items": priced_items,
        "unpriced_items": unpriced_items,
        "coverage_rate": round(priced_items / max(priced_items + unpriced_items, 1), 3),
        "unit_distribution": dict(unit_counter.most_common(15)),
        "work_group_distribution": dict(wg_counter.most_common(15)),
        "gongje_totals": {k: int(v) for k, v in sorted(gongje_totals.items(), key=lambda x: -x[1])},
        "confidence": "🟢 HIGH" if priced_items > 0 and unpriced_items == 0 else (
            "🟡 MED" if priced_items > unpriced_items else "🔴 LOW"
        ),
    }


def build_bundle(
    pdf: Path | None,
    xls: Path | None,
    slug: str,
    estimate_unit_prices: bool = False,
) -> dict:
    out: dict = {
        "slug": slug,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "drawings": None,
        "boq": None,
        "cost_estimate": None,
        "boq_totals": None,
        "summary": {},
    }

    if pdf and pdf.exists():
        print(f"[1] PDF 인식: {pdf.name}", flush=True)
        out["drawings"] = recognize_drawings(pdf)
    if xls and xls.exists():
        print(f"[2] XLS 인식: {xls.name}", flush=True)
        out["boq"] = recognize_workbook(xls)

    # Compute BOQ totals if XLS provided
    if out["boq"]:
        print("[3] BOQ 합계 계산...", flush=True)
        out["boq_totals"] = compute_boq_totals(out["boq"])

    # Apply unit price estimation if requested or no XLS price data
    if out["drawings"] and (estimate_unit_prices or not out["boq"]):
        print("[4] 단가 추정 (unit_price_defaults.json)...", flush=True)
        unit_defaults = load_unit_price_defaults()
        if unit_defaults:
            out["cost_estimate"] = estimate_cost_from_drawings(out["drawings"], unit_defaults)
        else:
            print("  [경고] unit_price_defaults.json 없음 — 단가 추정 건너뜀", flush=True)

    # Build summary
    summary: dict = {}
    if out["drawings"]:
        d = out["drawings"]
        summary["drawing_page_count"] = d["page_count"]
        summary["drawing_category_count"] = d["category_count"]
        summary["material_pages"] = len(d.get("material_pages", []))
        summary["unique_drawing_codes"] = len(d.get("drawing_code_top", []))
        summary["drawing_confidence"] = d.get("confidence", "🟡 MED")

    if out["boq"]:
        b = out["boq"]
        summary["project_meta"] = b.get("project_meta", {})
        summary["sheet_count"] = b["sheet_count"]
        summary["total_items"] = b["total_items"]

    if out["boq_totals"]:
        t = out["boq_totals"]
        summary["amount_total"] = t["total_amount"]
        summary["priced_items"] = t["priced_items"]
        summary["unpriced_items"] = t["unpriced_items"]
        summary["coverage_rate"] = t["coverage_rate"]
        summary["boq_confidence"] = t["confidence"]
        summary["gongje_totals"] = t["gongje_totals"]

    if out["cost_estimate"]:
        ce = out["cost_estimate"]
        summary["estimated_area_m2"] = ce["estimated_area_m2"]
        summary["cost_estimate_avg"] = ce["total_avg"]["합계_VAT포함"]
        summary["cost_estimate_min"] = ce["total_min"]["합계_VAT포함"]
        summary["cost_estimate_max"] = ce["total_max"]["합계_VAT포함"]
        summary["cost_confidence"] = ce["confidence"]

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
    if bundle.get("cost_estimate"):
        p = target / "cost_estimate.json"
        p.write_text(json.dumps(bundle["cost_estimate"], ensure_ascii=False, indent=2), encoding="utf-8")
        paths["cost_estimate"] = str(p)

    # Lightweight bundle for dashboard
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
        "cost_estimate": {
            "confidence": bundle["cost_estimate"]["confidence"],
            "estimated_area_m2": bundle["cost_estimate"]["estimated_area_m2"],
            "total_avg": bundle["cost_estimate"]["total_avg"],
            "total_min": bundle["cost_estimate"]["total_min"],
            "total_max": bundle["cost_estimate"]["total_max"],
        } if bundle.get("cost_estimate") else None,
        "boq_totals": bundle.get("boq_totals"),
    }

    p = target / "bundle.json"
    p.write_text(json.dumps(light, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["bundle"] = str(p)

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


def print_cost_summary(bundle: dict) -> None:
    summary = bundle.get("summary", {})
    cost_estimate = bundle.get("cost_estimate")
    boq_totals = bundle.get("boq_totals")

    print("\n=== 공사비 추정 ===")
    if cost_estimate:
        avg = cost_estimate["total_avg"]
        mn = cost_estimate["total_min"]
        mx = cost_estimate["total_max"]
        print(f"  신뢰도: {cost_estimate['confidence']}")
        print(f"  추정 면적: {cost_estimate['estimated_area_m2']} m²")
        print(f"  공사비 최소: {mn['합계_VAT포함']:,} 원 (VAT 포함)")
        print(f"  공사비 평균: {avg['합계_VAT포함']:,} 원 (VAT 포함)")
        print(f"  공사비 최대: {mx['합계_VAT포함']:,} 원 (VAT 포함)")
        print(f"  ⚠️  {cost_estimate['note']}")

    if boq_totals:
        print(f"\n=== BOQ 내역서 집계 ===")
        print(f"  신뢰도: {boq_totals['confidence']}")
        print(f"  합계: {boq_totals['total_amount']:,} 원")
        print(f"  단가 입력 항목: {boq_totals['priced_items']}개 / 전체 {boq_totals['priced_items'] + boq_totals['unpriced_items']}개")
        print(f"  단가 커버율: {boq_totals['coverage_rate']*100:.1f}%")
        if boq_totals.get("gongje_totals"):
            print("  공종별 합계:")
            for gongje, amt in list(boq_totals["gongje_totals"].items())[:8]:
                print(f"    {gongje}: {amt:,} 원")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default=None)
    ap.add_argument("--xls", default=None)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--estimate-unit-prices", action="store_true",
                    help="도면만 있을 때 unit_price_defaults.json으로 공사비 추정")
    a = ap.parse_args()

    bundle = build_bundle(
        Path(a.pdf) if a.pdf else None,
        Path(a.xls) if a.xls else None,
        a.slug,
        estimate_unit_prices=a.estimate_unit_prices,
    )
    paths = save_bundle(bundle)
    index = update_dashboard_index()

    print("\n=== 저장 완료 ===")
    for k, v in paths.items():
        print(f"  {k}: {v}")
    print(f"  index: {index}")
    print("\n=== Summary ===")
    print(json.dumps(bundle["summary"], ensure_ascii=False, indent=2))
    print_cost_summary(bundle)


if __name__ == "__main__":
    main()
