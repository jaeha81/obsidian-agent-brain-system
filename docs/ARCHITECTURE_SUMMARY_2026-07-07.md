# 버키 OS (Obsidian Agent Brain System) 아키텍처 요약

작성일: 2026-07-07
범위: 폴더 구조 / 모델 호출 위치 / 설정 파일 / 시크릿 처리 / 현재 기능 / 개선 포인트

---

## 1. 전체 개념

Bucky(오케스트레이터) → Claude Code(구현) → Codex(독립 검수) → Gemini(보조 전문가 5종)
4-에이전트 체계 위에, Discord 채널별 역할 컨텍스트를 동적으로 주입하는 멀티에이전트 시스템.

- **Bucky**: 지시 수신·분류·에이전트 파견 (오케스트레이터, `scripts/bucky_*.py`)
- **Claude Code**: 구현/운영 에이전트 (이 CLAUDE.md 체계)
- **Codex**: Claude 구현 완료 후 독립 검수
- **Gemini**: research / rag / multimodal / content / validator 5개 역할

---

## 2. 폴더 구조

```
obsidian-agent-brain-system/
├─ ObsidianVault/              # Obsidian 노트베이스 (실체는 Google Drive 동기화, git은 00_System만 추적)
│  ├─ 00_System/               # 라우팅 규칙·에이전트 역할·채널 정의
│  │  └─ channel_roles/        # Discord 채널별 역할 md (12개)
│  ├─ 03_Projects/             # 프로젝트/에이전트 지시서 (agents/, github-repos/, ecommerce-roadmap/)
│  ├─ 03_Knowledge/            # 정적 Wiki (정제된 지식)
│  ├─ 08_Content/              # 콘텐츠·블로그·영상 (Gemini 산출물)
│  └─ 10_AgentBus/             # 에이전트 간 메시지 큐 (inbox/{claude,codex,gemini}, outbox/{completed,failed})
├─ scripts/                    # 메인 엔진 (Python/PowerShell, 90+ 스크립트)
│  ├─ bucky_orchestrator.py / bucky_dispatcher.py / bucky_client.py / bucky_worker_pool.py
│  ├─ discord_bot.py / discord_intake.py
│  ├─ gemini_client.py         # Gemini 5역할 클라이언트
│  ├─ model_router.py          # Sonnet/Haiku/Opus 자동 라우팅
│  ├─ estimation/               # 견적 파이프라인 (PDF 도면 + Excel BOQ)
│  └─ pre-commit-safety.sh      # 커밋 안전장치
├─ api/                        # Vercel 엣지 함수
│  ├─ golf-chat.js             # Anthropic 직접 호출 (claude-haiku-4-5-20251001)
│  ├─ protected.js / login.js / logout.js   # 로그인 게이트
├─ docs/                       # 대시보드·웹UI (Vercel 배포)
│  └─ data/estimation/         # 견적 산출물 라이트 번들
├─ data/                       # 로컬 런타임 데이터 (charlie/ 감시 로그 등)
├─ protected/                  # 보호 페이지 (bucky-daily, investment-report, wishket)
└─ .gitignore                  # .env*, secrets/, credentials/, Vault 대부분 제외
```

---

## 3. 모델 호출 위치

| 위치 | 모델 | 방식 | 비고 |
|---|---|---|---|
| `scripts/bucky_client.py` | Claude (Sonnet→Haiku→Opus 폴백) | Claude Code CLI 구독 호출 (`CLAUDE_COMMAND` env, 기본 `claude`) | **API 키 미사용** — CLI 구독 기반 |
| `scripts/gemini_client.py:19-20,122-126` | `gemini-2.0-flash` (env `GEMINI_MODEL`) | REST, `GEMINI_API_KEY` | research/rag/multimodal/content/validator 5역할 |
| `api/golf-chat.js:40-60` | `claude-haiku-4-5-20251001` (하드코딩) | `https://api.anthropic.com/v1/messages`, `ANTHROPIC_API_KEY` (Vercel 암호화) | 골프 예약 챗봇 |
| `scripts/gpt_auto_login.py` | OpenAI | 자동로그인 유틸 | 실사용 중 아님으로 보임 |

Bucky의 핵심 호출 경로는 API 키가 아니라 **Claude Code CLI 구독**을 그대로 쓰는 구조라, 별도 과금 없이 Sonnet 한도 초과 시 Haiku→Opus로 자동 폴백한다.

---

## 4. 설정 파일

| 파일 | 용도 | git 추적 |
|---|---|---|
| `.env` (`.env.example` 존재) | Discord 토큰, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY` 등 | 아니오 |
| `vercel.json` | 배포/리다이렉트/보호 API 라우팅 | 예 |
| `.gitignore` | 시크릿·Vault·임시파일 제외 규칙 | 예 |
| `scripts/estimation/unit_price_defaults.json` | 견적 단가 테이블 | 예 |
| `.claude/settings.json` | Claude Code 프로젝트 로컬 설정 | 아니오 |
| `ObsidianVault/00_System/channel_roles/*.md` | Discord 채널별 프롬프트 (12개) | 예 |

---

## 5. 시크릿 처리 방식

**모범 사례로 되어 있는 부분**
- `.env*`가 `.gitignore`에서 완전 제외, `.env.example`만 커밋
- `load_dotenv(ROOT / ".env")` 표준 패턴 (`gemini_client.py`, `bucky_client.py`, `discord_bot.py`)
- Bucky(Claude) 경로는 API 키 없이 CLI 구독만 사용 — 키 유출 표면 자체가 작음
- Vercel 함수는 쿠키 기반 세션 검증(`api/protected.js`)으로 페이지 보호

**확인된 리스크**
- `api/golf-chat.js`가 `ANTHROPIC_API_KEY`를 서버리스 함수에서 직접 사용 — Vercel 암호화로 완화되지만 키 로테이션 정책은 별도로 없음
- git 히스토리에 과거 커밋 시점 시크릿이 남아있을 가능성은 이번 조사에서 별도 검증되지 않음 (필요 시 `git log -p` 전수 스캔 권장)

---

## 6. Discord 채널 구조

| 채널 | 역할 파일 | 역할 |
|---|---|---|
| jh-chat | JHHUB_ROLE.md | 메인 오케스트레이터 |
| claude-code-context | CLAUDE_CODE_ROLE.md | Claude Code 구현 |
| codex-review | CODEX_ROLE.md | Codex 독립 검수 |
| daily-plus | DAILYPLUS_ROLE.md | 일일보고 |
| kmong / wishket | KMONG_ROLE.md / WISHKET_ROLE.md | 외주 프로젝트 관리 |
| task-board | TASKBOARD_ROLE.md | 할일 추적 |
| shorts / threads | SHORTS_ROLE.md / THREADS_ROLE.md | 콘텐츠 생성 |
| chsh-mining | CHSH_MINING_ROLE.md | 마이닝 데이터 |
| my-intro | MYINTRO_ROLE.md | 소개 페이지 |
| repo-dashboard | REPO_DASHBOARD_ROLE.md | 저장소 상태 |

라우팅 흐름: Discord 메시지 → `discord_bot.py` → 키워드/역할 분류 → `bucky_dispatcher.py` 점수 기반 에이전트 선택 → AgentBus inbox 저장 → 처리 후 outbox → Discord 포스팅.

최근 커밋: "채널별 역할 컨텍스트를 ask_bucky에 배선"(9b32d17), "jh-local 채널 구현 - 로컬 PC 상태 실시간 대화"(2f9a1b6).

---

## 7. 현재 가능한 주요 기능

- **Bucky 오케스트레이션**: P0~P3 우선순위 분류, 키워드 스코어링 라우팅, 워커 풀 병렬 실행
- **Discord 봇**: `!status`/`!help`/`!reset`/`!queue`/`!pack` 명령, 자동 브리핑 스케줄, 채널별 역할 자동 배선
- **견적 파이프라인** (`scripts/estimation/`): PDF 도면 인식 + Excel BOQ 파싱 → 통합 견적, 신뢰도 표기(🟢/🟡/🔴)
- **Gemini 5역할**: research / RAG(Vault 검색) / multimodal(도면·사진 분석) / content(블로그·쇼츠) / validator(교차검증)
- **대시보드**: daily-plus, task-board, bucky-os, ai-usage, channel-roles, charlie-system-audit
- **인테이크**: Discord export → AgentBus, 영상→지식 변환, URL/텍스트 자동 캡처
- **패턴 감지/자기반성**: 반복 작업 자동화 제안, 진화 로그 분석

---

## 8. 잠재적 개선점

| 우선순위 | 항목 | 내용 | 위치 |
|---|---|---|---|
| P1 | 경로 하드코딩 | `G:\내 드라이브\obsidian-agent-brain-system` 절대경로가 여러 스크립트에 반복 | `scripts/estimation/boq_builder.py:39`, `scripts/bucky_dispatcher.py:10` |
| P1 | 모델명 하드코딩 | 모델 교체 시 코드 수정 필요 | `api/golf-chat.js:54`, `scripts/gemini_client.py:20` |
| P2 | 경로 정의 중복 | Vault/AgentBus 경로가 여러 파일에 흩어져 있음 → 단일 `config.py` 모듈화 권장 | 전역 |
| P2 | 에이전트 지시서 최신화 확인 | `ObsidianVault/03_Projects/agents/` 내용이 실제 라우팅 규칙과 일치하는지 재확인 필요 | — |
| P3 | 테스트 커버리지 | `tests/` 내 테스트가 상대적으로 적음, 핵심 라우팅 로직 테스트 보강 필요 | `tests/` |
| P3 | 레거시 정리 | `legacy_*.py`, `*.bak_*` 류 파일 존재 — 정기 정리 필요 | `scripts/` |
| P3 | 모델 폴백 모니터링 | Sonnet 한도 초과 후 자동 폴백이 잦으면 토큰 낭비 가능 → 사전 한도 추적 필요 | `scripts/model_router.py` |

---

*본 문서는 코드 조사 기반 스냅샷이며, 이후 구조 변경 시 최신화가 필요하다.*
