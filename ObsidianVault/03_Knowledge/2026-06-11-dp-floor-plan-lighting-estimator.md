---
title: Floor-Plan Lighting Estimator Concept
date: 2026-06-11
source: daily-plus/2026-06-10.md (Card 12)
priority: P3
category: knowledge
status: distilled
tags:
- lighting
- floor-plan
- estimator
- cad
- interior
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# Floor-Plan Lighting Estimator Concept

> ChatGPT Pulse 2026-06-10 Card 12 증류 (P3 · knowledge-candidate)

## 목적

평면도(PDF/PNG/DWG)에서 실별 조명 설비 수량을 자동 산출하는 개념 도구. 인테리어 조명 설계와 견적을 자동화한다.

## 입력 처리

- PDF/PNG/DWG 평면도 업로드
- 실내 영역 자동 감지
- 벽/창/문 인식
- 기본 천장높이 추론 (표시 없을 시 2.4m 기본값)

## 조명도 목표 기준 (KS A 3011)

| 공간 | 권장 조명도 |
|-----|-----------|
| 거실 | 150–300 lx |
| 주방 | 300–500 lx |
| 침실 | 75–150 lx |
| 욕실 | 150–300 lx |
| 사무실 | 500–750 lx |
| 복도 | 50–100 lx |

## 산출 공식

```
설비 개수 = (조명도 목표 × 면적) / (루멘 × CU × LLF)

CU: Coefficient of Utilization (0.5~0.8)
LLF: Light Loss Factor (0.7~0.9)
```

## 설비 유형

| 유형 | 루멘 범위 | 적용 공간 |
|-----|---------|---------|
| 다운라이트 (6인치) | 600–1200 lm | 거실, 복도 |
| 선형 LED (1200mm) | 2000–4000 lm | 주방, 사무실 |
| 트랙 헤드 | 500–1500 lm | 상업공간 |

## 출력 결과물

- PDF 제안서 (표지/평면/실내표/스케줄)
- CSV 내보내기 (실명, 면적, 설비유형, 수량, 단가)
- 균등 배치 레이아웃 (드래그로 조정 가능)

## MVP 구현 범위

- [ ] 실 인식 (이미지 → 폴리곤 감지)
- [ ] 면적 계산
- [ ] 조명도 목표 선택 UI
- [ ] 설비 개수 자동 계산
- [ ] CSV 출력

## 관련 컨텍스트

- [[CAD-to-Estimate PoC]] 파이프라인 확장
- [[Estimator CSV Standardization Kit]] 출력 연동
- Wishket 인테리어 프로젝트 견적 자동화
