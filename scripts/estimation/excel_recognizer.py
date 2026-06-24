"""
Excel BOQ recognizer.
Recognizes Korean SPC INTERIOR STANDARD ESTIMATE template (.xls/.xlsx):
  공종 | 번호 | 명칭 | 제조사 | 모델 | 규격 | 단위 | 수량 | 횟수 | 단가 | 금액
plus summary headers (가설/철거/벽체/천정/집기/기타) and overhead lines
(공과잡비/기업이윤/산재보험료/고용보험료/안전관리비).

Run:
    python -X utf8 scripts/estimation/excel_recognizer.py <xls_path> [--out <json>]
"""
from __future__ import annotations
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

HEADER_TOKENS = ["번호", "명", "제조사", "모델", "규", "단위", "수"]

# Heuristic column roles (Korean SPC template)
COLUMN_MAP_DEFAULT = {
    0: "work_group",
    1: "no",
    2: "name",
    3: "manufacturer",
    4: "model",
    5: "spec",
    6: "unit",
    7: "qty",
    8: "repeat",
    9: "unit_price",
    10: "amount",
}

SUMMARY_HEADERS = {
    "가설공사", "철거공사", "벽체공사", "천정공사", "집기공사", "기타공사",
    "합계", "총계", "공과잡비", "기업이윤", "산재보험료", "고용보험료", "안전관리비",
    "직사입 안전관리비",
}


def _open(path: Path) -> pd.ExcelFile:
    for engine in ("xlrd", "openpyxl", "calamine"):
        try:
            return pd.ExcelFile(path, engine=engine)
        except Exception:
            continue
    return pd.ExcelFile(path)


def _is_header_row(row: list[str]) -> bool:
    joined = " ".join(c for c in row if c).replace(" ", "")
    hits = sum(1 for tok in HEADER_TOKENS if tok in joined)
    return hits >= 4


def _coerce_number(v: str) -> float | None:
    if not v:
        return None
    s = v.replace(",", "").replace(" ", "")
    try:
        return float(s)
    except ValueError:
        return None


def _classify_row(row: list[str]) -> str:
    name = row[2].strip() if len(row) > 2 else ""
    if not any(c.strip() for c in row):
        return "blank"
    if name in SUMMARY_HEADERS:
        return "summary"
    if _is_header_row(row):
        return "header"
    # Detail item: has unit and qty
    unit = row[6].strip() if len(row) > 6 else ""
    qty = _coerce_number(row[7].strip()) if len(row) > 7 else None
    if name and (unit or qty is not None):
        return "item"
    if name:
        return "label"
    return "noise"


def _extract_meta(df: pd.DataFrame) -> dict:
    """Look at first 10 rows for project meta (공사명, 납품처, 견적일 etc)."""
    meta: dict = {}
    for i in range(min(10, len(df))):
        row = df.iloc[i].fillna("").astype(str).tolist()
        text = " ".join(row)
        for label, key in [
            ("공 사 명", "project_name"),
            ("공사명", "project_name"),
            ("납 품 처", "client"),
            ("납품처", "client"),
            ("견 적 일", "quoted_at"),
            ("견적일", "quoted_at"),
            ("ESTIMATE", "form_kind"),
        ]:
            if label in text and key not in meta:
                # value usually in next non-empty column on same row
                idx_label = next((j for j, c in enumerate(row) if label in c), -1)
                if idx_label >= 0:
                    for j in range(idx_label + 1, len(row)):
                        v = row[j].strip()
                        if v:
                            meta[key] = v
                            break
    return meta


def recognize_sheet(df: pd.DataFrame, sheet_name: str) -> dict:
    rows: list[list[str]] = [
        [str(c) if pd.notna(c) else "" for c in df.iloc[i].tolist()]
        for i in range(len(df))
    ]
    classified = [(_classify_row(r), r) for r in rows]

    items: list[dict] = []
    summary: list[dict] = []
    current_group = ""

    for kind, r in classified:
        if kind == "item":
            wg = r[0].strip() if r and r[0].strip() else current_group
            if r and r[0].strip():
                current_group = r[0].strip()
            item = {
                "work_group": wg,
                "no": r[1].strip() if len(r) > 1 else "",
                "name": r[2].strip() if len(r) > 2 else "",
                "manufacturer": r[3].strip() if len(r) > 3 else "",
                "model": r[4].strip() if len(r) > 4 else "",
                "spec": r[5].strip() if len(r) > 5 else "",
                "unit": r[6].strip() if len(r) > 6 else "",
                "qty": _coerce_number(r[7].strip()) if len(r) > 7 else None,
                "repeat": _coerce_number(r[8].strip()) if len(r) > 8 else None,
                "unit_price": _coerce_number(r[9].strip()) if len(r) > 9 else None,
                "amount": _coerce_number(r[10].strip()) if len(r) > 10 else None,
            }
            items.append(item)
        elif kind == "summary":
            summary.append({
                "name": r[2].strip() if len(r) > 2 else "",
                "raw": [c for c in r if c.strip()],
            })

    return {
        "sheet": sheet_name,
        "row_count": len(rows),
        "item_count": len(items),
        "summary_count": len(summary),
        "items": items,
        "summary": summary,
        "work_groups": sorted({i["work_group"] for i in items if i["work_group"]}),
    }


def recognize_workbook(path: Path) -> dict:
    xls = _open(path)
    sheets: list[dict] = []
    project_meta: dict = {}
    for s in xls.sheet_names:
        try:
            df = pd.read_excel(path, sheet_name=s, header=None, engine=xls.engine)
        except Exception as e:
            sheets.append({"sheet": s, "error": str(e)})
            continue
        if not project_meta:
            project_meta = _extract_meta(df)
        sheets.append(recognize_sheet(df, s))

    total_items = sum(s.get("item_count", 0) for s in sheets)
    return {
        "xls_path": str(path),
        "engine": xls.engine,
        "project_meta": project_meta,
        "sheet_count": len(sheets),
        "total_items": total_items,
        "sheets": sheets,
    }


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("xls")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    result = recognize_workbook(Path(a.xls))
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"Saved: {a.out}")
    else:
        print(text[:3000])

    print(f"\nSummary: project={result['project_meta']}, "
          f"sheets={result['sheet_count']}, total_items={result['total_items']}")
    for s in result["sheets"]:
        if "item_count" in s:
            print(f"  - {s['sheet']}: {s['item_count']} items, "
                  f"groups={s['work_groups'][:5]}{'...' if len(s['work_groups'])>5 else ''}")


if __name__ == "__main__":
    main()
