# Codex 독립 검수 요청 — Bucky OS V3 G6 게이트 (최종: Phase D·E + P0 완료 판정)

- 작성일: 2026-07-13
- 요청자: Claude Code (구현) → Codex (독립 검수 #5, **최종 게이트**)
- 브랜치: `bucky-os-v3-core` (HEAD = `c47d294`)
- 검수 대상 커밋 (3건 — **커밋 단위가 검수 정본**):
  - `ad78af5` — Stage 20: 01_RAW provenance 필드 + sidecar 처리 인덱스 (P0-4)
  - `15e65b8` — Stage 21: 브레인 현황 대시보드 생성기 + agents.yaml PyYAML 비의존 파서 (P0-10)
  - `c47d294` — Stage 20 테스트 실행 가드 (아래 §1.6 — 이번 세션 발견 결함의 수정)
- 부수 (검수 대상 아님, 단 내용 불일치 시 지적 대상): `274219e`(백로그·V3 플랜 상태표 동기화), `772e28b`(§1.5 사고 — 아래 필독)
- 기준 문서: `docs/bucky/implementation_backlog.md` §1·§2, `ObsidianVault/00_UPGRADE/BUCKY_SECOND_BRAIN_EVOLUTION_SPEC_v0.1_KR.md` §20 Story 5·6·7, `docs/adr/ADR-0003`·`ADR-0004`
- 직전 게이트: `docs/CODEX_REVIEW_REQUEST_G5.md` §5·§6 (완전 통과)
- 플랜 정본(`C:\Users\user1\.claude\plans\foamy-churning-swing.md`)은 CWD 밖 — 접근 금지. 백로그 문서가 CWD 내 대리 정본이다.

> Codex는 독립적으로 검수한다. Claude는 검수에 개입하지 않으며, 결과는 사용자에게 직접 보고된다.
> **이 게이트는 코드 리뷰 + P0 완료 판정의 이중 목적을 가진다.** §4가 이 게이트의 핵심이다.

---

## 1. 이번 변경의 원칙 (설계 전제)

1. **Stage 20 = provenance 전파 + 01_RAW 불변.** `knowledge_distiller.py`가 01_RAW frontmatter의 `conversation_id`를 증류 노트로 전파(`source_conversation_id`/`source_file`) + `supersedes`/`valid_until`/`last_verified` optional 필드. **01_RAW 원본은 태그 포함 완전 무수정** — 처리 완료 표시는 sidecar `data/memory/processed_index.jsonl`에 기록 (오픈 퀘스천 3, 2026-07-12 사용자 A안 확정). `wiki_gate.py`는 신규 필드 통과만(필터 불변).
2. **Stage 21 = 읽기 전용 관측.** `scripts/generate_brain_status.py`가 오라클 SQLite를 **읽기전용 URI(`file:...?mode=ro`)** 로 열어 집계 + usage_ledger 월간요약 + policy shadow 판정 분포 + agents.yaml 실행노드 → `docs/data/bucky_brain_status.json`·`agents_org.json`. 쓰기 경로 없음. 신규 스케줄 잡 없이 기존 08:00 파이프라인에 1단계(3d) 추가.
3. **보호 3종 무접촉**: `bucky-os.html`·`bucky-agent-os.html`·`ai-usage.html`은 수정하지 않았다. `org-structure.html`은 **기존 agent-tree를 유지한 채 "실행 인프라 현황" 섹션을 신설**했다(사용자 A안 — agents.yaml의 5개 실행노드는 agent-tree의 4개 논리역할과 다른 개념이라 통합하지 않고 분리).
4. **agents.yaml은 PyYAML에 의존하지 않는다** (§1.5 사고에서 파생된 제약): 오라클/Task Scheduler Python에 PyYAML이 없을 수 있어, `oracle/core/api_server.py`와 동일한 stdlib 평탄 파서를 사용한다.
5. **⚠️ 알려진 사고 (`772e28b`) — 중복 지적 불필요, 단 잔여 영향은 지적 대상**: 07-13 08:00 Task Scheduler 정기 파이프라인이 작업 중이던 **미커밋 워킹트리를 그대로 실행**해, 생성기 소스 없이 **산출물(`docs/bucky-brain.html`·`org-structure.html`·JSON)만** 자동 커밋·푸시했다. 그 시점 산출물의 `agents_org.json`은 PyYAML 부재로 **조용히 빈 배열**이었다. 이후 `15e65b8`에서 소스·파서 수정·테스트가 커밋되어 재현 가능 상태로 복구됐고 JSON도 재생성(5개 노드)됐다. 히스토리 재작성(force-push/rebase)은 안전 규칙상 하지 않았다. **검수 요청: 현재 HEAD 기준으로 산출물과 소스가 실제로 정합한지(재현 가능한지) 확인 요망.**
6. **⚠️ 이번 세션 발견 결함과 수정 (`c47d294`)**: `ad78af5`가 "테스트 8건"을 근거로 완료 보고됐으나, `knowledge_distiller.py:37`의 최상위 `import anthropic` 때문에 **SDK 미설치 환경에서는 테스트가 임포트 단계에서 죽어 실제로는 한 번도 실행된 적이 없었다**. 테스트 파일에만 임포트 가드를 추가(프로덕션 무변경)해 8건이 실행되게 했고, 전부 통과함을 확인했다. **검수 요청: 이 가드가 정당한 수정인지(테스트를 통과시키려 실체를 가린 것은 아닌지) — §3.4에서 판단 요망.**
7. 롤백: Stage 20 = revert(forward-only). Stage 21 = revert + 신규 파일 삭제(읽기전용이라 부작용 없음).

---

## 2. 변경 파일 목록

### Stage 20 — provenance (커밋 ad78af5)

| 파일 | 역할 |
|---|---|
| `scripts/knowledge_distiller.py` (수정) | `_extract_conversation_id()` + 증류 노트 frontmatter 신규 필드 + `_append_processed_index()` |
| `scripts/wiki_gate.py` (수정) | 신규 필드 통과 (필터 로직 불변) |
| `tests/test_knowledge_distiller_provenance.py` (신규 8 tests) | 필드 전파 · BOM 처리 · sidecar append · **01_RAW 해시 불변 회귀** |
| `data/memory/processed_index.jsonl` (신규 sidecar) | 처리 완료 인덱스 (01_RAW 무수정) |

### Stage 21 — 대시보드 (커밋 15e65b8 + 산출물 772e28b)

| 파일 | 역할 |
|---|---|
| `scripts/generate_brain_status.py` (신규 230줄) | 오라클 SQLite `mode=ro` 집계 + usage 월간요약 + policy shadow 분포 + agents.yaml(stdlib 파서) |
| `tests/test_generate_brain_status.py` (신규 13 tests) | 집계·폴백·**PyYAML 부재 회귀 가드**(`sys.meta_path` 차단) |
| `scripts/run_daily_plus_pipeline.ps1` (수정 +7) | 3d단계 추가 |
| `docs/bucky-brain.html` (신규, 772e28b) | 브레인 현황 대시보드 (checklist.html 정적 JSON 패턴) |
| `docs/org-structure.html` (수정, 772e28b) | "실행 인프라 현황" 섹션 신설 (기존 agent-tree 유지) |
| `docs/data/bucky_brain_status.json`·`agents_org.json` | 산출물 |

### 테스트 가드 (커밋 c47d294)

| 파일 | 역할 |
|---|---|
| `tests/test_knowledge_distiller_provenance.py` (+18) | anthropic 부재 시에만 sys.modules 스텁 주입. 스텁 생성자는 호출 즉시 RuntimeError (실 API 경로로 새면 드러남) |

---

## 3. 검수 항목 — 코드 (요청)

### 3.1 기존 기능 파손 여부 (최우선)

- [ ] Stage 20이 `knowledge_distiller.py`의 기존 증류 동작(3중 dedup·confidence·출력 경로)을 변형시키지 않았는가?
- [ ] `wiki_gate.py`의 5필터가 신규 필드 추가로 판정을 바꾸지 않는가 (통과만 시키는가)?
- [ ] Stage 21이 오라클 DB에 **쓰기**하는 경로가 정말 없는가? `mode=ro` URI가 WAL 모드 DB·잠금 상황에서 안전한가 — 08:00 파이프라인이 worker와 동시 실행될 때 경합·잠금 유발 가능성은?
- [ ] 보호 3종(`bucky-os.html`·`bucky-agent-os.html`·`ai-usage.html`) 무접촉이 실제로 지켜졌는가?

### 3.2 01_RAW 불변성 (Stage 20 핵심 계약)

- [ ] 증류 경로 어디에서도 01_RAW 원본에 쓰기·태그 추가가 발생하지 않는가? (`#processed` 태그 주입 경로가 정말 제거/부재인가)
- [ ] 해시 불변 회귀 테스트가 실제로 이를 고정하는가, 형식만 통과인가?
- [ ] sidecar `processed_index.jsonl`의 append가 중복 처리·경합(다중 프로세스)에서 인덱스를 망가뜨리는가? 기록 실패가 증류 자체를 막는가(막으면 안 됨)?
- [ ] BOM(`utf-8-sig`) 처리가 볼트 실파일 다수의 선두 BOM 상황을 실제로 커버하는가?

### 3.3 Stage 21 정합성

- [ ] `agents_org()`의 stdlib 평탄 파서가 `oracle/core/api_server.py`의 그것과 실제로 동등한가 — 두 곳이 갈라질 위험(중복 구현)은 수용 가능한가, 공용화가 옳은가?
- [ ] PyYAML 부재 회귀 테스트(`sys.meta_path` 차단)가 실효적인가 — 실제로 가드를 제거하면 FAIL하는가?
- [ ] `bucky_brain_status.json` payload에 프롬프트 원문·토큰·비밀값·PII가 실리는 경로가 없는가? (대시보드는 GitHub Pages로 **공개 배포**된다 — 이것이 최대 리스크)
- [ ] `data/usage/2026-07.jsonl`의 테스트 오염 데이터("boom/", "ProviderAdapter/" 등)가 대시보드에 그대로 노출된다(기지 사실, P2 백로그). 이것이 단순 노이즈인가, 공개 배포 관점에서 정보 누출인가?

### 3.4 테스트 가드의 정당성 (c47d294 — 판단 요망)

- [ ] anthropic 스텁 주입이 **테스트를 통과시키려 실체를 가린 것**인가, 아니면 SDK와 무관한 순수 헬퍼를 정당하게 격리한 것인가?
- [ ] 스텁 생성자의 즉시 RuntimeError가 "테스트가 실제 API 경로로 새는 것"을 실제로 막는가?
- [ ] 더 옳은 수정은 프로덕션 `knowledge_distiller.py`의 임포트를 지연시키는 것인가? (Claude는 프로덕션 무변경을 택했다 — 이 판단이 옳은지 평가 요망)

### 3.5 단순성 (Karpathy 기준)

- [ ] `generate_brain_status.py` 230줄이 "읽기 집계 + JSON 산출" 명분에 최소인가? 요청하지 않은 유연성이 들어갔는가?
- [ ] Stage 20의 optional 필드 3종(`supersedes`/`valid_until`/`last_verified`)이 **현재 아무도 소비하지 않는다** — 추측성 구현인가, P0-4 계약의 최소인가?

---

## 4. 검수 항목 — P0 완료 판정 (이 게이트의 핵심)

Stage 13~21 구현이 전부 끝났다. 스펙 §20 Story 5·6·7의 완료 조건과 대조해 **P0가 실제로 완료됐는지 독립 판정**을 요청한다.
Claude 측 자체 평가를 아래에 정직하게 기재한다. **이 자기평가가 과대/과소인지 판정하는 것이 요청의 본질이다.**

### 4.1 Story 5 — "중요한 기억은 근거를 가진다" (P0-4 / Stage 20)

| 스펙 완료 조건 | Claude 자체 평가 | 근거 |
|---|---|---|
| 사용자 프로필·선호 기억은 최소 하나의 원본 이벤트를 참조한다 | **부분** | 증류 노트는 `source_conversation_id`/`source_file`로 원본을 참조한다. 그러나 이는 **01_RAW→03_Knowledge 증류 경로에 한정**되며, 기존에 축적된 노트·memory 계층 전반에 소급 적용되지 않았다 |
| 사실과 추론을 구분한다 | **미충족** | 기존 `confidence` 필드가 있으나 사실/추론의 **기계적 구분 축은 없다** |
| 신뢰도와 마지막 확인 시점이 존재한다 | **필드만 존재** | `last_verified` optional 필드를 추가했으나 **채우는 주체·갱신 경로가 없다** |
| 사용자가 정정하면 최신 버전이 검색에 반영된다 | **미충족** | `supersedes` 필드만 있고 **검색·인덱스에 배선되지 않았다**(노드 버저닝은 보류 항목) |

### 4.2 Story 6 — "승인 피로를 줄인다" (P0-6 / Stage 18·19)

| 스펙 완료 조건 | Claude 자체 평가 | 근거 |
|---|---|---|
| T0/T1 작업은 정책에 따라 자동 실행된다 | **미충족(의도된 축소)** | policy_engine이 T0/auto로 **판정**하지만, shadow 모드라 그 판정이 실행을 좌우하지 않는다. 자동 실행 여부는 여전히 기존 경로가 결정한다 |
| T3 작업은 실행 전에 승인 요청이 발생한다 | **미충족(의도된 축소)** | `require_approval` 판정은 **이벤트로만 방출**된다. 실제 승인 요청·차단은 발생하지 않는다 (ADR-0004 shadow 계약) |
| 사용자는 기간·예산·범위 묶음 승인을 설정할 수 있다 | **미충족** | 미구현 |
| 모든 실행은 감사 로그에 남는다 | **충족** | Stage 15 event_log + Stage 17 model_decision + Stage 19 policy_decision |

### 4.3 Story 7 — "비용을 통제한다" (P0-7 / Stage 10·19)

| 스펙 완료 조건 | Claude 자체 평가 | 근거 |
|---|---|---|
| 호출별 모델·토큰·비용이 기록된다 | **충족** | usage_ledger (provider_adapter 단일 관문 + bucky_client) |
| 프로젝트별 예산을 설정할 수 있다 | **미충족** | **월 전역 임계(`budget.monthly_warn_usd`)만** 존재. 프로젝트별 예산 없음 |
| 예산 임계치에서 경고 또는 차단된다 | **경고만 충족** | `budget_warning` 이벤트 방출. 차단 없음(의도 — 예산 강제는 보류 항목) |
| 저비용/로컬 대체 경로가 존재한다 | **부분** | model_router 3티어 + provider_candidates는 존재하나, **실동작 provider는 claude_code뿐**(나머지 스텁) — 실제 대체 전환은 검증되지 않았다 |

### 4.4 판정 요청 (Codex가 답할 것)

1. **위 자기평가가 정직한가?** 과대 보고(실제보다 충족으로 기재)나 과소 보고가 있는가?
2. **"P0 완료"를 선언할 수 있는가?** 스펙 Story 5/6/7의 완료 조건을 엄격 적용하면 **상당수가 미충족**이다. Claude의 입장은 "P0의 **배관(instrumentation·인터페이스·shadow 관측)**은 완료, 그러나 스펙 Story의 **행동 조건(자동 실행·차단·검색 반영)**은 의도적으로 범위 밖(P1/보류)"이다. 이 포지션이 타당한가, 아니면 P0 미완료로 판정해야 하는가?
3. 미충족 항목 중 **G6 통과 전에 반드시 메워야 할 것**이 있는가? (있다면 무엇을, 왜)
4. Story 5/6/7 외에 **Stage 13~21이 건드린 범위에서 놓친 P0**가 있는가? (백로그 §2 매핑표 대조)

---

## 5. Claude 측 검증 증거 (참고 — 2026-07-13 HEAD c47d294에서 실측)

```
$ python -X utf8 -m unittest tests.test_config tests.test_task_spec tests.test_model_router_v3 \
    tests.test_event_log tests.test_registry tests.test_provider_adapter tests.test_policy_engine \
    tests.test_knowledge_distiller_provenance tests.test_generate_brain_status
  Ran 168 tests — OK
  (기준셋 147 + Stage 20의 8 + Stage 21의 13)

$ python -X utf8 oracle/tests/test_worker.py       → 21 PASS / 0 FAIL
$ python -X utf8 oracle/tests/test_api_server.py   → 38 PASS / 0 FAIL
$ python -X utf8 oracle/tests/test_client.py       → 22 PASS / 0 FAIL
$ python -X utf8 oracle/tests/test_pipeline_e2e.py → 10 PASS / 0 FAIL
```

### 테스트 실행법 주의 (게이트 #1~#4 경험 계승)

- unittest는 **repo 루트에서 `-m unittest`로만** 실행. oracle 4종은 **직접 실행**.
- **`anthropic` SDK는 이 환경에 미설치다** — `c47d294` 가드 덕에 Stage 20 테스트가 실행된다. 가드 없이는 ImportError로 죽는다(§1.6).
- **PyYAML도 없을 수 있다** — `agents_org()`가 stdlib 파서인 이유(§1.4).
- 깨끗한 clone에는 `data/usage/`·`.env`가 없다 — 부재 시 빈 집계(cost 0)·crash 없음이 통과 기준.
- 기지 사실, **중복 지적 불필요**: gbrain 구 토큰 git 히스토리 잔존(재발급 P1) / G5 비차단 권고 4건(§5.3 백로그) / `data/usage/` 테스트 오염 데이터(P2) / G4 권고 2(append 경합 통합테스트 미이행).

---

## 6. Codex 검수 결과 (2026-07-13)

> 전사: Codex exec 최종 메시지 **원문** (일회용 clone @ `c47d294`, danger-full-access, CWD 밖 접근·네트워크 금지 규칙 하 실행)
> ⚠️ **한계**: 스펙 원문(`ObsidianVault/00_UPGRADE/...SPEC_v0.1_KR.md`)이 `.gitignore`의 `ObsidianVault/*`로 git 미추적 → clone에 부재. Codex는 요청서 §4에 **전사된** Story 5/6/7 조건으로 판정했다(본인이 미검증 항목으로 명시). 전사 충실성 자체는 미검증 — 재실행 시 스펙을 clone에 복사할 것.

```
[코드 판정] 조건부 통과

[P0 완료 판정] 미완료

[발견 이슈]
[P0] docs/CODEX_REVIEW_REQUEST_G6.md:163 — Story 5/6/7 완료 조건 중 사실·추론 구분, 검증 시점 갱신, 정정의 검색 반영, 정책 기반 자동 실행·승인 차단·묶음 승인, 프로젝트별 예산, 실제 저비용 대체 경로가 구현되지 않았다. “배관 완료”는 스펙의 행동 완료 조건을 대체하지 못한다.

[P1] scripts/knowledge_distiller.py:1463 — 주제 병합 경로는 `source_conversation_id`를 기존 노트에 기록하지 않는다. 병합 본문에는 원본 파일명만 추가되어 Stage 20의 provenance 계약이 신규 노트 경로보다 약하다.
  → 병합된 인사이트에도 원본 경로와 conversation_id를 구조적으로 보존한다.

[P2] scripts/knowledge_distiller.py:1500 — sidecar append 실패가 같은 `try`의 `OSError`로 처리되어 이미 생성·병합된 증류 결과까지 실패로 집계한다. 상태는 1498~1499행에서 먼저 저장되므로 재실행 시 스킵될 수 있어, sidecar 누락을 자동 복구하지 못한다.
  → sidecar 실패를 증류 성공과 분리해 경고·재시도 큐에 기록한다.

[P2] tests/test_knowledge_distiller_provenance.py:152 — 01_RAW 불변 테스트는 `extract_conversation_id()`와 `append_processed_index()`만 호출한다. 실제 `process_batch()` 성공·병합 경로 전체에서 원본 해시가 불변인지 고정하지 못한다.
  → API를 격리한 `process_batch()` 통합 회귀 테스트를 추가한다.

[P2] tests/test_generate_brain_status.py:165 — PyYAML 부재 테스트는 이미 import된 `generate_brain_status`를 재사용한다. 향후 모듈 최상위에 PyYAML 의존성이 재도입되는 회귀는 탐지하지 못한다.
  → 격리 subprocess에서 yaml import를 차단한 뒤 모듈을 처음부터 import한다.

[P2] docs/data/bucky_brain_status.json:20 — 커밋 산출물은 164개 usage 기록을 포함하지만 깨끗한 clone에는 원본 `data/usage`가 없어 동일 payload를 재생성할 수 없다. 비밀값·PII·프롬프트 원문은 없으나 `boom/`, `ProviderAdapter/` 등 테스트 내부 명칭이 공개된다.
  → 공개 산출 전 테스트 원장을 격리하고 생성 입력의 출처·시점을 명시한다.

[P3] scripts/generate_brain_status.py:141 — `api_server.py` 파서를 중복 구현하면서 한쪽은 fail-fast, 한쪽은 형식 오류를 조용히 건너뛴다. 현재 평탄 YAML에는 동등하게 동작하지만 장기적으로 해석이 갈라질 수 있다.
  → 공용 평탄 파서를 추출하거나 동일 fixture 계약 테스트를 공유한다.

[P3] scripts/knowledge_distiller.py:1037 — `supersedes`, `valid_until`, `last_verified`는 소비·갱신 경로가 없는 예약 필드다. 스펙 방향에는 부합하지만 현재 완료 근거로 계산할 수 없다.

[필수 수정]
- P0 완료 선언 전 Story 5/6/7의 미충족 행동 조건을 구현하거나, 사용자 승인으로 스펙/P0 범위를 공식 변경해야 한다.
- Stage 20 병합 경로에 conversation_id 기반 provenance를 보존해야 한다.
- sidecar 기록 실패가 증류 성공을 실패로 뒤집거나 복구 불가능한 누락을 만들지 않도록 분리해야 한다.
- 위 두 경로를 실제 `process_batch()` 통합 테스트로 고정해야 한다.

[P0 판정 근거]
1. 자기평가는 대체로 정직하다. 특히 주요 미충족 사항을 숨기지 않았다. 다만 Story 5의 “부분 충족” 근거는 병합 경로에서 conversation_id가 보존되지 않아 보고보다 좁다. “모든 실행 감사 로그”와 “호출별 원장 기록”도 검증된 배선 경로 범위에서만 충족으로 보는 것이 정확하다. 명백한 과소 보고는 없다.
2. P0 완료 선언은 불가능하다. instrumentation·인터페이스·shadow 관측 완료는 구현 단계 완료일 수 있으나, 스펙 완료 조건인 자동 실행, 사전 승인·차단, 정정 검색 반영, 프로젝트 예산 등을 P1/보류로 옮긴 것만으로 P0가 완료되지는 않는다.
3. G6에서 반드시 메워야 할 것은 최소한 Stage 20의 병합 provenance와 sidecar 실패 격리다. 전체 P0 완료 선언을 원한다면 Story 5/6/7의 나머지 미충족 조건도 구현하거나 스펙 범위를 명시적으로 재승인해야 한다.
4. 백로그 §2에는 P0-1~8, P0-10, P0-11만 있고 P0-9 매핑이 없다. 저장소 내 `P0-9` 정의도 검색되지 않았으며 스펙 원문이 clone에 없어 누락 여부를 최종 확정할 수 없다. 확인 가능한 Stage 13~21 매핑 범위에서는 이외의 새 P0 누락을 발견하지 못했다.

[권고 사항]
- anthropic 스텁은 SDK와 무관한 순수 helper 테스트 격리로서 정당하다. 생성자 즉시 실패도 API 경로 누출 방어에 유효하다. 다만 장기적으로는 프로덕션 SDK import를 실제 API 사용 지점으로 지연해 순수 helper를 정상 import 가능하게 하는 편이 단순하다.
- SQLite `mode=ro` 연결에는 쓰기 경로가 없고 테스트에서도 쓰기가 거부됐다. WAL writer와의 일반적인 동시 읽기는 허용되며, 현재 짧은 집계 쿼리는 잠금 위험이 낮다.
- 보호 대상 3종 HTML은 지정 세 커밋에서 변경되지 않았다.
- 공개 JSON에는 현재 프롬프트·비밀값·PII가 없고 렌더링 값도 HTML escape된다.
- `[반복 패턴 경보]` 등록된 반복 패턴은 없었다.

[독립 재검증 수행 내역]
- `git show ad78af5`, `git show 15e65b8`, `git show c47d294`: 실제 diff 확인.
- 지정 unittest 명령: `Ran 168 tests in 0.469s`, `OK`.
- `python -X utf8 oracle/tests/test_worker.py`: 21 PASS / 0 FAIL.
- `python -X utf8 oracle/tests/test_api_server.py`: 38 PASS / 0 FAIL.
- `python -X utf8 oracle/tests/test_client.py`: 22 PASS / 0 FAIL.
- `python -X utf8 oracle/tests/test_pipeline_e2e.py`: 10 PASS / 0 FAIL.
- Oracle 합계: 91 PASS / 0 FAIL.
- `agents_org.json`의 5개 노드는 현재 stdlib 파서 결과와 일치.
- 지정 세 커밋에서 보호 HTML 3종 diff 없음.
- 테스트가 생성한 ignored `data/usage/2026-07.jsonl`만 제거해 검수 전 상태를 복원. 최종 Git 상태는 기존 untracked 검수 요청서만 존재.

[미검증 항목]
- 요청된 스펙 원문 `ObsidianVault/00_UPGRADE/BUCKY_SECOND_BRAIN_EVOLUTION_SPEC_v0.1_KR.md`가 현재 clone과 모든 로컬 Git ref에 없어 직접 대조하지 못했다. 요청서에 전사된 Story 5/6/7 조건으로 판정했다.
- P0-9의 원문 정의와 매핑 여부는 스펙 부재로 확인하지 못했다.
- 네트워크 접근 금지에 따라 GitHub Pages 배포본과 로컬 HTTP 브라우저 미리보기는 열지 않았다.
- 실제 WAL writer가 동시에 부하를 발생시키는 장시간 경합 테스트와 다중 프로세스 sidecar append 테스트는 수행하지 않았다.
```

---

## 7. 필수수정 이행 (2026-07-13) — 재검수 요청

G6 검수(§6)의 필수 수정 4건에 대한 처리 결과다. **이 섹션이 재검수 대상이다.**

### 7.1 필수수정 ① P0 완료 판정 — 사용자 결정: **A안 (범위 공식 축소)**

Codex의 요구("구현하거나, 사용자 승인으로 스펙/P0 범위를 공식 변경")에서 **후자**를 사용자가 선택했다 (2026-07-13).

- **결정 내용**: P0 완료 기준 = **배관(instrumentation·인터페이스·shadow 관측)까지**. 스펙 §20 Story 5·6·7의 **행동 조건**(사실/추론 구분, 정정의 검색 반영, 정책 기반 자동 실행, 승인 차단, 묶음 승인, 프로젝트별 예산)은 **P1로 이월**.
- **기록 위치**: `docs/bucky/implementation_backlog.md` **§2.1** (신규) — 결정·근거·경위 + 이월 항목 7건의 P1 매핑표.
- **P1 신규 행**: 같은 문서 §3에 P1-8 ~ P1-12 추가 (+ P0-9 관련 P1-7).
- **롤백 스위치 유지**: `features.policy_enforcement: off` / `features.worker_adapter_dispatch: false` 그대로.
- **근거 정합성**: 원 플랜 오픈 퀘스천 1(「이번 범위는 shadow까지」)과 일치.

> 검수 요청: 이 범위 축소가 **문서에 정직하게(축소 사실을 숨기지 않고) 기록**되었는지, 그리고 P0 완료를 이 축소된 기준으로 선언하는 것이 성립하는지 판정 바란다.

### 7.2 필수수정 ② 병합 경로 provenance — 이행

- `scripts/knowledge_distiller.py` `merge_into_existing_note()`에 `source_conversation_id` 파라미터 추가. 병합 블록에 `**source_file**` / `**source_conversation_id**` 두 줄을 기록한다.
- 호출부 2곳(주제 병합 / 파일명 일치 병합) 모두 `conversation_id`를 전달.
- provenance 라인은 의도적으로 `- ` 접두사를 쓰지 않는다 — 기존 insights 중복 제거 정규식(`^- (.+)$`)이 다음 병합 때 이 라인들을 인사이트로 오인 수집하는 것을 막기 위함.

### 7.3 필수수정 ③ sidecar 실패 격리 — 이행

`process_batch()`의 성공 경로를 다음과 같이 바꿨다.

- **순서 반전**: `append_processed_index()`를 `save_state()` **앞으로** 옮겼다. 기존 순서(state 먼저)에서는 sidecar 기록이 실패해도 state가 남아 재실행이 파일을 스킵 → 인덱스 누락이 **영구화**됐다.
- **예외 격리**: sidecar append의 `OSError`를 전용 `try/except`로 잡는다. 증류 자체는 성공했으므로 **실패로 집계하지 않고**(`fail`/`stats["failed"]` 불변) 경고 + 에러 리포트 기록만 한다.
- **자기치유**: sidecar 실패 시 state를 저장하지 않으므로 다음 실행이 같은 파일을 다시 처리해 인덱스를 복구한다. (`detect_duplicates()`는 동일 파일 경로를 중복으로 보지 않으므로 재실행 경로가 막히지 않음을 확인했다.)

### 7.4 필수수정 ④ process_batch 통합 회귀 테스트 — 이행

`tests/test_knowledge_distiller_provenance.py`에 `ProcessBatchIntegrationTests` 3건 추가. `distill_file`만 스텁(API 미호출)하고 **배치 로직은 실제로 실행**하며, 모든 경로 상수(`VAULT_BASE`/`OUTPUT_BASE`/`STATE_FILE`/`RETRY_QUEUE`/`PROCESSED_INDEX_FILE`/`CONTENT_HASH_REGISTRY`/`ERROR_REPORT`)를 임시 디렉터리로 격리한다.

| 테스트 | 고정하는 계약 |
|---|---|
| `test_new_note_path_records_provenance_and_leaves_raw_untouched` | 신규 노트 경로: frontmatter에 `source_conversation_id` 기록 + sidecar 1행 + **01_RAW SHA-256 불변** |
| `test_merge_path_records_conversation_id_and_leaves_raw_untouched` | 병합 경로: 신규 파일 미생성, 병합 블록에 `source_conversation_id` 기록, 기존 frontmatter 보존, sidecar `output_path`가 병합 대상, **01_RAW SHA-256 불변** |
| `test_sidecar_failure_is_not_counted_as_distill_failure_and_stays_retryable` | sidecar `OSError` 주입 시: `fail=0`·`stats["failed"]=0`, 노트는 디스크에 존재, **state 미저장**(재시도 가능), 01_RAW 불변 |

### 7.5 검증 증거

```
$ python -X utf8 -m unittest tests.test_knowledge_distiller_provenance
Ran 11 tests in 0.065s
OK
```

전체 스위트 회귀 대조 (`python -X utf8 -m unittest discover -s tests -p "test_*.py"`):

| | 테스트 수 | failures | errors |
|---|---|---|---|
| 베이스라인(변경분 stash) | 423 | 19 | 13 |
| 변경 후 | 426 (+3) | **19** | **13** |

→ **신규 회귀 0건**. 기존 실패 32건은 Stage 13~21과 무관한 이월 항목(discord 등 선택적 의존 모듈)이며 P1-7로 등록했다.

### 7.6 비차단 지적 처리

§6의 비차단 지적 4건은 **이번 범위에서 수정하지 않았다**(G6 통과 조건이 아님). 백로그 P1/P2로 이월한다.

- PyYAML 부재 테스트의 subprocess 격리 (`tests/test_generate_brain_status.py:165`)
- `bucky_brain_status.json`의 테스트 원장 노출 (비밀값·PII 없음 — 정리 대상)
- `generate_brain_status.py:141` api_server 파서 중복 구현 공용화
- **P0-9 매핑 누락은 확인 후 수정했다**: 스펙 원문은 `P0-N` 표기를 쓰지 않고 「P0 — 기반 안정화」 1~11 순번 목록만 두며 **9번 = 「테스트 하네스」**. 백로그 §2에 P0-9 행을 추가하고 부분 충족(하네스 존재하나 discover 기준 32건 기존 실패)으로 정직하게 기재했다.

### 7.7 재검수 범위

- 커밋: 아래 커밋 1건 (`docs/CODEX_REVIEW_REQUEST_G6.md` 포함)
- 판정 요청: (a) §7.1 범위 축소의 기록 정직성 및 P0 완료 선언 성립 여부, (b) 필수수정 ②③④가 §6 지적을 실제로 해소했는지, (c) 신규 회귀 없음 재현
- **스펙 원문 대조 가능**: `ObsidianVault/00_UPGRADE/BUCKY_SECOND_BRAIN_EVOLUTION_SPEC_v0.1_KR.md` (2015줄)은 `.gitignore`의 `ObsidianVault/*`로 여전히 git 미추적이다. 재검수 전 clone에 **수동 복사**해 §20 Story 5/6/7 및 P0 목록을 직접 대조할 것.
