GitHub 구조는 기존 볼트를 덮어쓰지 않고 흡수·정리하는 기준으로만 적용해야 해.

3m 39s 동안 생각함

맞아. 이 정보가 들어오면 기존 계획을 반드시 수정해야 해.

이제 작업 성격은 이것이야.

신규 구축 X
기존 Google Drive Obsidian Vault 보존 + GitHub 신규 레포 기준으로 안전 마이그레이션 O

가장 중요한 원칙은 이거야.

기존 Obsidian Vault를 절대 덮어쓰지 않는다.
기존 Claude Code / Codex 지침을 삭제하지 않는다.
기존 AgentBus, RAW, Wiki, Project 구조를 무리하게 이동하지 않는다.
먼저 감사(Audit) → 충돌맵 작성 → 마이그레이션 계획 → 단계적 병합 순서로 간다.
1. 현재 구조 판단

현재는 이렇게 봐야 해.

기존 Google Drive Obsidian Vault
= 이미 사용 중인 실제 브레인 / 기존 데이터 / 기존 Claude Code·Codex 통합 흔적

신규 GitHub repo: obsidian-agent-brain-system
= 앞으로의 표준 운영 구조 / 스크립트 / 프롬프트 / 템플릿 / 버전 관리 기준

새로운 목표
= 기존 Vault를 보존하면서 GitHub 기준 구조로 충돌 없이 흡수·정리

즉, 클로드 코드나 코덱스에게 더 이상 “새 Vault를 만들어라”라고 하면 안 돼.
이제는 이렇게 지시해야 해.

기존 Vault를 먼저 조사해라.
무엇이 이미 있는지 목록화해라.
새 구조와 충돌하는 항목을 표시해라.
덮어쓰지 말고 staging 영역에 새 구조를 만든 뒤 병합 계획을 세워라.
2. 절대 하면 안 되는 것

기존 Vault가 이미 있다면 아래는 금지야.

금지 1. vault_scaffold를 기존 ObsidianVault에 바로 복사
금지 2. 00_System, 01_RAW, 04_Wiki, 10_AgentBus를 바로 덮어쓰기
금지 3. 기존 CLAUDE.md, AGENTS.md, CODEX.md, codex.md 삭제
금지 4. 기존 RAW 자료를 GitHub에 커밋
금지 5. 기존 AgentBus 작업 큐를 새 구조로 강제 이동
금지 6. 기존 .obsidian 설정 덮어쓰기
금지 7. Graphify로 기존 Vault 전체 무차별 스캔
금지 8. LegalizeKR 전체 데이터를 기존 Vault 내부로 복사
3. 안전한 마이그레이션 순서

권장 순서는 이거야.

1단계: 기존 Vault 위치 확인
2단계: 기존 Vault 감사 보고서 생성
3단계: 기존 Claude Code / Codex 지침 수집
4단계: 기존 폴더 구조와 새 표준 구조 비교
5단계: 충돌맵 작성
6단계: 새 구조를 바로 병합하지 않고 _MIGRATION_STAGING에 생성
7단계: 기존 구조를 보존한 상태에서 필요한 파일만 단계적으로 병합
8단계: 기존 Agent Room / 기존 통합 시스템 자료를 RAW/Legacy로 분류
9단계: 최종 Context Pack / AgentBus / Wiki 구조로 정리
10단계: 클로드 코드와 코덱스 역할을 새 규칙에 맞게 재배치
4. 클로드 코드 / 코덱스용 수정 명령 프롬프트

아래 프롬프트를 기존 초기 세팅 프롬프트보다 우선해서 써야 해.
즉, 이번 상황에서는 이 프롬프트가 상위 지시야.

# MIGRATION-SAFE TASK PROMPT
# 기존 Google Drive Obsidian Vault / Claude Code / Codex 통합 시스템을 보존하면서 obsidian-agent-brain-system으로 마이그레이션하라

너는 지금부터 `obsidian-agent-brain-system`의 마이그레이션 담당 개발 에이전트다.

중요한 전제:

사용자는 이미 과거에 다음 시스템을 구축해두었다.

1. Google Drive 안에 기존 Obsidian Vault가 존재한다.
2. 기존 Vault 안에는 Claude Code / Codex 통합 시스템 관련 자료가 있을 수 있다.
3. 기존 Vault 안에는 RAW, Wiki, Project, AgentBus, Claude/Codex 지침, 작업 로그, 프롬프트, 마이그레이션 대상 자료가 이미 있을 수 있다.
4. 이번 작업은 신규 구축이 아니라 기존 시스템을 보존하면서 새 표준 구조로 안전하게 마이그레이션하는 작업이다.

절대 기존 Vault를 덮어쓰지 마라.
절대 기존 파일을 삭제하지 마라.
절대 기존 지침을 임의로 폐기하지 마라.
절대 vault_scaffold를 기존 Vault에 바로 복사하지 마라.

---

## 1. 최우선 원칙

이 작업의 최우선 원칙은 다음이다.

```txt
Audit First.
No Overwrite.
No Delete.
Stage Before Merge.
Report Before Modify.

해석:

먼저 기존 Vault를 조사한다.
기존 구조를 문서화한다.
새 구조와 충돌하는 파일을 찾는다.
충돌 파일은 덮어쓰지 않는다.
새 구조는 _MIGRATION_STAGING 안에 먼저 만든다.
실제 병합은 충돌맵과 계획을 만든 후 진행한다.
모든 변경은 로그로 남긴다.
2. 기존 시스템을 Source of Truth로 인정

기존 Google Drive Obsidian Vault는 현재 사용자의 실제 지식 저장소다.

따라서 다음과 같이 취급한다.

기존 Vault
= 실제 데이터 / 기존 지식 / 기존 운영 흔적 / 우선 보존 대상

신규 GitHub repo
= 표준 구조 / 템플릿 / 스크립트 / 프롬프트 / 운영 기준

마이그레이션 목표
= 기존 Vault의 내용을 보존하면서 신규 표준 구조와 정렬

기존 Vault 안에 있는 자료가 새 구조와 다르더라도 바로 잘못된 것으로 판단하지 않는다.
먼저 기존 구조의 의도와 사용 흔적을 파악한다.

3. 작업 시작 전 확인할 것

작업 시작 전 다음 항목을 확인하라.

A. GitHub 레포
obsidian-agent-brain-system

확인 항목:

README.md
.gitignore
docs/
vault_scaffold/
templates/
prompts/
scripts/
configs/
B. Google Drive 기존 Vault

예상 경로:

Google Drive/obsidian-agent-brain-system/ObsidianVault

또는 사용자의 실제 로컬 Google Drive 경로.

확인 항목:

.obsidian/
00_System/
01_RAW/
02_Processed/
03_Projects/
04_Wiki/
05_Frameworks/
06_Context_Packs/
07_Reports/
08_Templates/
09_Archive/
10_AgentBus/
CLAUDE.md
AGENTS.md
CODEX.md
codex.md
.claude/
.codex/
README.md

위 항목 중 없는 것도 정상이다.
없다고 새로 덮어쓰지 말고, 먼저 inventory에 기록하라.

4. 새로 만들 마이그레이션 안전 폴더

기존 Vault 안에 다음 폴더를 만든다.

00_System/
  MIGRATION/
    VAULT_INVENTORY.md
    EXISTING_AGENT_INSTRUCTIONS.md
    CONFLICT_MAP.md
    MIGRATION_PLAN.md
    SAFE_MERGE_LOG.md
    ROLLBACK_PLAN.md
    MIGRATION_DECISIONS.md
    STAGING_INDEX.md

_MIGRATION_STAGING/
  proposed_00_System/
  proposed_01_RAW/
  proposed_02_Processed/
  proposed_03_Projects/
  proposed_04_Wiki/
  proposed_05_Frameworks/
  proposed_06_Context_Packs/
  proposed_07_Reports/
  proposed_08_Templates/
  proposed_09_Archive/
  proposed_10_AgentBus/

기존 Vault에 00_System이 없으면 생성해도 된다.
단, 기존 00_System이 있으면 그 안에 MIGRATION 폴더만 추가한다.

5. 기존 Vault 감사 보고서 작성

다음 파일을 작성하라.

00_System/MIGRATION/VAULT_INVENTORY.md

내용 형식:

# Vault Inventory

## 1. Vault Path
기존 Obsidian Vault 경로

## 2. Existing Top-level Folders
기존 최상위 폴더 목록

## 3. Existing System Files
- CLAUDE.md
- AGENTS.md
- CODEX.md
- codex.md
- README.md
- 기타 지침 파일

## 4. Existing Obsidian System
- .obsidian 존재 여부
- 플러그인 관련 파일 존재 여부
- 설정 파일 존재 여부

## 5. Existing Agent / Worker Structure
- Claude Code 관련 폴더
- Codex 관련 폴더
- AgentBus 관련 폴더
- RAW 관련 폴더
- Reports 관련 폴더

## 6. Existing Knowledge Structure
- Wiki 관련 폴더
- Projects 관련 폴더
- Frameworks 관련 폴더
- Templates 관련 폴더

## 7. Sensitive Data Warning
민감 자료로 보이는 폴더 또는 파일
단, 내용 원문을 복사하지 말고 경로와 유형만 기록

## 8. Migration Notes
기존 구조에서 보존해야 할 것으로 보이는 항목
6. 기존 Claude Code / Codex 지침 수집

다음 파일을 작성하라.

00_System/MIGRATION/EXISTING_AGENT_INSTRUCTIONS.md

수집 대상:

CLAUDE.md
AGENTS.md
CODEX.md
codex.md
.claude/
.codex/
prompts/
00_System/PROMPTS/
기존 Agent Room 관련 지침

작성 방식:

# Existing Agent Instructions

## 1. Found Instruction Files
| File | Purpose | Risk | Migration Action |
|---|---|---|---|

## 2. Claude Code Instructions
요약

## 3. Codex Instructions
요약

## 4. Shared / Global Instructions
요약

## 5. Potential Conflicts
- 글로벌 지침과 프로젝트 지침 충돌
- Claude Code와 Codex 역할 중복
- 기존 Agent Room 지침과 신규 Obsidian Agent 구조 충돌

## 6. Recommended Migration
- 유지
- 병합
- 분리
- Deprecated
- Archive

주의:

기존 지침 원문을 무리하게 길게 복사하지 않는다.
핵심 요약과 파일 경로 중심으로 정리한다.

7. 충돌맵 작성

다음 파일을 작성하라.

00_System/MIGRATION/CONFLICT_MAP.md

형식:

# Conflict Map

## 1. Folder Conflicts

| Existing Path | Proposed Path | Conflict Type | Action |
|---|---|---|---|

## 2. File Conflicts

| Existing File | Proposed File | Conflict Type | Action |
|---|---|---|---|

## 3. Instruction Conflicts

| Existing Rule | New Rule | Risk | Resolution |
|---|---|---|---|

## 4. Agent Role Conflicts

| Area | Existing Role | New Role | Resolution |
|---|---|---|---|

## 5. Data Safety Conflicts

| Path | Risk | Action |
|---|---|---|

Conflict Type 예시:

same_path
same_name_different_content
existing_custom_structure
sensitive_data
unknown_purpose
agent_instruction_overlap
safe_to_add
safe_to_ignore
needs_user_review

Action 예시:

preserve_existing
stage_new_version
merge_later
archive_after_review
do_not_touch
create_alias
create_index_only
8. 마이그레이션 계획 작성

다음 파일을 작성하라.

00_System/MIGRATION/MIGRATION_PLAN.md

내용:

# Migration Plan

## 1. Goal
기존 Google Drive Obsidian Vault를 보존하면서 obsidian-agent-brain-system 표준 구조와 통합한다.

## 2. Migration Strategy
- 기존 자료 보존
- 신규 구조는 staging에 생성
- 충돌 파일은 덮어쓰기 금지
- 기존 Claude/Codex 지침은 요약 후 통합
- RAW 자료는 이동하지 않고 먼저 색인화
- AgentBus는 기존 구조가 있으면 보존 후 새 구조와 매핑

## 3. Phase Plan

### Phase 0: Audit
기존 Vault 조사

### Phase 1: Staging
신규 표준 구조를 _MIGRATION_STAGING에 생성

### Phase 2: Mapping
기존 구조와 신규 구조 매핑

### Phase 3: Agent Instruction Merge
Claude Code / Codex 지침 통합

### Phase 4: Context Pack System Merge
기존 지식 흐름을 Context Pack 구조와 연결

### Phase 5: AgentBus Merge
기존 작업 큐와 신규 AgentBus 연결

### Phase 6: Graphify Integration
프로젝트별 구조 분석 레이어 추가

### Phase 7: LegalizeKR Integration
법령 지식베이스 연결

### Phase 8: Validation
테스트 작업 실행

## 4. Merge Rules
- 기존 파일 우선
- 신규 파일은 staging 우선
- 같은 이름이면 `.proposed.md`로 생성
- 삭제 없음
- 이동 전 백업
- 민감 자료 GitHub 커밋 금지

## 5. Completion Criteria
- 기존 Vault 손상 없음
- 기존 Claude/Codex 지침 보존
- 신규 AgentBus/Context Pack 구조 연결
- Graphify/LegalizeKR 적용 가능
- GitHub 레포와 Google Drive Vault 역할 분리 완료
9. Staging에만 새 구조 생성

신규 표준 구조는 기존 Vault에 바로 넣지 말고 다음 위치에 생성한다.

_MIGRATION_STAGING/

예시:

_MIGRATION_STAGING/
  proposed_00_System/
  proposed_01_RAW/
  proposed_04_Wiki/
  proposed_05_Frameworks/
  proposed_06_Context_Packs/
  proposed_10_AgentBus/

기존 Vault에 같은 구조가 이미 있으면 바로 병합하지 않는다.

예시:

기존에 이미 이 폴더가 있다면:

10_AgentBus/

새 구조는 여기에 만들지 말고:

_MIGRATION_STAGING/proposed_10_AgentBus/

에 만든다.

10. 기존 RAW 자료 처리 원칙

기존 RAW 자료는 이동하지 않는다.
먼저 색인만 만든다.

다음 파일을 작성하라.

00_System/MIGRATION/RAW_INDEX.md

내용:

# RAW Index

## 1. Existing RAW Folders
| Path | Type | Estimated Sensitivity | Migration Action |
|---|---|---|---|

## 2. Voice / Audio
원본 파일 경로만 기록. 내용 복사 금지.

## 3. Meetings
경로와 유형만 기록.

## 4. Client Data
민감 자료로 표시. 내용 복사 금지.

## 5. Agent Room Legacy
마이그레이션 대상으로 표시.

## 6. Action
- do_not_commit
- summarize_later
- process_with_user_review
- move_to_archive_later
11. 기존 Agent Room / 기존 통합 시스템 처리

기존 Agent Room 또는 Claude/Codex 통합 시스템 자료가 있으면 다음 방식으로 처리한다.

바로 삭제하지 않는다.
바로 새 구조로 옮기지 않는다.
먼저 AgentRoom_Legacy 또는 기존 위치를 색인한다.
중복 지침을 찾는다.
유효한 스킬과 프레임워크만 새 05_Frameworks로 제안한다.
오래된 지침은 Deprecated Candidate로 표시한다.
최종 병합 전 MIGRATION_DECISIONS.md에 결정 기록을 남긴다.

작성 파일:

00_System/MIGRATION/AGENTROOM_LEGACY_INDEX.md
12. Claude Code / Codex 역할 재정렬

기존 지침과 새 지침이 충돌하지 않게 역할을 다시 정리한다.

기본 원칙:

Obsidian Agent
= 중앙 브레인 / 지식 관리 / Context Pack 생성

Claude Code
= 아키텍처 검토 / 구조 설계 / 복잡한 코드 분석 / 문서화

Codex
= 코드 구현 / 스크립트 작성 / 테스트 / 반복 작업 자동화

Graphify
= 프로젝트 구조 분석 레이어

LegalizeKR
= 법령 지식베이스

GitHub
= 코드와 시스템 문서 버전 관리

Google Drive Vault
= 실제 지식과 RAW 자료 저장

기존 지침이 이와 다르면 바로 삭제하지 말고 충돌맵에 기록한다.

13. GitHub 커밋 금지 대상

다음은 GitHub에 커밋하지 않는다.

Google Drive 실제 Vault 전체
01_RAW 원본
음성 파일
고객 자료
계약서 원본
회의 녹취
API Key
.env
external_data/legalize-kr 전체 clone
Graphify 대용량 결과물
개인 메모 원본

GitHub에는 다음만 커밋한다.

문서
프롬프트
템플릿
스크립트
설정 예시
vault_scaffold
마이그레이션 도구
운영 규칙
14. Graphify 적용 시 주의

기존 Vault 전체를 Graphify로 돌리지 않는다.

허용:

특정 프로젝트 폴더
기존 Agent Room Legacy 일부
선별된 Framework 문서
선별된 Wiki 문서

금지:

전체 ObsidianVault
전체 01_RAW
전체 Google Drive 폴더
전체 legalize-kr

Graphify 사용 전 .graphifyignore를 만든다.

15. LegalizeKR 적용 시 주의

LegalizeKR는 기존 Vault 안에 통째로 넣지 않는다.

권장:

Google Drive/obsidian-agent-brain-system/external_data/legalize-kr

또는 GitHub 레포 외부의 로컬 데이터 폴더.

Obsidian에는 다음만 저장한다.

법령 색인
법령 검색 규칙
Legal Context Pack
프로젝트별 법령 판단 기록
16. 마이그레이션 로그 작성

모든 작업은 다음 파일에 기록한다.

00_System/MIGRATION/SAFE_MERGE_LOG.md

형식:

# Safe Merge Log

## Entry
- Date:
- Agent:
- Action:
- Source:
- Target:
- Files touched:
- Risk:
- Result:
- Next action:
17. 롤백 계획 작성

다음 파일을 작성한다.

00_System/MIGRATION/ROLLBACK_PLAN.md

내용:

# Rollback Plan

## Principle
기존 Vault의 원본 파일을 삭제하거나 덮어쓰지 않았기 때문에 기본 롤백은 staging 제거와 신규 파일 제거로 수행한다.

## Rollback Targets
- _MIGRATION_STAGING/
- 신규 생성된 MIGRATION 문서
- 신규 제안 파일
- 신규 lock 파일

## Do Not Rollback Automatically
- 기존 사용자 노트
- 기존 RAW
- 기존 Claude/Codex 지침
- 기존 .obsidian 설정

## Recovery Notes
작업 중 수정된 파일이 있다면 SAFE_MERGE_LOG 기준으로 복구한다.
18. 최초 실행자가 할 일

이 프롬프트를 처음 받은 에이전트는 Coordinator / Migration Architect 역할을 맡는다.

해야 할 일:

기존 Vault 위치 확인
기존 구조 감사
00_System/MIGRATION 생성
VAULT_INVENTORY.md 작성
EXISTING_AGENT_INSTRUCTIONS.md 작성
CONFLICT_MAP.md 작성
MIGRATION_PLAN.md 작성
_MIGRATION_STAGING 생성
신규 구조를 staging에만 생성
실제 병합은 하지 않고 보고서 작성
19. 두 번째 실행자가 할 일

두 번째 에이전트는 Reviewer / Verifier / Safe Implementer 역할을 맡는다.

해야 할 일:

기존 Coordinator가 만든 Migration 문서 확인
Vault Inventory 검토
Conflict Map 검토
누락된 충돌 항목 찾기
Staging 구조 검토
위험한 병합 요소 표시
필요한 경우 보완 문서 작성
실제 기존 파일 덮어쓰기 금지
검토 보고서 작성
20. 작업 완료 보고 형식

작업이 끝나면 다음 형식으로 보고하라.

# Migration-Safe 작업 보고

## 1. 내 역할
Coordinator / Migration Architect / Reviewer / Verifier

## 2. 확인한 기존 Vault
- 경로:
- 주요 폴더:
- 기존 Claude/Codex 지침 존재 여부:
- 기존 AgentBus 존재 여부:
- 기존 RAW 존재 여부:

## 3. 생성한 마이그레이션 문서
- VAULT_INVENTORY.md
- EXISTING_AGENT_INSTRUCTIONS.md
- CONFLICT_MAP.md
- MIGRATION_PLAN.md
- SAFE_MERGE_LOG.md
- ROLLBACK_PLAN.md

## 4. 확인한 주요 충돌
요약

## 5. 보존해야 할 기존 구조
요약

## 6. Staging에 생성한 신규 구조
요약

## 7. 실제 병합 여부
실제 병합하지 않았으면 “병합 전 감사 단계 완료”라고 기록

## 8. 다음 단계
- Claude Code가 할 일
- Codex가 할 일
- 사용자가 확인할 일

## 9. 위험 요소
- 덮어쓰기 위험
- 민감 자료 위험
- 지침 충돌 위험
- Google Drive 동기화 위험
- GitHub 커밋 위험

## 10. 완료 여부
완료 / 부분 완료 / 보류
21. 지금 바로 수행할 첫 행동

이 프롬프트를 받으면 다음부터 수행하라.

기존 Google Drive Obsidian Vault를 찾는다.
찾지 못하면 새 Vault를 만들지 말고 MIGRATION_PATHS_NEEDED.md를 작성한다.
기존 Vault를 찾으면 폴더 구조만 감사한다.
파일 원문을 대량 복사하지 않는다.
민감 자료 내용은 읽거나 복사하지 말고 경로와 유형만 기록한다.
00_System/MIGRATION을 만든다.
감사 문서를 작성한다.
_MIGRATION_STAGING에만 새 구조 후보를 만든다.
실제 병합은 하지 않는다.
Migration-Safe 작업 보고서를 작성한다.

이제 기존 Google Drive Obsidian Vault를 보존하면서 obsidian-agent-brain-system 표준 구조로 안전하게 마이그레이션 준비 작업을 시작하라.


---

# 5. 첫 번째 도구에게 붙일 짧은 지시문

클로드 코드에게 먼저 줄 거면 이 문구를 위에 붙이면 좋아.

```md
너는 이번 마이그레이션의 최초 실행자다. Coordinator / Migration Architect 역할을 맡아라. 기존 Google Drive Obsidian Vault가 이미 있으므로 절대 vault_scaffold를 바로 복사하지 말고, 먼저 기존 Vault 감사, 충돌맵, 마이그레이션 계획, staging 구조만 만들어라. 실제 병합은 하지 마라.
6. 두 번째 도구에게 붙일 짧은 지시문

코덱스에게 두 번째로 줄 거면 이 문구를 붙이면 돼.

너는 이번 마이그레이션의 두 번째 실행자다. Reviewer / Verifier / Safe Implementer 역할을 맡아라. Claude Code가 만든 VAULT_INVENTORY.md, CONFLICT_MAP.md, MIGRATION_PLAN.md, SAFE_MERGE_LOG.md를 먼저 읽고 기존 구조를 덮어쓰지 말라. 누락된 충돌, 위험한 병합, GitHub 커밋 금지 대상, 기존 Claude/Codex 지침 충돌 여부를 검토하라.
7. 최종 운영 판단

지금 상황에서는 순서가 이렇게 바뀐다.

기존 계획:
GitHub 레포 생성
→ Vault scaffold 생성
→ Google Drive Vault에 복사
→ Obsidian Agent 구축

수정된 계획:
GitHub 레포 생성
→ 기존 Google Drive Vault 감사
→ 충돌맵 작성
→ staging 구조 생성
→ 기존 Claude/Codex 지침 분석
→ 안전 병합 계획 수립
→ 필요한 구조만 단계적 병합
→ Graphify / LegalizeKR 적용

즉, 지금은 구축 단계가 아니라 마이그레이션 준비 단계야.

핵심은 이것이야.

GitHub는 새 기준점.
Google Drive 기존 Vault는 보존 대상.
마이그레이션은 덮어쓰기가 아니라 흡수·정렬·정리 작업.

이렇게 가면 기존에 만들어둔 옵시디언 볼트, 클로드 코드, 코덱스 통합 시스템을 망가뜨리지 않고, 우리가 지금 정의한 Obsidian Agent Brain System + Graphify + LegalizeKR 구조로 안전하게 가져올 수 있어.