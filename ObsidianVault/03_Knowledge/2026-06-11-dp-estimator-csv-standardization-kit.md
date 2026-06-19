---
title: Estimator CSV Standardization Kit
date: 2026-06-11
source: daily-plus/2026-06-10.md (Card 2)
priority: P1
category: knowledge
status: distilled
tags:
- csv
- estimator
- standardization
- google-apps-script
- interior
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# Estimator CSV Standardization Kit

> ChatGPT Pulse 2026-06-10 Card 2 증류 (P1 · knowledge-candidate)

## 목적

인테리어·건축 현장 견적 데이터를 표준 CSV 형식으로 정규화하는 자동화 키트. Google Apps Script 기반으로 필드 매핑, 단위 변환, 중복 병합, 이상값 플래그 처리를 자동화한다.

## 표준 CSV 헤더

| 컬럼명 | 설명 |
|-------|-----|
| 현장 | 프로젝트 이름 또는 주소 |
| 공사번호 | 고유 공사 ID |
| 공종 | 목공, 전기, 설비, 도장 등 |
| 품목코드 | 내부 자재 코드 |
| 품명 | 자재 또는 작업명 |
| 규격 | 규격/사양 |
| 단위 | ㎡, m, 개, 식 등 |
| 수량 | 숫자 |
| 단가 | 원 |
| 금액 | 수량 × 단가 |
| 비고 | 예외사항 |

## Google Apps Script 자동화 처리

- **숫자 정리**: 콤마, 공백, 이상 문자 제거
- **단위 통일**: 평 → ㎡ (1평 = 3.3058㎡), 자 → m 등
- **중복 병합**: 동일 품목코드 행 합산
- **가격 이상 플래그**: 시세 대비 ±30% 이상 자동 표시
- **UTF-8 인코딩**: BOM 포함, 로케일 설정, 선행 0 보존 (공사번호 등)

## 출력 시트 구조

```
정규화_견적   ← 정리된 표준 데이터
예외사항      ← 플래그된 항목 목록
```

## 구현 우선순위

- [ ] 단위 변환 함수 (평 → ㎡, 자 → m)
- [ ] 중복 품목코드 병합 로직
- [ ] 이상값 감지 임계값 설정
- [ ] CSV export 함수

## 관련 컨텍스트

- 인테리어·건축 설계 자동화 파이프라인 일부
- Wishket 견적 프로젝트와 연동 가능
- [[견적자동화파이프라인]], [[csv-estimator]]
