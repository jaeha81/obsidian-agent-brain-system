---
title: AI API 토큰 비용 계산기와 모델별 비교
date: 2026-06-25
source: daily-plus/2026-06-25.md (Card 3)
priority: P3
category: knowledge
status: distilled
tags:
- ai-api
- token-cost
- cost-calculator
- bedrock
- openai
- model-routing
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: cost-ops
---

# AI API 토큰 비용 계산기와 모델별 비교

> ChatGPT Pulse 2026-06-25 Card 3 증류 (P3 · knowledge-candidate)

## 핵심 원칙

- 입력(input)과 출력(output) 토큰에 각각 별도 과금
- 출력 토큰이 보통 더 비쌈
- 모델 성능이 높을수록 단위당 비용 증가

## 비용 계산 공식

```
총 비용 = (입력_토큰 / 1,000,000 × 입력_단가) + (출력_토큰 / 1,000,000 × 출력_단가)
```

### 예시 (GPT-5.5 기준)

| 항목 | 값 |
|------|----|
| 입력 단가 | $5.00 / 1M tokens |
| 출력 단가 | $30.00 / 1M tokens |
| 예: 2,000 in + 4,000 out | $0.01 + $0.12 = **$0.13** |
| 예: 50 in + 100 out | 극히 낮음 (< $0.004) |

## 대체 제공자 비교

| 제공자 | 특징 |
|--------|------|
| OpenAI 직접 API | GPT-5.5: $5/$30 per 1M |
| AWS Bedrock (GPT-5.5/5.4) | OpenAI와 동일 요율 |
| AWS Bedrock (Nova 계열) | 훨씬 저렴, 토큰당 비용 대폭 감소 |
| 기타 벤더 | 몇 센트~수십 달러 범위 |

## 실무 적용 원칙

1. **고비용 작업 감지**: 예상 토큰 수 × 단가로 사전 계산
2. **임계값 차단**: 호출당 비용이 설정값 초과 시 차단 또는 저비용 모델로 자동 전환
3. **저비용 대체**: GPT-5.5 → Nova 계열 등 라우팅 규칙 적용

## JH 환경 적용 포인트

- [[project_model_routing]] 참조 — 작업 유형별 Sonnet/Haiku/Opus 라우팅 정책과 연계
- 비용 한도 초과 시 NOTICE/URGENT/AUTO 규칙 (`2026-06-25-dp-api-cost-spike-alert-rules`) 발동

## 연결 노트
- [[2026-06-25-dp-api-cost-spike-alert-rules]]
- [[2026-06-05-dp-model-runtime-adapter-check]]
- [[bucky-ai-api-routing-policy]]
