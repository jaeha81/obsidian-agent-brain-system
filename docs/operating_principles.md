# Operating Principles
> Created: 2026-05-22

## Core Principles

### 1. Audit First
새 구조를 적용하기 전에 반드시 기존 상태를 감사한다.
기존 파일의 역할과 충돌 가능성을 먼저 확인한다.

### 2. No Overwrite
기존 파일을 덮어쓰지 않는다.
특히: CLAUDE.md, wiki/, raw/, .obsidian/

### 3. No Delete Without Approval
파일/폴더 삭제는 사용자 명시적 승인 없이 실행하지 않는다.

### 4. Stage Before Merge
병합 전에 `_MIGRATION_STAGING/` 에서 검증한다.
검증 완료 후 실제 폴더로 이동한다.

### 5. Report Before Modify
대규모 변경 전에 변경 계획을 사용자에게 보고한다.
승인 후 실행한다.

### 6. Security First
API Key, 비밀번호, PII는 어떤 파일에도 포함하지 않는다.
민감 자료는 Google Drive에만 보관하고 GitHub에는 절대 커밋하지 않는다.

### 7. Minimal Context
에이전트에게 전달하는 컨텍스트는 최소화한다.
전체 Vault를 한 번에 읽지 않는다.
관련 프로젝트 폴더와 필요한 파일만 참조한다.

## Agent Collaboration Rules

- Claude Code와 Codex는 같은 파일을 동시에 수정하지 않는다.
- 작업 시작 전 LOCKS/ 에 잠금 파일 생성.
- 작업 완료 후 잠금 파일 즉시 삭제.
- Codex는 Claude Code의 독립 검토자다 — 사용자에게 직접 보고한다.

## Vault Management Rules

- 04_Wiki/ 는 LLM이 관리한다. 사용자가 직접 편집하지 않는다.
- 01_RAW/ 는 불변이다. 내용 수정 없이 원본 그대로 보관한다.
- 02_Processed/ 는 원본 처리 결과물이다.
- 10_AgentBus/ 는 에이전트 전용이다.

## Graphify Rules

- Graphify는 전체 Vault 스캔을 하지 않는다.
- 프로젝트 레벨 또는 지정된 범위만 분석한다.
- .graphifyignore 로 제외 범위를 명시한다.

## LegalizeKR Rules

- legalize-kr 데이터는 external_data/ 에만 위치한다.
- ObsidianVault 내부에 직접 복사하지 않는다.
- Context Pack을 통해 필요한 부분만 참조한다.
