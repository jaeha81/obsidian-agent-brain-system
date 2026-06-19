---
title: 원격 실패 시 로컬 전환
date: 2026-05-28
source: daily-plus/2026-05-28.md (Card 6)
priority: P2
category: knowledge
status: distilled
tags:
- fallback
- local-llm
- reliability
- dispatcher
- resilience
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 원격 실패 시 로컬 전환

> ChatGPT Pulse 2026-05-28 Card 6 증류 (P2 · knowledge)

## 목적
원격 LLM 장애 시 로컬 LLM으로 자동 전환하는 원격 계획·로컬 실행 패턴. 디스패처/로컬 실행기/검증 스니펫으로 구성. API 장애나 네트워크 단절 시에도 에이전트 워크플로우의 연속성을 보장.

## 핵심 내용
- **폴백 트리거 조건**:
  - HTTP 응답 없음 (타임아웃 10초)
  - HTTP 5xx 오류 2회 연속
  - API 토큰 한도 초과
  - 네트워크 연결 불가
- **디스패처 로직**:
  ```python
  async def dispatch(prompt: str) -> str:
      try:
          return await remote_llm(prompt, timeout=10)
      except (TimeoutError, APIError, RateLimitError):
          logger.warning("Remote LLM failed, switching to local")
          return await local_llm(prompt)
  ```
- **로컬 LLM 설정**:
  - ollama + llama3 또는 mistral 권장
  - GPU 없는 환경: llama.cpp CPU 모드
  - 응답 품질 저하 허용 범위 사전 정의
- **검증 스니펫**: 원격/로컬 응답 스키마 동일 여부 체크

## 구현 체크리스트
- [ ] 폴백 트리거 조건별 예외 처리 코드 작성
- [ ] ollama 또는 llama.cpp 로컬 설치 및 모델 다운로드
- [ ] 디스패처 retry 로직 (지수 백오프)
- [ ] 폴백 발생 시 알림 (Discord/로그)
- [ ] 원격/로컬 응답 품질 비교 테스트

## 관련 컨텍스트
- 로컬 에이전트 오프라인 우선: `2026-05-28-dp-local-agent-offline-first.md`
- 온디바이스 API 비용 절감: `2026-05-28-dp-on-device-api-cost-reduction.md`
- Model Routing 정책: Vault Memory `project_model_routing.md`

## 관련 노트
- [[hubs/JH System]]
