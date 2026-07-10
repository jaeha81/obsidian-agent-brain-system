# Bucky OS V3 — 현재 시스템 건강검진 보고서 (AUDIT)

- 작성일: 2026-07-10
- 작성 기준: V3 인테이크 문서(`ObsidianVault/00_UPGRADE/upgrade-intake-2026-07-10.md`, 07-07 작성분)와 실제 저장소 상태 대조
- 조사 방법: 저장소 실측 스캔 (파일 존재 여부·구조·하드코딩 검색)
- 브랜치: `bucky-os-v3-core` (master에서 분기, 07-10)

---

## 1. 한 줄 요약

V3 인테이크 문서의 **방향(버키 중심 멀티모델 오케스트레이션)은 유효**하나, 문서가 07-07 작성이라
**07-08 이후 확정·구축된 오라클 2계층 구조와 oracle/core 큐가 반영되지 않았다.**
그대로 실행하면 큐(작업 접수창구)가 이중화된다. 이 보고서가 그 간극을 교정하는 기준 문서다.

---

## 2. 확정된 상위 결정 (V3 문서보다 우선)

| 결정 | 확정일 | 내용 |
|---|---|---|
| 오라클·집PC 2계층 | 07-08 | 오라클 = 명령/오케스트레이터, 집PC = 데이터 보유 + 실행 |
| Phase 3 착수 순서 | 07-08 | API → Queue → Registry → Discord. 집PC는 폴링(pull) 방식 |
| 큐 정본 단일화 | 07-10 (사용자 승인) | 작업 큐 정본 = oracle SQLite 큐. 10_AgentBus 파일 큐 신설 안 함 |

---

## 3. 실측 인벤토리 (2026-07-10 기준)

### 3.1 오케스트레이션 계층 (scripts/)

| 파일 | 상태 | 역할 |
|---|---|---|
| `bucky_orchestrator.py` | 존재 | 작업을 에이전트별 분류·병렬 실행 (P0~P2 피드백 루프 포함) |
| `bucky_dispatcher.py` | 존재 | 태스크 유형 분류 + 에이전트 배분 (배분만, 직접 구현 안 함) |
| `bucky_client.py` | 존재 | Claude Code CLI 래퍼 — AI 추론 실행 경로 |
| `bucky_worker_pool.py` | 존재 | Discord 명령 비동기 백그라운드 실행 워커 풀 |
| `model_router.py` | 존재 | **이미 작업유형(task_type) 기반 라우팅** — `TASK_TO_MODEL` 매핑, `select_model`/`fallback_chain`/`explain` 보유 |

### 3.2 오라클 큐 계층 (oracle/) — Phase 3에서 구축 완료

| 파일 | 역할 |
|---|---|
| `oracle/core/api_server.py` | 태스크 생성/조회/선점(claim)/상태보고 HTTP API. SQLite 저장, Bearer 인증 |
| `oracle/core/client.py` | API 래퍼 (submit/get/claim/update). stdlib 전용 |
| `oracle/core/worker.py` | 집PC 폴링 워커 — 오라클 API를 폴링해 태스크 실행 |
| `oracle/core/obsidian_index.py` | 볼트 경량 인덱스 검색 (B3). `/api/v1/index/*` 라우트로 노출 |
| `oracle/tests/` | 통합 테스트 4종 (api_server/client/worker/pipeline_e2e) |
| `oracle/DEPLOY.md` | Oracle #2 라이브 배포 런북 |

### 3.3 AgentBus (ObsidianVault/10_AgentBus/)

- 하위 디렉터리 23개, 총 약 3,379개 파일 **운영 중**.
- 주요: inbox(967), claims(1330), outbox(137), completed(144), archive(565), handoffs(78), reports(35) 등.
- V3 문서가 가정한 `inbox/{claude,codex,gemini}` 단순 구조와 다름 — 실구조가 훨씬 크고 살아 있음.

### 3.4 Discord

- `scripts/discord_bot.py`: 약 262KB 단일 대형 파일. `bucky_client` 경유로 Claude 호출.
- 음성 코드 이미 다수 내장: gTTS(TTS), discord-ext-voice-recv(음성 수신), STT 고도화(enhancer→CLI→API 폴백).
- V3의 "message/voice pipeline 4분할"은 신설이 아니라 **대형 파일 분해 수술**이다 (고위험).

### 3.5 Gemini / OpenAI / Anthropic API

- `scripts/gemini_client.py`: 존재. `GEMINI_API_KEY`, `GEMINI_MODEL`(기본 `gemini-2.0-flash`) env 사용 — V3가 요구하는 env 기반 처리 이미 충족.
- OpenAI: 실사용 어댑터 없음 (V3 문서 인식과 일치).
- Anthropic API: `api/golf-chat.js` 등 Vercel 함수에서 사용 (모델명 하드코딩 존재 — 3.6 참조).

### 3.6 하드코딩 실측치 (V3 P0 대상)

- **절대경로** (`G:\내 드라이브` 계열): py/js **25개 파일**.
  대표: `scripts/bucky_dispatcher.py`(VAULT 경로 직접 하드코딩), `scripts/estimation/boq_builder.py`, `scripts/estimation/sample_analyzer.py`, `scripts/session_turn_counter.py`, `scripts/resolve_migration_conflicts.py`
- **모델명** (`claude-`/`gemini-`/`gpt-` 문자열): 테스트 제외 **24개 파일**.
  대표: `scripts/agent_dispatcher.py`, `scripts/bucky_agent_os_api.py`, `scripts/bucky_dispatcher.py`, `scripts/bucky_nlp_preprocessor.py`, `scripts/bucky_stt_enhancer.py`

### 3.7 V3가 신설하자는 구조물 — 전부 미존재 (충돌 없음)

- `config/` — 없음
- `scripts/core/`, `scripts/providers/`, `scripts/routing/`, `scripts/discord/` — 없음
- `docs/BUCKY_OS_V3_*.md` — 이 보고서가 최초

### 3.8 테스트 기준선

- 저장소 루트 `tests/`: 36개 py 테스트 + 1개 js 테스트 존재.
- `oracle/tests/`: 4개 통합 테스트 (stdlib 전용, 실서버 기동 방식).

### 3.9 시크릿 점검 (07-10 실측)

- git 추적 중인 실제 비밀정보 파일: **없음**.
- `.gitignore`에 `.env`, `.env.*`, `secrets/`, `credentials/` 제외 규칙 정상 존재.
- 이름에 "secret"이 들어가나 코드 파일인 것 2개: `scripts/legacy_secret_decision_register.py`, `scripts/legacy_secret_manifest.py` (비밀값 아님).

---

## 4. V3 인테이크 문서의 낡은 전제 — 교정 목록

| # | V3 문서의 전제 | 실제 | 교정 |
|---|---|---|---|
| 1 | AgentBus에 파일 기반 큐(queue/pending·running·retry·dead_letter) 신설 | oracle SQLite+HTTP 큐 이미 구축·테스트 완료 | **큐 정본 = oracle 큐. 파일 큐 신설 안 함** (사용자 승인, 07-10) |
| 2 | 기존 model_router는 모델명 중심이라 교체 필요 | 이미 task_type 기반 + fallback 보유 | 신규 작성이 아니라 **provider 차원 확장** |
| 3 | AgentBus는 inbox/{claude,codex,gemini} 수준 | 23개 디렉터리 3,379 파일 운영 중 | 구조 변경은 별도 마이그레이션 계획 필수 |
| 4 | Discord pipeline 분리는 신규 골격 작업 | 262KB 파일에 음성 포함 이미 내장 | 분해 수술로 재분류 — **후순위·별도 승인 게이트** |
| 5 | (문서에 없음) 오라클·집PC 2계층 | 07-08 확정 + Phase 3 구축 완료 | V3의 "Bucky Kernel" 배치는 이 2계층 위에 설계 |

---

## 5. 리스크 목록

| 리스크 | 심각도 | 완화책 |
|---|---|---|
| 큐 이중화로 태스크 상태 정본 분열 | 높음 | 교정 #1 — oracle 큐 단일화 확정 |
| discord_bot.py 분해 중 봇 중단 | 높음 | V3 후반부로 이연, 별도 승인 게이트 |
| 하드코딩 25+24 파일 일괄 수정 시 회귀 | 중간 | config 스캐폴드만 먼저, 파일별 점진 이관 |
| 10_AgentBus 구조 변경으로 기존 워크플로 파손 | 중간 | 기존 구조 유지, 신규는 병행 도입만 |
| .env/시크릿 노출 | 낮음 (현재 깨끗) | 매 단계 커밋 전 재점검 |

---

## 6. 다음 문서

실행 순서·단계별 변경 파일·롤백 방법은 `docs/BUCKY_OS_V3_MIGRATION_PLAN.md` 참조.
