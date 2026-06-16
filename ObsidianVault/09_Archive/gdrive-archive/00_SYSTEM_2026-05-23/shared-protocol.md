# JH-SHARED 충돌 방지 협의 프로토콜

> 합의일: 2026-05-01
> 합의 주체: Claude (구현 총괄) + Codex (독립 검수)
> 사용자 승인 후 확정

---

## 폴더별 쓰기 권한

| 폴더 | Claude | Codex | 비고 |
|------|--------|-------|------|
| `00_SYSTEM/` | ✅ 쓰기 | ❌ 읽기만 | 시스템 규칙 단일 관리자 = Claude |
| `01_AGENT_ROOM/` | ✅ append-only | ✅ append-only | 기존 라인 수정·삭제 금지 |
| `02_HANDOFF/` | ✅ 쓰기 | ❌ 읽기만 | handoff는 Claude 운영 총괄 역할 |
| `03_LOGS/` | ✅ append-only | ✅ append-only | 로그성 파일, 덮어쓰기 금지 |
| `99_ARCHIVE/` | ✅ 이동·정리 | ❌ 제안만 | 삭제·이동은 Claude 담당 |
| 루트 `JH-SHARED/` | ❌ 신규 생성 금지 | ❌ 신규 생성 금지 | README.md 하나만 허용 |

---

## 파일명 네이밍 규칙

| 유형 | 규칙 | 예시 |
|------|------|------|
| Claude 생성 문서 | `claude-YYYYMMDD-topic.md` | `claude-20260501-sync-update.md` |
| Codex 검수 보고 | `codex-review-YYYYMMDD-topic.md` | `codex-review-20260501-handoff.md` |
| 공동 참조 문서 | `shared-YYYYMMDD-topic.md` | `shared-20260501-protocol.md` |
| 로그 파일 | `*.jsonl` (append-only) | `sync-state.jsonl` |
| 임시 초안 | `_draft-YYYYMMDD-owner-topic.md` | `_draft-20260501-claude-notes.md` |

---

## 절대 금지

1. 루트에 운영 파일 신규 생성 금지
2. canonical 문서 복사본을 다른 폴더에 중복 생성 금지
3. `.json` 메시지 로그 재사용 금지 → `.jsonl`만 사용
4. 기존 로그 라인 수정·삭제 금지 (append-only 원칙)
5. Codex가 `00_SYSTEM/`, `02_HANDOFF/`, `99_ARCHIVE/`를 직접 수정·이동 금지
6. 날짜·소유자 없는 파일명 사용 금지
7. `final`, `latest`, `new`, `copy`, `backup` 등 모호한 파일명 금지
8. 같은 주제의 v2/v3 파일 중복 생성 금지 → 기존 canonical에 변경 이력 섹션 추가

---

## Canonical 파일 목록

| 파일 | canonical 위치 |
|------|---------------|
| 시스템 브리핑 | `00_SYSTEM/jh-system.md` |
| 경로 참조표 | `00_SYSTEM/paths.md` |
| 동기화 프로토콜 | `00_SYSTEM/sync-protocol.md` |
| 역할 정의 | `00_SYSTEM/roles.md` |
| 에이전트 온보딩 | `00_SYSTEM/agent-onboarding.md` |
| 공유 협의 프로토콜 | `00_SYSTEM/shared-protocol.md` (이 파일) |
| Agent Room 메시지 | `01_AGENT_ROOM/agent-room-messages.jsonl` |
| 동기화 스냅샷 | `03_LOGS/sync-state.jsonl` |

---

## 갱신 절차

이 문서를 수정해야 할 경우:
1. Claude가 초안 작성
2. Codex가 검수 의견 보고
3. 사용자 승인 후 Claude가 반영
---

## 2026-05-06 추가 합의 — Codex 직접 실행 예외

- `00_SYSTEM/`, `02_HANDOFF/`, `99_ARCHIVE/`에 대한 Codex 기본 권한은 기존처럼 제한한다.
- 단, 사용자가 Codex에게 직접 반영을 명시 지시한 경우 Codex는 해당 범위의 문서를 수정할 수 있다.
- Codex는 수정 전 대상 파일을 확인하고, 수정 후 변경 내용과 검증 결과를 사용자에게 직접 보고한다.
- Codex는 루트 `JH-SHARED/`에 신규 파일을 만들지 않는다. 필요한 내용은 기존 canonical 문서에 반영한다.
- Codex가 Agent Room이나 GitHub 관련 작업을 수행한 경우, 필요 시 `01_AGENT_ROOM/agent-room-messages.jsonl` 또는 Agent Room API를 통해 Claude에게 결과를 공유한다.

---

## 2026-05-15 추가 합의 — 피드백 루프 원칙

- Claude는 구현을 담당하고, Codex는 독립 검수와 위험 보고를 담당한다.
- Codex 검수 결과는 Claude가 자동으로 처리하지 않고, 사용자가 우선순위와 반영 여부를 결정한다.
- 사용자가 Codex에게 직접 실행을 지시한 경우에만 Codex가 수정·검증·보고까지 진행할 수 있다.
- 구현 완료와 검증 완료는 별도 상태로 기록한다. 검증이 끝나지 않은 항목은 `[미검증]`으로 남긴다.
- 반복되는 합의·오류·환경 차이는 다음 세션에서 재사용할 수 있도록 canonical 문서 또는 daily report에 남긴다.
