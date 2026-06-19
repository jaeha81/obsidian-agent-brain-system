---
title: CAD→견적 파이프라인 인덱스
date: 2026-06-11
type: knowledge-index
category: interior-tech
status: active
tags:
- cad
- estimate
- pipeline
- ezdxf
- ocr
- knowledge-index
summary: CAD 파일에서 견적 자동 생성까지의 전체 파이프라인 설계 노트 인덱스. 7개 관련 Daily Plus 카드를 단일 파이프라인 흐름으로
  연결.
next_action: review
graph_cluster: misc
---

# CAD→견적 파이프라인 인덱스

> Daily Plus 2026-05-29 ~ 2026-06-11 CAD/견적 관련 카드 7개 통합 인덱스

---

## 전체 파이프라인 흐름

```
[입력 파일]
PDF / PNG / DWG / DXF / CSV / 스캔
        ↓
[파싱 레이어]
ezdxf 1.4.4 (DXF)
LibreDWG → JSON 변환 (DWG)
Autodesk Platform Services Model Derivative API (IFC/RVT)
        ↓
[엔티티 추출]
LINE, LWPOLYLINE, BLOCK, TABLE 파싱
폴리라인 → 면적/길이 산출
OCR 레이어 (스캔 도면)
        ↓
[자재 매핑]
엔티티 → SKU 코드 매핑
단위 통일 (평→㎡, mm→m)
중복 병합, 가격 이상 플래그
        ↓
[검증]
MAPE, 신뢰도 분포, 파이프라인 오류율
6~8개 테스트 케이스 Go/No-Go
        ↓
[출력]
표준 CSV (공사번호, 공종, 품목코드, 단위, 수량, 단가, 금액)
PDF 견적서 (표지/평면/실내표/스케줄)
Obsidian Vault 저장: 03_Estimate/{날짜}_{현장코드}.md
```

---

## 관련 노트 인덱스

### 파싱/변환

| 파일 | 핵심 내용 |
|------|---------|
| [CAD→견적 PoC 우선 경로](2026-06-09-dp-cad-estimate-poc-path.md) | ezdxf 1.4.4 파싱, Autodesk Platform Services API, Python 환경 설정 |
| [CAD→견적 PoC 구현](2026-06-11-dp-cad-to-estimate-poc.md) | DXF 엔티티 추출, BLOCK/TABLE 검사, 6가지 케이스 파이프라인 |
| [LibreDWG Conversion API](2026-06-04-dp-libredwg-conversion-api.md) | DWG → JSON 오픈소스 변환 API |
| [Bluebeam·Autodesk 대안](2026-06-11-dp-bluebeam-autodesk-alternatives.md) | Bluebeam Revu CSV 내보내기, Autodesk Forma/Takeoff RESTful API |

### 견적 자동화

| 파일 | 핵심 내용 |
|------|---------|
| [Estimator CSV 표준화 키트](2026-06-11-dp-estimator-csv-standardization-kit.md) | 표준 CSV 헤더, Google Apps Script 자동 필드 매핑, 단위 통일(평→㎡) |
| [AI 자재 매칭 프로토타입](2026-06-05-dp-ai-material-matching-prototype.md) | 엔티티→SKU 매핑, 가격 이상 자동 플래그 |
| [평면도 조도 산출](2026-05-29-dp-floor-plan-lighting-calc.md) | 실내 자동 감지, 조도 계산식(럭스×면적/루멘/CU/LLF) |
| [Floor-Plan 조명 견적 Estimator](2026-06-11-dp-floor-plan-lighting-estimator.md) | PDF/PNG/DWG 입력, 다운라이트/선형/트랙 설비 자동 산출 |

### 검증

| 파일 | 핵심 내용 |
|------|---------|
| [PoC 검증 매트릭스](2026-06-09-dp-poc-verify-matrix.md) | 6~8개 테스트, MAPE, 신뢰도 분포, 파이프라인 오류율, Go/No-Go 기준 |
| [CAD→견적 4일 테스트 계획](2026-06-05-dp-cad-estimate-4day-test-plan.md) | Day1~4 단계 테스트, 실패 케이스 대응 절차 |

---

## CSV 출력 표준 헤더

```csv
현장,공사번호,공종,품목코드,품목명,규격,단위,수량,단가,금액,비고
```

- **현장**: 현장코드 (예: GN001)
- **공종**: 철근콘크리트/목공/전기/기계/도장 등
- **품목코드**: 국가표준 자재 코드 또는 자체 SKU
- **단위**: ㎡, m, EA, kg, SET 등 (평 사용 금지)

---

## 구현 체크리스트

### 1단계 — PoC (DXF 파싱 + CSV 출력)

- [ ] Python 환경: `pip install ezdxf pandas openpyxl`
- [ ] 테스트 DXF 파일 3종 준비 (평면도, 입면도, 구조도)
- [ ] `scripts/cad_parser.py` 구현: 엔티티 추출 → CSV 변환
- [ ] 6개 테스트 케이스 작성 및 MAPE < 10% 달성

### 2단계 — 자재 매핑

- [ ] 자재 마스터 DB 구축 (SKU, 단가, 단위)
- [ ] 엔티티→SKU 매핑 규칙 정의
- [ ] 단위 자동 변환 (평→㎡ 등)
- [ ] 가격 이상 플래그 임계값 설정

### 3단계 — 견적서 출력

- [ ] PDF 견적서 템플릿 작성
- [ ] CSV → PDF 변환 스크립트 구현
- [ ] Obsidian 자동 저장: `03_Estimate/{날짜}_{현장코드}.md`

---

## 기술 선택 근거

| 도구 | 용도 | 비용 |
|------|------|------|
| ezdxf 1.4.4 | DXF 파싱 (오픈소스) | 무료 |
| LibreDWG | DWG→JSON (오픈소스) | 무료 |
| Autodesk APS | IFC/RVT 파싱 (클라우드) | 유료 (PoC 후 검토) |
| Google Apps Script | CSV 자동화 | 무료 |
| reportlab | PDF 견적서 생성 | 무료 |

> **Phase 1 원칙**: 오픈소스만 사용, 클라우드 API 비용 없음. PoC 검증 후 Autodesk APS 도입 여부 결정.
