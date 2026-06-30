# Google Drive Vault Policy
> Created: 2026-05-22

## Purpose

Google Drive is used as the storage layer for the actual Obsidian Vault and RAW data.
GitHub stores only code, scripts, templates, and scaffolds — never actual knowledge data.

## Folder Name

`obsidian-agent-brain-system`

## Recommended Structure

```
Google Drive/
  obsidian-agent-brain-system/
    ObsidianVault/          ← Obsidian에서 이 폴더를 Vault로 열기
    RAW_IMPORT/
      Voice/
      Discord/
      Meetings/
      Client/
      AgentRoom_Legacy/
    external_data/
      legalize-kr/          ← git clone으로 별도 관리
      graphify_selected/
    backups/
    exports/
```

## Role Separation

| 저장소 | 내용 | GitHub 커밋 |
|--------|------|------------|
| GitHub | 코드, 스크립트, 템플릿, vault_scaffold | Yes |
| Google Drive | 실제 Vault 노트, RAW 데이터, 민감 자료 | No |

## Do Not Commit to GitHub

다음 항목은 GitHub에 절대 커밋하지 않는다:

- RAW 음성 파일 (*.mp3, *.wav, *.m4a)
- 클라이언트 데이터, 미팅 녹음
- 계약서
- API Key, 비밀번호, 토큰
- 개인 메모, PII
- `external_data/legalize-kr/` 전체 클론
- 대용량 Graphify 출력물
- `ObsidianVault/` 전체

## Obsidian Vault

사용자는 다음 폴더를 Obsidian Vault로 열어야 한다:

```
Google Drive/obsidian-agent-brain-system/ObsidianVault
```

## Sync

Google Drive의 자동 동기화 기능을 사용한다.
추가 스크립트 동기화가 필요한 경우 `scripts/sync_to_drive.sh` 참조.

## Backup Policy

- 주기적 백업: `backups/vault-backup-YYYYMMDD/`
- Phase 2 마이그레이션 시작 전 반드시 백업
- 백업 보존 기간: 최소 30일
