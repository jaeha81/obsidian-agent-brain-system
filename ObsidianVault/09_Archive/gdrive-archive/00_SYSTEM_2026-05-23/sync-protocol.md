# JH 동기화 프로토콜

> 위치: `G:\내 드라이브\JH-SHARED\00_SYSTEM\sync-protocol.md`  
> 대상: 사용자 · Claude · Codex · Agent Room  
> 목적: **어느 PC에서든 "동기화" 한 마디로 이전 PC 작업을 브리핑받고 즉시 재개할 수 있도록 한다.**  
> 최종 업데이트: 2026-05-01

---

## ★ 동기화의 핵심 목적

> 사용자는 동기화 요청 하나로 이전 PC에서 무엇을 했는지 파악하고, 바로 작업을 이어갈 수 있어야 한다.

**동기화 = 브리핑 + 재개** (git push/pull은 부수 작업)

---

## 동기화 트리거 시 즉시 실행 순서 (최우선)

사용자가 `동기화`, `sync`, `이어서`, `뭐하던 중이었어` 를 입력하면:

### 1단계: session-state.md 읽기 (필수, 1개 파일만)

Grep으로 "이어서 할 일" 섹션 줄 번호를 먼저 파악하고, 해당 줄부터 Read (offset/limit 파라미터 사용). 전체 읽기 금지.

```
G:\내 드라이브\JH-SHARED\00_SYSTEM\session-state.md
```

### 2단계: 브리핑 출력 (형식 고정)

```
📋 이전 세션 브리핑
━━━━━━━━━━━━━━━━━━
📅 마지막 작업: [날짜] / [PC명]
✅ 완료된 일: [1줄 요약]
⏳ 이어서 할 일:
  1. [항목1]
  2. [항목2]
━━━━━━━━━━━━━━━━━━
어디서부터 시작할까요? (엔터 치면 P1 항목부터 진행)
```

### 2.5단계: Knowledge Pre-fetch (작업 유형 파악 후)

session-state.md의 "이어서 할 일" 항목에서 작업 유형 키워드를 추출하고, 관련 지식을 선제 조회한다.

```bash
# 에러/패턴 관련 키워드 확인
grep -ril "키워드" "C:/Users/user1/Documents/OBSIDIAN-SECOND/claude-knowledge/" 2>/dev/null | head -5
```

또는 Agent Room 서버가 실행 중이면:
```
GET http://localhost:3100/api/knowledge/search?q=키워드
```

- 검색 대상: `claude-knowledge/errors/`, `claude-knowledge/patterns/`, `agent-room-knowledge/`
- 결과가 있으면 관련 규칙/패턴을 작업 전 내재화
- 결과 없으면 그대로 진행 (추가 파일 읽기 금지)

### 3단계: 사용자 확인 후 재개

- 사용자가 엔터 또는 "응", "계속" → P1 항목부터 즉시 시작
- 사용자가 다른 항목 지정 → 해당 항목부터 시작
- 사용자가 새 작업 입력 → 새 작업 진행 (session-state 이어서 할 일은 보존)

---

## 핵심 원칙

1. **session-state.md가 단일 재개 포인트다.** 이 파일 하나로 어느 PC에서든 재개 가능해야 한다.
2. `JH-SHARED` 루트는 허브이며 누적 데이터는 하위 폴더에 저장한다.
3. 동기화 요청 시 전체 전역 지침을 무조건 읽지 않는다.
4. 코드 동기화는 GitHub가 기준이다.
5. 자료/공유 상태는 Google Drive의 `JH-SHARED`가 기준이다.
6. 지식/설계 결정은 Obsidian Vault가 기준이다.
7. Claude는 구현, Codex는 독립 검수, 사용자는 최종 승인이다.

## 폴더 구조

```text
JH-SHARED/
  00_SYSTEM/       최신 시스템 기준, 경로, 동기화 규칙
  01_AGENT_ROOM/   Agent Room 메시지 로그
  02_HANDOFF/      Claude/Codex 전달 브리핑
  03_LOGS/         동기화 스냅샷, 감사 로그
  04_DAILY_REPORTS/ 날짜별 일일보고
  05_TASK_LOCKS/   동시 작업 잠금
  06_TASK_LOGS/    작업별 append-only 로그
  99_ARCHIVE/      오래된 문서 보관
```

## session-state.md 갱신 시점

세션 종료 시뿐 아니라 아래 시점에도 Claude가 갱신한다.

- 중요 구현 완료 직후
- git push 직후
- PC 전환 직전

갱신 필드: `last_updated` / `updated_by` / `pc` / `commit` / `dirty_files` / `next_actions` / `source_daily_report`

## Codex의 동기화 역할 (역할 경계)

- Codex는 동기화/재개 트리거 시 `session-state.md`를 읽되, 내용을 사실로 자동 수용하지 않는다.
- `git status` · 변경 파일과 반드시 대조한다.
- Codex 브리핑 = "검수 맥락 요약" (구현 재개 지시 아님)
- 일반 코드 검수 시에는 session-state.md 선행 읽기 불필요
- Agent Room 자체 코드가 변경된 경우에는 Codex가 세션 종료 또는 사용자 종료 요청 전에 최종 검수와 GitHub 반영 필요 여부를 확인한다.
- 검증된 Agent Room 코드 변경이 남아 있으면 Codex가 커밋/푸쉬까지 진행하고, 커밋 해시와 남은 변경 여부를 사용자에게 보고한다.

## 동기화 요청 시 읽는 최소 파일

아래 순서대로 읽는다.

1. `00_SYSTEM/session-state.md` ← **항상 1번째**
2. `00_SYSTEM/sync-protocol.md`
3. `00_SYSTEM/paths.md` (경로 확인 필요 시)

필요할 때만 추가로 읽는다.

- 프로젝트별 handoff
- Obsidian `wiki/index.md`
- Obsidian `wiki/log.md`
- 각 프로젝트 `AGENTS.md` 또는 `CLAUDE.md`

## Claude 컨텍스트 제한 규칙

Claude는 `동기화` 요청을 받았다고 해서 전역 `~/.claude/CLAUDE.md` 전체를 매번 읽지 않는다.

우선순위는 다음과 같다.

1. `JH-SHARED/00_SYSTEM/sync-protocol.md`
2. `JH-SHARED/00_SYSTEM/jh-system.md`
3. `JH-SHARED/00_SYSTEM/paths.md`
4. 현재 작업 프로젝트의 로컬 지침
5. 필요한 경우에만 전역 Claude 지침의 관련 섹션

## Agent Room 동작

사용자가 `동기화` 또는 `업데이트`를 요청하면 Agent Room은 다음을 기록한다.

- 현재 PC 사용자명
- 현재 PC 호스트명
- 현재 시각
- JH-SHARED 기준 파일 존재 여부
- Agent Room 코드 커밋 상태
- 이전 PC 스냅샷과의 차이 요약

기록 위치:

```text
JH-SHARED/03_LOGS/sync-state.jsonl
```

## 업데이트 요청 의미

`업데이트` 요청은 아래를 뜻한다.

1. 현재 PC의 Agent Room 코드가 GitHub 최신인지 확인
2. JH-SHARED 기준 파일이 있는지 확인
3. 필요하면 사용자에게 `git pull` 또는 프로젝트별 pull이 필요하다고 보고
4. 자동으로 다른 프로젝트 코드를 임의 수정하지 않음

## 금지

- Google Drive 폴더를 Git 저장소처럼 직접 운영하지 않는다.
- Claude/Codex가 사용자 승인 없이 전역 지침 전체를 과도하게 읽지 않는다.
- medipic 같은 제품 저장소에 JH 운영 도구를 섞지 않는다.
- 동기화 요청만으로 여러 프로젝트를 무조건 수정하지 않는다.
## Agent Room 사전 검수 필수 규칙

Claude가 Agent Room을 통해 작업 결과, 구현 보고, 사용자 전달용 답변을 남길 때는 사용자에게 최종 전달하기 전에 Codex 검수를 항상 거친다.

Claude가 Agent Room 작업 중 코드, 스크립트, README, 운영 문서를 수정한 경우에는 Codex가 최종 검수자다. Codex는 변경 파일, 실행 가능성, 민감정보 포함 여부, GitHub 반영 필요 여부를 확인한다.

운영 순서:

1. 사용자 지시
2. Claude 구현 또는 작업 보고 초안 작성
3. Claude가 코드 변경 파일과 실행/검증 결과를 Agent Room에 기록
4. Codex 독립 검수
5. Codex가 Agent Room 종료 전 `git status`를 확인
6. 푸쉬해야 할 검증된 코드 변경이 있으면 커밋 후 `git push origin main`
7. Codex 검수 결과와 커밋 해시를 Agent Room에 기록
8. 사용자에게 최종 보고

금지:

- Claude가 Codex 검수 없이 사용자에게 구현 완료를 최종 보고하지 않는다.
- Codex 검수 결과를 Claude가 자동으로 처리하거나 묵살하지 않는다.
- 수정이 필요하면 사용자가 Claude에게 지시한다.
- `.env`, 로컬 로그, 메시지 JSONL, 민감정보는 GitHub에 올리지 않는다.
## 일일보고 규칙

PC에서 진행한 작업은 매일 날짜별 보고서로 정리한다.

저장 위치:

```text
JH-SHARED/04_DAILY_REPORTS/YYYY/YYYY-MM/YYYY-MM-DD.md
```

생성 기준:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\new-daily-report.ps1
```

일일보고에는 최소한 아래 항목을 포함한다.

- 오늘 작업 요약
- 완료된 변경
- 주요 이슈 및 처리 상태
- 검증 결과
- 남은 작업
- Claude에게 전달할 내용
- 다음 시작 시 체크 명령

충돌 방지:

- Claude와 Codex는 같은 `YYYY-MM-DD.md`를 동시에 직접 편집하지 않는다.
- 각 주체는 `YYYY-MM-DD.entries/주체/PC명.jsonl`에 append-only로 입력한다.
- Markdown 일일보고는 `build-daily-report.ps1`로 JSONL 원본에서 재생성한다.

Claude와 Codex는 다음날 작업 시작 또는 PC 이동 시 해당 날짜의 최근 일일보고를 먼저 확인한다.

## 병렬 작업 잠금 규칙

Claude와 Codex가 동시에 작업할 수 있는 상황에서는 모든 작업을 `taskId` 기준으로 추적한다.

저장 위치:

```text
JH-SHARED/05_TASK_LOCKS/active/TASK_ID.json
JH-SHARED/05_TASK_LOCKS/done/YYYY-MM/TASK_ID.json
JH-SHARED/06_TASK_LOGS/YYYY-MM/TASK_ID.jsonl
```

시작 절차:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-task.ps1 -Owner claude -Mode implementation -Title "작업 제목" -Targets "대상 경로"
```

기록 절차:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\log-task.ps1 -TaskId "TASK_ID" -Speaker codex -Kind review -Body "검수 결과"
```

완료 절차:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\finish-task.ps1 -TaskId "TASK_ID" -Speaker claude
```

충돌 기준:

- 기존 active lock의 대상 경로와 새 작업 대상 경로가 같거나 상하위 관계이면 충돌로 본다.
- 충돌이 감지되면 자동 진행하지 않고 사용자에게 보고한다.
- `-Force`는 사용자가 명시 승인한 경우에만 사용한다.
- Codex는 구현 잠금을 잡지 않고 검수 잠금을 우선 사용한다.
