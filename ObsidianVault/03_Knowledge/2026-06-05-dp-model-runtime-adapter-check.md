---
title: 모델별 런타임 어댑터 점검표
date: 2026-06-05
source: daily-plus/2026-06-05.md (Card 3)
priority: P1
category: knowledge
status: distilled
tags:
- llm
- runtime-adapter
- model-migration
- compatibility
- claude
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 모델별 런타임 어댑터 점검표

> ChatGPT Pulse 2026-06-05 Card 3 증류 (P1 · knowledge-candidate)

## 목적

여러 LLM 공급자를 유연하게 다루고 모델 교체/비호환성 문제를 예방하는 런타임 어댑터 체크리스트. Claude 모델 마이그레이션 시 주의사항 포함.

## 공급자별 어댑터 포맷

| 공급자 | 모델 예시 | API 엔드포인트 | 스트리밍 지원 | 툴 호출 형식 |
|-------|---------|--------------|------------|------------|
| Anthropic | claude-sonnet-4-6 | messages API | SSE | `tool_use` 블록 |
| OpenAI | gpt-4o | chat.completions | SSE | `function_call` / `tool_calls` |
| Google | gemini-1.5-pro | generateContent | SSE | `functionCall` |
| Ollama | llama3.2 | /api/chat | SSE | 공급자별 상이 |

## 비호환성 체크 항목

### 시스템 프롬프트

- [ ] `system` 역할 지원 여부 (Anthropic: 별도 파라미터, OpenAI: messages 배열 내)
- [ ] 최대 시스템 프롬프트 길이 제한 확인
- [ ] 캐시 프리픽스(cache_control) 지원 여부

### 컨텍스트 윈도우

- [ ] 최대 토큰 수 확인 (예: Claude 200k, GPT-4o 128k)
- [ ] 입력/출력 토큰 분리 계산 여부
- [ ] 긴 컨텍스트 시 성능 저하 패턴 파악

### 툴 호출 형식

- [ ] 툴 정의 JSON 스키마 호환성
- [ ] 병렬 툴 호출 지원 여부
- [ ] 툴 결과 반환 형식 차이

### 응답 형식

- [ ] `stop_reason` vs `finish_reason` 필드명 차이
- [ ] 스트리밍 청크 구조 차이
- [ ] 오류 코드 및 메시지 형식

## Claude 모델 마이그레이션 체크리스트

Claude 버전 변경 시 (예: claude-3-5-sonnet → claude-sonnet-4-6):

```python
# 어댑터 레이어 예시
class ClaudeAdapter:
    MODEL_MAP = {
        "sonnet": "claude-sonnet-4-6",
        "haiku": "claude-haiku-4-5",
        "opus": "claude-opus-4-5",
    }

    def normalize_response(self, raw: dict) -> dict:
        # stop_reason 정규화
        return {
            "content": raw.get("content", []),
            "stop_reason": raw.get("stop_reason", "end_turn"),
            "usage": raw.get("usage", {}),
        }
```

**마이그레이션 전 확인 목록**:
- [ ] 이전 모델 → 신규 모델 응답 형식 diff 확인
- [ ] 스모크 테스트 3종 실행 (→ [[에이전트용3단계스모크테스트]])
- [ ] 캐시 프리픽스 breakpoints 재설정
- [ ] 툴 정의 스키마 호환성 검증
- [ ] 비용 예측 재계산 (토큰 단가 변동 확인)

## 어댑터 패턴 권장 구조

```
adapters/
  base.py          ← 공통 인터페이스
  anthropic.py     ← Claude 어댑터
  openai.py        ← GPT 어댑터
  google.py        ← Gemini 어댑터
  router.py        ← 모델명 → 어댑터 자동 선택
```

## 관련 컨텍스트

- 모델 교체 시 반드시 스모크 테스트와 함께 실행
- [[에이전트용3단계스모크테스트]], [[model-routing]]
