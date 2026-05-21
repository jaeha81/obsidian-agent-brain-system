현재 상태는 이렇게 정리하면 돼.

GitHub Repo:
obsidian-agent-brain-system
→ 개발 기준 저장소 / 클로드 코드·코덱스 공동 작업 공간

Google Drive Folder:
obsidian-agent-brain-system
→ 실제 옵시디언 Vault / RAW 자료 / 음성·문서·마이그레이션 자료 보관소

중요한 운영 원칙은 이거야.

GitHub = 코드, 스크립트, 템플릿, 시스템 설계, 문서화
Google Drive = 실제 지식 데이터, RAW 자료, 음성, 고객 자료, 옵시디언 Vault

즉, GitHub에는 뼈대와 자동화 로직을 올리고, Google Drive에는 실제 데이터와 옵시디언 지식베이스를 둔다고 보면 돼.

1. 추천 폴더 구조
Google Drive 쪽

Google Drive에 만든 obsidian-agent-brain-system 폴더 안에는 이렇게 잡는 게 좋아.

Google Drive/
  obsidian-agent-brain-system/
    ObsidianVault/
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

    RAW_IMPORT/
      Voice/
      Discord/
      Meetings/
      Client/
      AgentRoom_Legacy/

    external_data/
      legalize-kr/
      graphify_selected/

    backups/
    exports/

여기서 핵심은 ObsidianVault야.
옵시디언에서 이 폴더를 Vault로 열면 돼.

GitHub 레포 쪽

GitHub 레포는 이렇게 잡으면 돼.

obsidian-agent-brain-system/
  README.md
  .gitignore

  docs/
    system_overview.md
    operating_principles.md
    setup_guide.md
    claude_code_guide.md
    codex_guide.md
    discord_flow.md
    github_flow.md

  vault_scaffold/
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

  templates/
    context_pack_template.md
    dev_report_template.md
    project_template.md
    wiki_template.md
    migration_template.md
    framework_card_template.md
    legal_context_pack_template.md
    graphify_context_pack_template.md

  prompts/
    universal_master_prompt.md
    obsidian_agent_prompt.md
    claude_code_worker_prompt.md
    codex_worker_prompt.md
    legalizekr_integration_prompt.md
    graphify_integration_prompt.md

  scripts/
    init_vault_scaffold.sh
    sync_to_drive.sh
    graphify_build.sh
    graphify_update.sh
    graphify_query.sh
    legalize_sync.sh
    legalize_search.sh

  configs/
    paths.example.json
    agent_config.example.md

GitHub 레포에는 실제 고객 자료, 음성 원본, 개인정보, 법령 전체 데이터, API 키를 넣지 않는 게 좋아.

2. 지금 바로 해야 할 다음 순서
1단계

GitHub 레포를 로컬에 clone한다.

git clone https://github.com/사용자명/obsidian-agent-brain-system.git
cd obsidian-agent-brain-system
2단계

.gitignore를 먼저 만든다.

# Secrets
.env
.env.*
*.key
*.pem
*.crt
secrets/
credentials/

# RAW sensitive data
01_RAW/
RAW_IMPORT/
*.mp3
*.wav
*.m4a
*.mp4
*.mov

# External data
external_data/
data_sources/

# Obsidian private runtime
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/cache/
.trash/

# Graphify output/cache
graphify-out/cache/
graphify-out/cost.json
graphify-out/manifest.json

# Python / Node
__pycache__/
.venv/
venv/
node_modules/

# OS
.DS_Store
Thumbs.db
3단계

GitHub 레포에는 옵시디언 Vault의 실제 데이터가 아니라, vault_scaffold라는 뼈대만 만든다.

4단계

Google Drive 폴더 안의 ObsidianVault에 실제 시스템을 만든다.

5단계

클로드 코드 또는 코덱스에게 아래 명령 프롬프트를 넣는다.

3. 클로드 코드 / 코덱스용 다음 명령 프롬프트

아래 내용을 그대로 넣으면 돼.

# TASK PROMPT
# obsidian-agent-brain-system 초기 레포 세팅 및 Google Drive Vault 연결 구조 구축

너는 지금부터 `obsidian-agent-brain-system` GitHub 레포의 초기 구조를 세팅하는 개발 에이전트다.

사용자는 이미 다음 두 가지를 생성했다.

1. GitHub Repository
   - 이름: obsidian-agent-brain-system
   - 역할: Obsidian Agent Brain System의 개발 기준 저장소

2. Google Drive Folder
   - 이름: obsidian-agent-brain-system
   - 역할: 실제 Obsidian Vault, RAW 자료, 음성 자료, 마이그레이션 자료, 외부 데이터 보관소

이 작업의 목표는 GitHub 레포와 Google Drive 폴더의 역할을 분리하고, Obsidian Agent Brain System의 초기 뼈대를 만드는 것이다.

---

## 1. 핵심 역할 분리

GitHub Repo는 다음을 저장한다.

- 시스템 설계 문서
- Claude Code / Codex / Obsidian Agent 프롬프트
- Context Pack 템플릿
- 개발 보고서 템플릿
- Graphify 연동 문서
- LegalizeKR 연동 문서
- 초기 Vault scaffold
- 자동화 스크립트
- 설정 예시 파일
- 운영 가이드

Google Drive Folder는 다음을 저장한다.

- 실제 Obsidian Vault
- RAW 자료
- 음성 원본
- 회의록
- 고객 자료
- Agent Room Legacy 자료
- external_data/legalize-kr
- Graphify 임시 분석 자료
- 백업 파일
- 민감 자료

GitHub에는 실제 민감 자료를 커밋하지 않는다.

---

## 2. GitHub 레포에 생성할 구조

현재 레포 루트에 다음 구조를 생성하라.

```txt
obsidian-agent-brain-system/
  README.md
  .gitignore

  docs/
    system_overview.md
    operating_principles.md
    setup_guide.md
    claude_code_guide.md
    codex_guide.md
    discord_flow.md
    github_flow.md
    google_drive_vault_policy.md

  vault_scaffold/
    00_System/
      AGENT_STATE.md
      MASTER_PLAN.md
      TASKS.md
      HANDOFF_LOG.md
      ROUTING_RULES.md
      LOCKS/
      CONFIG/
      PROMPTS/

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

    04_Wiki/
      Index.md
      Legal/
      Graphify/
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
      Graphify/
      LegalizeKR/
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
      Legal/
      Graphify/

    07_Reports/
      Daily/
      Weekly/
      Project/
      Agent_Reports/

    08_Templates/

    09_Archive/

    10_AgentBus/
      inbox/
      outbox/
        ClaudeCode/
        Codex/
      reports/
        ClaudeCode/
        Codex/
        Graphify/
        LegalizeKR/
      context_requests/
        legal/
        graphify/
      context_responses/
        legal/
        graphify/
      completed/
      failed/

  templates/
    context_pack_template.md
    dev_report_template.md
    project_template.md
    wiki_template.md
    migration_template.md
    framework_card_template.md
    legal_context_pack_template.md
    graphify_context_pack_template.md

  prompts/
    universal_master_prompt.md
    obsidian_agent_prompt.md
    claude_code_worker_prompt.md
    codex_worker_prompt.md
    legalizekr_integration_prompt.md
    graphify_integration_prompt.md

  scripts/
    init_vault_scaffold.sh
    sync_to_drive.sh
    graphify_build.sh
    graphify_update.sh
    graphify_query.sh
    legalize_sync.sh
    legalize_search.sh

  configs/
    paths.example.json
    agent_config.example.md

빈 폴더는 .gitkeep 파일을 넣어서 Git에 포함되게 하라.

3. .gitignore 생성

다음 항목을 포함한 .gitignore를 생성하라.

# Secrets
.env
.env.*
*.key
*.pem
*.crt
secrets/
credentials/

# RAW sensitive data
01_RAW/
RAW_IMPORT/
*.mp3
*.wav
*.m4a
*.mp4
*.mov

# External data
external_data/
data_sources/

# Obsidian private runtime
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/cache/
.trash/

# Graphify output/cache
graphify-out/cache/
graphify-out/cost.json
graphify-out/manifest.json

# Python
__pycache__/
.venv/
venv/
*.pyc

# Node
node_modules/
npm-debug.log

# OS
.DS_Store
Thumbs.db