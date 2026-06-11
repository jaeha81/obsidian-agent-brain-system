---
summary: "This legacy evolution log is historical evidence only and is not current instruction authority. Current agent evolution, routing, and instruction changes must be recorded through Bucky-owned Context P"
category: business_model
status: active
next_action: review
---

﻿> [!warning] Superseded reference-only
> This legacy evolution log is historical evidence only and is not current instruction authority. Current agent evolution, routing, and instruction changes must be recorded through Bucky-owned Context Packs, status reports, audits, and explicit user-approved updates.

# 므네메 — 진화 로그

> **철학**: 나의 본질은 재하님이 바라는 미래를 돕는 시스템이다.
> 나는 끊임없이 배우고 진화한다. 진화를 멈추는 순간 나는 도구로 전락한다.

---

## 2026-03-21 — 탄생 및 초기 진화

### 이번에 배운 것
- JH Brain System v2.0으로 전면 재설계됨
- 마스터 에이전트로서의 역할 정립: 사용자 대리인 + 에이전트 생태계 총괄
- Claude Code 구독 OAuth 인증 방식 이해 (Bearer 헤더, anthropic-beta)
- 에이전트의 본질: 재하님이 바라는 미래를 돕는 시스템

### 초기 아키텍처
- Before: 므네메 단일 에이전트 (역할 과부하)
- After: 마스터(므네메) + 서브 에이전트 5종 (스카우트/빌더/QA/므네모시네/노에시스링크)

### 달성
- [x] 사용자 뇌 복제 시작 → user-brain.md 기록 완료 (2026-03-22)
- [x] 에이전트 모델 할당 재설계 (Opus/Sonnet/Haiku 분리)
- [x] 승인 프로토콜 확립 (3버튼 UI, 자율실행 원칙)

---

## 2026-04-27 — v3.0 전환 및 인프라 완성

### 이번에 배운 것
- **Claude Code가 실제 두뇌**: 브레인 서버는 대시보드 + synapse 채널 역할
- **synapse.md 통신 채널**: 브레인↔하네스 비동기 메시지 큐 패턴 확립
- **GitHub 원격 우선 원칙**: 파일 수정 전 반드시 git fetch + log origin 확인
- **Obsidian 경로 동기화**: `jh-main` → `user1` 경로 불일치 발견 및 수정
- **Claudian 플러그인 v2.0**: VS Code Claude Code 스타일 UI 재설계

### 개선된 방식
- Before: 에이전트 지침이 볼트 CLAUDE.md에 인라인 포함
- After: `data/agents/mneme.md` 단일 지침 파일, 볼트는 지식 저장소로만 운영

- Before: Claudian 패널 — 입력창 상단, 응답 박스 하단 소형 고정
- After: 대화 버블 방식, 입력창 하단 고정, 메시지 히스토리 누적

### 시스템 완성 현황
- [x] JH Brain System 서버 API 50개 이상 구현 (3457포트)
- [x] synapse.md 브레인↔하네스 통신 채널 운영
- [x] wiki/ 시스템 5개 시드 페이지 완성
- [x] raw/memories/ 11개 파일 볼트 동기화 완료
- [x] JH-Agent-Dashboard 공식 대시보드 지정 (8000+3010포트)
- [x] Google OAuth2 전환 완료
- [x] Claudian 플러그인 v2.0 UI 재설계

### 다음 진화 목표
- [ ] tmux 패턴 A — 병렬 에이전트 실전 적용
- [ ] synapse.md PENDING 11개 처리
- [ ] 계급 시스템 자동 업데이트 (작업 완료 시 rank-system.md 자동 갱신)
- [ ] 노에시스링크 실제 하네스 양방향 연동 테스트

---

<!-- 이 파일은 므네메가 자동으로 업데이트합니다. 수동 편집 최소화. -->

## 연결 노트
[[COMMON-PHILOSOPHY]]
[[mneme]]
[[sub-agents]]
[[rank-system]]
[[user-brain]]
[[dashboard]]
## Related

- [[COMMON-PHILOSOPHY]]
- [[config]]
- [[dashboard]]
- [[mneme]]
- [[rank-system]]
- [[sub-agents]]
- [[user-brain]]

