---
type: knowledge-note
date: 2026-06-06
source: daily-plus
category: voice-pipeline
tags:
- area/ai_automation
- status/active
summary: 벤더 목록·음성 캡처·PDF 테이블을 표준 행으로 정규화하는 Excel 인제스트 스키마
status: applied
applied_at: 2026-06-11
graph_cluster: daily-practice
---

# Canonical Excel Ingest Schema

## 개요

벤더 리스트, 음성 캡처, PDF 테이블 등 이기종 소스를 단일 정규화 행으로 변환하는
표준 인제스트 스키마. 비개발자용 Google Sheets Apps Script + Python 예시 포함.

---

## 정규화 출력 스키마

```json
{
  "row_id": "uuid-v4",
  "source_type": "vendor_list | voice_capture | pdf_table",
  "source_file": "original_filename.xlsx",
  "ingested_at": "2026-06-06T09:00:00Z",
  "item": {
    "description_raw": "원본 품목 설명 텍스트",
    "sku": "SKU-001234",
    "sku_match_score": 0.91,
    "quantity": 150.0,
    "unit": "mm",
    "unit_original": "m",
    "unit_conversion_factor": 1000,
    "price_krw": 45000,
    "currency_original": "KRW",
    "geometry_qc": "pass"
  },
  "flags": []
}
```

---

## 처리 파이프라인

### 1. 퍼지 매칭: description → SKU

```python
from rapidfuzz import fuzz, process

SKU_CATALOG = {
    "페인트 흰색 18L": "SKU-001234",
    "타일 600x600 베이지": "SKU-005678",
    # ...
}

def match_sku(description: str, threshold: int = 85) -> tuple[str | None, float]:
    result = process.extractOne(
        description,
        SKU_CATALOG.keys(),
        scorer=fuzz.token_sort_ratio
    )
    if result and result[1] >= threshold:
        return SKU_CATALOG[result[0]], result[1] / 100.0
    return None, 0.0

# 임계값 85% 미만 → flags에 "sku_unmatched" 추가
```

### 2. 단위 정규화

```python
UNIT_MAP = {
    "m":   ("mm", 1000),
    "cm":  ("mm", 10),
    "ft":  ("mm", 304.8),
    "m2":  ("mm2", 1_000_000),
    "ea":  ("ea", 1),
    "box": ("ea", None),   # 박스당 수량 별도 확인 필요
}

def normalize_unit(value: float, unit: str) -> dict:
    if unit not in UNIT_MAP:
        return {"unit": unit, "value": value, "flag": "unit_unknown"}
    target_unit, factor = UNIT_MAP[unit]
    if factor is None:
        return {"unit": target_unit, "value": value, "flag": "box_qty_needed"}
    return {"unit": target_unit, "value": value * factor}
```

### 3. 통화 변환 (KRW 기준)

```python
def normalize_currency(amount: float, currency: str) -> int:
    rates = {"KRW": 1, "USD": 1350, "JPY": 9.2, "EUR": 1470}
    if currency not in rates:
        raise ValueError(f"Unknown currency: {currency}")
    return round(amount * rates[currency])
```

### 4. 지오메트리 QC

```python
def geometry_qc(width_mm: float, height_mm: float, item_type: str) -> str:
    limits = {
        "tile":  {"w": (50, 1200), "h": (50, 1200)},
        "panel": {"w": (300, 3000), "h": (300, 2400)},
    }
    if item_type not in limits:
        return "skip"
    lim = limits[item_type]
    w_ok = lim["w"][0] <= width_mm <= lim["w"][1]
    h_ok = lim["h"][0] <= height_mm <= lim["h"][1]
    return "pass" if (w_ok and h_ok) else "fail"
```

---

## Google Sheets Apps Script (비개발자용)

```javascript
// Tools > Script Editor에 붙여넣기
function normalizeSheet() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const data = sheet.getDataRange().getValues();
  
  data.forEach((row, i) => {
    if (i === 0) return; // 헤더 스킵
    const unit = row[4];   // E열: 단위
    const value = row[3];  // D열: 수량
    
    // m → mm 변환
    if (unit === "m") {
      sheet.getRange(i + 1, 4).setValue(value * 1000);
      sheet.getRange(i + 1, 5).setValue("mm");
    }
  });
  
  SpreadsheetApp.getUi().alert("정규화 완료!");
}
```

---

## 플래그 목록

| 플래그 | 설명 | 권고 조치 |
|--------|------|-----------|
| `sku_unmatched` | SKU 매칭 85% 미만 | 수동 SKU 입력 |
| `unit_unknown` | 알 수 없는 단위 | 원본 확인 후 재입력 |
| `box_qty_needed` | 박스당 수량 미확인 | 벤더 문의 |
| `geometry_fail` | 치수 범위 초과 | 설계 검토 |
| `currency_unknown` | 지원하지 않는 통화 | 수동 환율 입력 |

---

## 실행 예시

```bash
python ingest.py --input vendor_list.xlsx --source vendor_list --output normalized.json
# 출력: normalized.json (정규화 행 배열)
# 로그: ingest.log (플래그 항목 목록)
```

## 관련 노트
- [[hubs/JH System]]
