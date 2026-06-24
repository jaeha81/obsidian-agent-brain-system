# Claude Code Instructions - Obsidian Agent Brain System

> Canonical Bucky/Codex/Claude routing rules: `ObsidianVault/00_System/ROUTING_RULES.md` and `ObsidianVault/03_Projects/agents/bucky.md`
> **전역 절대 규칙** (세션 관리·저장 경계·완료 보고 형식·역할·Bucky 패킷): `C:\Users\user1\.claude\CLAUDE.md` 참조

---

## Agent OS Activation Rule

Treat Obsidian Agent Brain System as the agent operating system for JH work.

1. When user requests touch project setup, scope, routing, agent roles, or project-specific instructions, do not infer instructions from another repo or folder.
2. Ask Bucky, or read the Bucky-managed project instruction packet, before applying project-specific rules.
3. If Bucky is not actively available and no project instruction packet exists, apply only minimum safety rules: preserve user changes, avoid destructive actions, do not commit/push without explicit user approval, and report that a Bucky instruction packet is needed.
4. Use only Bucky-provided or Bucky-confirmed instructions inside the current project scope.
5. Keep handoffs to Codex concise and evidence-based. Codex reviews independently.

If the user already provided exact files, commands, execution order, or forbidden actions, treat that request as the active Bucky packet for the first step. Run the first requested command before reading plans, broad diffs, whole large files, memories, or unrelated repo state.

Do not call any selector on the hot path for explicit tasks. In this Windows/Google Drive runtime, starting Python or script files can be delayed enough to waste a full turn.

When Bucky is not waiting in the loop and packet selection is actually needed for an unclear or new-project task, use the no-Python fast selector first:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/context_pack_selector_fast.ps1 -Project "<repo-or-folder>" "<request text>"
```

Python deep-routing fallback (when PS1 is unavailable):

```bash
python -X utf8 scripts/context_pack_selector.py --packet --project "<repo-or-folder>" "<request text>"
```

Do not reuse packets from another repo or folder unless Bucky confirms they apply.

## Three-Tier Routing

Claude Code should not treat Bucky as mandatory prework for every task.

1. **Explicit command path:** If the user provides exact files, commands, execution order, or forbidden actions, execute the first requested command immediately. Do not run selector, read Context Packs, inspect broad diffs, or write a plan first.
2. **Normal implementation path:** If the user requests a change but the steps are not exact, write a short micro-plan and ask the user to confirm. After confirmation, use Bucky/context only for the specific missing policy or project knowledge.
3. **Bucky-first path:** Ask Bucky or use a selector before planning only for new projects, unclear instruction authority, security/auth/payment/deploy/customer-data risk, destructive actions, broad migrations, role/instruction changes, or when the user explicitly asks for Bucky confirmation.

## VS Code Context Activation

사용자가 "VS코드 확인", "VS코드 작업 이어서", "VS코드에 들어가" 등을 요청하면 즉시 실행:

```bash
python -X utf8 scripts/vscode_context.py
```

출력에서 `active_workspace`와 `recent_edited_files`를 읽어 현재 작업 맥락을 파악한 뒤 답변한다.

특정 파일을 VS Code에서 열어야 할 때:

```bash
python -X utf8 scripts/vscode_context.py --open "경로/파일.py:라인번호"
```

## Karpathy 코딩 가이드라인 (항상 적용)

> 출처: [Andrej Karpathy의 LLM 코딩 함정 관찰](https://x.com/karpathy/status/2015883857489522876). 전체 스킬: `.claude/skills/karpathy-guidelines/SKILL.md`.
> 트레이드오프: 속도보다 신중함을 우선한다. 사소한 작업엔 판단껏 적용.

### 1. 코딩 전에 생각하라 — 가정·혼란을 숨기지 마라

- 가정은 명시한다. 불확실하면 묻는다.
- 해석이 여러 개면 조용히 하나 고르지 말고 모두 제시한다.
- 더 단순한 방법이 있으면 말한다. 필요하면 반박한다.
- 불명확하면 멈추고 무엇이 혼란스러운지 짚은 뒤 묻는다.

### 2. 단순함 우선 — 문제를 푸는 최소 코드, 추측성 구현 금지

- 요청하지 않은 기능·추상화·유연성/설정성·불가능 시나리오 예외처리 금지.
- 200줄이 50줄로 가능하면 다시 쓴다.
- "시니어 엔지니어가 과하다고 할까?" → 그렇다면 단순화.

### 3. 외과적 변경 — 건드릴 것만 건드리고, 네가 만든 것만 정리하라

- 기존 코드의 인접 부분·주석·포맷을 "개선"하지 마라.
- 망가지지 않은 걸 리팩토링하지 마라. 기존 스타일에 맞춰라.
- 무관한 데드코드는 언급만 하고 삭제하지 마라.
- 단, 내 변경으로 못 쓰게 된 import·변수·함수는 제거한다.
- 기준: 바뀐 모든 줄이 사용자의 요청으로 직접 추적돼야 한다.

### 4. 목표 기반 실행 — 성공 기준을 정하고 검증될 때까지 반복

- "검증 추가" → "잘못된 입력 테스트를 쓰고 통과시킨다"
- "버그 수정" → "재현 테스트를 쓰고 통과시킨다"
- "X 리팩토링" → "전후 테스트 통과를 보장한다"
- 다단계 작업은 `단계 → 검증` 형식으로 간단한 계획을 먼저 제시한다.

---

## 지식 진화 루프 규칙 (Knowledge Evolution Loop)

> 영상 기반 원칙: "자동화보다 맥락이 먼저. 중복은 AI가 막는다." (투솔 AI, 2026-06-16)

### 중복 저장 금지 (Deduplication Gate)

- Raw/ 또는 01_RAW/에서 지식을 정제해 Wiki/로 옮기기 전, 동일 주제 기존 노트를 먼저 검색한다.
- 새 노트 저장 전 "이 내용이 이미 Wiki/나 03_Knowledge/에 있는지" 반드시 확인한다.
- 중복 판정 기준: 동일 개념 70% 이상 겹침 → 새 파일 생성 금지, 기존 노트에 섹션 추가.
- 동일 주제 노트가 이미 있으면 반드시 사용자에게 알리고 병합 여부를 결정하게 한다.

### 정적 vs 동적 정보 분리 원칙

- **정적 (Context)**: 브랜드, 비즈니스 모델, 미션, 전략, 말투, 경쟁사, 타겟 고객 → `Context/` 또는 `06_Context_Packs/`에 저장. 자주 변경하지 않는다.
- **동적 (Daily)**: 세션 로그, 태스크, 캘린더, 미팅, 슬랙 캡처, 인박스 → `Daily/` 또는 `00_Inbox/` + `04_DAILY_REPORTS/`에 저장. 날짜별로 쌓인다.
- 두 유형을 같은 폴더에 혼용하지 않는다.

### Raw → Wiki 파이프라인

Raw 데이터(유튜브 트랜스크립트, X 팁, 슬랙 링크)가 들어오면:
1. `01_RAW/` 또는 `Raw/`에 원본 저장
2. 정제 시 중복 체크 (위 기준 적용)
3. 정제본만 `04_Wiki/` 또는 `Wiki/`에 저장
4. 원본은 정제 완료 후 태그 추가 (`#processed`) — 삭제하지 않음

### 주기적 병합 패스 (Weekly Merge)

매주 1회, 다음을 실행한다:
- 가장 오래된 미처리 `01_RAW/` 파일 10개를 Wiki로 정제
- `00_Inbox/` 중 7일 이상 된 항목을 처리하거나 Archive로 이동
- 중복 노트 발견 시 병합 후 원본에 `#merged-into: <대상파일>` 태그 기록


---

## 견적 시스템 라우팅 (Estimation Pipeline)

견적 관련 요청 처리 시:

### 입력 자동 분류
- PDF 도면 첨부 → `jh-drawing-recognition` 활성화
- XLS/XLSX 첨부 → `jh-boq-builder` 활성화
- 자재 리스트 페이지 감지 → `jh-material-spec-extractor` 활성화
- 통합 견적 요청 → `jh-estimate` 오케스트레이터 활성화

### 실행 엔진 (로컬 Python)
```
scripts/estimation/
  ├─ pdf_text_extractor.py   # PyMuPDF 텍스트 추출 + OCR 폴백
  ├─ drawing_recognizer.py   # 도면번호/카테고리/MATERIAL LIST 탐지
  ├─ excel_recognizer.py     # SPC 표준 BOQ 12열 파싱
  └─ boq_builder.py          # 통합 오케스트레이터
```

### 산출물 저장 경계
- 원본 보존: `data/estimation_samples/<slug>/` (json)
- 대시보드 노출용: `docs/data/estimation/<slug>.json` (light bundle)
- 견적서 최종본: `ObsidianVault/03_Projects/estimation/<slug>/`

### 신뢰도 표기 강제 (모든 출력)
- 🟢 HIGH: 도면 텍스트 추출 + 표준 prefix 매칭
- 🟡 MED: 추정/평균값 사용
- 🔴 LOW: OCR 폴백 또는 image-only 페이지

### 사용자 검증 게이트
다음 단계 진행 전 사용자 승인 필수:
1. 도면 카테고리 분류 결과
2. 자재 카탈로그 추출 결과
3. BOQ 단가 입력 / 요율 확정
4. 견적서 최종 출력 직전

### 어뷰징 금지
- 도면 인식 결과를 검증 없이 견적서로 자동 변환 금지
- AI Vision 호출은 사용자 승인 후에만 (비용 발생)