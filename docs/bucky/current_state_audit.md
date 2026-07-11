# Bucky 세컨드 브레인 — 현재 상태 감사 (current_state_audit)

- 작성일: 2026-07-11 (Stage 13, 문서 전용 — 코드 무변경)
- 스펙 근거: `ObsidianVault/00_UPGRADE/BUCKY_SECOND_BRAIN_EVOLUTION_SPEC_v0.1_KR.md` §0.2 (볼트 로컬 문서 — git 미추적이므로 저장소 clone에는 없음)
- 조사 방법: 탐색 에이전트 3개 실측 (2026-07-11) + V3 AUDIT(07-10) 대조
- 브랜치: `bucky-os-v3-core`

---

## 1. 정본 관계 — V3 AUDIT 링크 재사용

시스템 전반의 실측 인벤토리·낡은 전제 교정·리스크 목록의 정본은
**[`docs/BUCKY_OS_V3_AUDIT.md`](../BUCKY_OS_V3_AUDIT.md)** (2026-07-10)이다. 본 문서는 그것을 대체하지 않고,
세컨드 브레인 스펙 v0.1 관점에서 **추가 실측 3건(§3)과 보안 발견(§4), 상위 확정 결정(§2)** 만 증보한다.

| 항목 | 정본 위치 |
|---|---|
| 오케스트레이션·오라클 큐·AgentBus·Discord·하드코딩·테스트·시크릿 실측 | [V3 AUDIT §3](../BUCKY_OS_V3_AUDIT.md) |
| V3 인테이크 문서의 낡은 전제 교정 5건 | [V3 AUDIT §4](../BUCKY_OS_V3_AUDIT.md) |
| 리스크 목록 | [V3 AUDIT §5](../BUCKY_OS_V3_AUDIT.md) |
| 실행 순서·롤백 | [`docs/BUCKY_OS_V3_MIGRATION_PLAN.md`](../BUCKY_OS_V3_MIGRATION_PLAN.md) |

---

## 2. 확정된 상위 결정 (V3 AUDIT §2 이후 추가분)

| 결정 | 확정일 | 내용 |
|---|---|---|
| **기억저장소 볼트 일원화** | 07-11 (사용자 확정) | **하나의 볼트 = 단일 정본.** 지식 정본은 ObsidianVault 하나이며 그 안의 SoT는 `03_Knowledge/`다. 파생 저장소(gbrain DB, oracle obsidian_index, bucky_memory SQLite, vault_rag 임베딩)는 전부 **캐시로 강등** — 유실·재구축이 가능해야 하고, 정본과 불일치 시 볼트가 이긴다. 신규 기능은 파생 저장소에만 존재하는 지식을 만들지 않는다. |
| 로컬 이전 도착지 | 07-11 (사용자 확정) | `D:\ai프로젝트\obsidian-agent-brain-system`(07-07 클론)으로 V3 이관 완료 후 컷오버. **컷오버 전 해당 클론에서 작업 금지** (현재 4일 뒤처짐). |
| 큐 정본 단일화 | 07-10 (사용자 승인) | 작업 큐 정본 = oracle SQLite 큐. `10_AgentBus` 파일 큐 신설 영구 금지. |
| 오라클·집PC 2계층 | 07-08 | 오라클 = 명령/오케스트레이터, 집PC = 데이터 보유 + 실행 (폴링 pull). |

---

## 3. 부록 인벤토리 — 스펙 관점 실측 3건 (2026-07-11, 탐색 에이전트 3개)

### 3.1 코어 (오케스트레이션·큐·실행)

**존재**: oracle SQLite 큐(상태 7종 전이표 + 원자 claim + Bearer 인증), TaskSpec/AgentResult/ModelDecision 계약(Python+JSON 스키마 이중), provider adapter 인터페이스 + 5종 등록(실동작 = claude_code뿐), model_router 3티어 + provider_candidates + explain(), bucky_client(한도 감지 + 모델/Codex/npm 폴백), cli-tools.jsonl 호출 로그(토큰·비용 없음), `oracle/core/agents.yaml` 5종(bucky-main, home-pc-agent, office-pc-agent, laptop-agent, interior-estimate-ai), Discord `/oracle` 투입구, `pending_approval/` 파일 승인 큐.

**공백**: usage 원장 / 정책 엔진 / 통합 이벤트 봉투(로그 3분산) / model_decision 방출 / worker 실행 결선(현재 echo 스텁) / 큐 retry·DLQ / 승인 경로 이중화.

### 3.2 메모리 (지식·볼트)

**존재**: 볼트 3층 구조(01_RAW → **03_Knowledge = SoT**), 수집기군(conversation_id 보유), wiki_gate 5필터, knowledge_distiller 3중 dedup + confidence provenance, obsidian_indexer → oracle `/index`(키워드), vault_rag 로컬 임베딩, gbrain 외부 MCP, bucky_memory SQLite.

**공백**: 불변 이벤트 원장 / valid_until·감쇠 / supersedes 기계관계 / #processed 자동화 / origin ID 전파 / 노드 버저닝 / 인덱스 배선 불일치(생산 `data/` vs 소비 `memory/`) / 크로스 소스 중복탐지.

### 3.3 대시보드·정책

**존재**: 대시보드 33개(라이브 API형 + 정적 JSON형), 보호 3종(bucky-os / bucky-agent-os / ai-usage — 불가침), Windows Task Scheduler 7종 + 웹훅, 승인 3중(파일큐 + CLI + Discord `!approve`), 비용 모니터링(티어 라우팅 + /spend pressure + ROI), 리스크 등급 문서(`bucky.md`·`ROUTING_RULES.md` — 산문).

**공백**: 정책 엔진 코드 / 예산 강제 / 실시간 조직도 / 중앙 스케줄 레지스트리 / `docs/bucky`·`docs/adr` 부재(본 Stage에서 신설 시작) / AGENTS_CANONICAL 깨진 참조 / 리스크 룰 코드화.

> 공백 22건의 해소 계획 3분류는 [`gap_analysis.md`](gap_analysis.md) 참조.

---

## 4. 보안 발견 (기록 의무)

| # | 발견 | 위치 | 조치 계획 |
|---|---|---|---|
| S1 | **gbrain MCP 프록시 토큰 하드코딩** — Bearer 토큰이 소스에 리터럴로 존재 (값은 본 문서에 전재하지 않음) | `scripts/gbrain_mcp_proxy.py:14` (`GBRAIN_TOKEN`) | Stage 10 동반 핫픽스로 env 이관 확정. Codex 게이트 #2 필수수정 3번(`.env` override 일관화)과 같은 파일군 — 함께 처리 후보 |

참고: git 추적 중인 비밀정보 파일은 없음(V3 AUDIT §3.9, 07-10 점검). 위 건은 git 추적 소스 내 하드코딩이므로 별개 사안이다.

---

## 5. 다음 문서

- 갭 3분류: [`gap_analysis.md`](gap_analysis.md)
- 스펙 §26 미확인 항목의 실측치: [`assumptions.md`](assumptions.md)
- 목표 아키텍처·백로그·ADR: Stage 14 산출 (`target_architecture.md`, `implementation_backlog.md`, `docs/adr/ADR-0001~0005`)
