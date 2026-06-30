# Setup Guide
> Created: 2026-05-22

## Prerequisites

- Git
- Python 3.9+ (Graphify용)
- Node.js 18+ (선택사항)
- Obsidian (최신 버전)
- Google Drive for Desktop

## Step 1 — GitHub Repo Clone

```bash
git clone https://github.com/YOUR_USERNAME/obsidian-agent-brain-system.git
cd obsidian-agent-brain-system
```

## Step 2 — Google Drive 폴더 확인

Google Drive for Desktop이 마운트된 경로 확인:
- Windows: `G:\내 드라이브\` 또는 `G:\My Drive\`
- macOS: `~/Google Drive/My Drive/`

`obsidian-agent-brain-system` 폴더가 있는지 확인.

## Step 3 — ObsidianVault 초기화

```bash
# Windows (PowerShell)
.\scripts\init_vault_scaffold.sh "G:\내 드라이브\obsidian-agent-brain-system\ObsidianVault"

# macOS/Linux
./scripts/init_vault_scaffold.sh "/path/to/Google Drive/obsidian-agent-brain-system/ObsidianVault"
```

## Step 4 — 경로 설정

```bash
cp configs/paths.example.json configs/paths.json
```

`configs/paths.json` 편집 — 실제 로컬 경로로 변경:
```json
{
  "google_drive_folder": "G:\\내 드라이브\\obsidian-agent-brain-system",
  "obsidian_vault": "G:\\내 드라이브\\obsidian-agent-brain-system\\ObsidianVault",
  ...
}
```

> **주의**: `configs/paths.json` 은 `.gitignore` 에 포함되어 있음. 커밋하지 않음.

## Step 5 — Obsidian에서 Vault 열기

1. Obsidian 실행
2. "Open folder as vault" 선택
3. `G:\내 드라이브\obsidian-agent-brain-system\ObsidianVault` 선택
4. 플러그인 설치 필요 시 Community Plugins에서 설치

## Step 6 — Graphify 설치 (선택사항)

```bash
pip install graphifyy
```

설정: `ObsidianVault/05_Frameworks/Graphify/graphify_config.md` 참조

## Step 7 — LegalizeKR 설정 (선택사항)

```bash
# external_data 폴더로 이동 후 clone
cd "G:\내 드라이브\obsidian-agent-brain-system\external_data"
git clone https://github.com/legally-copyleft/legalize-kr.git
```

설정: `ObsidianVault/05_Frameworks/LegalizeKR/` 참조

## Verification

```bash
# 폴더 구조 확인
Get-ChildItem -Recurse -Directory "G:\내 드라이브\obsidian-agent-brain-system\ObsidianVault" | Select-Object FullName

# .gitignore 적용 확인
git check-ignore ObsidianVault/ external_data/ RAW_IMPORT/
```

## Troubleshooting

| 문제 | 해결 |
|------|------|
| Obsidian이 Vault를 인식 못함 | 폴더 경로에 한글 포함 확인, 권한 확인 |
| sync_to_drive.sh 오류 | Google Drive for Desktop 실행 여부 확인 |
| Graphify import 오류 | Python 버전 확인 (3.9+) |
