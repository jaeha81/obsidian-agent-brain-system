# Bucky Orchestrator Evolution Guardrails

## 목적

Bucky Agent Orchestrator는 Claude Code와 Codex의 상위 판단 에이전트다. 새 기능 도입과 수익화 실험은 계속 추진하되, 기존 Obsidian Agent Brain System의 개발 방식, 스킬, 하네스프레임워크, 대시보드, 링크, 사이트 설정, PC별 운영 구조를 깨지 않는 것을 기본 조건으로 한다.

## 보호 대상

- `AGENTS.md`, `CLAUDE.md`, Bucky/Codex/Claude 역할 규칙
- `skills/`, Context Pack, 하네스프레임워크 관련 문서와 스크립트
- `dashboard/`, `docs/*dashboard*`, `ObsidianVault/00_Dashboard/`
- `.env`, API Key, 웹훅, 로그인 세션, 사이트 링크, Google Drive/GitHub 경로
- `scripts/pc_identity.py`, `scripts/sync_sentinel.py`, `scripts/preflight_check.py`
- Git branch/worktree, PC별 primary/secondary 운영 규칙

## 도입 원칙

1. 새 기능 도입은 허용한다.
2. 기존 기능과 충돌하면 새 기능을 먼저 격리한다.
3. 기존 대시보드와 설정 파일은 덮어쓰지 않는다.
4. 기존 데이터 필드는 유지하고 새 필드는 추가 방식으로 확장한다.
5. Claude Code는 구현, Codex는 독립 검수, Bucky는 판단과 라우팅을 맡는다.
6. 미등록 PC는 기본적으로 `secondary`로 취급한다.
7. 집 PC(`PC_NAME=home`, `PC_ROLE=primary`)만 canonical Vault 직접 쓰기 권한을 갖는다.

## Bucky 판단 루프

```text
사용자 요청
→ 현재 PC/브랜치/저장소/대시보드 영향도 감지
→ 요청 의도 분류
→ 위험도 판단
→ 실험/확장/코어 변경 범위 결정
→ Claude Code 구현 또는 Codex 검수 라우팅
→ 결과 검증
→ Obsidian 지식화
→ Dashboard 반영 여부 판단
→ 수익화 후보 추출
```

## 변경 게이트

아래 항목에 닿는 변경은 바로 적용하지 않고 영향도 검토가 필요하다.

- `.env`, API Key, 인증/토큰, 웹훅
- Obsidian 플러그인 설정과 Vault 경로
- Dashboard 생성 스크립트와 기존 HTML 출력물
- Context Pack 선택기와 에이전트 역할 규칙
- Git worktree, branch routing, PC identity
- 외장하드/Google Drive/GitHub 저장소 기준 경로

## 권장 적용 단계

1. `Experiment`: 새 방향을 문서나 별도 실험 스크립트로 분리한다.
2. `Adapter`: 기존 Bucky/Claude/Codex 흐름을 직접 바꾸지 않고 연결 계층을 둔다.
3. `Review`: Codex가 보안, 대시보드 영향, 역할 충돌, 설정 위험을 검수한다.
4. `Promote`: 문제가 없을 때만 Extension 레이어로 승격한다.
5. `Dashboard`: 기존 섹션을 삭제하지 않고 새 상태 섹션으로 추가한다.

## 실패 시 원칙

- 기존 시스템을 롤백 가능한 상태로 둔다.
- 새 기능만 끄면 기존 루프가 계속 돌아가야 한다.
- 링크, 사이트 설정, API 연결, 대시보드 출력이 깨졌다면 수익화 실험보다 복구를 우선한다.
