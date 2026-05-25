---
tags: [migration, system, archive]
created: 2026-05-25
type: migration-check
---

# 마이그레이션 크로스체크 — 2026-05-25

> 소스: `G:\내 드라이브\JH-SHARED\00_SYSTEM\` (11개 파일)  
> 대상: `ObsidianVault/` (worktree: obsidian-agent-brain-system)  
> 확인자: Claude Sub-Agent (자동 분석)

---

## 현황 요약

ObsidianVault worktree(`ObsidianVault/`)는 현재 **초기 단계**로, 실제 이관된 파일이 매우 제한적이다.

- 실존 폴더: `00_System/`, `07_Reports/` 2개만
- `05_Frameworks/guides/` 폴더 자체가 아직 미생성
- 법률/지식 Context Pack 폴더 미생성 (vault_scaffold에 `.gitkeep`만 존재)
- 실제 Obsidian Vault (로컬: `C:\Users\user1\Documents\Obsidian Vault\`)는 별도 구조(00_Inbox, 01_Projects 등)를 사용 중

---

## ✅ 이관 완료

| G드라이브 파일 | 상태 | ObsidianVault 대응 |
|---|---|---|
| (없음 — 직접 대응 없음) | — | — |

**참고:** G드라이브 00_SYSTEM 파일들은 Obsidian Vault에 직접 복사 이관된 파일이 없다. 대신 `CLAUDE.md` 전역 지침에 포인터(`상세 → ObsidianVault/05_Frameworks/guides/...`)로 참조되는 구조다. `ObsidianVault/00_System/BUCKY_STATUS.md`는 Bucky 플러그인이 자동 생성하는 런타임 파일로, G드라이브 소스와 무관하다.

---

## ⚠️ 미이관 (처리 필요)

### 시스템 가이드 파일 — ObsidianVault/05_Frameworks/guides/ 로 이관 권장

| G드라이브 파일 | 크기 | 권장 Vault 경로 | 이유 |
|---|---|---|---|
| `00_SYSTEM/sync-protocol.md` | 9.7KB | `ObsidianVault/05_Frameworks/guides/sync-protocol.md` | CLAUDE.md가 이미 이 경로를 포인터로 참조 |
| `00_SYSTEM/agent-onboarding.md` | 2.6KB | `ObsidianVault/05_Frameworks/guides/agent-onboarding.md` | 에이전트 온보딩 절차 — 지식 자산 |
| `00_SYSTEM/jh-system.md` | 3.1KB | `ObsidianVault/05_Frameworks/guides/jh-system.md` | 시스템 브리핑 — 지식 자산 |
| `00_SYSTEM/paths.md` | 3.0KB | `ObsidianVault/05_Frameworks/guides/paths.md` | 경로 참조표 — 지식 자산 |
| `00_SYSTEM/roles.md` | 2.5KB | `ObsidianVault/05_Frameworks/guides/roles.md` | 역할 정의 — 지식 자산 |
| `00_SYSTEM/shared-protocol.md` | 4.1KB | `ObsidianVault/05_Frameworks/guides/shared-protocol.md` | 충돌 방지 프로토콜 — 지식 자산 |

### Boris 보고서 — ObsidianVault/07_Reports/ 로 이관 권장

| G드라이브 파일 | 크기 | 권장 Vault 경로 | 이유 |
|---|---|---|---|
| `00_SYSTEM/boris-phase1-report.md` | 5.5KB | `ObsidianVault/07_Reports/boris-phase1-report.md` | 완료 보고서 — 개발 기록 |
| `00_SYSTEM/boris-phase2-report.md` | 4.1KB | `ObsidianVault/07_Reports/boris-phase2-report.md` | 완료 보고서 — 개발 기록 |
| `00_SYSTEM/boris-phase2-plan.md` | 6.9KB | `ObsidianVault/07_Reports/boris-phase2-plan.md` | 설계 계획 — 개발 기록 |

### 병렬 세션 템플릿 — ObsidianVault/08_Templates/ 로 이관 권장

| G드라이브 파일 | 크기 | 권장 Vault 경로 | 이유 |
|---|---|---|---|
| `00_SYSTEM/parallel-session-template.md` | 2.8KB | `ObsidianVault/08_Templates/parallel-session-template.md` | 재사용 템플릿 — 지식 자산 |

### session-state.md — 이관 불필요 (G드라이브 전용 유지)

| G드라이브 파일 | 이유 |
|---|---|
| `00_SYSTEM/session-state.md` | 동적 파일 (세션마다 덮어씀). G드라이브가 멀티 PC 공유 허브이므로 이 위치가 canonical. Vault 이관 시 오히려 충돌 우려 |

---

## 🔒 G드라이브 전용 유지 (이관 불필요)

| 파일/폴더 | 이유 |
|---|---|
| `01_AGENT_ROOM/agent-room-messages.jsonl` | 실시간 append-only 메시지 큐 — Claude↔Codex 공유 채널. Vault에 넣으면 Git 오염 우려 |
| `01_AGENT_ROOM/inbox/` | 수신 큐 디렉터리. 처리 후 `processed/`로 이동하는 파이프라인 전용 |
| `01_AGENT_ROOM/processed/` | 처리 완료 메시지 아카이브. 운영 데이터이므로 Vault 불필요 |
| `01_AGENT_ROOM/failed/` | 실패 메시지 보관. 운영 데이터 |
| `00_SYSTEM/session-state.md` | 위 참조 — 동적 재개 포인터 |

---

## 이관 우선순위 권장

| 우선순위 | 파일 | 이유 |
|---|---|---|
| P1 | `sync-protocol.md` | CLAUDE.md가 이미 `ObsidianVault/05_Frameworks/guides/sync-protocol.md`를 참조 — 포인터 깨짐 상태 |
| P1 | `paths.md` | CLAUDE.md 포인터 `knowledge-paths.md` 관련 |
| P2 | `agent-onboarding.md`, `roles.md`, `shared-protocol.md`, `jh-system.md` | 지식 자산 체계화 |
| P3 | boris 보고서 3개, parallel-session-template.md | 개발 기록 보관 |

---

## 이관 전 선행 작업

1. `ObsidianVault/05_Frameworks/guides/` 폴더 생성 (현재 미존재)
2. `ObsidianVault/08_Templates/` 폴더 생성 (현재 미존재)
3. vault_scaffold 폴더 구조를 실제 ObsidianVault에 적용 (Phase 1 완료 작업)
