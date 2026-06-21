---
type: system
---
# Vault 경계 표시

이 파일이 있는 경로가 ObsidianVault의 루트입니다.

## 에이전트 준수 사항

- Claude Code / Codex는 **이 Vault 경계 밖** 경로를 임의 탐색하지 않는다.
- 특히 `G:\내 드라이브\JH-SHARED` (구 Agent Room)는 **읽기 금지** 경로.
- Google Drive 데이터 접근이 필요하면 `gdrive_agent_room_migrator.py`를 통해
  ObsidianVault 안으로 먼저 이관 후 처리한다.

## 허용 경로 (Claude Code 작업 대상)

- `G:\내 드라이브\obsidian-agent-brain-system\` (이 저장소)
- `ObsidianVault\` (Vault 루트)
- `scripts\` (스크립트)

[[bucky-system-hub]]
