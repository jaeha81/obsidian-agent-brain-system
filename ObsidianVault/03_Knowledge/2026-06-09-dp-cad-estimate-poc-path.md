---
title: CAD→견적 PoC 우선 경로
date: 2026-06-09
source: daily-plus/2026-06-09.md (Card 5)
priority: P1
category: knowledge
status: distilled
tags:
- cad
- estimate
- ezdxf
- poc
- python
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# CAD→견적 PoC 우선 경로

> ChatGPT Pulse 2026-06-09 Card 5 증류 (P1 · knowledge-candidate)

## 목적

ezdxf 1.4.4로 DXF 파싱→소재 SKU 매핑→CSV 추출 PoC를 Python 환경에서 구현한다.

## ezdxf 설치 및 환경

```bash
pip install ezdxf==1.4.4
# 보안 이슈: 1.3.x 이하 버전 사용 금지 (CVE-2024-xxxx)
```

## DXF 파싱 코드

```python
import ezdxf
from ezdxf.math import BoundingBox

def parse_dxf(file_path: str) -> list[dict]:
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()
    items = []
    for entity in msp:
        if entity.dxftype() == 'LINE':
            length = entity.dxf.start.distance(entity.dxf.end)
            items.append({
                'type': 'LINE',
                'layer': entity.dxf.layer,
                'length_mm': round(length, 2)
            })
        elif entity.dxftype() == 'LWPOLYLINE':
            area = entity.get_area()
            items.append({
                'type': 'AREA',
                'layer': entity.dxf.layer,
                'area_sqm': round(area / 1_000_000, 4)  # mm² → ㎡
            })
    return items
```

## SKU 매핑 로직

```python
LAYER_TO_SKU = {
    'WALL': {'sku': 'WD-PANEL-12T', 'unit': '㎡', 'price': 45000},
    'FLOOR': {'sku': 'FL-TILE-600', 'unit': '㎡', 'price': 38000},
    'CEILING': {'sku': 'CL-GYPSUM-9T', 'unit': '㎡', 'price': 22000},
}

def map_sku(parsed_items: list) -> list[dict]:
    result = []
    for item in parsed_items:
        sku_info = LAYER_TO_SKU.get(item['layer'].upper(), {})
        if sku_info:
            qty = item.get('area_sqm') or item.get('length_mm', 0) / 1000
            result.append({
                '품목코드': sku_info['sku'],
                '단위': sku_info['unit'],
                '수량': round(qty, 2),
                '단가': sku_info['price'],
                '금액': round(qty * sku_info['price'])
            })
    return result
```

## CSV 출력 형식

```python
import csv

def export_csv(mapped_items: list, output_path: str):
    fieldnames = ['품목코드', '단위', '수량', '단가', '금액']
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(mapped_items)
```

## 클라우드 서비스 옵션

| 서비스 | 특징 | 비고 |
|--------|------|------|
| APS Model Derivative API | DWG→SVF 변환 | 유료 |
| ODA Cloud | DXF→PDF/SVG | 멤버십 필요 |
| ezdxf 로컬 | DXF 직접 파싱 | 무료, PoC 적합 |

## 관련 컨텍스트

- [[poc-verify-matrix]]
- [[aps-oda-alternatives]]
- [[estimator-csv-standardization-kit]]
