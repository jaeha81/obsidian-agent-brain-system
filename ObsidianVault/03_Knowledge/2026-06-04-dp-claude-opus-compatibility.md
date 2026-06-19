---
type: knowledge-note
date: 2026-06-04
source: daily-plus
category: agent-prompting
tags:
- '#area/ai_automation'
- '#status/active'
summary: Claude Opus 4.8 주요 변경사항 — trustworthy performance 중심 전환, Bucky/Claude 통합
  마이그레이션 가이드
status: staged
applied_at: 2026-06-11
approval_required: true
approval_note: Bucky approval needed before applying to integration
graph_cluster: daily-practice
---

# Claude Opus 4.8 Compatibility Brief

## 개요

Claude Opus 4.8은 raw capability 위주에서 **trustworthy performance** 중심으로 전환된 주요 업데이트다. JH 에이전트 시스템의 Bucky/Claude 통합에 직접 영향을 미치는 변경사항을 포함한다.

## 주요 변경사항

### 1. 신뢰성 우선 설계
- 응답 일관성 강화: 동일 프롬프트에 대한 편차 감소
- 거절율 조정: 과도한 거절 패턴 수정, 작업 완수율 향상
- Tool use reliability: 복잡한 multi-step 도구 체인 안정성 개선

### 2. 프롬프트 포맷 변경
- System prompt 구조: 역할 정의를 앞부분에 명확히 배치 권장
- XML 태그 사용: `<instruction>`, `<context>`, `<output_format>` 태그 지원 강화
- 긴 컨텍스트 처리: 200K 토큰에서의 정보 retrieval 정확도 향상

### 3. 에이전트 루프 변경
- 자율 판단 범위 확대: 명시적 승인 없이 수행 가능한 작업 범위 조정
- 중단 조건 명확화: 불확실 시 질문하는 빈도 조정 (과도한 확인 감소)

## JH 에이전트 시스템 마이그레이션 포인트

### Bucky 통합
```python
# 기존 패턴 (4.7 이하)
system = "당신은 Bucky입니다. 오케스트레이터 역할..."

# 권장 패턴 (4.8+)
system = """<role>Bucky — JH 에이전트 오케스트레이터</role>
<capabilities>task routing, approval gating, memory management</capabilities>
<constraints>approval_required 항목은 반드시 사용자 확인 후 실행</constraints>"""
```

### Claude Code 통합
- `--system-prompt` 파일 방식 유지 가능
- 도구 허용 목록 재검토: 4.8에서 도구 실행 패턴 변경 가능성

## 체크리스트 (Bucky 승인 필요)

- [ ] Bucky 시스템 프롬프트 XML 태그 방식으로 전환 여부 검토
- [ ] `bucky.md` 프롬프트 포맷 업데이트 적용 승인
- [ ] Claude Code 설정 파일 호환성 테스트
- [ ] 기존 tool use 체인 회귀 테스트 실행

## 참고

- 공식 릴리즈 노트: Anthropic changelog 2026-06
- 관련 노트: `2026-05-28-dp-codex-claude-separation-pattern.md`

## 관련 노트
- [[hubs/JH System]]
