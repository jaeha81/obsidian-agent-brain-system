---
title: 휴먼 검수와 롤백 운영 패턴
date: 2026-06-05
source: daily-plus/2026-06-05.md (Card 4)
priority: P1
category: knowledge
status: distilled
tags:
- human-review
- rollback
- canary
- feature-flag
- dashboard
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: daily-practice
---

# 휴먼 검수와 롤백 운영 패턴

> ChatGPT Pulse 2026-06-05 Card 4 증류 (P1 · knowledge-candidate)

## 목적

신뢰 가능한 예측 검증-운영을 대시보드에 넣을 수 있는 실전 설계안. 기능플래그로 카나리→링(1%→5%→25%→100%) 자동 승격·자동 롤백. 검증 UI는 소형 카드.

## 카나리 승격 임계값

| 단계 | 트래픽 비율 | 대기 시간 | 자동 승격 조건 |
|-----|-----------|---------|--------------|
| 카나리 | 1% | 30분 | 오류율 < 0.5%, p99 레이턴시 < 2s |
| 링 1 | 5% | 1시간 | 오류율 < 0.3%, 검수자 승인 1명 |
| 링 2 | 25% | 2시간 | 오류율 < 0.2%, 검수자 승인 2명 |
| 전체 | 100% | — | 모든 링 통과 |

```yaml
# feature-flag 예시 (LaunchDarkly / GrowthBook 호환)
feature_flag:
  key: "new-estimate-model-v2"
  rollout:
    canary: 1
    ring1: 5
    ring2: 25
    full: 100
  auto_rollback:
    error_rate_threshold: 0.5
    latency_p99_ms: 2000
```

## 롤백 트리거 조건

자동 롤백이 실행되는 조건:

- **오류율**: 현재 단계 임계값 초과 시 즉시 이전 단계로 복귀
- **레이턴시 급증**: p99 레이턴시 2배 이상 상승
- **검수자 거부**: 링 승격 단계에서 검수자가 명시적 거부
- **수동 롤백**: 대시보드 "즉시 롤백" 버튼 클릭

```python
def check_auto_rollback(metrics: dict, flag: FeatureFlag) -> bool:
    if metrics["error_rate"] > flag.threshold.error_rate:
        trigger_rollback(flag, reason="error_rate_exceeded")
        return True
    if metrics["p99_latency_ms"] > flag.threshold.latency_p99_ms:
        trigger_rollback(flag, reason="latency_spike")
        return True
    return False
```

## 검증 카드 UI 구성

대시보드에 삽입하는 소형 카드 컴포넌트:

```
┌─────────────────────────────────────┐
│  새 견적 모델 v2  [카나리: 1%]  🟡    │
│  오류율: 0.2%  레이턴시: 340ms        │
│  검수자: ○ 승인 대기                  │
│  [승인] [거부] [롤백]                  │
└─────────────────────────────────────┘
```

**필드 구성**:
- 기능명 + 현재 단계
- 실시간 오류율 + p99 레이턴시
- 검수자 승인 상태
- 액션 버튼 (승인 / 거부 / 즉시 롤백)

## 구현 체크리스트

- [ ] 기능플래그 시스템 선택 (LaunchDarkly / GrowthBook / 자체 구현)
- [ ] 메트릭 수집 파이프라인 연동 (Prometheus / Datadog)
- [ ] 자동 승격 조건 함수 구현
- [ ] 롤백 트리거 함수 구현
- [ ] 대시보드 검증 카드 컴포넌트 개발
- [ ] 검수자 알림 (Slack / Discord 웹훅)

## 관련 컨텍스트

- AI 모델 배포 및 에이전트 업그레이드 시 필수 패턴
- [[approval-gate]], [[에이전트용3단계스모크테스트]]
