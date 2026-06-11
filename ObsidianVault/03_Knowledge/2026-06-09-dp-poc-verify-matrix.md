---
title: PoC 검증 매트릭스와 실패 대응
date: 2026-06-09
source: daily-plus/2026-06-09.md (Card 6)
priority: P1
category: knowledge
status: distilled
tags:
  - poc
  - verification
  - test-plan
  - go-nogo
  - dxf
  - daily-plus
  - knowledge
---

# PoC 검증 매트릭스와 실패 대응

> ChatGPT Pulse 2026-06-09 Card 6 증류 (P1 · knowledge-candidate)

## 목적

도면→물량/매핑 PoC 테스트 플랜. 6-8개 짧은 테스트로 파싱·매핑·단위변환·가격이상·오류복구를 검증하고 수치 임계값으로 Go/No-Go를 결정한다.

## 6개 핵심 테스트 케이스

| # | 테스트명 | 입력 | 기대값 | 임계값 |
|---|---------|------|--------|--------|
| T01 | 기본 파싱 | 단순 DXF (선 10개) | 10개 엔티티 파싱 | 100% 파싱 성공 |
| T02 | 면적 추출 | 폴리라인 구역 3개 | 면적값 ±5% 이내 | 오차 < 5% |
| T03 | SKU 매핑 | 레이어명 WALL/FLOOR/CEILING | 올바른 SKU 반환 | 매핑률 > 90% |
| T04 | 단위 변환 | mm² 면적값 | ㎡ 변환 정확도 | 오차 < 0.1% |
| T05 | 가격 이상 탐지 | 시세 대비 2배 단가 | 플래그 발생 | 탐지율 100% |
| T06 | 오류 복구 | 깨진 DXF 파일 | 예외 처리 + 로그 | 크래시 없음 |

## 추가 테스트 (옵션)

| # | 테스트명 | 조건 |
|---|---------|------|
| T07 | 대용량 DXF | 1,000개 이상 엔티티 | 30초 내 처리 |
| T08 | 한국어 레이어명 | 레이어명 "벽체/바닥/천장" | 인코딩 오류 없음 |

## Go/No-Go 기준값

```
GO 조건 (모두 충족 필요):
  T01: 파싱 성공률 = 100%
  T02: 면적 오차 < 5%
  T03: SKU 매핑률 > 90%
  T04: 단위 변환 오차 < 0.1%
  T05: 가격 이상 탐지율 = 100%
  T06: 오류 처리 시 크래시 없음

NO-GO 조건 (하나라도 해당):
  T01 실패 → DXF 파서 교체 검토
  T02 오차 > 10% → 파싱 로직 수정
  T03 매핑률 < 80% → SKU 테이블 보완
```

## 오류 유형별 대응

| 오류 유형 | 증상 | 대응 |
|-----------|------|------|
| 파싱 실패 | ezdxf.InvalidDXFDocument | DXF 버전 확인 (R12/R2000) |
| 인코딩 오류 | UnicodeDecodeError | `encoding='cp949'` 시도 |
| 좌표 이상 | 음수 면적 | 폴리라인 방향(CW/CCW) 확인 |
| 레이어 없음 | KeyError | 기본값 SKU 또는 수동 매핑 |

## 실패 학습 방법

1. 실패 케이스를 `test_failures/` 폴더에 원본 DXF와 함께 보관
2. 실패 원인과 해결책을 이 파일 하단에 추가
3. 다음 PoC 버전에서 회귀 테스트로 포함

## 관련 컨텍스트

- [[cad-estimate-poc-path]]
- [[estimator-csv-standardization-kit]]
- [[ibujang-ops-report]]
