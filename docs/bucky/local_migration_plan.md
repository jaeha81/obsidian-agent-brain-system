# 로컬 D: 이전 실행 계획서 (콜드 컷오버)

> 작성: 2026-07-21 (vscode 환경) · 상태: **승인 대기** · 실행은 승인 후에만
> 결정 확정: **M1 = A** (운영 전부 D:, 매일밤 D:→G: 단방향 백업) / **M2 = A** (전역 CLAUDE.md 저장경계 + settings.json 훅 G:→D: 갱신)
> 관련: `docs/bucky/current_state_audit.md:30` (컷오버 확정), memory `project_local_migration_target.md`

---

## 0. 한눈에 (비개발자용 요약)

지금 브레인 시스템은 **구글드라이브(G:)** 위에서 돌아갑니다. 구글드라이브는 "스트리밍 마운트"라 파일이 실제로 PC에 없을 때가 있고, 예전에 여기서 **DB가 손상된 적(06-28)**이 있습니다. 그래서 운영 전체를 **내 컴퓨터의 D: 드라이브(로컬)**로 옮기고, 구글드라이브는 **매일밤 백업본만 받는 창고**로 강등합니다.

- **옮긴 뒤**: 실행·저장·정본 = D: / 구글드라이브 = 백업 창고
- **가장 위험한 함정**: 볼트 13,904개 파일 중 git이 추적하는 건 34개뿐 → **git으로만 옮기면 13,870개가 증발**. 반드시 파일 통째 복사(robocopy) 병행.

---

## ⛔ 치명 함정 3가지 (실행 전 반드시 숙지)

| # | 함정 | 근거(실측) | 대응 |
|---|------|-----------|------|
| 1 | **git만으로는 볼트 전멸** | `git ls-files ObsidianVault` = 34 vs 실제 13,904 | robocopy 파일복사 **병행 필수** (ObsidianVault\, data\, .env, brain_mcp\) |
| 2 | **D: 클론이 죽어있음** | D: HEAD=`9b32d17` master, 07-05 (18일 stale). 운영은 `bucky-os-v3-core` HEAD `348f21f` | 단순 pull 불가 → **재클론/재fetch**. D: 로컬커밋·미추적파일 덮기 전 확인 |
| 3 | **08:00 자동 파이프라인이 split-brain 유발** | `BuckyDailyPlusPipeline`이 G:에서 자동 커밋/푸시 | 컷오버 시작 시 **반드시 Disable** (안 하면 G:서 다시 갈라짐) |

---

## 1. 옮길 대상 (데이터)

robocopy로 파일 통째 복사(git 미추적분 포함):
- `ObsidianVault\` (13,904 파일 — 볼트 본체, 최우선)
- `data\` (체크리스트·메모리 인덱스·암호화 미러 등)
- `.env` (git 미추적 비밀값)
- `brain_mcp\` (미추적 신규 폴더)
- 그 외 git 추적분은 재클론으로 커버

**제외(옮기지 않음)**:
- gbrain DB = `C:\Users\user1\.gbrain\brain.pglite\` (원래 C: 상주, 이전 불필요)
- `gbrain-http-serve` 예약작업 = G: 무참조 (건드릴 필요 없음)

---

## 2. 재배선 대상 (경로가 G:를 가리키는 곳)

### 2-1. 예약작업 5개
- `bucky-chat-server`
- `BuckyDailyPlusPipeline` (⛔ 컷오버 시 Disable 후 D:로 재작성)
- `ObsidianBrain_CollectionScheduler`
- `ObsidianBrain_ModalityCheck`
- `ObsidianBrain_WikiLint`

### 2-2. Startup 3개
- `watchdog.lnk`
- `chat_server_autostart.vbs` (⚠️ 중복기동 주의)
- `SupabaseQueueWorker` → `worker_launcher.py:19` 하드코딩 경로

### 2-3. 설정/소스 하드코딩
- 전역 `settings.json` 훅 5개 (변경 전 `.bak` 백업)
- 전역 `CLAUDE.md` 저장경계 루트
- `.codex/config.toml` L86
- `automation.toml` L12
- `.claude.json`, `.mcp.json`
- 소스 27개 파일의 하드코딩 `G:` 경로

**완화 요소**:
- `scripts/core/config.py` 이미 포터블 (`BUCKY_ROOT` 환경변수 지원)

---

## 2-4. 정찰 확정 데이터 (2026-07-21 병렬 조사 3건)

- **D: 여유 253 GB vs 필요 ~0.4 GB** (볼트 380MB/13,904, data 11MB, brain_mcp 0.02MB) — 용량 무제한.
- **D:-only 내용 안전조치 완료**: 미추적 3파일 → scratchpad `D_clone_rescue/` 백업. 로컬커밋 `9b32d17` 작업은 G: 운영브랜치에 `a29806d`로 이미 반영 = 소실 없음. → **D: 통째 덮기 안전.**
- **소스 하드코딩 A그룹 = 29파일/34라인** (개별 치환 필수, `core.config` 미사용): resolve_migration_conflicts.py:21, apply_conflict_merges.py:18, four_folder_migration.py:32, estimation/boq_builder.py:39, estimation/sample_analyzer.py:22, brain_mcp/brain_mcp.py:24, start_obsidian_vault_mcp.bat:3, bucky_dispatcher.py:10, session_turn_counter.py:3, gpt/claude/codex_session·log_collector, collection_pipeline.py:21, docker_sync.py:45·51·57, fix_l002_graph_cluster.py:7, knowledge_distiller.py:41, legal_node_cleanup.py:25, subscription_roi.py:46, sync_vault_to_gbrain.py:27·28, test_nav_pages.ps1·py, open_gpt_login.bat:3, run_pattern_extractor.bat:2, setup_claude_settings.ps1:11·59·86, bucky_sub_agents/vault_node_deduplicator.py:39.
- **설정 3건**: `.mcp.json:23`(repo), `.codex/config.toml:12`(repo, ← 원래 "automation.toml L12"는 오인, 실체는 이 파일), `.claude.json:1563`(home, gbrain MCP 인자). ⚠️ `automation.toml` 존재 안 함.
- **settings.json 훅 5건**(home): L72 bucky_awareness, L82 session_turn_counter, L136 bucky_awareness(codex), L148 context_warning, L157 statusLine claude_statusline. (SessionStart L114는 C: 경로라 무관.)
- **⛔ C그룹 = 일괄치환 금지** (repo 아닌 별개 G: 위치/동기화 로직): JH-SHARED(agent_room_migrator·gdrive_agent_room_migrator·migration_crosscheck·bucky_dispatcher:20), 견적시스템 입력(sample_analyzer:20·21), 레거시 병합소스(four_folder_migration:26~29), docker_sync GDRIVE_PATH(47·53·59), **pc_identity.py(동기화 정책)**, **sync_sentinel.py(G: 감지가드 — D:서 무력화, 재설계 필요)**, jh_local_status.py:114, legacy_residue_scanner.py:70.
- **예약작업/Startup 실제 정의**:
  - `bucky-chat-server`(pythonw+Python312, WorkingDir만 G:), `BuckyDailyPlusPipeline`(-File 경로+WorkingDir, 08:00), `ObsidianBrain_CollectionScheduler/ModalityCheck/WikiLint`(인자경로+WorkingDir, WorkingDir는 소문자 `g:`).
  - Startup 실제파일명: `BuckyDiscordWatchdog.lnk`(Arguments의 vbs경로), `bucky_chat_server_autostart.vbs`(target+CurrentDirectory 2곳, ⚠️Python314 사용+8765 중복시작), `SupabaseQueueWorker.lnk`→`.bucky_worker\worker_launcher.py:19` SCRIPT 상수. (`scripts\worker_launcher.py`는 없음.)
- **경로 표기**: 개발 저장경계=`D:\AI프로젝트\`(CLAUDE.md). 기존 D: 클론 실경로=`D:\ai프로젝트\`(Windows 대소문자 무시 = 동일 위치).

## 3. 실행 6단계 (단계 → 검증)

### 단계 1 — 상시 프로세스·예약작업 콜드 정지
- 정지 대상(실측 PID): 디스코드봇 `120484`, watchdog `3080/114084`, worker `155616`, chat http `4173`
- 예약작업 Disable: 위 5개 (특히 `BuckyDailyPlusPipeline`)
- **검증**: 위 프로세스 목록이 비었는지 `tasklist`로 확인, G: 볼트를 문 claude.exe/MCP 세션 없는지 확인
- ⛔ **이 이전은 vscode 한 환경에서만**. 다른 claude 세션이 G: MCP(`brain_mcp.py`)를 물고 있으면 먼저 종료.

### 단계 2 — D: 재클론
- D: 기존 클론(`9b32d17` master, 미추적 docx 3개 있음) 처리 결정 후:
- `bucky-os-v3-core` HEAD `348f21f` 로 재클론 또는 재fetch+checkout
- **검증**: `git rev-parse --abbrev-ref HEAD` = `bucky-os-v3-core`, `git log -1` = `348f21f`

### 단계 3 — robocopy 데이터 복사
- G: → D: 단방향 복사: `ObsidianVault\`, `data\`, `.env`, `brain_mcp\`
- **검증**: `find D:.../ObsidianVault -type f | wc -l` ≈ 13,904 (G:와 파일 수 대조)

### 단계 4 — 경로 재배선 (변경 전 .bak 백업)
- 전역 `settings.json` → `.bak` 백업 후 훅 5개 G:→D:
- 전역 `CLAUDE.md` 저장경계 루트 G:→D:
- 예약작업 5개 + Startup 3개 D:로 재작성 (⛔ 한글경로 런처 함정: D:도 `ai프로젝트` 한글 포함 → pythonw 직접 + WorkingDirectory, vbs/lnk 인코딩 주의)
- `.codex/config.toml`, `automation.toml`, `.claude.json`, `.mcp.json`, 소스 27개 하드코딩
- **검증**: 각 파일에서 `G:` grep 잔존 0, `.bak` 존재 확인

### 단계 5 — D:에서 재기동 + E2E
- 예약작업/Startup Enable, 상시 프로세스 D:에서 기동
- E2E: 디스코드→큐→worker→결과, chat server(8765), 테일스케일(8443)
- **검증**: 각 경로 실제 응답 확인 (실기능, HTTP 200 아님)

### 단계 6 — 며칠 관찰 후 G: 강등
- 며칠간 D: 운영 안정 확인
- G:는 백업 창고로 강등, D:→G: 단방향 백업 스케줄만 남김
- **검증**: G:에 자동 쓰기 없음, D:→G: 백업 1회 성공

---

## 4. 롤백

- 단계 4 이전(경로 재배선 전)까지는 예약작업 Enable + 상시 프로세스 재기동으로 G: 운영 즉시 복귀
- 단계 4 이후 문제 시: `settings.json.bak` 등 `.bak` 복원 → G: 경로 되돌림
- 볼트/데이터는 G: 원본을 지우지 않으므로(단계 6 전까지) 데이터 손실 없음

---

## 5. 승인 요청 항목

아래 3가지에 대한 승인이 필요합니다:
1. **전역 파일 변경**: `settings.json` 훅 5개 + `CLAUDE.md` 저장경계 (전 프로젝트 영향, `.bak` 백업 후 진행)
2. **콜드 정지**: 상시 프로세스 4개 + 예약작업 5개 일시 중단 (이전 중 봇/자동화 멈춤)
3. **D: 기존 클론 처리**: 07-05 stale 클론의 미추적 docx 3개 — 보존/삭제 결정

> 승인 시 "1·2·3 승인" 또는 개별 지정. 승인 후 단계 1부터 진행하며, 각 단계 완료 시 증거(명령→출력)와 함께 보고합니다.
