---
title: CAD→견적 MVP 4일 테스트 계획
date: 2026-06-05
source: daily-plus/2026-06-05.md (Card 6)
priority: P1
category: knowledge
status: distilled
tags:
  - cad
  - estimate
  - mvp
  - testing
  - dxf
  - bim
  - daily-plus
  - knowledge
---

# CAD→견적 MVP 4일 테스트 계획

> ChatGPT Pulse 2026-06-05 Card 6 증류 (P1 · knowledge-candidate)

## 목적

CAD/BIM 도면 파일을 자동 처리하고 텍스트·치수·SKU를 추출해 DB 자재와 매핑하는 4일짜리 실전 워크플로우. 우선권: DXF > SVG > PNG.

## 파일 형식 우선순위

| 순위 | 형식 | 이유 | 처리 방식 |
|-----|-----|-----|---------|
| 1 | DXF | 벡터, 레이어 정보 포함, 파싱 용이 | ezdxf 라이브러리 |
| 2 | DWG | 업계 표준이나 독점 포맷 | LibreDWG 변환 후 DXF 처리 |
| 3 | SVG | 벡터 기반, 치수 텍스트 추출 가능 | XML 파싱 |
| 4 | PDF | 벡터 PDF는 텍스트 추출 가능 | pdfminer / pymupdf |
| 5 | PNG/JPG | 래스터, OCR 필요 | Tesseract + vision model |

## 4일 테스트 일정

### Day 1 — 파일 인제스트 + 텍스트 추출

- DXF 파일 3종 로드 (단순 평면도 / 복잡 평면도 / 설비 도면)
- 레이어별 텍스트·치수 추출
- 추출 결과 CSV 저장
- **목표**: 텍스트 추출률 ≥ 90%

### Day 2 — SKU 매핑 + 자재 DB 연결

- 추출 텍스트 → SKU 퍼지 매칭 (임계값 85%)
- 자재 DB 쿼리 (품목코드, 단가, 단위)
- 미매핑 항목 수동 검토 대기열 생성
- **목표**: SKU 자동 매핑률 ≥ 70%

### Day 3 — 견적서 생성 + 검증

- 매핑 결과 → 표준 견적 CSV 변환
- 금액 계산 (수량 × 단가)
- 사람 검수용 diff 보고서 생성
- **목표**: MAPE ≤ 15% (수동 견적 대비)

### Day 4 — 엣지 케이스 + 실패 대응

- 스캔 PDF, 기울어진 도면, 다국어 텍스트 테스트
- 실패 케이스 분류 및 폴백 로직 구현
- 파이프라인 최종 정리 및 문서화

## 합격 기준

| 지표 | 목표값 | 측정 방법 |
|-----|-------|---------|
| 텍스트 추출률 | ≥ 90% | 수동 샘플 대비 |
| SKU 자동 매핑률 | ≥ 70% | 전체 항목 대비 |
| MAPE (견적 오차) | ≤ 15% | 전문가 견적 대비 |
| 신뢰도 점수 | ≥ 0.75 | 모델 출력 confidence |
| 처리 시간 | ≤ 60초/도면 | 평균 A2 크기 기준 |

## 실패 시 대응

| 실패 유형 | 대응 방법 |
|---------|---------|
| 텍스트 추출 실패 | Vision model (GPT-4o/Claude) OCR 폴백 |
| SKU 미매핑 | 수동 검토 대기열 → 사람 검수 |
| 치수 인식 오류 | 레이어 필터 재조정 |
| 처리 시간 초과 | 병렬 처리 / 청크 분할 |

## 도구 스택

```
ezdxf          ← DXF 파싱
LibreDWG       ← DWG → DXF 변환
pymupdf        ← PDF 텍스트 추출
Tesseract      ← 래스터 이미지 OCR
thefuzz        ← 퍼지 문자열 매칭 (SKU)
pandas         ← 데이터 변환 및 CSV 생성
```

## 관련 컨텍스트

- PlanSwift QC 파일럿과 연계 (→ [[planswift-qc-pilot]])
- [[estimator-csv-standardization-kit]], [[ai-material-matching-prototype]]
