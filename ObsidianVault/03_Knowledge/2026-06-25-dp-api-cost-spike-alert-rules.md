---
title: API 비용 스파이크 대응 규칙 (NOTICE·URGENT·AUTO)
date: 2026-06-25
source: daily-plus/2026-06-25.md (Card 4)
priority: P3
category: knowledge
status: distilled
tags:
- api-cost
- spike-detection
- alert-rules
- automation
- notice-urgent-auto
- cost-management
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: cost-ops
---

# API 비용 스파이크 대응 규칙 (NOTICE·URGENT·AUTO)

> ChatGPT Pulse 2026-06-25 Card 4 증류 (P3 · knowledge-candidate)

## 3단계 에스컬레이션 구조

```
예산 임계값 도달
  → NOTICE (80%) : 알림 발송
    → URGENT (90%) : 비핵심 모델 다운그레이드 + 캐시 강제
      → AUTO (100%) : 비핵심 작업 자동 차단 (백프레셔)
```

## 단계별 액션 규칙표

| 단계 | 트리거 | 자동 액션 | 알림 |
|------|--------|-----------|------|
| NOTICE | 예산 80% 도달 | 없음 (모니터링 강화) | 이메일/Slack 경고 |
| URGENT | 예산 90% 도달 | 모델 다운그레이드, 캐시 강제 활성화 | 긴급 알림 + 담당자 호출 |
| AUTO | 예산 100% 도달 | 비핵심 작업 중단, 낮은 비용 옵션 전환 | 자동 차단 알림 |

## 예측 기반 비용 관리

- 호출 로그를 웨어하우스에 적재 후 **48시간 단기 예측** 수행
- 과거 소비 · 토큰 패턴으로 비용 폭주 사전 감지
- Rate Limit 헤더 / Billing API 활용 → 남은 쿼터 실시간 추적

## API 한도 모니터링 포인트

```
Rate Limit 헤더 실시간 파싱
  → 80~90% 구간에서 알람 설정
  → 초과 직전 자동 제어 삽입
```

## 구현 시 참고 패턴

1. **로그 수집**: 모든 API 호출 → 웨어하우스 적재 (비용·토큰·지연 포함)
2. **예측 모델**: 과거 패턴 → 48h 예측치 계산
3. **임계값 알람**: 80% / 90% / 100% 도달 시 각각 다른 액션
4. **자동 대응**: 고비용 모델 → 저비용 모델 라우팅 전환
5. **실시간 쿼터 추적**: 벤더 API 헤더 파싱으로 남은 쿼터 확인

## JH 환경 적용 포인트

- [[bucky-ai-api-routing-policy]] 폴백 체인과 연계 가능
- [[2026-06-25-dp-ai-api-token-cost-calculator]] 단가 테이블과 결합하여 실제 임계값 계산

## 연결 노트
- [[2026-06-25-dp-ai-api-token-cost-calculator]]
- [[bucky-ai-api-routing-policy]]


## 2026-06-27 보충: 48시간 예측 기반 운영 설정

> ChatGPT Pulse 2026-06-27 Card 3 증류 (P3 · verification)

### 실측 지출 스냅샷 (2026-06-27 기준)

| 항목 | 값 |
|------|-----|
| 최근 7일 지출 | $1,120 |
| 최근 24시간 | $180 |
| 버킷 사용액 | $2,950 / $4,000 (73.8%) |
| 48시간 예측 | $7,430 → 185.8% (초과 위험 큼) |

### 바로 적용할 YAML 설정 (복붙용)

```yaml
budget:
  limit: 4000
  gates:
    - level: notice
      when_pct: 0.80
      actions: [notify_ops, tag_heavy]
    - level: urgent
      when_pct: 0.90
      actions: [reroute_to_cheap, set_max_output_512]
    - level: auto
      when_pct: 1.00
      actions: [pause_bulk, throttle_high_cost_50, cache_only_low]

routing:
  rules:
    - match: {heavy: true, env: "staging"}
      route: "cheap-model"
    - match: {task: "summary|embed", size: "large"}
      route: "cheap-model"

limits:
  max_output_tokens: 512
  max_input_tokens: 12000

batch:
  schedule_minutes: 60
```

### 즉시 차단 체크리스트

- [ ] BUDGET_LIMIT=4000, NOTICE=0.8, URGENT=0.9, AUTO=1.0 환경변수 확인
- [ ] heavy=true 잡 라우팅 규칙 활성화 여부
- [ ] 배치 크론 완화 (`*/60 * * * *`) 적용 여부
- [ ] AUTO 발동 시 정지 목록: 대용량 요약, 대량 임베딩, 샘플 생성형 콘텐츠

## 2026-06-28 보충: 예측 공식과 멱등 정책 상세

> ChatGPT Pulse 2026-06-28 Card 5 증류 (P1 · knowledge-candidate)

### 핵심 예측 공식

```
avg_hour = spent_7d / 168
spike_uplift = max(0.15, (spent_last24h / avg_hour - 1) * 0.5)
forecast_48h = current_bucket_used + avg_hour × 48 × (1 + spike_uplift)
```

- `avg_hour`: 7일 실측 지출 ÷ 168시간 (래그 지표)
- `spike_uplift`: 최근 24시간 스파이크 감지 (리드 지표) — 최소 15% 상향
- `forecast_48h`: 현재 사용액 + 48시간 예측치

### 폴백 모델 매핑 (fallback_map)

| 고비용 모델 | 폴백 |
|-------------|------|
| `gpt-5.5` | `gpt-5.4-mini` |
| `openai-expensive` | `bedrock-nemotron-nano-2` |

### 멱등 정책 (중복 알림 방지)

```python
new_sha = sha256(canonicalize(snapshot_json))
if new_sha != last_emitted_sha and gate:
    emit(gate, actions, idempotency_key=f"policy/{vendor}/{new_sha}")
```

벤더 스냅샷 정규화 → sha256 비교 → 내용이 바뀌었을 때만 알림/조치 발행.

### 운영 팁

- 리드·래그 지표 분리: `spent_last24h`(스파이크 감지) vs `spent_7d`(기반 추정)
- 샘플링 간격: 15~60분 권장
- NOTICE → Slack 채널, URGENT/AUTO → 온콜 + 런북 링크
