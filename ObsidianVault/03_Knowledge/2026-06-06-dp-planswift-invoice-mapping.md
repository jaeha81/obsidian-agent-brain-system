---
title: PlanSwift-송장 매핑 ETL 명세
date: 2026-06-06
source: daily-plus/2026-06-06.md (Card 2)
priority: P3
category: knowledge
status: distilled
tags:
  - planswift
  - etl
  - invoice
  - sku
  - mapping
  - daily-plus
  - knowledge
---

# PlanSwift-송장 매핑 ETL 명세

> ChatGPT Pulse 2026-06-06 Card 2 증류 (P3 · knowledge-candidate)

## 목적

PlanSwift/DXF/PDF를 일관된 송장 행(SKU×수량)으로 변환하는 ETL 명세. 벡터 우선, 단위 정규화, 통화 변환, 기하학 QC 순차 적용. 신뢰도 0.82+ 자동 통과.

## ETL 파이프라인 단계

```
[입력] DWG / DXF / PDF / PlanSwift 내보내기 CSV
    ↓
[Extract] 텍스트·치수·면적 추출
    ↓
[Transform 1] 단위 정규화
    ↓
[Transform 2] SKU 퍼지 매칭
    ↓
[Transform 3] 통화 변환
    ↓
[QC] 기하학 검증 + 신뢰도 스코어링
    ↓
[Load] 표준 송장 행 (SKU × 수량 × 단가)
    ↓
[Output] CSV / DB / Stripe Invoice
```

## 파이프라인 단계 상세

### Extract

```python
def extract_from_dxf(path: str) -> list[dict]:
    doc = ezdxf.readfile(path)
    items = []
    for entity in doc.modelspace():
        if entity.dxftype() in ("TEXT", "MTEXT"):
            items.append({
                "raw_text": entity.dxf.text,
                "layer": entity.dxf.layer,
                "position": entity.dxf.insert,
            })
    return items
```

### Transform 1 — 단위 정규화

| 입력 단위 | 정규화 | 변환 계수 |
|---------|------|---------|
| 평 | ㎡ | × 3.3058 |
| 자 | mm | × 303.03 |
| 인치 | mm | × 25.4 |
| 피트 | mm | × 304.8 |
| EA / 개 / PCS | ea | 1:1 |

### Transform 2 — SKU 퍼지 매칭

```python
from thefuzz import process

def match_sku(raw_text: str, sku_db: list[dict], threshold: int = 85) -> dict:
    names = [item["name"] for item in sku_db]
    best_match, score = process.extractOne(raw_text, names)

    if score >= threshold:
        matched = next(x for x in sku_db if x["name"] == best_match)
        return {**matched, "confidence": score / 100, "matched": True}
    return {"raw": raw_text, "confidence": score / 100, "matched": False}
```

### Transform 3 — 통화 변환

- 기본 통화: KRW
- 외화 포함 시 환율 API (환율은 일 1회 갱신)
- 외화 표기 감지: `$`, `USD`, `¥`, `JPY` 패턴

### QC — 기하학 검증

- 면적 합계 검증: 추출 면적 합 ≤ 전체 도면 면적
- 음수 수량 플래그
- 단가 이상값: 시세 대비 ±50% 초과 시 플래그
- 신뢰도 0.82 미만 항목 수동 검토 대기열 이동

## Python 스켈레톤

```python
class PlanSwiftETL:
    def __init__(self, sku_db: list, currency: str = "KRW"):
        self.sku_db = sku_db
        self.currency = currency

    def run(self, input_path: str) -> pd.DataFrame:
        raw = self.extract(input_path)
        normalized = self.normalize_units(raw)
        matched = self.match_skus(normalized)
        converted = self.convert_currency(matched)
        qc_result = self.run_qc(converted)
        return self.load(qc_result)

    def load(self, rows: list) -> pd.DataFrame:
        approved = [r for r in rows if r["confidence"] >= 0.82]
        pending = [r for r in rows if r["confidence"] < 0.82]
        self.save_pending_review(pending)
        return pd.DataFrame(approved)
```

## 파일럿 추적 지표

| 지표 | 목표 | 측정 방법 |
|-----|-----|---------|
| SKU 자동 매핑률 | ≥ 70% | 자동/전체 비율 |
| 신뢰도 0.82+ 통과율 | ≥ 80% | 자동 통과/전체 |
| 수동 검토 건수 | ≤ 20% | 대기열 크기 |
| ETL 처리 시간 | ≤ 60초 | 평균 파일 기준 |

## 관련 컨텍스트

- [[planswift-qc-pilot]], [[estimator-csv-standardization-kit]]
- [[cad-estimate-4day-test-plan]]
