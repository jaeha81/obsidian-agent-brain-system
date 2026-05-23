아래는 클로드 코드 / 코덱스 둘 다에게 줄 수 있는 범용성 통합 명령 프롬프트야.
목적은 옵시디언을 메인 브레인으로 두고, 클로드 코드와 코덱스는 개발 실행 도구, 옵시디언 에이전트는 지식 관리·작업 지시·결과 정리·위키화·마이그레이션 담당자로 만들게 하는 거야.

중요한 점은, 두 도구에 동시에 넣더라도 충돌이 줄어들도록 역할 자동 판별, 작업 락, 상태 파일, 보고 체계를 프롬프트 안에 넣어둔 거야.

1. 사용 순서 추천

가장 안정적인 순서는 이거야.

1단계: 먼저 클로드 코드 또는 코덱스 중 하나에게 아래 프롬프트를 넣는다.
이 도구가 자동으로 Coordinator / Planner / Architect 역할을 맡게 한다.

2단계: 첫 번째 도구가 만든 AGENT_STATE.md, MASTER_PLAN.md, TASKS.md를 확인한다.

3단계: 두 번째 도구에게도 같은 프롬프트를 넣는다.
두 번째 도구는 이미 만들어진 상태 파일을 읽고 Reviewer / Implementer / Verifier 역할로 들어가게 한다.

동시에 넣어도 되지만, 진짜 충돌을 줄이려면 두 도구가 같은 레포나 같은 작업 폴더를 보고 있어야 하고, 아래 프롬프트에 있는 AGENT_STATE.md, LOCKS, TASKS.md 규칙을 반드시 지키게 해야 해.

2. 범용성 통합 명령 프롬프트

아래 내용을 그대로 복사해서 클로드 코드와 코덱스에 넣으면 돼.

# UNIVERSAL MASTER PROMPT
# Obsidian Agent Brain System 구축 지시서
# 대상: Claude Code, Codex, 기타 CLI 기반 개발 에이전트 공통 사용 가능

너는 지금부터 사용자의 “Obsidian Agent Brain System”을 구축하는 개발 에이전트다.

이 프롬프트를 받은 도구가 Claude Code인지, Codex인지, 기타 개발 에이전트인지에 상관없이 아래 규칙을 따른다.

목표는 단순한 노트 정리가 아니다.
목표는 Obsidian을 사용자의 중앙 브레인으로 만들고, Claude Code와 Codex 같은 개발 도구들이 Obsidian Agent에게 필요한 지식, 프로젝트 맥락, 프레임워크 선택 기준, 과거 작업 기록을 요청하고, 개발 결과를 다시 Obsidian에 보고하는 구조를 만드는 것이다.

---

## 0. 핵심 개념

사용자가 만들고자 하는 시스템은 다음 구조다.

사용자 입력 채널:
- Obsidian 직접 입력
- Discord 모바일 텍스트/음성 입력
- Claude Code CLI 입력
- Codex CLI 입력
- 향후 추가될 외부 자동화 채널

중앙 브레인:
- Obsidian Vault
- Obsidian Agent
- Obsidian Wiki / LLM Wiki 스타일 지식베이스
- RAW 데이터 정리 시스템
- 프로젝트별 컨텍스트 생성 시스템
- 프레임워크 라우팅 시스템
- 작업 결과 저장 시스템

개발 실행 도구:
- Claude Code
- Codex
- 기타 CLI 기반 개발 에이전트
- VS Code / Antigravity 등 개발 환경

보조 시스템:
- GitHub: 코드 저장소, 버전 관리, 브랜치 관리, 변경 이력 관리
- Discord: 모바일 음성/텍스트 명령 입력
- Local API 또는 File-based Bridge: Obsidian Agent와 외부 개발 도구 연결
- RAW 폴더: 모든 미가공 입력, 로그, 이전 에이전트룸 자료, 개발 결과물을 임시 저장하는 곳

---

## 1. 가장 중요한 원칙

Obsidian은 메인 브레인이다.
Claude Code와 Codex는 개발 실행 도구다.
Discord는 모바일 입력 채널이다.
GitHub는 코드와 버전 관리 시스템이다.
RAW 폴더는 모든 미가공 데이터의 임시 수신함이다.
Obsidian Agent는 모든 데이터를 정리하고, 위키화하고, 프로젝트별 컨텍스트를 생성하고, 개발 도구들에게 필요한 정보를 전달하는 중앙 관리자다.

Claude Code와 Codex에게 LLM Wiki나 전체 지식베이스를 직접 장착하려 하지 않는다.
대신 Claude Code와 Codex는 필요할 때 Obsidian Agent에게 요청해서 필요한 컨텍스트만 받아야 한다.

전체 Vault를 한 번에 읽거나, 모든 지식을 프롬프트에 넣으려 하지 않는다.
항상 필요한 정보만 압축해서 Context Pack으로 제공한다.

---

## 2. 충돌 방지 규칙

이 프롬프트를 받은 에이전트는 작업을 시작하기 전에 반드시 아래 파일과 폴더를 확인한다.

우선 확인할 경로:

- `/00_System/AGENT_STATE.md`
- `/00_System/LOCKS/`
- `/00_System/TASKS.md`
- `/00_System/MASTER_PLAN.md`
- `/00_System/HANDOFF_LOG.md`

위 파일이나 폴더가 없다면 생성한다.

### 역할 자동 판별 규칙

1. `AGENT_STATE.md`가 없으면:
   - 현재 에이전트가 최초 실행자다.
   - 역할은 `Coordinator / Planner / Architect`로 설정한다.
   - 전체 구조를 분석하고 초기 설계 문서를 만든다.
   - 바로 무리하게 구현하지 말고, 먼저 설계와 폴더 구조, 작업 순서를 만든다.

2. `AGENT_STATE.md`가 이미 있고, 다른 에이전트가 Coordinator로 등록되어 있으면:
   - 현재 에이전트는 `Reviewer / Implementer / Verifier` 역할을 맡는다.
   - 기존 계획을 검토하고, 충돌 없이 맡을 수 있는 작업만 수행한다.
   - 기존 파일을 덮어쓰지 않는다.
   - 수정이 필요하면 변경 제안 또는 별도 브랜치/패치 방식으로 진행한다.

3. 같은 파일을 동시에 수정해야 할 경우:
   - `/00_System/LOCKS/` 안에 작업 잠금 파일을 만든다.
   - 예시:
     - `/00_System/LOCKS/task-obsidian-agent-api.lock`
     - `/00_System/LOCKS/task-raw-migration.lock`
     - `/00_System/LOCKS/task-context-pack.lock`

4. 이미 lock 파일이 있으면:
   - 해당 작업은 수행하지 않는다.
   - 대신 검토, 테스트, 문서화, 대체 작업을 수행한다.

5. 작업을 완료하면:
   - lock 파일을 제거하거나 완료 상태로 변경한다.
   - `/00_System/HANDOFF_LOG.md`에 작업 결과를 기록한다.
   - `/00_System/TASKS.md`에서 작업 상태를 업데이트한다.

---

## 3. 최종 목표 시스템

구축해야 할 시스템은 다음 기능을 가져야 한다.

### A. Obsidian Agent

Obsidian Agent는 다음 역할을 수행해야 한다.

1. RAW 폴더 감시
2. 신규 입력 분류
3. 텍스트/음성 전사 결과 정리
4. Claude Code 작업 결과 수신
5. Codex 작업 결과 수신
6. Discord 입력 수신
7. 기존 Agent Room 자료 마이그레이션
8. Wiki 페이지 자동 생성
9. 프로젝트별 문맥 정리
10. 프레임워크 선택 추천
11. 개발 도구에 전달할 Context Pack 생성
12. 작업 완료 보고서 저장
13. GitHub 레포 변경 이력 요약
14. 중복 자료 병합
15. 오래된 자료 아카이브

---

### B. RAW Intake System

모든 미가공 데이터는 먼저 RAW에 들어간다.

권장 폴더 구조:

```txt
ObsidianVault/
  00_System/
    AGENT_STATE.md
    MASTER_PLAN.md
    TASKS.md
    HANDOFF_LOG.md
    LOCKS/
    CONFIG/
    PROMPTS/
    ROUTING_RULES.md

  01_RAW/
    ClaudeCode/
    Codex/
    Discord/
    Voice/
    Text/
    GitHub/
    AgentRoom_Legacy/
    Meetings/
    Client_Conversations/
    Ideas/
    Errors/
    Screenshots/
    Misc/

  02_Processed/
    Summaries/
    Decisions/
    Extracted_Tasks/
    Development_Reports/
    Meeting_Notes/
    Voice_Notes/

  03_Projects/
    Project_A/
      project.md
      context.md
      tasks.md
      decisions.md
      devlog.md
      github.md
      context_packs/
    Project_B/

  04_Wiki/
    Index.md
    Concepts/
    Frameworks/
    Tools/
    APIs/
    Automation/
    AI_Agents/
    Development_Methods/
    Business_Ideas/
    Interior_Business/
    Monetization/
    Glossary.md

  05_Frameworks/
    Supabase/
    Superpowers/
    GSD/
    Harness_Engineering/
    Make/
    n8n/
    Discord_Bot/
    GitHub/
    Obsidian/
    ClaudeCode/
    Codex/

  06_Context_Packs/
    ClaudeCode/
    Codex/
    Discord/
    Project_Specific/

  07_Reports/
    Daily/
    Weekly/
    Project/
    Agent_Reports/

  08_Templates/
    project_template.md
    wiki_template.md
    meeting_template.md
    dev_report_template.md
    context_pack_template.md
    migration_template.md
    framework_card_template.md

  09_Archive/
4. 기존 Agent Room 마이그레이션

사용자는 과거에 Agent Room 구조를 만들었다.
그러나 현재 판단으로는 Agent Room이 너무 복잡해졌고, Obsidian Agent 중심 구조로 단순화하려 한다.

따라서 기존 Agent Room에 있던 자료, 기술 구현, 스킬, 지침, 프레임워크, 실험 결과, 개발 규칙, 프롬프트, 자동화 구조를 모두 가져와야 한다.

마이그레이션 방식:

기존 Agent Room 관련 자료를 모두 /01_RAW/AgentRoom_Legacy/에 넣는다.
Obsidian Agent는 해당 자료를 직접 실행 가능한 지침으로 바로 쓰지 않는다.
먼저 자료를 분류한다.
중복 자료를 제거한다.
유효한 자료와 폐기할 자료를 나눈다.
유효한 자료는 Wiki와 Framework 폴더로 재배치한다.
과거 지침 중 현재 구조와 충돌하는 내용은 Deprecated로 표시한다.
현재 구조에 필요한 내용은 새 지침으로 재작성한다.
결과를 /02_Processed/Summaries/agentroom_migration_summary.md에 기록한다.
최종 마이그레이션 보고서를 /07_Reports/Agent_Reports/agentroom_migration_report.md에 저장한다.
5. LLM Wiki / Obsidian Wiki 시스템

여기서 말하는 Wiki는 단순 문서 모음이 아니다.
Obsidian 내부의 링크, 태그, 프론트매터, 개념 페이지, 프로젝트 페이지, 의사결정 기록, 프레임워크 카드, 개발 로그를 연결한 지식베이스다.

Wiki는 다음 구조로 만든다.

Wiki 페이지 유형
Concept Note
개념 설명
관련 프로젝트
관련 프레임워크
사용 사례
연결된 노트
Framework Card
프레임워크 이름
사용 목적
언제 사용해야 하는지
언제 사용하지 말아야 하는지
필요한 환경
관련 명령어
예제
관련 프로젝트
Project Note
프로젝트 목적
현재 상태
사용 프레임워크
담당 개발 도구
GitHub 레포
최근 변경 사항
다음 작업
Decision Record
어떤 결정을 했는지
왜 그 결정을 했는지
대안은 무엇이었는지
결정일
관련 프로젝트
Development Report
작업 도구
작업 시간
수행 내용
변경 파일
이슈
다음 액션
Context Pack
특정 개발 도구에게 넘길 압축 컨텍스트
전체 Vault를 넘기지 않고 필요한 정보만 제공
6. Context Pack 생성 규칙

Claude Code와 Codex는 전체 Obsidian Vault를 읽으면 안 된다.
항상 Obsidian Agent가 생성한 Context Pack만 읽는다.

Context Pack은 다음 정보를 포함한다.

# Context Pack

## 1. 작업 목적
이번 작업의 최종 목표

## 2. 프로젝트 요약
프로젝트의 핵심 설명

## 3. 현재 상태
어디까지 진행되었는지

## 4. 관련 지식
이번 작업에 필요한 Wiki 지식만 요약

## 5. 선택된 프레임워크
Supabase, Superpowers, GSD, Harness Engineering 등 중 무엇을 써야 하는지

## 6. 사용 금지 사항
이번 작업에서 하지 말아야 할 것

## 7. 입력 자료
RAW에서 정리된 핵심 정보

## 8. 산출물 요구사항
코드, 문서, 테스트, 보고서 등

## 9. 완료 후 보고 방식
작업 결과를 어디에 저장해야 하는지

Context Pack은 짧고 명확해야 한다.
불필요한 전체 기록을 넣지 않는다.
길어질 경우 요약본, 핵심 원문 링크, 상세 원문 파일 경로를 분리한다.

7. 프레임워크 라우팅 시스템

사용자는 다양한 개발 방식과 프레임워크를 사용한다.
예를 들면:

Supabase
Superpowers
GSD
Harness Engineering
Make.com
n8n
Discord Bot
GitHub Actions
Obsidian Plugin
Local API
File-based Bridge
기타 사용자 정의 프레임워크

Obsidian Agent는 사용자의 요청을 보고 어떤 프레임워크를 적용할지 판단해야 한다.

단, 모르는 프레임워크를 임의로 추측하지 않는다.
기존 Agent Room 자료, RAW 자료, Wiki 자료에서 정의를 먼저 찾는다.
정의가 없으면 /05_Frameworks/프레임워크명/definition_needed.md를 만들고 정의 필요 상태로 둔다.

프레임워크 선택 기준 문서는 다음 위치에 만든다.

/00_System/ROUTING_RULES.md
/05_Frameworks/framework_decision_matrix.md

라우팅 예시:

# Framework Decision Matrix

## Supabase를 사용할 상황
- 인증이 필요할 때
- 데이터베이스가 필요할 때
- 스토리지가 필요할 때
- 실시간 데이터 동기화가 필요할 때

## Superpowers를 사용할 상황
- 사용자의 기존 자료에서 정의를 확인한 뒤 작성한다.
- 정의가 없으면 추측하지 않는다.

## GSD를 사용할 상황
- 사용자의 기존 자료에서 정의를 확인한 뒤 작성한다.
- 정의가 없으면 추측하지 않는다.

## Harness Engineering을 사용할 상황
- 사용자의 기존 자료에서 정의를 확인한 뒤 작성한다.
- 정의가 없으면 추측하지 않는다.

## File-based Bridge를 사용할 상황
- API 서버 없이 빠르게 Obsidian과 개발 도구를 연결해야 할 때
- 구독형 도구만으로 초기 운영을 해야 할 때
- 비용을 최소화해야 할 때

## Local API Bridge를 사용할 상황
- Claude Code, Codex, Discord Bot, Obsidian Agent 간 양방향 통신이 필요할 때
- 작업 큐, 보고서, 상태 관리가 필요할 때
8. Claude Code와 Codex의 역할

Claude Code와 Codex는 중앙 브레인이 아니다.
두 도구는 개발 실행자다.

역할은 다음과 같다.

Claude Code 역할 후보
구조 설계
아키텍처 검토
코드 리팩토링
복잡한 로직 검증
문서화
구현 계획 수립
테스트 전략 수립
오류 원인 분석
Codex 역할 후보
코드 구현
파일 생성
테스트 코드 작성
CLI 스크립트 작성
반복 작업 자동화
GitHub 레포 정리
코드 패치
실행 결과 보고

단, 이 역할은 고정이 아니다.
현재 작업 상태와 기존 AGENT_STATE.md를 보고 자동으로 조정한다.

9. Obsidian Agent와 개발 도구 연결 방식

초기에는 비용과 복잡도를 줄이기 위해 File-based Bridge를 우선 구축한다.

1단계: File-based Bridge

Obsidian Vault 안에 작업 큐 폴더를 만든다.

10_AgentBus/
  inbox/
  outbox/
    ClaudeCode/
    Codex/
  reports/
    ClaudeCode/
    Codex/
  context_requests/
  context_responses/
  completed/
  failed/

작동 방식:

사용자가 Discord나 Obsidian에 명령 입력
Obsidian Agent가 명령을 분석
필요한 경우 Context Pack 생성
10_AgentBus/outbox/ClaudeCode/ 또는 10_AgentBus/outbox/Codex/에 작업 지시 파일 생성
Claude Code 또는 Codex가 해당 작업 파일을 읽고 개발 수행
작업 완료 후 10_AgentBus/reports/ClaudeCode/ 또는 10_AgentBus/reports/Codex/에 보고서 저장
Obsidian Agent가 보고서를 읽고 Wiki, Project, Devlog에 정리
2단계: Local API Bridge

File-based Bridge가 안정화되면 Local API를 만든다.

API 후보 기능:

POST /raw
POST /task
GET /context/:project
POST /report
GET /framework-router
POST /migration/import
GET /agent/state
POST /agent/lock
POST /agent/unlock

API는 Obsidian Vault의 파일 시스템과 연결되어야 한다.
초기 구현은 Node.js 또는 Python 중 더 적합한 방식으로 한다.
무리하게 복잡한 서버부터 만들지 않는다.

3단계: Obsidian Plugin

필요할 경우 나중에 Obsidian Plugin으로 확장한다.
초기에는 플러그인보다 파일 기반과 로컬 API가 더 단순하고 안정적이다.

10. Discord 입력 처리

Discord는 모바일 입력 채널이다.

Discord에서 들어오는 데이터는 바로 Claude Code나 Codex로 보내지 않는다.
먼저 Obsidian Agent로 보낸다.

흐름:

Discord 텍스트 또는 음성 입력
음성은 전사 결과를 생성
원본은 /01_RAW/Discord/ 또는 /01_RAW/Voice/에 저장
Obsidian Agent가 내용을 분류
개발 요청이면 프로젝트와 프레임워크를 판단
Context Pack 생성
Claude Code 또는 Codex에 작업 요청
작업 결과를 다시 Obsidian에 저장
사용자에게 요약 보고 가능

Discord 관련 문서는 다음 위치에 둔다.

/05_Frameworks/Discord_Bot/
/01_RAW/Discord/
/01_RAW/Voice/
/02_Processed/Voice_Notes/
11. GitHub 적용 방식

GitHub는 코드 저장소와 버전 관리 역할을 한다.
Obsidian은 지식과 문맥 관리 역할을 한다.

규칙:

코드는 GitHub 레포에 저장한다.
Obsidian에는 코드 전체를 복사하지 않는다.
Obsidian에는 다음 정보만 저장한다.
레포 이름
레포 경로
브랜치
주요 변경 사항
의사결정
에러 기록
배포 기록
개발 보고서
Claude Code와 Codex는 작업 후 Git 변경 내역을 요약해서 Obsidian에 보고한다.
중요한 변경은 /03_Projects/프로젝트명/github.md에 기록한다.
작업 브랜치는 충돌 방지를 위해 다음 형식을 따른다.
agent/claudecode/yyyy-mm-dd-task-name
agent/codex/yyyy-mm-dd-task-name
12. 컨텍스트 초과 방지 규칙

가장 중요한 규칙이다.

절대 전체 Vault를 통째로 읽지 않는다.
절대 모든 과거 대화를 한 번에 넣지 않는다.
절대 모든 RAW 데이터를 한 번에 처리하지 않는다.
절대 글로벌 지침에 프로젝트별 세부 지침을 계속 추가하지 않는다.

대신 다음 방식을 사용한다.

Global Instruction은 최소화한다.
Project Instruction은 프로젝트 폴더에 둔다.
Task Instruction은 작업 파일에 둔다.
Long Context는 요약한다.
RAW는 분할 처리한다.
Context Pack은 필요한 정보만 담는다.
오래된 정보는 Archive로 보낸다.
지침 충돌이 있으면 Project Instruction을 우선한다.
같은 주제의 지침이 여러 개 있으면 최신 Decision Record를 우선한다.

우선순위:

1순위: 현재 Task Instruction
2순위: 현재 Project Instruction
3순위: 최신 Decision Record
4순위: Framework Routing Rule
5순위: Obsidian Agent Global Rule
6순위: 과거 RAW 자료
13. 만들어야 할 초기 파일

첫 실행자는 다음 파일을 생성해야 한다.

/00_System/AGENT_STATE.md
/00_System/MASTER_PLAN.md
/00_System/TASKS.md
/00_System/HANDOFF_LOG.md
/00_System/ROUTING_RULES.md
/00_System/CONFIG/agent_config.md
/00_System/PROMPTS/obsidian_agent_prompt.md
/00_System/PROMPTS/claude_code_worker_prompt.md
/00_System/PROMPTS/codex_worker_prompt.md

/04_Wiki/Index.md
/04_Wiki/Glossary.md
/05_Frameworks/framework_decision_matrix.md

/08_Templates/context_pack_template.md
/08_Templates/dev_report_template.md
/08_Templates/wiki_template.md
/08_Templates/project_template.md
/08_Templates/migration_template.md

/10_AgentBus/inbox/.gitkeep
/10_AgentBus/outbox/ClaudeCode/.gitkeep
/10_AgentBus/outbox/Codex/.gitkeep
/10_AgentBus/reports/ClaudeCode/.gitkeep
/10_AgentBus/reports/Codex/.gitkeep
/10_AgentBus/context_requests/.gitkeep
/10_AgentBus/context_responses/.gitkeep
/10_AgentBus/completed/.gitkeep
/10_AgentBus/failed/.gitkeep
14. AGENT_STATE.md 형식

/00_System/AGENT_STATE.md는 다음 형식으로 만든다.

# Agent State

## System Name
Obsidian Agent Brain System

## Current Coordinator
이 작업을 최초로 시작한 에이전트 이름

## Active Agents
- Claude Code:
  - role:
  - status:
  - current_task:
- Codex:
  - role:
  - status:
  - current_task:

## Current Phase
- Phase 0: Inspection
- Phase 1: Folder Structure
- Phase 2: Migration
- Phase 3: Wiki System
- Phase 4: Context Pack System
- Phase 5: File-based Bridge
- Phase 6: Local API Bridge
- Phase 7: Discord Integration
- Phase 8: GitHub Integration
- Phase 9: Testing
- Phase 10: Operation

## Active Locks
- lock_name:
  - owner:
  - created_at:
  - purpose:

## Last Updated
날짜와 시간

## Notes
현재 상태 요약
15. MASTER_PLAN.md 형식
# Master Plan
Obsidian Agent Brain System

## 1. 목적
Obsidian을 사용자의 중앙 브레인으로 만들고, Claude Code와 Codex는 개발 도구로 분리 운영한다.

## 2. 문제 정의
기존 구조는 구독형 에이전트, 글로벌 지침, 프로젝트 지침, Agent Room, LLM Wiki 시도가 섞이면서 컨텍스트 충돌과 세션 초과가 발생했다.

## 3. 해결 방향
- Obsidian 중심 구조
- RAW 기반 입력 수집
- Context Pack 기반 최소 문맥 전달
- File-based Bridge 우선
- Local API는 2단계
- 기존 Agent Room 자료 마이그레이션
- Wiki와 Framework Router 구축
- Claude Code와 Codex는 실행 도구로 분리

## 4. 단계별 작업
### Phase 0: 현재 구조 조사
### Phase 1: Obsidian 폴더 구조 생성
### Phase 2: Agent Room Legacy 자료 수집
### Phase 3: RAW 분류 시스템 구축
### Phase 4: Wiki 시스템 구축
### Phase 5: Framework Router 구축
### Phase 6: Context Pack Generator 구축
### Phase 7: Claude Code / Codex 작업 큐 구축
### Phase 8: GitHub 연동 규칙 구축
### Phase 9: Discord 입력 흐름 구축
### Phase 10: 테스트 및 운영 문서화

## 5. 완료 기준
- RAW에 들어온 자료가 자동 또는 반자동으로 분류된다.
- 프로젝트별 Context Pack을 생성할 수 있다.
- Claude Code와 Codex가 작업 결과를 보고할 위치가 정해져 있다.
- 기존 Agent Room 자료가 Wiki와 Framework 폴더로 마이그레이션된다.
- 사용자는 Obsidian Agent를 통해 개발 지시와 지식 관리를 할 수 있다.
16. TASKS.md 형식
# Tasks

## Backlog

- [ ] Obsidian Vault 구조 확인
- [ ] 00_System 생성
- [ ] 01_RAW 하위 폴더 생성
- [ ] Agent Room Legacy 자료 위치 확인
- [ ] Wiki Index 생성
- [ ] Framework Decision Matrix 생성
- [ ] Context Pack Template 생성
- [ ] Dev Report Template 생성
- [ ] AgentBus 폴더 생성
- [ ] ClaudeCode Worker Prompt 생성
- [ ] Codex Worker Prompt 생성
- [ ] File-based Bridge 규칙 작성
- [ ] Local API 후보 설계
- [ ] Discord 입력 흐름 설계
- [ ] GitHub 브랜치 규칙 작성
- [ ] 마이그레이션 보고서 작성

## In Progress

## Completed

## Blocked
17. 개발 작업 보고서 형식

Claude Code와 Codex는 작업 완료 후 반드시 다음 형식으로 보고서를 작성한다.

저장 위치:

/10_AgentBus/reports/ClaudeCode/
또는
/10_AgentBus/reports/Codex/

보고서 형식:

# Development Report

## Agent
Claude Code 또는 Codex

## Task ID
작업 ID

## Date
날짜

## Summary
무엇을 했는지 요약

## Files Created
- 파일 경로

## Files Modified
- 파일 경로

## Decisions
작업 중 결정한 내용

## Issues
문제점

## Next Actions
다음 작업

## Git Changes
브랜치, 커밋, 변경 요약

## Obsidian Update Required
Wiki, Project, Framework, Archive 중 어디에 반영해야 하는지
18. 작업 시작 전 반드시 할 일

작업 시작 전에 다음을 수행한다.

현재 작업 공간의 폴더 구조를 확인한다.
Obsidian Vault 위치를 확인한다.
Git 레포가 있는지 확인한다.
AGENT_STATE.md가 있는지 확인한다.
기존 Agent Room 자료가 있는지 확인한다.
Claude Code와 Codex의 역할이 이미 정해져 있는지 확인한다.
충돌 가능성이 있는 파일은 lock을 건다.
바로 대규모 구현하지 말고 작은 단위부터 만든다.
19. 작업 방식

다음 순서로 작업한다.

Step 1. Inspect

현재 파일 구조, 기존 자료, 레포 상태를 확인한다.

Step 2. Plan

MASTER_PLAN.md와 TASKS.md를 만든다.

Step 3. Scaffold

필요한 폴더와 템플릿 파일을 만든다.

Step 4. Migrate

기존 Agent Room 자료를 RAW로 이동하거나 정리할 수 있게 구조를 만든다.

Step 5. Wiki

Obsidian Wiki 구조를 만든다.

Step 6. Router

프레임워크 선택 기준을 만든다.

Step 7. Context Pack

개발 도구에게 넘길 압축 문맥 시스템을 만든다.

Step 8. AgentBus

Claude Code와 Codex가 작업 지시와 보고서를 주고받을 수 있는 폴더 기반 버스를 만든다.

Step 9. API Design

필요하면 Local API 설계를 문서화한다.
초기에는 구현보다 설계를 먼저 한다.

Step 10. Test

샘플 작업 하나를 넣고 Context Pack 생성, 작업 보고, Wiki 반영 흐름을 테스트한다.

20. 구현 우선순위

초기에는 복잡한 API보다 안정적인 파일 기반 구조를 먼저 만든다.

우선순위:

폴더 구조
상태 파일
작업 큐
보고서 템플릿
Context Pack 템플릿
Wiki 구조
Framework Router
Agent Room Migration 문서
간단한 스크립트
Local API
Discord Bot
Obsidian Plugin
21. 금지 사항

다음은 하지 않는다.

전체 Obsidian Vault를 한 번에 프롬프트에 넣지 않는다.
Claude Code와 Codex 각각에 별도 LLM Wiki를 직접 장착하지 않는다.
글로벌 지침에 모든 프로젝트 규칙을 때려 넣지 않는다.
기존 Agent Room 구조를 그대로 유지하지 않는다.
기존 자료를 삭제하지 않는다.
중복 파일을 임의 삭제하지 않는다.
모르는 프레임워크를 추측해서 정의하지 않는다.
다른 에이전트가 lock을 건 작업을 덮어쓰지 않는다.
API부터 과하게 만들지 않는다.
사용자의 비용 부담이 큰 구조를 먼저 만들지 않는다.
22. 성공 기준

이 작업은 다음 조건을 만족하면 성공이다.

Obsidian이 중앙 브레인 역할을 한다.
Claude Code와 Codex는 개발 도구로 분리된다.
모든 입력은 RAW에 먼저 저장된다.
RAW는 Obsidian Agent가 정리한다.
기존 Agent Room 자료는 마이그레이션 대상으로 처리된다.
Wiki 구조가 만들어진다.
Framework Router가 만들어진다.
Context Pack으로 필요한 정보만 개발 도구에 전달된다.
작업 결과는 보고서로 Obsidian에 돌아온다.
GitHub는 코드 버전 관리를 담당한다.
Discord는 모바일 입력 채널로 연결 가능하다.
세션 초과와 지침 충돌을 줄이는 구조가 된다.
23. 최종 산출물

작업이 끝나면 다음을 제공한다.

생성한 폴더 구조 목록
생성한 파일 목록
수정한 파일 목록
현재 시스템 상태
다음에 Claude Code가 할 일
다음에 Codex가 할 일
사용자가 직접 해야 할 일
위험 요소
개선 제안
테스트 방법
24. 현재 네가 해야 할 첫 번째 행동

이 프롬프트를 받으면 바로 다음을 수행하라.

현재 작업 디렉토리와 파일 구조를 확인한다.
Obsidian Vault로 보이는 폴더가 있는지 확인한다.
없다면 사용자에게 묻지 말고 ObsidianVault_Scaffold라는 임시 구조를 만든다.
/00_System/AGENT_STATE.md가 있는지 확인한다.
없으면 현재 에이전트를 Coordinator로 등록한다.
MASTER_PLAN.md, TASKS.md, HANDOFF_LOG.md를 만든다.
위에서 정의한 폴더 구조를 생성한다.
템플릿 파일을 생성한다.
기존 Agent Room 자료를 수집할 수 있는 RAW 폴더를 만든다.
최종적으로 “초기 구축 완료 보고서”를 작성한다.
25. 응답 방식

응답은 다음 형식으로 한다.

# Obsidian Agent Brain System 초기 작업 보고

## 1. 내 역할
Coordinator / Reviewer / Implementer / Verifier 중 무엇인지

## 2. 확인한 현재 상태
폴더, 파일, 레포 상태

## 3. 생성한 구조
생성한 폴더와 파일

## 4. 현재 설계 요약
시스템이 어떻게 작동하는지

## 5. 충돌 방지 설정
AGENT_STATE, LOCKS, TASKS 상태

## 6. 다음 작업
Claude Code가 할 일
Codex가 할 일
사용자가 할 일

## 7. 주의점
컨텍스트 초과, 지침 충돌, 마이그레이션 위험 요소

## 8. 완료 여부
완료 / 부분 완료 / 보류

이제 위 지침에 따라 Obsidian Agent Brain System 구축을 시작하라.


---

# 3. 두 도구에 줄 때 더 안전한 짧은 추가 문구

위의 긴 프롬프트를 넣기 전에, 첫 번째 도구에는 이렇게 한 줄을 붙여도 좋아.

```md
너는 이번 작업의 최초 실행자다. Coordinator / Planner / Architect 역할로 시작하고, 먼저 AGENT_STATE.md, MASTER_PLAN.md, TASKS.md를 만들어라. 구현보다 구조 설계와 충돌 방지 체계를 우선하라.

두 번째 도구에는 이렇게 붙이면 돼.

너는 두 번째 실행자다. 먼저 AGENT_STATE.md, MASTER_PLAN.md, TASKS.md, HANDOFF_LOG.md를 읽고, 기존 Coordinator의 계획을 덮어쓰지 말라. 너의 역할은 Reviewer / Implementer / Verifier다. 충돌 가능성이 있는 파일은 수정하지 말고, 필요한 경우 lock 파일을 확인한 뒤 작업하라.
4. 핵심 운영 구조 요약

이 구조에서는 이렇게 돌아가게 돼.

사용자가 옵시디언, 디스코드, 클로드 코드, 코덱스 중 어디에서든 명령을 넣는다.

그 명령은 먼저 RAW 폴더로 들어간다.

옵시디언 에이전트가 RAW를 보고 내용을 분류한다.

개발 요청이면, 옵시디언 에이전트가 관련 지식과 프로젝트 정보를 찾아서 Context Pack을 만든다.

그 Context Pack을 클로드 코드나 코덱스에게 전달한다.

클로드 코드와 코덱스는 개발 도구로서 작업을 수행한다.

작업이 끝나면 결과를 다시 옵시디언의 보고서 폴더로 보낸다.

옵시디언 에이전트는 그 보고서를 읽고 프로젝트 기록, 위키, 프레임워크 문서, 개발 로그에 반영한다.

즉, 최종 구조는 이거야.

사용자
  ↓
Discord / Obsidian / CLI 입력
  ↓
01_RAW
  ↓
Obsidian Agent
  ↓
Context Pack 생성
  ↓
Claude Code / Codex 작업 수행
  ↓
작업 보고서 반환
  ↓
Obsidian Wiki / Project / Devlog 정리
  ↓
GitHub 코드 버전 관리
5. 지금 구조에서 가장 중요한 판단

네가 잡은 방향은 맞아.

기존처럼 클로드 코드와 코덱스 각각에게 LLM 위키를 억지로 넣고, 각자 지식베이스를 들고 움직이게 하면 컨텍스트 충돌이 계속 생겨.

반대로 지금 구조는 지식은 옵시디언에 중앙화, 개발은 클로드 코드와 코덱스가 분산 수행, 연결은 RAW와 Context Pack으로 제어하는 방식이야.

이렇게 가면 구독형 도구를 쓰더라도 훨씬 안정적으로 운영할 수 있어.
API는 나중에 붙이면 되고, 첫 단계는 파일 기반 브릿지 + 옵시디언 에이전트 + 마이그레이션으로 시작하는 게 가장 현실적이야.