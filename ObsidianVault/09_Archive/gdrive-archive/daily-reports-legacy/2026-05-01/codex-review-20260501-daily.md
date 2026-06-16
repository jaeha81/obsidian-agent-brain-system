[Codex 검수 결과]
─────────────────
상태: FAIL

▶ 검수 대상:
- C-01: `D:\ai프로젝트\jh-brain-system\src\orchestrator\nodes.py` `awaiting_node()` 재진입 로직
- C-02: `D:\ai프로젝트\jh-harness\src\cli\second-brain.js` Obsidian 쓰기 구조

▶ 발견 이슈:

[P2] `src/orchestrator/nodes.py:134` / `src/orchestrator/graph.py:36` — `awaiting_node()` 첫 진입 시 `awaiting_since`만 기록하고 반환하지만, LangGraph는 같은 노드에서 멈추지 않고 즉시 조건 분기(`route_after_approval`)를 실행한다. 이 상태에는 `user_approved`와 `user_notes`가 없으므로 `route_after_approval()`이 `abort`를 반환해 `END`로 종료될 가능성이 높다.
  → LangGraph 실행 모델에 맞게 `interrupt()`/checkpoint 기반 승인 대기 또는 명시적 재호출 진입점을 사용하도록 구조를 바꿔야 한다.

[P2] `src/orchestrator/nodes.py:146` — 타임아웃 시 `user_approved=False`, `user_notes=[]`만 반환하고 `phase`나 `awaiting_since` 정리 없이 종료 분기에 의존한다. 이후 같은 상태를 재사용하면 과거 `awaiting_since`가 남아 재진입 판단이 꼬일 수 있다.
  → 타임아웃/abort 상태를 명시 필드로 기록하고 재시작 시 `awaiting_since` 초기화 규칙을 분리해야 한다.

[P1] `src/cli/obsidian-api.js:210` — FS 모드 `appendNote()`가 기존 파일을 `readFile`로 읽은 뒤 `writeFile`로 전체 재기록한다. Obsidian, Claude, Harness, 다른 Noesis 프로세스가 같은 노트를 동시에 수정하면 중간 변경분을 덮어써 데이터 손실이 발생할 수 있다.
  → FS 모드 append는 원자적 append API 또는 파일 잠금/버전 확인을 적용하고, 가능하면 Obsidian Local REST API 모드를 기본 쓰기 경로로 강제해야 한다.

[P1] `src/cli/obsidian-api.js:186` / `src/cli/second-brain.js:338` / `src/cli/second-brain.js:457` — `writeNote()`가 FS 모드에서 대상 노트를 전체 덮어쓴다. `updateDashboard()`, `patchFrontmatter()` 같은 경로는 최신 파일 버전 확인 없이 전체 내용을 재작성하므로 수동 편집 또는 병렬 동기화와 충돌 시 손실 위험이 있다.
  → 쓰기 전 mtime/hash 검증, 임시 파일 후 atomic rename, 충돌 감지 실패 처리, 또는 REST API PATCH 우선 정책을 추가해야 한다.

▶ AI-Slop 감지:
  • `src/orchestrator/nodes.py:149` — "분기는 route_after_approval에서 처리"라는 주석이 실제 LangGraph 대기 semantics를 보장하지 않는데도 대기 상태처럼 설명한다.
  • `src/cli/second-brain.js:60` — `SyncQueue`는 메모리 큐만 제공하며 프로세스 재시작 시 유실된다. "과부하 방지/배치 저장" 역할을 기대한다면 영속 큐가 아니라는 제약이 명시되어야 한다.

▶ 반복 패턴 경보:
  • 현재 `C:\Users\user1\.codex\memories\error-patterns.md`에는 등록된 반복 패턴이 없는 것으로 확인됨.

▶ 검수 제한:
  • `git status` 확인은 승인되지 않아 수행하지 못함. 본 검수는 사용자가 명시한 C-01/C-02 파일과 직접 관련 코드 경로 기준이다.

─────────────────
수정이 필요하면 Claude에게 지시해 주세요.

---

## 추가 검수 - 2026-05-01 P1 수정사항 및 awaiting_node 구조

[Codex 검수 결과]
─────────────────
상태: FAIL

▶ 검수 대상:
- `D:\ai프로젝트\jh-harness\src\cli\obsidian-api.js`
- `D:\ai프로젝트\jh-brain-system\src\orchestrator\nodes.py`
- `D:\ai프로젝트\jh-brain-system\src\orchestrator\graph.py`
- `D:\ai프로젝트\jh-brain-system\src\orchestrator\cli.py`

▶ 발견 이슈:

[P1] `src/cli/obsidian-api.js:173`, `src/web/server.js:1129` - `writeNote()`/`appendNote()`가 `notePath`를 검증하지 않고 `path.join(mode.vaultPath, notePath)`에 직접 사용한다. 웹 API 요청 본문 `path`가 그대로 들어오므로 `../` 또는 절대경로 입력 시 vault 밖 파일 읽기/쓰기/덮어쓰기 가능성이 있다.
  → `resolveVaultPath(vaultPath, notePath)`를 추가해 `path.resolve()` 결과가 vault root 내부인지 검증하고, `readNote/writeNote/appendNote` 모두 같은 검증을 사용해야 한다.

[P2] `src/cli/obsidian-api.js:189` - `writeNote()`의 임시 파일명이 항상 `full + '.tmp'`라서 같은 노트에 동시 write가 발생하면 tmp 파일 충돌이 난다. 한 호출이 다른 호출의 tmp 내용을 rename하거나, 나중 호출이 `ENOENT`로 실패할 수 있다.
  → tmp 파일명을 process id/UUID 기반으로 고유화하고, 실패 시 tmp cleanup을 `finally`에서 수행해야 한다.

[P2] `src/cli/obsidian-api.js:189-191` - atomic rename 자체는 기존 직접 `writeFile(full)`보다 안전하지만, Windows/동기화 폴더/Obsidian 감시 환경에서는 rename 직전 실패 시 `.tmp` 찌꺼기가 남고, rename 실패가 사용자에게만 throw된다.
  → `try/finally` cleanup, 에러 메시지 표준화, 가능하면 `fs.move(tmp, full, { overwrite: true })` 또는 rename 실패 시 명시 처리 규칙을 추가한다.

[P2] `src/cli/obsidian-api.js:215` - `appendNote()`를 `appendFile()` 단일 호출로 바꾼 것은 read-modify-write 데이터 손실 위험을 줄이는 올바른 방향이다. 다만 새 파일에도 항상 선행 개행이 생기고, 기존 파일이 이미 개행으로 끝난 경우 빈 줄이 누적될 수 있다.
  → 새 파일 여부/파일 크기/마지막 바이트를 확인해 필요한 경우에만 구분 개행을 붙인다.

[P2] `src/orchestrator/nodes.py:115`, `src/orchestrator/graph.py:36`, `src/orchestrator/cli.py:45` - 현재 `awaiting_node()`는 첫 진입에서 `awaiting_since`만 반환한 뒤, 같은 실행 tick에서 즉시 `route_after_approval()`로 넘어간다. 초기 상태의 `user_approved=False`, `user_notes=[]` 때문에 실제 승인 대기 없이 `abort -> END`가 된다.
  → 현재 구조에는 LangGraph `interrupt()` + checkpointer 기반 대기가 더 적합하다. `awaiting_node()` 내부에서 승인 요청 payload를 `interrupt()`로 내보내고, CLI/API가 같은 `thread_id`로 `Command(resume={...})`를 호출해 재개하는 구조로 바꿔야 한다.

▶ 판단:
- `writeNote` 수정: 부분적으로 올바름. 직접 덮어쓰기보다 안전하지만 tmp 파일명 충돌, cleanup, vault 경로 검증이 빠져 있어 완료된 P1 수정으로 보기 어렵다.
- `appendNote` 수정: 핵심 P1인 read-modify-write 손실 위험은 상당히 해소했다. 단, vault 경로 검증 누락은 별도 P1로 남아 있고, 개행 정책은 P2/P3 보완 대상이다.
- `awaiting_node` 방향: 외부에서 state를 직접 업데이트하는 API 방식보다 `interrupt()`/checkpoint 방식이 jh-brain-system의 LangGraph 구조에 더 맞다. 현재 프로젝트는 `brain_orchestrator.invoke(initial_state)` 단발 실행 구조이고 `compile()`에 checkpointer가 없으므로, 외부 state 주입 방식을 택하려면 별도의 실행 저장소/세션 API/상태 병합 규칙을 새로 만들어야 한다. 반면 LangGraph 공식 HITL 모델은 이 문제를 위해 `interrupt()`, checkpointer, `Command(resume=...)`, 동일 `thread_id` 재개를 제공한다.

▶ 구체적 수정 방향:
1. `graph.py`에서 checkpointer를 추가한다. 개발/로컬 우선이면 `MemorySaver`, 실제 24시간 대기와 프로세스 재시작 복구가 필요하면 SQLite/Postgres checkpointer를 사용한다.
2. `awaiting_node()`에서 출력/타임스탬프 기록 후 `interrupt({"project_name": ..., "plan_md": ..., "awaiting_since": ...})`를 호출한다. resume 값은 `{ "approved": true, "notes": [] }`처럼 단순 JSON으로 제한한다.
3. resume 결과에 따라 `user_approved`, `user_notes`, `awaiting_since`를 반환한다. 승인 거절/타임아웃은 별도 `approval_status` 또는 `phase`로 명시해 재실행 시 과거 awaiting 상태가 섞이지 않게 한다.
4. `cli.py`는 `thread_id`를 생성/표시하고, 첫 `invoke()` 결과의 `__interrupt__`를 사용자에게 보여준 뒤 승인 명령에서 `Command(resume=...)`로 같은 `thread_id`를 재개하도록 분리한다.
5. API 기반 승인이 필요하면 "외부 state 직접 수정"이 아니라 interrupt resume API를 감싸는 엔드포인트로 만든다. 즉 `/approve`가 저장된 `thread_id`로 `graph.invoke(Command(resume=approval), config=...)`를 호출하게 한다.

▶ 참고 근거:
- LangGraph Python interrupt 문서: `interrupt()`는 그래프 실행을 멈추고 외부 입력을 기다리며, 재개 시 `Command(resume=...)`와 동일 `thread_id`를 사용한다.
- LangGraph 문서상 static interrupt는 디버깅/테스트용에 가깝고, human-in-the-loop에는 노드 내부 `interrupt()`가 권장된다.

▶ AI-Slop 감지:
  • `src/orchestrator/nodes.py:149` - "분기는 route_after_approval에서 처리"라는 주석은 실제 승인 대기를 보장하지 않는데 대기 구조처럼 설명한다.

▶ 반복 패턴 경보:
  • 현재 `C:\Users\user1\.codex\memories\error-patterns.md`에는 등록된 반복 패턴이 없는 것으로 확인했다.

─────────────────
수정이 필요하면 Claude에게 지시해 주세요.
