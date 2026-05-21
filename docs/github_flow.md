# GitHub Flow
> Created: 2026-05-22

## Repository Structure

```
obsidian-agent-brain-system/
├── .gitignore
├── README.md
├── docs/           ← 시스템 문서
├── vault_scaffold/ ← ObsidianVault 초기 구조 템플릿
├── templates/      ← 노트, 보고서 템플릿
├── prompts/        ← 에이전트 프롬프트
├── scripts/        ← 자동화 스크립트
└── configs/        ← 설정 예시 파일
```

## Branch Strategy

| 브랜치 | 용도 |
|--------|------|
| `main` | 안정 버전 |
| `dev` | 개발 작업 |
| `feature/{name}` | 기능별 개발 |

## Commit Rules

- 커밋 메시지: `{type}: {description}`
- type: feat, fix, docs, chore, refactor
- 예: `feat: add graphify_build.sh script`

## What NOT to Commit

`.gitignore` 에 포함된 항목:

- `ObsidianVault/` — Google Drive에 저장
- `RAW_IMPORT/` — 민감 데이터
- `external_data/` — legalize-kr 등 대용량/민감
- `backups/`, `exports/`
- `.env`, `*.key`, API Key
- `configs/paths.json` — 로컬 경로 포함

## Sync Protocol

1. 스크립트/템플릿/프롬프트 변경 → GitHub commit + push
2. Vault 내용 변경 → Google Drive 자동 동기화
3. 두 저장소는 독립적으로 관리

## Release Tags

의미 있는 시스템 완성 단계마다 태그 생성:
- `v0.1.0` — Phase 1 완료 (repo scaffold)
- `v0.2.0` — Graphify 통합 완료
- `v0.3.0` — LegalizeKR 통합 완료
- `v1.0.0` — 전체 시스템 안정화
