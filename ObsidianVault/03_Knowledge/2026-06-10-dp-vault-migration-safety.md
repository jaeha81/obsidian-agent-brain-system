---
type: knowledge-note
date: 2026-06-10
source: daily-plus
category: verification
tags:
- '#area/ai_automation'
- '#status/active'
summary: Vault Migration Safety Checklist — Git/오프라인 아카이브, rsync/Syncthing, 플러그인 상태
  관리 포함
status: applied
applied_at: 2026-06-11
graph_cluster: daily-practice
---

# Vault Migration Safety Checklist

Obsidian Vault는 마크다운 폴더다. 커뮤니티 권장: 백업과 동기화를 분리해서 관리.
Git으로 전체 히스토리(플러그인 설정 포함) 캡처 + rsync/Syncthing 자동화.

---

## 핵심 원칙

1. **백업 ≠ 동기화**: iCloud/OneDrive 동기화는 백업이 아님. 별도 오프라인 아카이브 필수.
2. **플러그인 상태 포함**: `.obsidian/` 폴더 전체를 Git에 포함해야 완전 복구 가능.
3. **이전 전 검증 후 전환**: 마이그레이션 완료 후 최소 3일은 구 Vault 유지.
4. **단계별 검증**: 각 단계 완료 후 체크리스트 확인, 한꺼번에 진행 금지.

---

## 마이그레이션 전 준비 체크리스트

- [ ] 현재 Vault 경로 확인 (`G:\내 드라이브\obsidian-agent-brain-system\ObsidianVault\`)
- [ ] 전체 파일 수 기록: `find ObsidianVault/ -name "*.md" | wc -l`
- [ ] `.obsidian/plugins/` 설치 플러그인 목록 저장
- [ ] Git 상태 확인: `git status` → 미커밋 파일 없음 확인
- [ ] 마지막 커밋 해시 기록 (롤백 기준점)
- [ ] Obsidian 앱 완전 종료 (파일 잠금 해제)

---

## Git 히스토리 캡처

### .gitignore 설정 (Vault 전용)

```gitignore
# Obsidian Vault .gitignore
.obsidian/workspace.json       # 세션별 창 상태 (제외)
.obsidian/workspace-mobile.json
.trash/
.DS_Store
Thumbs.db

# 포함 (명시적 허용)
# .obsidian/plugins/           → 플러그인 포함
# .obsidian/themes/            → 테마 포함
# .obsidian/snippets/          → CSS 스니펫 포함
# .obsidian/app.json           → 앱 설정 포함
# .obsidian/community-plugins.json → 플러그인 목록 포함
```

### 커밋 전략

```bash
# 일별 자동 커밋 (Git hook 또는 cron)
cd "G:/내 드라이브/obsidian-agent-brain-system"
git add ObsidianVault/
git commit -m "vault: daily snapshot $(date +%Y-%m-%d)"

# 마이그레이션 직전 스냅샷
git add -A
git commit -m "vault: pre-migration snapshot $(date +%Y-%m-%dT%H:%M:%S)"
git tag "pre-migration-$(date +%Y%m%d)"
```

---

## 오프라인 아카이브 (rsync)

### 로컬 NAS/외장 드라이브 동기화

```bash
# rsync: 원본 → 아카이브 (삭제 동기화 포함)
rsync -avz --delete \
  "G:/내 드라이브/obsidian-agent-brain-system/ObsidianVault/" \
  "/d/backup/obsidian-vault-archive/"

# Windows PowerShell 버전
robocopy "G:\내 드라이브\obsidian-agent-brain-system\ObsidianVault" \
  "D:\backup\obsidian-vault-archive" /MIR /R:3 /W:5
```

### Syncthing 설정 (피어-투-피어 동기화)

```yaml
# syncthing 폴더 설정
folders:
  - id: obsidian-vault
    label: "ObsidianVault"
    path: "G:/내 드라이브/obsidian-agent-brain-system/ObsidianVault"
    type: sendreceive
    devices:
      - id: <home-pc-device-id>
      - id: <nas-device-id>
    ignorePatterns:
      - ".obsidian/workspace.json"
      - ".trash"
```

---

## 플러그인 상태 관리

### 마이그레이션 시 플러그인 재설치 방지

```bash
# 플러그인 목록 내보내기
cat .obsidian/community-plugins.json

# 수동 재설치 없이 새 환경에서 복구
# → .obsidian/ 폴더 전체 복사 후 Obsidian 재시작
```

### 플러그인 상태 백업 항목

| 항목 | 경로 | 중요도 |
|---|---|---|
| 설치 플러그인 목록 | `.obsidian/community-plugins.json` | 필수 |
| 플러그인 설정 | `.obsidian/plugins/<plugin-id>/data.json` | 필수 |
| 테마 | `.obsidian/themes/` | 권장 |
| CSS 스니펫 | `.obsidian/snippets/` | 권장 |
| 앱 설정 | `.obsidian/app.json` | 필수 |
| 단축키 | `.obsidian/hotkeys.json` | 권장 |

---

## 마이그레이션 후 검증 체크리스트

- [ ] 파일 수 일치 확인: `find NewVault/ -name "*.md" | wc -l` == 이전 기록값
- [ ] 링크 무결성 확인: Obsidian → Graph View → orphan 노드 비교
- [ ] 플러그인 정상 작동 확인 (상위 5개 플러그인 기능 테스트)
- [ ] Git log 연속성 확인: `git log --oneline -10`
- [ ] 구 Vault 3일 병행 유지 후 최종 삭제
- [ ] rsync/Syncthing 새 경로로 업데이트

---

## 롤백 절차

```bash
# 마이그레이션 실패 시 태그 기준으로 롤백
git checkout pre-migration-20260610

# 또는 특정 파일만 복구
git checkout pre-migration-20260610 -- ObsidianVault/path/to/file.md
```

## 관련 노트
- [[hubs/JH System]]
