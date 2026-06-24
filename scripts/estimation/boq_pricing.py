"""
BOQ pricing — work_group/unit/name 기반으로 BOQ items에 단가를 채운다.

Input  : excel_recognizer가 만든 boq_workbook dict (sheets[].items[])
Output : 같은 dict, 각 item.unit_price + item.amount 채워짐 + price_meta 추가

A진행 = 실제 BOQ 항목 × 매핑 단가 (수량은 이미 BOQ에 있음).
B근거 = 직영/먹메김 "내부 수평 비계" 등의 M2 값에서 실측 면적 추출.

신뢰도 표기는 모두 🟡 MED (기준 단가 사용, 협력사 확정가 아님).
"""
from __future__ import annotations
from typing import Any

# work_group + unit → 기본 단가 (KRW). name 키워드로 보정.
# 출처: unit_price_defaults.json 한국 인테리어 평균 단가 (2024-25)
WORK_GROUP_PRICES: dict[tuple[str, str], int] = {
    # 경량(칸막이/석고/천장틀)
    ("경량", "M2"): 55_000,   # 경량칸막이 단면
    ("경량", "M"): 35_000,    # 몰딩/런너
    ("경량", "EA"): 80_000,
    ("경량", "SET"): 1_200_000,  # 가설도어 SET
    ("경량", "식"): 800_000,
    # 타일
    ("타일", "M2"): 120_000,  # 자재+시공 포함
    ("타일", "M"): 40_000,
    ("타일/메지", "M2"): 12_000,
    ("타일/메지", "개소"): 350_000,  # 계단 조성 등
    ("타일/부자재", "M2"): 18_000,
    # 습식 (방수/몰탈)
    ("습식", "M2"): 35_000,
    ("습식", "M"): 28_000,    # 방수턱 철근/몰탈
    ("습식-1", "M2"): 22_000, # 보호몰탈
    # 철거
    ("철거", "M2"): 40_000,
    ("철거", "인"): 280_000,  # 폐기물 반출 일당
    ("폐기물", "대"): 450_000, # 폐기물 처리비 차량당
    ("폐기물", "M2"): 22_000,
    # 직영 (가설/관리)
    ("직영", "일"): 250_000,
    ("직영", "M2"): 18_000,   # 비계/보양
    ("직영", "식"): 1_500_000,
    # 목공
    ("목공", "M2"): 8_000,    # 먹메김
    ("목공", "M"): 32_000,    # 거푸집
    # 도장
    ("도장", "M2"): 18_000,   # 방염
    ("도장", "식"): 600_000,
    # 청소
    ("청소", "M2"): 8_000,
    ("청소", "식"): 700_000,
    # 금속 (가구/커스텀)
    ("금속", "EA"): 1_800_000,
    # 구매 (직접 자재)
    ("구매", "EA"): 400_000,
    ("구매", "일"): 80_000,   # 집진기 렌탈 등
    # 소방
    ("소방", "식"): 850_000,
    # 미분류 (LOT 일괄)
    ("", "LOT"): 3_000_000,
}

# name 키워드 보정 (work_group이 일반적인 경우 더 정확한 단가로 덮어씀)
NAME_KEYWORD_PRICES: list[tuple[str, str, int]] = [
    # (키워드, unit, price)
    ("DIGITAL MENU", "EA", 3_500_000),
    ("MENU BOARD", "EA", 2_800_000),
    ("가구몸통", "EA", 1_800_000),
    ("무늬목 필름", "EA", 450_000),
    ("자동문", "M2", 350_000),  # 후문 자동문 벽체철거
    ("자동문", "SET", 4_500_000),
    ("대리석", "M2", 180_000),
    ("바닥타일 구배 몰탈", "M2", 28_000),
    ("바닥타일", "M2", 120_000),
    ("액체방수", "M2", 32_000),
    ("방수턱 철근", "M", 22_000),
    ("방수턱 몰탈", "M", 28_000),
    ("방수턱거푸집", "M", 35_000),
    ("내부 수평 비계", "M2", 18_000),
    ("현장보양", "M2", 6_000),
    ("준공청소-내부", "M2", 9_000),
    ("준공청소-외부", "식", 600_000),
    ("방염필증", "식", 550_000),
    ("외부 가설 철거", "M2", 35_000),
    ("가설칸막이 재설치", "식", 1_800_000),
    ("가설칸막이", "M2", 65_000),
    ("가설 도어", "SET", 1_500_000),
    ("먹메김", "M2", 5_500),
    ("방화카", "EA", 280_000),
    ("집진기", "일", 95_000),
    ("폐기물 반출", "인", 280_000),
    ("폐기물처리비", "대", 480_000),
    ("현장정리정돈", "일", 220_000),
    ("주방출입구 계단조성", "개소", 850_000),
    ("지정 메지", "M2", 14_000),
    ("타일 부자재", "M2", 18_000),
    ("대리석 부자재", "M2", 25_000),
    ("보호몰탈 공급 및 설치", "M2", 24_000),
    ("바닥공사", "LOT", 8_500_000),
    ("철거 공사", "LOT", 6_500_000),
]


def lookup_unit_price(item: dict) -> tuple[int, str, str]:
    """Return (unit_price, source, confidence) for a BOQ item.

    Priority:
      1) name 키워드 (가장 정확)
      2) work_group + unit
      3) 단위만으로 fallback (마지막)
    """
    name = (item.get("name") or "").strip()
    wg = (item.get("work_group") or "").strip()
    unit = (item.get("unit") or "").strip().upper()
    # excel은 m2를 종종 소문자로 저장 → 정규화
    if unit == "M²":
        unit = "M2"

    # 1) name 키워드
    for kw, kw_unit, price in NAME_KEYWORD_PRICES:
        if kw in name and (not kw_unit or kw_unit.upper() == unit):
            return price, f"name:{kw}", "🟡 MED"

    # 2) work_group + unit
    key = (wg, unit)
    if key in WORK_GROUP_PRICES:
        return WORK_GROUP_PRICES[key], f"work_group:{wg}/{unit}", "🟡 MED"

    # 3) work_group 무관, unit만으로 fallback
    unit_fallback = {
        "M2": 40_000,
        "M": 15_000,
        "EA": 180_000,
        "SET": 800_000,
        "식": 800_000,
        "LOT": 2_500_000,
        "개소": 350_000,
        "일": 200_000,
        "인": 250_000,
        "대": 450_000,
        "PCS": 25_000,
    }
    if unit in unit_fallback:
        return unit_fallback[unit], f"unit_only:{unit}", "🔴 LOW"

    return 50_000, "default", "🔴 LOW"


# 합계/소계/공란 행은 가격 매핑에서 제외 — name 패턴
SKIP_NAME_PATTERNS = ("합 계", "합계", "소 계", "소계", "총 계", "총계", "TOTAL", "SUBTOTAL")


def is_total_row(item: dict) -> bool:
    name = (item.get("name") or "").strip()
    if not name:
        return True
    upper = name.upper().replace(" ", "")
    for pat in SKIP_NAME_PATTERNS:
        if pat.replace(" ", "").upper() in upper:
            return True
    return False


def _dedupe_sheets(boq_data: dict) -> list[dict]:
    """동일 항목 구성의 시트 중복 제거. 첫 시트만 사용한다.
    chipotle BOQ의 경우 시트 2/3이 완전 동일 → 하나만 채택.
    """
    seen_signatures: set[str] = set()
    unique: list[dict] = []
    for sheet in boq_data.get("sheets", []):
        items = sheet.get("items") or []
        if not items:
            continue
        # 시트의 첫 5개 항목 (name, qty)으로 시그니처 구성
        sig_parts = [f"{(it.get('name') or '').strip()}:{it.get('qty')}" for it in items[:5]]
        sig = "|".join(sig_parts) + f"|n={len(items)}"
        if sig in seen_signatures:
            continue
        seen_signatures.add(sig)
        unique.append(sheet)
    return unique


def price_boq_workbook(boq_data: dict) -> dict:
    """Fill unit_price + amount for every BOQ item. Mutates and returns boq_data.

    중복 시트는 자동 제거, 합계 행은 단가 매핑 제외.
    """
    priced_total = 0.0
    confidence_counter: dict[str, int] = {"🟡 MED": 0, "🔴 LOW": 0}
    source_counter: dict[str, int] = {}
    skipped_total_rows = 0
    priced_items = 0

    unique_sheets = _dedupe_sheets(boq_data)

    for sheet in boq_data.get("sheets", []):
        keep_sheet = sheet in unique_sheets
        for item in sheet.get("items", []):
            if not keep_sheet:
                item["unit_price"] = 0
                item["amount"] = 0
                item["price_source"] = "duplicate_sheet_skipped"
                item["price_confidence"] = "—"
                continue
            if is_total_row(item):
                item["unit_price"] = 0
                item["amount"] = 0
                item["price_source"] = "total_row_skipped"
                item["price_confidence"] = "—"
                skipped_total_rows += 1
                continue
            qty = item.get("qty")
            if qty is None:
                qty = 1.0
                item.setdefault("note", []).append("qty=None → 1로 가정")
            unit_price, source, conf = lookup_unit_price(item)
            amount = float(qty) * float(unit_price)
            item["unit_price"] = unit_price
            item["amount"] = round(amount, 0)
            item["price_source"] = source
            item["price_confidence"] = conf
            priced_total += amount
            priced_items += 1
            confidence_counter[conf] = confidence_counter.get(conf, 0) + 1
            src_key = source.split(":")[0]
            source_counter[src_key] = source_counter.get(src_key, 0) + 1

    boq_data["price_meta"] = {
        "method": "WORK_GROUP_PRICES + NAME_KEYWORD_PRICES (boq_pricing.py)",
        "priced_total_raw": int(priced_total),
        "priced_items": priced_items,
        "skipped_total_rows": skipped_total_rows,
        "deduped_sheets_used": [s.get("sheet") or s.get("name") or "(unnamed)" for s in unique_sheets],
        "confidence_counter": confidence_counter,
        "source_counter": source_counter,
        "note": "협력사 확정 단가 아님. 한국 인테리어 평균(2024-25) 기준 추정.",
    }
    return boq_data


def build_cost_estimate_from_boq(
    boq_priced: dict,
    actual_area_m2: float | None,
    rates: dict | None = None,
) -> dict:
    """BOQ 단가 매핑 결과 + 실측 면적(B근거)으로 cost_estimate dict 생성."""
    rates = rates or {}
    indirect_rate = rates.get("간접비", 0.15)
    safety_rate = rates.get("안전관리비", 0.0186)
    insurance_rate = rates.get("산재보험", 0.038)
    vat_rate = rates.get("VAT", 0.10)
    night_surcharge = 0.15  # 신세계 입점 2공구 야간공사 할증

    from collections import defaultdict
    wg_total: dict[str, float] = defaultdict(float)
    items_list: list[dict] = []
    for sheet in boq_priced.get("sheets", []):
        for it in sheet.get("items", []):
            if it.get("price_source") in ("total_row_skipped", "duplicate_sheet_skipped"):
                continue
            wg = it.get("work_group") or "(미분류)"
            amt = it.get("amount", 0) or 0
            wg_total[wg] += amt
            items_list.append({
                "공종": wg,
                "품명": it.get("name"),
                "규격": it.get("spec"),
                "수량": it.get("qty"),
                "단위": it.get("unit"),
                "단가": it.get("unit_price"),
                "금액": int(amt),
                "단가출처": it.get("price_source"),
                "신뢰도": it.get("price_confidence"),
            })

    raw_total = sum(wg_total.values())

    def apply_rates(base: float) -> dict:
        direct = base
        indirect = direct * indirect_rate
        safety = (direct + indirect) * safety_rate
        insurance = (direct + indirect) * insurance_rate
        subtotal = direct + indirect + safety + insurance
        vat = subtotal * vat_rate
        return {
            "직접공사비": int(direct),
            "간접비": int(indirect),
            "안전관리비": int(safety),
            "산재보험": int(insurance),
            "소계": int(subtotal),
            "VAT": int(vat),
            "합계_VAT포함": int(subtotal + vat),
        }

    avg_total = apply_rates(raw_total)
    min_total = apply_rates(raw_total * 0.85)
    max_total = apply_rates(raw_total * (1 + night_surcharge))

    return {
        "method": "A방식 (BOQ 110항목 × 매핑 단가) + B근거 (BOQ 실측 면적)",
        "confidence": "🟡 MED",
        "note": "협력사 확정 단가 아님. 신세계 야간공사 할증 15% (max). 현설 누락 10개 항목 미반영.",
        "actual_area_m2": actual_area_m2,
        "actual_area_pyeong": round(actual_area_m2 / 3.305, 2) if actual_area_m2 else None,
        "raw_total_krw": int(raw_total),
        "per_m2_avg": int(raw_total / actual_area_m2) if actual_area_m2 else None,
        "per_pyeong_avg": int(raw_total / (actual_area_m2 / 3.305)) if actual_area_m2 else None,
        "gongje_breakdown": {k: int(v) for k, v in sorted(wg_total.items(), key=lambda x: -x[1])},
        "items": items_list,
        "total_min": min_total,
        "total_avg": avg_total,
        "total_max": max_total,
        "missing_from_briefing": [
            "재료분리대 코너 전체 회수",
            "방수 4회 (액방2 + 비노출2)",
            "오이코스 천정 터치업",
            "PDR 룸 LED 도시 1.7~1.8개",
            "후문 자동문 900→1000mm 확장",
            "FSL 베이스 + 하부 습식 매트",
            "아크 구조물 자중 + 코브 조명",
            "메뉴보드 코너 앵글 레이저커팅",
            "멕시칸 그릴 부속 부품",
            "우드 루버 설치 인건비",
        ],
    }


def extract_actual_area(boq_data: dict) -> dict:
    """B 근거: BOQ 항목에서 실측 면적을 추출한다.
    먹메김/내부 수평 비계/현장보양/방염은 전체 시공면적과 동일하게 잡힌다.
    """
    candidates: list[tuple[str, float]] = []
    for sheet in boq_data.get("sheets", []):
        for item in sheet.get("items", []):
            name = (item.get("name") or "").strip()
            unit = (item.get("unit") or "").upper()
            qty = item.get("qty")
            if not qty or unit != "M2":
                continue
            if any(kw in name for kw in ("먹메김", "내부 수평 비계", "현장보양", "방염", "준공청소-내부")):
                candidates.append((name, float(qty)))

    if not candidates:
        return {"actual_area_m2": None, "candidates": []}

    # 가장 빈도 높은 면적이 실측 면적 (대부분 266.49 같이 동일값)
    area_counter: dict[float, int] = {}
    for _, q in candidates:
        area_counter[q] = area_counter.get(q, 0) + 1
    main_area = max(area_counter.items(), key=lambda x: x[1])[0]

    return {
        "actual_area_m2": main_area,
        "evidence_item_count": area_counter[main_area],
        "candidates": [{"name": n, "qty_m2": q} for n, q in candidates],
        "source": "BOQ 직영/도장/청소 공통면적 항목 (B근거)",
    }
