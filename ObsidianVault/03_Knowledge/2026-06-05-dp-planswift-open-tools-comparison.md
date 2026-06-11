---
title: PlanSwift와 오픈 도구 비교표
date: 2026-06-05
source: daily-plus/2026-06-05.md (Card 7)
priority: P3
category: knowledge
status: distilled
tags:
  - planswift
  - cad
  - open-source
  - takeoff
  - automation
  - daily-plus
  - knowledge
---

# PlanSwift와 오픈 도구 비교표

> ChatGPT Pulse 2026-06-05 Card 7 증류 (P3 · knowledge-candidate)

## 목적

건축·CAD·개발 도구 간 데이터 흐름 구축 시 상용 툴(PlanSwift)과 오픈소스 툴의 구조·제약 비교. API 자동화 가능성과 CSV 우선 파이프라인.

## PlanSwift vs 오픈소스 비교표

| 항목 | PlanSwift | LibreCAD | FreeCAD | Bluebeam Revu | 자체 파이프라인 |
|-----|----------|---------|--------|--------------|--------------|
| 라이선스 | 상용 (유료) | GPL v2 | LGPL | 상용 (유료) | 자유 |
| DXF 지원 | O | O | O | O (PDF→) | ezdxf |
| BIM/IFC 지원 | 제한적 | X | O | X | IfcOpenShell |
| API 자동화 | 플러그인 API | CLI 제한 | Python API | 제한적 | 완전 자유 |
| CSV 내보내기 | O | 수동 | 스크립트 | O | 네이티브 |
| 클라우드 연동 | 제한적 | X | X | 클라우드 버전 | 자유 |
| 월 비용 | $99~$299 | 무료 | 무료 | $349~/년 | 개발 비용만 |
| 학습 곡선 | 중간 | 높음 | 높음 | 중간 | 낮음 (스크립트) |

## API 자동화 가능성

### PlanSwift

- 플러그인 SDK 제공 (C#/.NET 기반)
- REST API 없음 → COM 자동화 또는 플러그인 필수
- CSV/Excel 내보내기는 가능하나 배치 자동화 어려움
- **결론**: 자동화 병목, CSV 추출 후 외부 처리 권장

### 오픈소스 경로 (권장)

```python
# ezdxf 기반 DXF 자동 처리
import ezdxf

doc = ezdxf.readfile("floor_plan.dxf")
msp = doc.modelspace()

for entity in msp:
    if entity.dxftype() == "TEXT":
        print(f"텍스트: {entity.dxf.text}, 위치: {entity.dxf.insert}")
    if entity.dxftype() == "DIMENSION":
        print(f"치수: {entity.dxf.text_midpoint}")
```

## CSV 우선 파이프라인 설계

PlanSwift 또는 CAD 도구에 직접 연동하는 대신 CSV를 공통 인터페이스로 사용:

```
CAD 도구 / PlanSwift
    ↓ (CSV 내보내기)
표준 CSV (estimator-csv-standardization-kit)
    ↓ (정규화)
견적 DB / 자재 매핑
    ↓ (출력)
견적서 / 인보이스
```

**장점**:
- 도구 교체 시 파이프라인 재사용 가능
- 사람 검수 포인트 명확
- 자동화 테스트 용이

## 구현 권장 사항

- 단기 (MVP): PlanSwift CSV 내보내기 → 표준화 스크립트
- 중기: ezdxf 기반 DXF 직접 파싱 파이프라인 구축
- 장기: IFC/BIM 파일 지원 (IfcOpenShell 연동)

## 관련 컨텍스트

- [[cad-estimate-4day-test-plan]], [[planswift-qc-pilot]]
- [[estimator-csv-standardization-kit]]
