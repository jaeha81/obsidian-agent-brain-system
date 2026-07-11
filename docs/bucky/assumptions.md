# Bucky 세컨드 브레인 — 가정·실측 대장 (assumptions)

- 작성일: 2026-07-11 (Stage 13, 문서 전용 — 코드 무변경)
- 스펙 근거: `ObsidianVault/00_UPGRADE/BUCKY_SECOND_BRAIN_EVOLUTION_SPEC_v0.1_KR.md` §26 ("Claude Code는 저장소 조사 후 아래 항목을 채운다") + §0.6 (질문보다 실행 가능한 가정 우선)
- 표기: **[실측]** = 저장소·코드에서 직접 확인 / **[실측-부재]** = 검색 결과 존재하지 않음을 확인 / **[가정]** = 합리적 가정 (반증 시 본 문서 갱신)

---

## 1. 스펙 §26 unknowns → 실측값

스펙 원문의 `unknown` 항목을 2026-07-11 실측으로 대체한 결과다.

```yaml
runtime:
  language: Python 3.x            # [실측] scripts/·oracle/ 전반. oracle/core는 표준 라이브러리 전용
  framework: 없음                  # [실측] 웹 프레임워크 미사용 — oracle/core/api_server.py는 http.server(ThreadingHTTPServer) + sqlite3 stdlib
  deployment: 2계층                # [실측+확정결정 07-08] Oracle Cloud VM = 명령/오케스트레이터, 집PC(Windows 11) = 데이터 보유 + 실행
  local_pc_bridge: 폴링(pull)      # [실측] oracle/core/worker.py가 오라클 HTTP API를 폴링해 태스크 선점(claim)

data:
  primary_database: SQLite        # [실측] oracle 큐 DB + bucky_memory. 별도 DB 서버 없음
  vector_store: 전용 벡터DB 없음    # [실측] vault_rag 로컬 임베딩 + oracle obsidian_index 키워드 검색이 대체. 전부 파생(캐시) — §2 참조
  object_storage: 없음             # [실측] 파일시스템 — G:드라이브 동기화 + ObsidianVault
  backup_policy: 미문서화          # [가정] 공식 백업 정책 없음. 수동 복원 관행만 존재(gbrain DB 108MB 복원, 06-28). P1에서 문서화 필요

agents:
  bucky_core_version: V3 진행 중   # [실측] bucky-os-v3-core 브랜치 — Stage 3~8 구현 완료, Codex 게이트 #1 통과·#2 조건부 통과(필수수정 6건 승인 대기)
  current_agent_count: 5          # [실측] oracle/core/agents.yaml — bucky-main, home-pc-agent, office-pc-agent, laptop-agent, interior-estimate-ai
  soul_mode: 구현 없음             # [실측-부재] scripts/·oracle/·config/ 검색 결과 0건
  luna_mode: 구현 없음             # [실측-부재] 동일 검색 0건
  terra_mode: 구현 없음            # [실측-부재] 동일 검색 0건
  self_improvement_loop: 없음      # [실측-부재] 자기개선 루프 구현 부재 — 스펙 P5(에이전트 팩토리·자기진화)는 플랜 Non-goals

models:
  openai: 실사용 어댑터 없음        # [실측] V3 AUDIT §3.5. Codex CLI는 독립 검수 용도로만 사용 (추론 경로 아님)
  anthropic: 주 경로               # [실측] Claude Code CLI 경유(scripts/bucky_client.py — 한도 감지 + 모델/Codex/npm 폴백) + Vercel 함수 일부 직접 API
  google: env 기반 클라이언트 존재  # [실측] scripts/gemini_client.py — GEMINI_API_KEY / GEMINI_MODEL(기본 gemini-2.0-flash)
  grok: 미도입                     # [실측-부재]
  ollama: 간접 사용                # [실측] gbrain MCP 검색의 로컬 Ollama 의존성. 추론 라우팅 대상 아님
  huggingface_models: 미도입       # [실측-부재]

automation:
  make_com: 미도입                 # [실측-부재] 스펙의 희망 통합 — 현 시스템에 없음
  scheduler: Windows Task Scheduler 7종 + 웹훅  # [실측] 단, git 밖 존재 — 복원 시 수동 재등록 필요(07-11 전수 수리 이력)
  event_bus: 없음                  # [실측-부재] 로그 3분산이 현실 — Stage 15에서 단일 append-only 이벤트 로그(bucky-events.jsonl) 신설 예정 (버스/큐 아님)
  mcp_support: 있음                # [실측] gbrain 외부 MCP(HTTP) + 저장소 .mcp.json

security:
  secrets_manager: 없음            # [실측] .env + .gitignore 규칙으로 관리. git 추적 비밀파일 없음(V3 AUDIT §3.9). 예외 1건 = gbrain_mcp_proxy.py:14 토큰 하드코딩 → Stage 10 핫픽스
  auth: 토큰 기반                  # [실측] oracle API Bearer 인증 + Discord 봇 권한
  audit_log: 부분                  # [실측] cli_call_logger(cli-tools.jsonl — 토큰·비용 필드 없음). 통합 감사 로그는 Stage 15 대상
  data_encryption: 없음            # [실측] 로컬·드라이브 동기화 평문 저장 (at-rest 암호화 없음)
```

---

## 2. 상위 원칙 가정 (스펙 §26 외 — 설계 전제)

| # | 전제 | 성격 | 내용 |
|---|---|---|---|
| A1 | **볼트 단일 정본** | 확정 결정 (07-11 사용자) | 지식 정본은 ObsidianVault 하나(SoT = `03_Knowledge/`). gbrain DB·oracle 인덱스·bucky_memory·vault_rag 임베딩은 **캐시** — 언제든 볼트에서 재구축 가능해야 하며, 불일치 시 볼트가 이긴다. Stage 15~21 신규 산출물도 이 원칙을 따른다 |
| A2 | 큐 단일 정본 | 확정 결정 (07-10 사용자) | 작업 상태 정본 = oracle SQLite 큐. 10_AgentBus 파일 큐 신설 영구 금지 |
| A3 | jsonl append 안전성 | [가정] | G:드라이브 동기화 위 jsonl append는 경합 가능 — 기록 실패는 try/except 격리로 실행 비차단(플랜 리스크 3). 관측 후 위치 재검토 |
| A4 | 단일 사용자 시스템 | [가정] | 동시 사용자 1명(JH) 전제 — 멀티테넌시·권한 분리 비대상. Discord 봇 노출 범위는 개인 서버 |
| A5 | 이벤트 로그 ≠ 이벤트 버스 | 설계 결정 | 스펙 §26의 event_bus는 도입하지 않는다. Stage 15의 산출물은 구독·라우팅 없는 단일 append-only 관측 로그다 (ADR-0003으로 Stage 14에서 소급 기록 예정) |

## 3. 갱신 규약

- 이 문서의 [가정] 항목이 실측으로 반증되면 해당 줄을 실측으로 교체하고 이 절에 이력을 남긴다.
- Stage 착수 전 확인이 필요한 미결정 3건(정책 enforce 전환 / 데이터 위치·git 추적 / 01_RAW #processed 방식)은 플랜 "오픈 퀘스천"이 정본이며 여기 중복 기재하지 않는다.
