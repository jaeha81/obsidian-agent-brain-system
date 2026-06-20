---
title: Runnable 6-Case CAD-to-Estimate PoC
date: 2026-06-11
source: daily-plus/2026-06-10.md (Card 3)
priority: P3
category: knowledge
status: distilled
tags:
- cad
- estimate
- ezdxf
- poc
- autodesk
- interior
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: daily-practice
---

# Runnable 6-Case CAD-to-Estimate PoC

> ChatGPT Pulse 2026-06-10 Card 3 증류 (P3 · knowledge-candidate)

## 목적

DXF 도면에서 자동으로 수량을 추출하여 견적서를 생성하는 PoC. ezdxf 라이브러리로 로컬 파싱, Autodesk Platform Services로 클라우드 메타데이터 추출을 병행한다.

## 기술 스택

### 로컬 파싱 (ezdxf)
```python
import ezdxf

doc = ezdxf.readfile("plan.dxf")
msp = doc.modelspace()

for entity in msp:
    if entity.dxftype() == "LINE":
        start = entity.dxf.start
        end = entity.dxf.end
        length = start.distance(end)
    elif entity.dxftype() == "LWPOLYLINE":
        # 면적 계산
        pass
    elif entity.dxftype() == "INSERT":
        # 블록 참조 (창호, 기둥 등)
        block_name = entity.dxf.name
```

### 클라우드 파싱 (Autodesk Platform Services)
- Model Derivative API → 구조화된 메타데이터 (JSON)
- DWF, RVT, IFC 형식 지원
- 층별, 실별 면적 자동 추출

## 6-Case 테스트 시나리오

| # | 도면 유형 | 추출 목표 |
|---|----------|----------|
| 1 | 단순 평면도 | 전체 바닥 면적 |
| 2 | 구획 평면도 | 실별 면적 분리 |
| 3 | 창호 도면 | 창문/문 개수 |
| 4 | 천장 도면 | 천장 면적 + 다운라이트 위치 |
| 5 | 단면도 | 벽체 높이 × 길이 = 도배 면적 |
| 6 | 배치도 | 외부 공사 범위 |

## 평가 지표

- 자동 매핑 비율 (MAPE)
- 신뢰도 분포 (95th percentile)
- 파이프라인 오류율

## 구현 상태

- [ ] ezdxf 기반 LINE/LWPOLYLINE 파서
- [ ] 블록 카운터 (INSERT 엔티티)
- [ ] 면적 계산 알고리즘
- [ ] CSV 견적 출력 연동

## 관련 컨텍스트

- [[Estimator CSV Standardization Kit]] 와 연동
- Autodesk Platform Services API 키 필요
