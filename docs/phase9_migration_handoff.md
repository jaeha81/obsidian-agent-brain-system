# Phase 9 — Existing Vault Migration Handoff
> Created: 2026-05-22 | Status: 별도 세션 예정

## Overview

Phase 9는 기존 Vault(`C:\Users\user1\Documents\Obsidian Vault\`)의 남은 콘텐츠를
신규 Vault(`G:\내 드라이브\obsidian-agent-brain-system\ObsidianVault\`)로 선택적으로 병합한다.

이미 Phase 2에서 다음 항목이 마이그레이션 완료됨:
- wiki/ → 04_Wiki/JH/ (22개)
- raw/memories/ → 01_RAW/memories/ (12개)
- raw/memories2/ → 01_RAW/memories2/ (13개, 중복 2개 제거)
- 00_Inbox/ → 01_RAW/inbox/ (5개)
- 01_Projects/ + output/ → 03_Projects/ (21개)
- infranodus/ → 07_Reports/infranodus/ + 09_Archive/ (24개)
- sessions + templates + archive → 09_Archive/ (77개)

## Remaining Migration Candidates

| 기존 위치 | 신규 위치 | 우선순위 | 비고 |
|-----------|-----------|----------|------|
| wiki/ (추가 항목) | 04_Wiki/JH/ | 낮음 | 이미 일부 마이그레이션 완료 |
| raw/ (추가 항목) | 01_RAW/ | 낮음 | memories/memories2 완료 |
| .obsidian/ | — | 제외 | 설정 충돌 위험, 건드리지 말 것 |
| CLAUDE.md | — | 제외 | 기존 Vault 전용, 덮어쓰기 금지 |
| plugins/ | — | 별도 검토 | 플러그인 호환성 확인 필요 |

## Migration Safety Rules

1. **Audit First** — `VAULT_INVENTORY.md`, `CONFLICT_MAP.md` 재확인 후 진행
2. **No Overwrite** — 동일 파일명 존재 시 타임스탬프 접미사 또는 별도 서브폴더 사용
3. **No Delete** — 기존 Vault 원본 삭제 금지
4. **Stage Before Merge** — 스테이징 폴더에 복사 후 검토, 확인 후 최종 위치로 이동
5. **SAFE_MERGE_LOG.md** — 모든 복사/이동 작업 기록

## Session Start Command

```
세션 재개: obsidian-agent-brain-system Phase 9 — 기존 Vault 선택적 마이그레이션.
AGENT_STATE.md, SAFE_MERGE_LOG.md, CONFLICT_MAP.md 확인 후
C:\Users\user1\Documents\Obsidian Vault\의 미이전 항목을
G:\내 드라이브\obsidian-agent-brain-system\ObsidianVault\ 로 Migration-Safe 원칙에 따라 병합.
기존 Vault 원본 삭제 금지, .obsidian/ 및 CLAUDE.md 건드리지 말 것.
```

## References

- `ObsidianVault/00_System/VAULT_INVENTORY.md`
- `ObsidianVault/00_System/CONFLICT_MAP.md`
- `ObsidianVault/00_System/MIGRATION_PLAN.md`
- `ObsidianVault/00_System/SAFE_MERGE_LOG.md`
- `ObsidianVault/00_System/ROLLBACK_PLAN.md`
