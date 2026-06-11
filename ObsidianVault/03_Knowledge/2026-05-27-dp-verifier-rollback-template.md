---
title: 검증자와 롤백 템플릿 모음
date: 2026-05-27
source: daily-plus/2026-05-27.md (Card 6)
priority: P1
category: knowledge
status: distilled
tags:
  - verification
  - rollback
  - bucky
  - codex
  - agent-orchestration
  - daily-plus
  - knowledge
---

# 검증자와 롤백 템플릿 모음

> ChatGPT Pulse 2026-05-27 Card 6 증류 (P1 · knowledge)

## 목적
에이전트/오케스트레이션 작업 자동 검증 및 실패 시 안전 롤백을 위한 BUCKY Verifier 템플릿. Codex·Claude 모두 붙여넣기용으로 plan→executor→outputs 흐름 검증. 에이전트 작업의 신뢰성과 복원력을 보장하는 표준 절차.

## 핵심 내용
- **자동 검증 체크리스트**:
  - plan.json 스키마 유효성 검사
  - executor 출력물 예상 파일/필드 존재 여부
  - SHA256 해시 일치 (plan → outputs)
  - 감사 로그 타임스탬프 연속성 확인
- **롤백 트리거 조건**:
  - 검증 실패 2회 이상
  - executor 타임아웃 (기본 60초)
  - 출력물 스키마 불일치
  - 감사 로그 누락
- **감사 로그 필수 항목**:
  ```json
  {
    "task_id": "...",
    "agent": "bucky|codex|claude",
    "action": "plan|execute|verify|rollback",
    "timestamp": "ISO8601",
    "input_sha256": "...",
    "output_sha256": "...",
    "status": "success|failure|rollback",
    "error": null
  }
  ```
- **롤백 실행 순서**: 감사 로그 기록 → 출력물 제거 → 이전 상태 복원 → 알림 발송

## 구현 체크리스트
- [ ] plan.json JSON Schema 정의 및 검증 함수 작성
- [ ] executor 출력물 기대값 명세 문서화
- [ ] 롤백 트리거 조건 코드 구현
- [ ] 감사 로그 필수 필드 강제 검증
- [ ] 롤백 후 알림(Discord/이메일) 발송 연동

## 관련 컨텍스트
- Codex·Claude 분리 운영 패턴: `2026-05-28-dp-codex-claude-separation-pattern.md`
- JCS 검증용 1줄 스모크: `2026-05-29-dp-jcs-smoke-verifier.md`
- Bucky 운영 규칙: `ObsidianVault/03_Projects/agents/bucky.md`
