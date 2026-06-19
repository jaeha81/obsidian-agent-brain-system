---
title: 이부장 오늘의 운영 리포트
date: 2026-06-09
source: daily-plus/2026-06-09.md (Card 1)
priority: P1
category: knowledge
status: distilled
tags:
- ibujang
- ops-report
- quality-check
- deployment
- rollback
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 이부장 오늘의 운영 리포트

> ChatGPT Pulse 2026-06-09 Card 1 증류 (P1 · knowledge-candidate)

## 목적

이부장 에이전트 일일 운영 지시서. 4단계 실행으로 품질 유지, 배포 무결성, 매출 실험, 결과 보고를 자동화한다.

## 4단계 지시서 포맷

### 1단계 — 품질(드리프트) 체크

```
지시: 오늘 처리된 견적 데이터의 드리프트를 확인하라.
기준:
  - 단가 이상: 시세 대비 ±30% 초과 항목
  - 단위 불일치: ㎡/m²/평 혼재
  - 누락 필드: 품목코드, 수량, 단가 중 하나라도 공백
보고: 이상 항목 수 + 비율 + 최악 3건 요약
```

### 2단계 — 배포 무결성 확인

```
지시: 오늘의 매니페스트 체크섬을 검증하라.
명령: sha256sum manifest.json | diff - manifest.sha256
결과: PASS 또는 FAIL + 불일치 파일 목록
```

### 3단계 — 매출 실험(A/B) 시작

```
지시: 가격 제안 A/B 테스트를 오늘 배포하라.
A안: 표준 견적 + 10% 마진
B안: 패키지 번들 + 15% 마진
추적 지표: 성사율, 평균 견적 금액, 고객 피드백 점수
```

### 4단계 — 결과 보고

```
보고 시각: 매일 17:00
형식:
  - 처리 건수: N건
  - 드리프트 감지: N건 (비율 X%)
  - 배포 상태: PASS/FAIL
  - A/B 결과: A안 성사율 X% vs B안 Y%
  - 추천 액션: [이부장 판단]
```

## 드리프트 체크 방법

```python
# drift_check.py
import pandas as pd

df = pd.read_csv('견적_오늘.csv')
anomalies = df[
    (df['단가'] > df['시세_단가'] * 1.3) |
    (df['단가'] < df['시세_단가'] * 0.7)
]
print(f"이상 항목: {len(anomalies)}건 ({len(anomalies)/len(df)*100:.1f}%)")
```

## 롤백 트리거

다음 조건 발생 시 즉시 롤백:
- 드리프트 비율 > 20%
- 매니페스트 체크섬 FAIL
- A/B 테스트 성사율 < 전일 대비 30% 하락

## 관련 컨텍스트

- [[manifest-hmac-acceptance]]
- [[poc-verify-matrix]]
- [[3-mvp-7day-launch]]
