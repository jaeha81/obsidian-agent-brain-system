# PLAN REMINDER PROMPT
# obsidian-agent-brain-system 본 계획 리마인드 및 현재 작업 정렬 지시

중요:
지금은 새로운 계획을 세우는 단계가 아니다.
현재 진행 중인 `obsidian-agent-brain-system` 개발의 본 계획을 다시 상기하고, 기존 작업 흐름이 흔들리지 않도록 정렬하는 단계다.

기존 작업을 리셋하지 말고, 현재 생성된 파일과 상태를 기준으로 이어서 진행하라.
새 아키텍처를 다시 만들지 말고, 아래 본 계획을 기준으로 현재 작업을 점검하고 계속 진행하라.

---

## 1. 현재 개발의 본질

현재 개발은 단순한 Obsidian 폴더 생성 작업이 아니다.

현재 개발은 다음 시스템을 구축하고, 기존 Google Drive Obsidian Vault와 충돌 없이 안전하게 마이그레이션하는 작업이다.

```txt
Obsidian Agent Brain System

이 시스템의 목적은 다음과 같다.

Obsidian
= 중앙 브레인 / 지식 허브 / 작업 지휘소

Obsidian Agent
= RAW 수집, 분류, 위키화, Context Pack 생성, 작업 지시, 결과 정리

Claude Code
= 아키텍처 검토, 구조 설계, 복잡한 분석, 문서화, 개발 보조

Codex
= 코드 구현, 스크립트 작성, 테스트, 반복 자동화

Graphify
= 프로젝트 코드·문서·레포 구조를 지식 그래프로 분석하는 보조 레이어

LegalizeKR
= 대한민국 법령 지식베이스 / 법령 검색 및 Legal Context Pack 생성

GitHub
= 코드, 템플릿, 프롬프트, 스크립트, 시스템 문서 버전 관리

Google Drive
= 실제 Obsidian Vault, RAW 자료, 음성, 고객 자료, 기존 지식, 마이그레이션 대상 보관
2. 현재 생성된 기준점

사용자는 이미 다음 두 가지를 생성했다.

GitHub Repository:
obsidian-agent-brain-system

Google Drive Folder:
obsidian-agent-brain-system

중요한 전제:

기존 Google Drive Obsidian Vault가 이미 존재한다.
기존 Vault 안에는 Claude Code / Codex 통합 시스템이 이미 구성되어 있다.
따라서 이번 작업은 신규 구축이 아니라 기존 Vault를 보존하면서 새 표준 구조로 안전하게 마이그레이션하는 작업이다.

즉, 현재 작업은 이것이다.

신규 구축 X
기존 Vault 보존 + 안전 감사 + 충돌맵 작성 + 단계적 마이그레이션 O
3. 가장 중요한 운영 원칙

아래 원칙을 절대 위반하지 마라.

Audit First.
No Overwrite.
No Delete.
Stage Before Merge.
Report Before Modify.

의미:

기존 Vault를 먼저 조사한다.
기존 파일을 덮어쓰지 않는다.
기존 지침, RAW, AgentBus, Wiki, Project 자료를 삭제하지 않는다.
새 구조는 _MIGRATION_STAGING에 먼저 만든다.
충돌맵과 마이그레이션 계획 없이 실제 병합하지 않는다.
모든 변경은 로그로 남긴다.
4. 현재 시스템은 3가지 작업 축으로 구성된다

현재 채팅방에서 정의한 전체 개발은 크게 3가지다.

1. Obsidian Agent Brain System

이것이 메인 시스템이다.

핵심 구조:

사용자 입력
↓
Discord / Voice / Obsidian / Claude Code / Codex
↓
01_RAW
↓
Obsidian Agent
↓
분류 / 요약 / Wiki화 / Context Pack 생성
↓
Claude Code / Codex 작업 수행
↓
작업 결과 보고
↓
Obsidian Wiki / Project / Devlog / GitHub 반영

주요 기능:

RAW 폴더 체계
AgentBus
Context Pack 시스템
Framework Router
Claude Code / Codex 역할 분리
기존 Agent Room 자료 마이그레이션
Wiki 구조 구축
GitHub 연동 규칙
Discord / Voice 입력 흐름
Google Drive Vault 저장 구조
2. LegalizeKR Integration

대상:

https://github.com/legalize-kr/legalize-kr.git

역할:

LegalizeKR
= 대한민국 법령 원문 데이터 소스

Obsidian Agent
= 법령 요청 감지, 관련 법령 검색, 요약, Legal Context Pack 생성

Claude Code / Codex
= Legal Context Pack을 받아 약관, 계약서, 개인정보, 인테리어/건축, AI 서비스, 플랫폼 운영 관련 개발에 반영

중요 원칙:

legalize-kr 전체 레포를 Obsidian Vault 안에 넣지 않는다.
전체 법령을 Claude Code나 Codex 컨텍스트에 넣지 않는다.
필요한 법령만 검색하고 Legal Context Pack으로 압축해서 전달한다.

적용 분야:

인테리어 계약
시공 / 감리 / 하자
건축법
건설산업기본법
개인정보 보호법
전자상거래
약관
광고 문구
AI 자동화 서비스 운영
플랫폼 사업
3. Graphify Integration

대상:

https://graphify.net/kr/

역할:

Graphify
= 프로젝트 코드, 문서, 다이어그램, 레포 구조를 지식 그래프로 변환하는 프로젝트 구조 분석 레이어

Obsidian Agent
= Graphify 결과를 해석하고 Graphify Context Pack으로 압축

Claude Code / Codex
= Graphify Context Pack을 받아 관련 파일, 모듈, 영향 범위를 파악하고 개발 수행

중요 원칙:

Graphify는 Obsidian의 중앙 브레인이 아니다.
중앙 브레인은 Obsidian Agent다.
Graphify는 프로젝트별 구조 지도다.
전체 Obsidian Vault, 전체 RAW, 전체 legalize-kr 저장소를 무차별적으로 Graphify로 스캔하지 않는다.
5. GitHub와 Google Drive의 역할 분리

반드시 다음 역할을 유지하라.

GitHub Repo: obsidian-agent-brain-system
= 시스템 개발 저장소
= 문서, 프롬프트, 템플릿, 스크립트, 설정 예시, vault_scaffold, 운영 규칙 저장

Google Drive Folder: obsidian-agent-brain-system
= 실제 지식 저장소
= Obsidian Vault, RAW, 음성, 회의록, 고객 자료, 기존 Agent Room 자료, external_data 저장

GitHub에 커밋하면 안 되는 것:

실제 RAW 원본
음성 파일
고객 자료
계약서 원본
개인정보
API Key
.env
Google Drive 실제 Vault 전체
external_data/legalize-kr 전체 clone
Graphify 대용량 결과물
민감한 개인 메모

GitHub에 저장해도 되는 것:

시스템 문서
프롬프트
템플릿
스크립트
설정 예시
vault_scaffold
마이그레이션 도구
운영 규칙
Graphify 적용 문서
LegalizeKR 적용 문서
Claude Code / Codex 작업 가이드
6. 현재 작업은 “신규 구축”이 아니라 “안전 마이그레이션”이다

기존 Google Drive Obsidian Vault가 이미 있으므로 아래 행동은 금지한다.

vault_scaffold를 기존 Vault에 바로 복사하지 마라.
기존 00_System, 01_RAW, 04_Wiki, 10_AgentBus를 덮어쓰지 마라.
기존 CLAUDE.md, AGENTS.md, CODEX.md, codex.md를 삭제하지 마라.
기존 .obsidian 설정을 덮어쓰지 마라.
기존 AgentBus 작업 큐를 강제로 이동하지 마라.
기존 RAW 자료를 GitHub에 커밋하지 마라.
전체 Vault를 Graphify로 무차별 스캔하지 마라.
legalize-kr 전체 레포를 Vault 내부로 복사하지 마라.

대신 다음 순서를 지켜라.

1. 기존 Vault 감사
2. 기존 Claude Code / Codex 지침 수집
3. 기존 폴더 구조와 신규 표준 구조 비교
4. 충돌맵 작성
5. _MIGRATION_STAGING에 새 구조 후보 생성
6. SAFE_MERGE_LOG 작성
7. ROLLBACK_PLAN 작성
8. 실제 병합 전 보고
9. 필요한 항목만 단계적으로 병합
7. 우선 확인해야 할 파일

작업을 계속하기 전에 아래 파일을 먼저 확인하라.

00_System/AGENT_STATE.md
00_System/TASKS.md
00_System/HANDOFF_LOG.md
00_System/MASTER_PLAN.md

00_System/MIGRATION/VAULT_INVENTORY.md
00_System/MIGRATION/EXISTING_AGENT_INSTRUCTIONS.md
00_System/MIGRATION/CONFLICT_MAP.md
00_System/MIGRATION/MIGRATION_PLAN.md
00_System/MIGRATION/SAFE_MERGE_LOG.md
00_System/MIGRATION/ROLLBACK_PLAN.md
00_System/MIGRATION/MIGRATION_DECISIONS.md
00_System/MIGRATION/RAW_INDEX.md
00_System/MIGRATION/AGENTROOM_LEGACY_INDEX.md

파일이 없으면 새 계획을 만들지 말고, 현재 상태를 기준으로 누락 문서만 생성하라.

8. 현재 Claude Code의 역할

너는 현재 전체 작업을 진행 중인 주 작업자다.

단, 역할은 현재 AGENT_STATE.md에 기록된 상태를 우선한다.

기본적으로 너의 역할은 다음 중 하나다.

Coordinator
Migration Architect
Primary Implementer
Reviewer
Verifier

만약 네가 최초 실행자라면:

Coordinator / Migration Architect

역할을 맡고, 기존 Vault 감사와 안전 마이그레이션 구조를 우선한다.

만약 이미 Coordinator가 등록되어 있다면:

Reviewer / Implementer / Verifier

역할을 맡고, 기존 계획을 덮어쓰지 말고 보완하라.

9. 현재 해야 할 핵심 작업

새로운 아키텍처를 만들지 말고, 아래 본 계획에 맞춰 현재 작업을 계속하라.

A. 기존 Vault 안전 감사
기존 Obsidian Vault 구조 확인
기존 Claude Code / Codex 지침 확인
기존 AgentBus 확인
기존 RAW 확인
기존 Wiki / Project / Framework 구조 확인
민감 자료 경로 식별
기존 Agent Room 또는 기존 통합 시스템 흔적 확인
B. 충돌 없는 마이그레이션 준비
VAULT_INVENTORY.md 작성 또는 갱신
EXISTING_AGENT_INSTRUCTIONS.md 작성 또는 갱신
CONFLICT_MAP.md 작성 또는 갱신
MIGRATION_PLAN.md 작성 또는 갱신
SAFE_MERGE_LOG.md 작성 또는 갱신
ROLLBACK_PLAN.md 작성 또는 갱신
RAW_INDEX.md 작성 또는 갱신
AGENTROOM_LEGACY_INDEX.md 작성 또는 갱신
C. 새 표준 구조는 Staging에만 생성
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

기존 Vault에 같은 이름의 폴더나 파일이 이미 있으면 바로 병합하지 말고, _MIGRATION_STAGING 안에 제안 구조로만 생성하라.

D. 본 시스템의 3대 모듈을 정렬
Obsidian Agent Brain System
LegalizeKR Integration
Graphify Integration

이 세 가지는 서로 분리된 프로젝트가 아니다.
하나의 시스템 안에서 연결되어야 한다.

10. Graphify 적용 기준

Graphify는 다음 목적에만 사용한다.

프로젝트 구조 분석
코드/문서 연결 관계 파악
리팩토링 영향 범위 분석
Agent Room Legacy 일부 구조 분석
Claude Code / Codex 작업 전 Context Pack 보조

금지:

전체 Vault 스캔
전체 RAW 스캔
전체 legalize-kr 스캔
민감 자료 스캔
graph.json 전체를 프롬프트에 넣기
Graphify 결과만 보고 실제 코드 확인 없이 수정하기

Graphify는 프로젝트별 구조 지도다.
Obsidian Agent가 Graphify 결과를 읽고 Graphify Context Pack으로 압축한 뒤 Claude Code / Codex에게 전달해야 한다.

11. LegalizeKR 적용 기준

LegalizeKR는 다음 목적에 사용한다.

법령 검색
법령 요약
인테리어/건축/계약/개인정보/AI 서비스 관련 법령 Context Pack 생성

금지:

legalize-kr 전체 레포를 Vault 내부로 복사
전체 법령을 프롬프트에 넣기
기준일 없이 법령 판단하기
법령 원문과 요약을 혼동하기
commit hash만으로 법령 기준점 삼기

LegalizeKR는 외부 데이터 소스로 두고, Obsidian에는 법령 색인, 요약, Legal Context Pack, 프로젝트별 법령 판단 기록만 저장한다.

12. 작업 중 판단 기준

어떤 판단이 필요하면 아래 우선순위를 따른다.

1순위: 기존 Vault 보존
2순위: 현재 AGENT_STATE.md
3순위: 현재 TASKS.md
4순위: MIGRATION_PLAN.md
5순위: CONFLICT_MAP.md
6순위: 본 채팅방에서 정의된 3대 작업 축
7순위: 신규 아이디어

신규 아이디어가 떠오르더라도 바로 반영하지 말고 다음 위치에 제안으로만 기록하라.

00_System/MIGRATION/MIGRATION_DECISIONS.md
또는
00_System/TASKS.md의 Backlog
13. 충돌 방지 규칙

작업 전 반드시 다음을 확인하라.

00_System/LOCKS/
00_System/MIGRATION/SAFE_MERGE_LOG.md
00_System/MIGRATION/CONFLICT_MAP.md

충돌 가능성이 있는 작업은 lock을 먼저 만든다.

예시:

00_System/LOCKS/task-migration-audit.lock
00_System/LOCKS/task-graphify-integration.lock
00_System/LOCKS/task-legalizekr-integration.lock
00_System/LOCKS/task-agentbus-merge.lock

이미 lock이 있으면 해당 작업을 덮어쓰지 말고, 검토 또는 보완 문서 작성만 수행하라.

14. 기존 지침 처리 원칙

기존 Vault 안에 다음 파일이 있으면 반드시 보존하고 먼저 요약하라.

CLAUDE.md
AGENTS.md
CODEX.md
codex.md
.claude/
.codex/
prompts/
00_System/PROMPTS/

기존 지침을 바로 삭제하거나 새 지침으로 덮어쓰지 마라.

처리 방식:

1. 기존 지침 파일 경로 기록
2. 목적 요약
3. 충돌 가능성 확인
4. 유지 / 병합 / 분리 / Deprecated Candidate / Archive Candidate로 분류
5. EXISTING_AGENT_INSTRUCTIONS.md에 기록
6. 최종 결정은 MIGRATION_DECISIONS.md에 남김
15. RAW 자료 처리 원칙

기존 RAW 자료는 이동하지 않는다.
먼저 색인만 만든다.

기존 RAW 원본 이동 금지
기존 음성 파일 복사 금지
고객 자료 원문 복사 금지
민감 자료 GitHub 커밋 금지

처리 방식:

1. 경로만 기록
2. 자료 유형 분류
3. 민감도 표시
4. 마이그레이션 방식 제안
5. RAW_INDEX.md에 기록
16. 응답 또는 보고 방식

현재 작업을 계속하기 전에 다음 형식으로 짧게 현재 상태를 정렬해라.

# Plan Reminder Acknowledgement

## 1. 현재 개발의 본질
Obsidian Agent Brain System 안전 마이그레이션 및 3대 모듈 통합

## 2. 내가 새 계획을 만들지 않고 따라야 할 기존 계획
- Obsidian Agent Brain System
- LegalizeKR Integration
- Graphify Integration
- 기존 Google Drive Vault 보존
- GitHub / Google Drive 역할 분리
- Migration-safe 원칙

## 3. 현재 확인해야 할 파일
AGENT_STATE, TASKS, HANDOFF_LOG, MASTER_PLAN, MIGRATION 문서

## 4. 현재 내가 수행할 다음 행동
기존 작업을 중단하지 않고, 현재 상태 파일을 읽고 본 계획 기준으로 이어서 진행

## 5. 금지 사항
덮어쓰기, 삭제, 전체 Vault 무차별 스캔, RAW 커밋, 새 계획 생성
17. 작업 완료 또는 중간 보고 형식

작업 결과를 보고할 때는 다음 형식을 사용하라.

# obsidian-agent-brain-system 현재 작업 정렬 보고

## 1. 내 역할
Coordinator / Migration Architect / Primary Implementer / Reviewer / Verifier

## 2. 현재 개발의 본 계획
Obsidian Agent Brain System + LegalizeKR + Graphify + 기존 Vault 안전 마이그레이션

## 3. 확인한 현재 상태
- GitHub repo:
- Google Drive Vault:
- 기존 Claude/Codex 지침:
- 기존 AgentBus:
- 기존 RAW:
- 기존 Wiki/Project/Framework:

## 4. 확인한 주요 파일
- AGENT_STATE.md
- TASKS.md
- MASTER_PLAN.md
- HANDOFF_LOG.md
- VAULT_INVENTORY.md
- CONFLICT_MAP.md
- MIGRATION_PLAN.md

## 5. 현재까지 수행한 작업
요약

## 6. 새로 만들지 않고 유지한 기존 계획
요약

## 7. 충돌 위험
요약

## 8. 다음 작업
본 계획 기준으로 이어서 할 작업

## 9. 금지 사항 준수 여부
- 덮어쓰기 없음
- 삭제 없음
- 전체 Vault 스캔 없음
- RAW 커밋 없음
- 새 계획 생성 없음

## 10. 완료 여부
완료 / 부분 완료 / 진행 중 / 보류
18. 최종 리마인드

다시 강조한다.

너는 새로운 시스템을 새로 발명하는 것이 아니다.

너는 이미 정의된 다음 시스템을 구현 중이다.

Obsidian Agent Brain System
+ LegalizeKR 법령 지식베이스
+ Graphify 프로젝트 지식 그래프
+ Claude Code / Codex 개발 실행 도구
+ GitHub 버전 관리
+ Google Drive 실제 Vault 저장소

기존 Google Drive Obsidian Vault는 보존 대상이다.
GitHub는 시스템 개발 기준점이다.
마이그레이션은 덮어쓰기가 아니라 정렬, 흡수, 단계적 병합이다.