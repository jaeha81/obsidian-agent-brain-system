---
type: entity
updated: 2026-04-27
sources: [CLAUDE.md, AGENT_MEMORY.md]
tags: [system, jh-brain, architecture, express]
  - #status/archive
---

# JH Brain System

재하님의 두 번째 뇌를 구현하는 중앙 관제 허브.
Claude Code (tmux) 환경 위에서 실행되는 에이전트 오케스트레이터.

---

## 기본 정보

| 항목 | 내용 |
|------|------|
| 위치 | `D:\ai프로젝트\jh-brain-system\` |
| 서버 | `npm start` → http://localhost:3457 |
| 스택 | Express.js + Vanilla JS + Three.js |
| 외부 연동 | Google Sheets / Google Drive |
| Sheets ID | `1FI8K4MNhWYAMKBtjBdTTjAOqwjM0wwtWmZrYN_366G8` |
| 볼트 연결 | `C:\Users\user1\Documents\Obsidian Vault` |

---

## 역할

JH 생태계의 중심 허브. 모든 입력(사용자 지시, GitHub 변경, 에이전트 결과)은 이곳을 통해 수신·분류·라우팅된다.

```
외부 입력
    ↓
[JH Brain System] ← 중앙 관제
    ↙         ↘
[개발 자산]    [지식 자산]
JH Harness    OBSIDIAN-SECOND
Obsidian Vault
```

---

## 에이전트 체계 (므네메 오케스트레이터)

| 역할 | 담당 | 모델 |
|------|------|------|
| 복잡한 분석·설계 | 므네메 직접 처리 | Opus/Sonnet |
| 반복적 구현 | 빌더 위임 (tmux 창) | Sonnet |
| 단순 파일 생성 | Haiku subprocess | Haiku |
| 정보 수집·조사 | 스카우트 위임 | Haiku |
| 검증·오류 탐지 | QA 위임 | Sonnet |
| Obsidian 기록 | 므네모시네 위임 | Haiku |

---

## 공유 메모리

`AGENT_MEMORY.md` — 세션 간 컨텍스트 브리지. 에이전트들의 유일한 공유 상태.

| 섹션 | 내용 |
|------|------|
| 섹션 2 | 현재 작업 상태 |
| 섹션 4 | 파일 소유권 (에이전트별) |
| 섹션 5 | Decision Log |
| 섹션 6 | 블로킹 이슈 |
| 섹션 7 | 완료 체크리스트 |

---

## Google Cloud 연동

- API 엔드포인트: `http://localhost:3457/api/google/*`
- Drive 폴더: `1n7iAzpdiL0znTvgggL6lDK8TNmwRLy8Z` (Obsidian Agent)

---

## 관련 페이지
- [[entity-mneme]] — 브레인시스템 마스터 에이전트
- [[entity-agent-ecosystem]] — 전체 에이전트 구조
- [[concept-dev-workflow]] — 브레인시스템에서 사용하는 개발 워크플로우
