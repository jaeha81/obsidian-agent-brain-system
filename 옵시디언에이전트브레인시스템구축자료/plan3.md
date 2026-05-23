Google Drive 연결 정책 문서 생성

다음 파일을 생성하라.

docs/google_drive_vault_policy.md

내용은 다음 구조로 작성하라.

# Google Drive Vault Policy

## Purpose

Google Drive is used as the storage layer for the actual Obsidian Vault and RAW data.

## Folder Name

obsidian-agent-brain-system

## Recommended Structure

```txt
Google Drive/
  obsidian-agent-brain-system/
    ObsidianVault/
    RAW_IMPORT/
    external_data/
    backups/
    exports/
Role Separation

GitHub stores system code and templates.
Google Drive stores real knowledge data and sensitive materials.

Do Not Commit

The following should not be committed to GitHub:

RAW voice files
Customer data
Meeting recordings
Contracts
API keys
Personal notes
external_data/legalize-kr full clone
Large Graphify outputs
Obsidian Vault

The user should open the following folder as the Obsidian Vault:

Google Drive/obsidian-agent-brain-system/ObsidianVault

---

## 6. paths.example.json 생성

다음 파일을 생성하라.

```txt
configs/paths.example.json

내용:

{
  "github_repo": "obsidian-agent-brain-system",
  "google_drive_folder": "Google Drive/obsidian-agent-brain-system",
  "obsidian_vault": "Google Drive/obsidian-agent-brain-system/ObsidianVault",
  "raw_import": "Google Drive/obsidian-agent-brain-system/RAW_IMPORT",
  "external_data": "Google Drive/obsidian-agent-brain-system/external_data",
  "legalize_kr": "Google Drive/obsidian-agent-brain-system/external_data/legalize-kr",
  "graphify_selected": "Google Drive/obsidian-agent-brain-system/external_data/graphify_selected"
}

실제 사용자 로컬 경로는 커밋하지 말고, 이 파일은 예시로만 둔다.

7. init_vault_scaffold.sh 생성

다음 스크립트를 생성하라.

scripts/init_vault_scaffold.sh

역할:

vault_scaffold 구조를 실제 Google Drive의 ObsidianVault로 복사할 수 있게 한다.
기존 파일이 있으면 덮어쓰기 전에 확인 또는 skip 처리한다.
민감 자료는 건드리지 않는다.

기본 구조:

#!/usr/bin/env bash
set -e

SOURCE_DIR="./vault_scaffold"
TARGET_DIR="$1"

if [ -z "$TARGET_DIR" ]; then
  echo "Usage: ./scripts/init_vault_scaffold.sh /path/to/ObsidianVault"
  exit 1
fi

if [ ! -d "$SOURCE_DIR" ]; then
  echo "Source vault_scaffold not found."
  exit 1
fi

mkdir -p "$TARGET_DIR"

rsync -av --ignore-existing "$SOURCE_DIR/" "$TARGET_DIR/"

echo "Vault scaffold initialized at: $TARGET_DIR"
8. 초기 AGENT_STATE.md 작성

다음 파일을 작성하라.

vault_scaffold/00_System/AGENT_STATE.md

내용:

# Agent State

## System Name
Obsidian Agent Brain System

## Current Coordinator
Not assigned yet

## Active Agents

### Claude Code
- role:
- status:
- current_task:

### Codex
- role:
- status:
- current_task:

## Current Phase
Phase 0: Repository and Vault Scaffold Initialization

## Active Locks
None

## Last Updated
TBD

## Notes
GitHub repository and Google Drive folder have been created.
The next step is to initialize the repository scaffold and copy the vault scaffold into the Google Drive ObsidianVault folder.
9. 초기 MASTER_PLAN.md 작성

다음 파일을 작성하라.

vault_scaffold/00_System/MASTER_PLAN.md

내용:

# Master Plan

## System
Obsidian Agent Brain System

## Current Status
- GitHub repository created: obsidian-agent-brain-system
- Google Drive folder created: obsidian-agent-brain-system

## Main Modules

1. Obsidian Agent Brain System
2. LegalizeKR Integration
3. Graphify Integration
4. Claude Code / Codex Worker Flow
5. Discord / Voice Input Flow
6. GitHub Version Control Flow
7. Google Drive Vault Storage Flow

## Phase Plan

### Phase 0
Initialize GitHub repository scaffold and Google Drive Vault structure.

### Phase 1
Create Obsidian Agent core system folders.

### Phase 2
Create RAW intake and AgentBus flow.

### Phase 3
Create Context Pack system.

### Phase 4
Integrate Graphify as project knowledge graph layer.

### Phase 5
Integrate LegalizeKR as external legal knowledge base.

### Phase 6
Connect Claude Code and Codex worker reporting flow.

### Phase 7
Connect Discord / Voice input pipeline.

### Phase 8
Test end-to-end workflow.
10. 초기 TASKS.md 작성

다음 파일을 작성하라.

vault_scaffold/00_System/TASKS.md

내용:

# Tasks

## Backlog

- [ ] Clone GitHub repository locally
- [ ] Create repository scaffold
- [ ] Create .gitignore
- [ ] Create README.md
- [ ] Create vault_scaffold
- [ ] Create Google Drive Vault policy
- [ ] Create path config example
- [ ] Create init_vault_scaffold.sh
- [ ] Copy vault scaffold to Google Drive ObsidianVault
- [ ] Open ObsidianVault in Obsidian
- [ ] Add LegalizeKR integration files
- [ ] Add Graphify integration files
- [ ] Add Claude Code worker prompt
- [ ] Add Codex worker prompt
- [ ] Test AgentBus flow

## In Progress

## Completed

## Blocked
11. 작업 완료 후 보고 형식

작업이 끝나면 다음 형식으로 보고하라.

# obsidian-agent-brain-system 초기 세팅 보고

## 1. 내 역할
Coordinator / Reviewer / Implementer / Verifier

## 2. 확인한 상태
- GitHub repo:
- Google Drive folder:
- Local repo path:
- Obsidian Vault path:

## 3. 생성한 폴더
목록

## 4. 생성한 파일
목록

## 5. .gitignore 적용 여부
적용 / 미적용

## 6. Google Drive Vault 연결 방식
설명

## 7. 다음 작업
- Claude Code가 할 일
- Codex가 할 일
- 사용자가 할 일

## 8. 주의사항
민감 자료, RAW, API Key, external_data 커밋 금지

## 9. 완료 여부
완료 / 부분 완료 / 보류

이제 위 지침에 따라 obsidian-agent-brain-system 레포의 초기 구조를 세팅하라.


---

# 4. 지금 너의 실제 다음 액션

너는 이제 이렇게 진행하면 돼.

```txt
1. GitHub repo를 로컬에 clone
2. 클로드 코드에게 위 프롬프트 전달
3. 클로드 코드가 초기 구조 생성
4. 코덱스에게 같은 프롬프트 + “검토자 역할” 지시
5. Google Drive의 ObsidianVault에 scaffold 복사
6. Obsidian에서 해당 Vault 열기
7. 그다음 Graphify / LegalizeKR 적용