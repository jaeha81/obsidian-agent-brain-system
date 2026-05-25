---
tags: [migration, status]
updated: 2026-05-25
generated_by: Agent-M (migration_crosscheck)
gdrive_root: "G:\\내 드라이브\\JH-SHARED"
vault_root: "G:\\내 드라이브\\obsidian-agent-brain-system\\ObsidianVault"
---
# G드라이브 이관 현황

> 분석 기준: 2026-05-25  
> 이관 로그(`gdrive-migration-log.json`) 미존재 → Vault 대상 경로 실존 + 수동 이관 기록 기반 크로스체크  
> 분석 도구: `scripts/migration_crosscheck.py` 정의 기준 + `gdrive_agent_room_migrator.py` MIGRATION_MAP 기준

---

## 이관 완료

### 00_SYSTEM (11개 파일) — 수동 이관 완료
소스: `JH-SHARED/00_SYSTEM/`  
대상: `ObsidianVault/05_Frameworks/guides/` (수동 이관, migrator 대상 경로와 다름)

| 파일 | 대상 경로 | 비고 |
|---|---|---|
| `agent-onboarding.md` | `05_Frameworks/guides/agent-onboarding.md` | 생성 완료 |
| `boris-phase1-report.md` | `05_Frameworks/guides/boris-phase1-report.md` | 생성 완료 |
| `boris-phase2-plan.md` | `05_Frameworks/guides/boris-phase2-plan.md` | 생성 완료 |
| `boris-phase2-report.md` | `05_Frameworks/guides/boris-phase2-report.md` | 생성 완료 |
| `jh-system.md` | `05_Frameworks/guides/jh-system.md` | 생성 완료 |
| `parallel-session-template.md` | `05_Frameworks/guides/parallel-session-template.md` | 생성 완료 |
| `paths.md` | `05_Frameworks/guides/paths.md` | frontmatter 업데이트 |
| `roles.md` | `05_Frameworks/guides/roles.md` | 생성 완료 |
| `session-state.md` | `05_Frameworks/guides/session-state-gdrive.md` | 스냅샷 미러 |
| `shared-protocol.md` | `05_Frameworks/guides/shared-protocol.md` | 머지 완료 (gdrive 버전이 최신) |
| `sync-protocol.md` | `05_Frameworks/guides/sync-protocol.md` | 머지 완료 (전체 섹션 포함) |

### 02_HANDOFF (7개 파일) — 수동 이관 완료
소스: `JH-SHARED/02_HANDOFF/`  
대상: `ObsidianVault/00_System/archive/handoffs/` (수동 이관)  
원본 7파일 전부 대응 파일 확인됨.

- `agent-startup-check.md`
- `claude-brief-agent-room-rehome.md`
- `claude-obsidian-upgrade.md`
- `claude-sync-context-guard.md`
- `codex-sync-redesign-협의.md`
- `handoff-20260502-claude-web.md`
- `session-handoff-20260430.md`

### 03_LOGS (일부, 2개 파일) — 수동 이관 완료
소스: `JH-SHARED/03_LOGS/`  
대상: `ObsidianVault/00_System/archive/`

- `sync-log.md` → `00_System/archive/sync-log-gdrive.md`
- `sync-manifest.md` → `00_System/archive/sync-manifest-gdrive.md`

---

## 미이관 (대기)

### 00_SYSTEM → `00_System/gdrive-system/` (migrator 경로 미존재)
수동 이관이 `05_Frameworks/guides/`로 완료됐으나, migrator 정의 경로(`00_System/gdrive-system/`)는 미생성.  
**자동 migrator 실행 시 중복 이관 발생 가능** — 주의 필요.

### 03_LOGS (잔여 19개 파일) → `05_Logs/gdrive-imported/`
대상 폴더 미존재 (`05_Logs/` 폴더 자체도 없음).

| 유형 | 파일 수 | 크기 |
|---|---|---|
| `.jsonl` 로그 파일 4개 | `agent-room-route-ingest.jsonl`, `daily-report-events.jsonl`, `routine-reports.jsonl`, `sync-state.jsonl` | 합계 약 1 MB |
| `.md` 파일 2개 (`DAILY/` 하위) | `2026-05-01.md`, `2026-05-20.md` | 약 5 KB |
| `.png` 스크린샷 13개 | `obsidian-jh-local-graph-*.png` | 합계 약 5.3 MB |

### 04_DAILY_REPORTS (16개 파일) → `05_Logs/daily-reports-gdrive/`
대상 폴더 미존재. `2026/2026-05/` 하위 14개 일별 리포트 + README + TEMPLATE.

| 파일 | 크기 |
|---|---|
| `2026-05-01.md` | 6.6 KB |
| `2026-05-02.md` | 11.6 KB |
| `2026-05-03.md` | 3.2 KB |
| `2026-05-04.md` | 3.3 KB |
| `2026-05-05.md` | 1.8 KB |
| `2026-05-11.md` | 2.1 KB |
| `2026-05-12.md` | 3.4 KB |
| `2026-05-15.md` | 7.5 KB |
| `2026-05-16.md` | 4.2 KB |
| `2026-05-20.md` | 4.7 KB |
| `2026-05-22.md` | 2.1 KB |
| `2026-05-25.md` | 1.4 KB |
| `2026-05-01.entries/codex/P0517A-22H2T8.jsonl` | 731 B |
| `2026-05-20.entries/codex/P0517A-22H2T8.jsonl` | 6.5 KB |
| `README.md` | 1.8 KB |
| `TEMPLATE.md` | 708 B |

### 06_TASK_LOGS (2개 파일) → `05_Logs/task-logs-gdrive/`
대상 폴더 미존재.

- `2026-05/TASK-20260502-134420.jsonl` (268 B)
- `README.md` (698 B)

### scripts/ (5개 파일) → `00_System/gdrive-scripts/`
대상 폴더 미존재.

- `export-caveman-skills.ps1`
- `generate-jh-wiki-graph.ps1`
- `import-caveman-skills.ps1`
- `jh-local-knowledge-graph.ps1`
- `obsidian-sync-notebook.sh`

### JH-SHARED 루트 파일 (3개) → `00_System/gdrive-root-files/`
migrator ROOT_FILE_PATTERNS (`*.json`, `*.md`) 대상. 대상 폴더 미존재.

- `README.md`
- `config.notebook.json`
- `session-handoff-20260501.md`
- `노트북-옵시디언-설정가이드.md` (`.md` 해당, 이관 대상)

---

## 제외 (이관 불필요 / 정책 미결)

### 01_AGENT_ROOM — 주파일 이관 완료, 잔여는 제외 권장
`agent-room-messages.jsonl` → `10_AgentBus/agent-room-messages.jsonl` 이관 완료.  
`processed/`, `failed/` 서브폴더의 처리 완료/실패 메시지 파일은 아카이브 성격으로 이관 생략 가능.

### 05_TASK_LOCKS — MIGRATION_MAP 미포함
`active/` 비어있음, `done/TASK-20260502-134420.jsonl` 1건.  
migrator MIGRATION_MAP에 미포함 → 이관 여부 사용자 결정 필요.

### 99_ARCHIVE — MIGRATION_MAP 미포함, 이관 불필요
22개 파일 보유. `00_SYSTEM_2026-05-23/` (00_SYSTEM 구 버전 백업), `daily-reports-legacy/`, 레거시 jsonl.  
G드라이브 내 아카이브로 보존 권장. 이관 필요 시 `09_Archive/gdrive-legacy/`로 별도 처리.

---

## 요약

| 항목 | 수치 |
|---|---|
| MIGRATION_MAP 대상 폴더 | 8개 (스크립트+루트파일 포함) |
| 이관 완료 (수동) | 00_SYSTEM(11), 02_HANDOFF(7), 03_LOGS 일부(2) |
| 이관 완료 (자동) | 01_AGENT_ROOM 주파일 1개 |
| 미이관 항목 | 약 45개 파일, 약 6~7 MB |
| 제외/보류 | 3개 폴더 (05_TASK_LOCKS, 99_ARCHIVE, 01_AGENT_ROOM 잔여) |
| 이관 로그 (`gdrive-migration-log.json`) | 미존재 — migrator 실행 후 생성됨 |

---

## 권장 조치

1. **migrator 실행 전 주의**: `00_SYSTEM` 파일들은 이미 `05_Frameworks/guides/`에 수동 이관됨.  
   migrator가 `00_System/gdrive-system/`으로 중복 복사하지 않도록 `--skip-log` 대신 수동 확인 필요.

2. **즉시 실행 가능 (미이관 폴더)**:
   ```
   python scripts/gdrive_agent_room_migrator.py --dry-run
   # 결과 확인 후:
   python scripts/gdrive_agent_room_migrator.py
   ```
   대상: `03_LOGS` (잔여), `04_DAILY_REPORTS`, `06_TASK_LOGS`, `scripts/`, 루트 파일

3. **05_Logs 폴더 미존재**: migrator가 자동 생성하므로 별도 수동 작업 불필요.

4. **05_TASK_LOCKS 이관 여부 결정**: migrator MIGRATION_MAP에 추가 여부를 결정한 후 스크립트 수정.

5. **99_ARCHIVE 정책 결정**: 이관 불필요 시 G드라이브에 보존. 이관 원할 경우 `09_Archive/gdrive-legacy/` 경로로 수동 처리.
