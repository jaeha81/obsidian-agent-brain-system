---
title: 온디바이스 실험으로 API 비용 줄이기
date: 2026-05-28
source: daily-plus/2026-05-28.md (Card 12)
priority: P1
category: knowledge
status: distilled
tags:
- on-device
- api-cost
- llm
- edge
- optimization
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 온디바이스 실험으로 API 비용 줄이기

> ChatGPT Pulse 2026-05-28 Card 12 증류 (P1 · knowledge)

## 목적
AI 추론비용 절감 3종 실험팩. 이미지/3D/에이전트 앱을 로컬+엣지에서 싸고 빠르게 실행. f16 기준 품질 유지하면서 토큰비·지연시간·처리량 동시 개선. 클라우드 API 의존도를 줄여 월 운영 비용을 구조적으로 낮추는 전략.

## 핵심 내용
- **모델 크기 선택 기준**:
  - 단순 분류/라우팅: 7B 이하 (llama3.2:3b, phi3:mini)
  - 코드 생성/분석: 13B~34B (codellama, deepseek-coder)
  - 복잡한 추론: 70B+ 또는 원격 API 유지
- **배치 처리**:
  ```python
  # 개별 호출 대신 배치로 비용 절감
  responses = await asyncio.gather(*[
      llm.ainvoke(prompt) for prompt in batch_prompts
  ])
  # OpenAI Batch API: 50% 할인
  ```
- **캐시 전략**:
  - 동일 프롬프트 SHA256 키로 Redis 캐시 (TTL 1시간)
  - 시맨틱 캐시: 유사도 0.95 이상이면 캐시 히트 처리
  - Claude Prompt Caching: 1024+ 토큰 고정 프리픽스에 cache_control 적용
- **로컬 추론 도구**: ollama, llama.cpp, vllm (GPU), mlx (Apple Silicon)
- **비용 측정**: 도입 전후 월 토큰 사용량 및 비용 비교 기록

## 구현 체크리스트
- [ ] 현재 API 호출 패턴 분석 (단순/복잡 분류)
- [ ] 단순 작업 로컬 모델 라우팅 구현
- [ ] Redis 프롬프트 캐시 구현
- [ ] OpenAI Batch API 또는 Claude Prompt Caching 적용
- [ ] 월별 비용 트래킹 대시보드 구축

## 관련 컨텍스트
- API 비용 절감 실전 스니펫: `2026-05-29-dp-api-cost-reduction-snippets.md`
- 원격 실패 시 로컬 전환: `2026-05-28-dp-remote-fail-local-fallback.md`
- AI Usage 대시보드: Vault Memory `project_session_2026-06-06.md`

## 관련 노트
- [[hubs/JH System]]
