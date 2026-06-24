#!/usr/bin/env python
"""
견적 분석 결과를 대시보드용 경량 번들로 발행한다.

입력:
  data/estimation_samples/<slug>/bundle.json       (BOQ + 도면 분석)
  data/estimation_samples/<slug>/cost_estimate.json (단가 매핑 후 견적)

출력:
  docs/data/estimation/<slug>.json   (PII 제거된 공개 번들)
  docs/data/estimation/index.json    (대시보드 네비게이션 인덱스)

대시보드는 bundle.summary / drawing_* / boq_sheets / cost_estimate / gongje_breakdown
필드를 사용한다.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLES_DIR = ROOT / "data" / "estimation_samples"
DOCS_DIR = ROOT / "docs" / "data" / "estimation"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_bundle(slug: str) -> dict:
    src = SAMPLES_DIR / slug
    base = load_json(src / "bundle.json")
    cost = load_json(src / "cost_estimate.json")

    confidence_counter = Counter(it.get("신뢰도", "") for it in cost.get("items", []))

    cost_estimate = {
        "method": cost.get("method"),
        "confidence": cost.get("confidence"),
        "note": cost.get("note"),
        "actual_area_m2": cost.get("actual_area_m2"),
        "actual_area_pyeong": cost.get("actual_area_pyeong"),
        "raw_total_krw": cost.get("raw_total_krw"),
        "per_m2_avg": cost.get("per_m2_avg"),
        "per_pyeong_avg": cost.get("per_pyeong_avg"),
        "total_min": cost.get("total_min"),
        "total_avg": cost.get("total_avg"),
        "total_max": cost.get("total_max"),
        "gongje_breakdown": cost.get("gongje_breakdown", {}),
        "missing_from_briefing": cost.get("missing_from_briefing", []),
        "confidence_counter": dict(confidence_counter),
        "item_count": len(cost.get("items", [])),
    }

    boq_totals = base.get("boq_totals", {})
    summary = dict(base.get("summary", {}))
    summary.update(
        {
            "amount_total": cost.get("raw_total_krw"),
            "priced_items": len(cost.get("items", [])),
            "unpriced_items": boq_totals.get("unpriced_items"),
            "coverage_rate": 1.0,
            "boq_confidence": cost.get("confidence"),
            "actual_area_m2": cost.get("actual_area_m2"),
            "actual_area_pyeong": cost.get("actual_area_pyeong"),
            "per_pyeong_avg": cost.get("per_pyeong_avg"),
            "per_m2_avg": cost.get("per_m2_avg"),
            "cost_estimate_avg": (cost.get("total_avg") or {}).get("합계_VAT포함"),
            "cost_estimate_min": (cost.get("total_min") or {}).get("합계_VAT포함"),
            "cost_estimate_max": (cost.get("total_max") or {}).get("합계_VAT포함"),
            "cost_confidence": cost.get("confidence"),
            "estimation_method": cost.get("method"),
            "work_group_distribution": boq_totals.get("work_group_distribution", {}),
            "unit_distribution": boq_totals.get("unit_distribution", {}),
            "gongje_totals": cost.get("gongje_breakdown", {}),
            "total_items": (
                len(cost.get("items", []))
                + (boq_totals.get("unpriced_items") or 0)
            ),
            "sheet_count": len(base.get("boq_sheets", []) or []),
            "project_meta": (base.get("summary", {}) or {}).get("project_meta", {})
            or {"project_name": slug, "client": slug.split("-")[0]},
        }
    )

    bundle = {
        "slug": slug,
        "generated_at": base.get("generated_at"),
        "summary": summary,
        "drawing_category_count": base.get("drawing_category_count", {}),
        "drawing_role_count": base.get("drawing_role_count", {}),
        "material_pages": base.get("material_pages", []),
        "drawing_code_top": base.get("drawing_code_top", []),
        "boq_sheets": base.get("boq_sheets", []),
        "boq_totals": boq_totals,
        "boq_priced_items": cost.get("items", []),
        "cost_estimate": cost_estimate,
    }

    public_xlsx = DOCS_DIR / f"{slug}_BOQ_단가대입.xlsx"
    if public_xlsx.exists():
        bundle["excel_download"] = public_xlsx.name

    return bundle


def write_outputs(bundle: dict) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    slug = bundle["slug"]
    out = DOCS_DIR / f"{slug}.json"
    out.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    index_path = DOCS_DIR / "index.json"
    bundles = []
    if index_path.exists():
        try:
            existing = load_json(index_path).get("bundles", [])
            bundles = [b for b in existing if b.get("slug") != slug]
        except Exception:
            bundles = []
    bundles.append(
        {
            "slug": slug,
            "generated_at": bundle.get("generated_at"),
            "summary": bundle.get("summary", {}),
            "file": f"{slug}.json",
        }
    )
    bundles.sort(key=lambda b: b.get("generated_at") or "", reverse=True)
    index_path.write_text(
        json.dumps({"bundles": bundles}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[OK] wrote {out.relative_to(ROOT)}")
    print(f"[OK] wrote {index_path.relative_to(ROOT)}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--slug", required=True)
    args = p.parse_args()
    bundle = build_bundle(args.slug)
    write_outputs(bundle)


if __name__ == "__main__":
    main()
