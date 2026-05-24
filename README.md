# Obsidian Agent Brain System

Obsidian을 중심 두뇌로, Bucky가 Claude Code와 Codex에 작업을 지시하는 지식 관리 + AI 협업 시스템.

## Architecture

```
GitHub (this repo)          Google Drive
────────────────────        ──────────────────────────────
scripts/                    obsidian-agent-brain-system/
templates/                    ObsidianVault/       ← Obsidian Vault
prompts/                      RAW_IMPORT/          ← 음성, 미팅 파일
docs/                         external_data/       ← legalize-kr 등
configs/                        legalize-kr/
vault_scaffold/                 graphify_selected/
                              backups/
                              exports/
```

## Key Components

| Component | Location | Role |
|-----------|----------|------|
| ObsidianVault | Google Drive | 중심 두뇌 (노트, 위키, 컨텍스트 팩) |
| AgentBus | ObsidianVault/10_AgentBus/ | 에이전트 간 파일 기반 통신 |
| Context Packs | ObsidianVault/06_Context_Packs/ | 에이전트용 압축 컨텍스트 |
| RAW_IMPORT | Google Drive | 음성·미팅·클라이언트 원본 |
| legalize-kr | Google Drive/external_data/ | 한국 법률 데이터 |
| Graphify | scripts/ + vault/ | 프로젝트 지식 그래프 |
| Harness Router | scripts/harness_router.py + vault | 개발 요구를 Superpowers/GSD/gstack 기준으로 분류 |

## Setup

### 1. Repository Clone
```bash
git clone https://github.com/YOUR_USERNAME/obsidian-agent-brain-system.git
```

### 2. ObsidianVault 초기화
```bash
./scripts/init_vault_scaffold.sh /path/to/Google/Drive/obsidian-agent-brain-system/ObsidianVault
```

### 3. Obsidian에서 Vault 열기
Obsidian → Open folder as vault → `ObsidianVault/` 선택

### 4. 경로 설정
```bash
cp configs/paths.example.json configs/paths.json
# paths.json 에서 실제 로컬 경로 설정
```

### 5. Docker 3-PC preflight
```bash
docker compose run --rm preflight
```

Docker is used for the shared Python runtime and startup checks. Keep Obsidian,
Claude Code, and Codex login sessions on the host unless the `host-cli` profile
is explicitly prepared. If Obsidian `bucky-agent` already owns the background
scripts, use Docker for `preflight` only. See [Docker 3-PC Workflow](docs/docker_3pc_workflow.md).

## Agent Roles

- **Bucky**: Obsidian 메인 오케스트레이터, 작업 분류, 지시, 결과 수집
- **Claude Code**: 구현, 파일 생성, 시스템 설정, 운영
- **Codex**: 독립 코드 리뷰, 로직 검증
- **User**: 아키텍처 결정, 민감 작업 승인

## Development Harness

개발 요청은 `Harness Router`가 먼저 분석한다. Router는 `ObsidianVault/05_Frameworks/Harness/`에 저장된 Superpowers, GSD, gstack 지식을 읽고, Claude Code에게는 구현 지시를, Codex에게는 검수 체크리스트를 전달한다.

## Security Rules

- API Key, 비밀번호, PII → 어떤 파일에도 포함 금지
- RAW/, external_data/, ObsidianVault/ → GitHub 커밋 금지
- 기존 CLAUDE.md, wiki/, raw/ → 덮어쓰기 절대 금지

## Docs

- [System Overview](docs/system_overview.md)
- [Google Drive Vault Policy](docs/google_drive_vault_policy.md)
- [Setup Guide](docs/setup_guide.md)
- [Bucky Agent Guide](docs/hermes_agent_guide.md)
- [Harness Framework Integration](docs/harness_framework_integration.md)
- [Operating Principles](docs/operating_principles.md)
