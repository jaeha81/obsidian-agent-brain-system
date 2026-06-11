---
title: 정규화 Excel 인제스트 스키마
date: 2026-06-06
source: daily-plus/2026-06-06.md (Card 9)
priority: P3
category: knowledge
status: distilled
tags:
  - excel
  - ingest
  - sku
  - normalization
  - apps-script
  - daily-plus
  - knowledge
---

# 정규화 Excel 인제스트 스키마

> ChatGPT Pulse 2026-06-06 Card 9 증류 (P3 · knowledge-candidate)

## 목적

지저분한 벤더 목록, 음성 캡처, PDF 테이블을 정규화된 행으로 변환. 설명→SKU 퍼지 매칭(85%), 단위 정규화(m→mm), 통화 변환(KRW), 기하학 QC.

## 정규화 파이프라인 단계

```
[입력 소스]
  벤더 Excel/CSV  /  음성 전사 텍스트  /  PDF 테이블 추출
        ↓
[Step 1] 컬럼 감지 + 헤더 정규화
        ↓
[Step 2] 텍스트 클렌징 (특수문자, 여분 공백)
        ↓
[Step 3] 단위 정규화 (m→mm, 평→㎡)
        ↓
[Step 4] 통화 정규화 → KRW
        ↓
[Step 5] SKU 퍼지 매칭 (임계값 85%)
        ↓
[Step 6] 기하학 QC (수량/면적 유효성)
        ↓
[출력] 정규화 행 테이블 (표준 CSV 스키마)
```

## Google Sheets Apps Script 샘플

```javascript
// Apps Script: 벤더 시트 → 정규화 시트 변환
function normalizeVendorSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const source = ss.getSheetByName("벤더원본");
  const target = ss.getSheetByName("정규화결과") || ss.insertSheet("정규화결과");

  const data = source.getDataRange().getValues();
  const headers = data[0];

  // 컬럼 인덱스 자동 감지
  const colMap = detectColumns(headers);
  const normalized = [];

  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const norm = {
      sku: matchSKU(row[colMap.name]),
      name: cleanText(row[colMap.name]),
      unit: normalizeUnit(row[colMap.unit]),
      qty: parseFloat(row[colMap.qty]) || 0,
      unit_price: convertToKRW(row[colMap.price], row[colMap.currency]),
      amount: 0,
    };
    norm.amount = norm.qty * norm.unit_price;
    normalized.push(Object.values(norm));
  }

  target.clearContents();
  target.getRange(1, 1, 1, 6).setValues([["SKU", "품명", "단위", "수량", "단가", "금액"]]);
  if (normalized.length > 0) {
    target.getRange(2, 1, normalized.length, 6).setValues(normalized);
  }
}

function detectColumns(headers) {
  const map = {};
  headers.forEach((h, i) => {
    const lower = h.toString().toLowerCase();
    if (lower.includes("품명") || lower.includes("name")) map.name = i;
    if (lower.includes("단위") || lower.includes("unit")) map.unit = i;
    if (lower.includes("수량") || lower.includes("qty")) map.qty = i;
    if (lower.includes("단가") || lower.includes("price")) map.price = i;
    if (lower.includes("통화") || lower.includes("currency")) map.currency = i;
  });
  return map;
}

function normalizeUnit(unit) {
  const unitMap = {
    "평": "㎡", "py": "㎡",
    "자": "mm", "ft": "mm", "feet": "mm",
    "인치": "mm", "inch": "mm", '"': "mm",
    "ea": "ea", "개": "ea", "pcs": "ea",
    "m": "m", "미터": "m",
  };
  return unitMap[unit.toString().trim().toLowerCase()] || unit;
}
```

## Python 예제

```python
import pandas as pd
from thefuzz import process

def normalize_excel(input_path: str, sku_db: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_excel(input_path)

    # 헤더 정규화
    df.columns = df.columns.str.strip().str.lower()

    # 텍스트 클렌징
    df["품명"] = df["품명"].str.strip().str.replace(r"\s+", " ", regex=True)

    # 단위 정규화
    unit_map = {"평": "㎡", "자": "mm", "인치": "mm", "개": "ea"}
    df["단위"] = df["단위"].replace(unit_map)

    # SKU 퍼지 매칭
    def match_sku(name):
        result = process.extractOne(name, sku_db["품명"].tolist())
        if result and result[1] >= 85:
            idx = sku_db[sku_db["품명"] == result[0]].index[0]
            return sku_db.loc[idx, "SKU"]
        return None

    df["SKU"] = df["품명"].apply(match_sku)

    # 기하학 QC: 음수 수량 플래그
    df["QC_경고"] = df["수량"].apply(lambda x: "음수수량" if x < 0 else "")

    return df
```

## 단위 정규화 전체 맵

| 입력 단위 | 정규화 | 변환 계수 |
|---------|------|---------|
| 평, py | ㎡ | × 3.3058 |
| 자, 尺 | mm | × 303.03 |
| 인치, inch, " | mm | × 25.4 |
| 피트, ft, feet | mm | × 304.8 |
| 개, ea, pcs, EA | ea | 1:1 |
| m, 미터 | m | 1:1 |
| cm | mm | × 10 |

## 관련 컨텍스트

- [[estimator-csv-standardization-kit]], [[planswift-invoice-mapping]]
- Google Sheets 기반 견적 자동화 파이프라인 연계
