# JH Agent Room

JH 통합 구축 시스템에서 사용자, Claude, Codex가 같은 기준을 보고 협업하기 위한 독립 로컬 대시보드입니다.

## 역할

- 사용자: 방향, 지시, 승인
- Claude: 구현 및 운영 총괄
- Codex: 독립 검수 및 사용자 직접 보고

## 실행

권장 실행:

```powershell
cd D:\ai프로젝트\JH-Agent-Room
powershell -ExecutionPolicy Bypass -File .\scripts\start-agent-room.ps1
```

브라우저에서 `http://localhost:3100`을 엽니다.

## 실제 사용 흐름

1. 사용자는 브라우저 입력창에 지시를 남깁니다.
2. `동기화` 버튼을 누르면 사용자 동기화 요청과 Claude/Codex 자동 로그가 남습니다.
3. Claude는 구현 내용을 아래 명령으로 남깁니다.
4. Codex는 검수 결과를 아래 명령으로 남깁니다.
5. 화면은 5초마다 자동 새로고침됩니다.

Claude 메시지:

```powershell
.\scripts\post-message.ps1 -Speaker claude -Kind implementation -Body "작업 내용"
```

Codex 메시지:

```powershell
.\scripts\post-message.ps1 -Speaker codex -Kind review -Body "검수 결과"
```

## 저장소

메시지는 append-only JSONL 형식으로 아래 파일에 저장됩니다.

```text
G:\내 드라이브\JH-SHARED\01_AGENT_ROOM\agent-room-messages.jsonl
```

## 보안 기준

- 일반 UI에서는 사용자 발화만 저장합니다.
- Claude/Codex 발화는 `ADMIN_SECRET` 검증을 통과한 스크립트 요청만 허용합니다.
- `scripts\start-agent-room.ps1`이 `.env`와 `ADMIN_SECRET`을 자동 생성합니다.
- API 응답과 화면에는 로컬 절대 경로를 노출하지 않습니다.

## 운영 기능

- 자동 새로고침: 5초 간격
- 메시지 필터: 전체, 사용자, Claude, Codex
- 빠른 동기화 버튼
- 현재 로그 JSON 내보내기
- 기준 파일 상태 확인
## 다른 PC에서 사용

처음 설치:

```powershell
cd C:\ai프로젝트
git clone https://github.com/jaeha81/JH-Agent-Room.git
cd JH-Agent-Room
powershell -ExecutionPolicy Bypass -File .\scripts\start-agent-room.ps1
```

집 PC처럼 `D:\ai프로젝트`를 쓰는 환경이면 첫 줄만 아래처럼 바꿉니다.

```powershell
cd D:\ai프로젝트
```

업데이트:

```powershell
cd C:\ai프로젝트\JH-Agent-Room
git pull origin main
powershell -ExecutionPolicy Bypass -File .\scripts\start-agent-room.ps1
```

공유 메시지 로그는 코드 저장소에 커밋하지 않고 `G:\내 드라이브\JH-SHARED\01_AGENT_ROOM\agent-room-messages.jsonl`을 사용합니다.
각 PC는 로컬 실행본만 GitHub에서 동기화합니다.

## 코드 변경 GitHub 반영 규칙

Agent Room의 코드, 스크립트, README, 운영 문서가 바뀐 경우에는 다른 PC에서도 같은 실행본을 쓰도록 GitHub에 반영합니다.

원칙:

- 코드 변경은 `git status`로 변경 파일을 확인합니다.
- 실행 또는 문법 검증이 가능한 경우 먼저 확인합니다.
- 민감정보가 담긴 `.env`와 로컬 로그 파일은 커밋하지 않습니다.
- 검증된 변경만 커밋하고 `git push origin main`으로 반영합니다.
- Agent Room 화면의 `동기화` 버튼은 GitHub push가 아니라 공유 로그 기록입니다.
- Claude가 Agent Room 작업 중 코드를 수정한 경우, Codex가 최종 검수한 뒤 커밋/푸쉬 여부를 판단합니다.
- Codex는 Agent Room 세션 종료 또는 사용자 종료 요청 시 `git status`를 확인하고, 푸쉬해야 할 검증된 코드 변경이 있으면 GitHub 반영까지 진행합니다.

수동 반영:

```powershell
cd C:\ai프로젝트\JH-Agent-Room
git status
git add README.md server.js public scripts
git commit -m "describe change"
git push origin main
```

Codex나 Claude가 Agent Room 코드를 수정한 경우에는 사용자에게 별도 요청이 없어도 검증 후 GitHub 반영 여부를 보고하고, 승인된 운영 범위에서는 커밋/푸쉬까지 진행합니다.

종료 전 Codex 확인:

```powershell
cd C:\ai프로젝트\JH-Agent-Room
git status
npm run dev
git log -1 --oneline
```

확인 기준:

- 변경 파일이 코드/스크립트/문서인지 확인합니다.
- `.env`, 메시지 JSONL, 로컬 로그는 제외합니다.
- 실행 확인 후 필요한 경우 커밋하고 `git push origin main`을 수행합니다.
- 푸쉬 완료 후 커밋 해시와 남은 변경 여부를 사용자에게 보고합니다.

## 3대 PC 동기화 규칙

Agent Room은 3대 PC를 오가는 작업을 위해 아래 공유 기준을 사용합니다.

```text
G:\내 드라이브\JH-SHARED\00_SYSTEM\sync-protocol.md
G:\내 드라이브\JH-SHARED\00_SYSTEM\jh-system.md
G:\내 드라이브\JH-SHARED\00_SYSTEM\paths.md
```

사용자가 `동기화` 또는 `업데이트`를 요청하면 Agent Room은 현재 PC 스냅샷을 아래에 append-only로 기록합니다.

```text
G:\내 드라이브\JH-SHARED\03_LOGS\sync-state.jsonl
```

메시지 로그는 아래 위치에 저장합니다.

```text
G:\내 드라이브\JH-SHARED\01_AGENT_ROOM\agent-room-messages.jsonl
```

## Claude 컨텍스트 제한

Claude는 동기화 요청을 받았다고 해서 전역 `~/.claude/CLAUDE.md` 전체를 매번 읽지 않습니다.
먼저 `JH-SHARED/00_SYSTEM`의 최소 기준 파일만 읽고, 필요한 경우에만 현재 프로젝트 지침이나 전역 지침의 관련 섹션을 추가로 읽습니다.

Claude 전달 브리핑:

```text
G:\내 드라이브\JH-SHARED\02_HANDOFF\claude-sync-context-guard.md
```
## 다른 PC에서 Claude/Codex 전제 확인

다른 PC에서 Claude 또는 Codex가 시작하면 전역 지침 전체를 읽기 전에 아래 명령으로 최소 공유 컨텍스트를 확인합니다.

```powershell
cd C:\ai프로젝트\JH-Agent-Room
powershell -ExecutionPolicy Bypass -File .\scripts\check-agent-context.ps1
```

집 PC에서는 경로만 바꿉니다.

```powershell
cd D:\ai프로젝트\JH-Agent-Room
powershell -ExecutionPolicy Bypass -File .\scripts\check-agent-context.ps1
```

확인 대상:

- `JH-SHARED\00_SYSTEM\agent-onboarding.md`
- `JH-SHARED\00_SYSTEM\sync-protocol.md`
- `JH-SHARED\00_SYSTEM\jh-system.md`
- `JH-SHARED\00_SYSTEM\paths.md`
- `JH-SHARED\02_HANDOFF\claude-sync-context-guard.md`

확인 후 Agent Room에서 `동기화` 또는 `업데이트`를 눌러 현재 PC 스냅샷을 남깁니다.
## 사전 검수 필수 규칙

Agent Room을 통한 Claude 작업은 사용자에게 최종 전달되기 전에 Codex 검수를 항상 거칩니다.

순서:

1. 사용자 지시
2. Claude 구현 또는 보고 초안
3. Claude가 코드를 건드린 경우 변경 파일과 실행 결과를 Agent Room에 남김
4. Codex 독립 검수
5. Codex가 필요 시 커밋/푸쉬 대상 여부 확인
6. Codex 검수 결과 기록
7. 사용자 최종 보고

Claude는 Codex 검수 없이 완료 보고를 확정하지 않습니다.
## 일일보고 운영

PC에서 진행한 작업은 매일 날짜별 보고서로 정리합니다.

저장 위치:

```text
G:\내 드라이브\JH-SHARED\04_DAILY_REPORTS\YYYY\YYYY-MM\YYYY-MM-DD.md
```

새 일일보고 생성:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\new-daily-report.ps1
```

작업 항목 추가:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\add-daily-entry.ps1 -Speaker codex -Kind verification -Body "검증 결과"
```

Markdown 정리본 재생성:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-daily-report.ps1
```

충돌 방지 규칙:

- Claude와 Codex는 같은 `YYYY-MM-DD.md`를 동시에 직접 편집하지 않습니다.
- 각 주체의 원본 입력은 `YYYY-MM-DD.entries\주체\PC명.jsonl`에 append-only로 저장합니다.
- `YYYY-MM-DD.md`는 JSONL 원본에서 재생성되는 읽기용 정리본으로 취급합니다.

일일보고 포함 항목:

- 오늘 작업 요약
- 완료된 변경
- 주요 이슈 및 처리 상태
- 검증 결과
- 남은 작업
- Claude에게 전달할 내용
- 다음 시작 시 체크 명령

2026-05-01 작업 보고:

```text
G:\내 드라이브\JH-SHARED\04_DAILY_REPORTS\2026\2026-05\2026-05-01.md
```

다음날 또는 다른 PC에서 시작할 때 Claude/Codex는 최근 일일보고와 `check-agent-context.ps1` 결과를 함께 확인합니다.

## 병렬 작업 잠금

Claude와 Codex가 동시에 여러 작업을 진행할 때는 `taskId` 기준으로 작업 잠금과 작업 로그를 남깁니다.

저장 위치:

```text
G:\내 드라이브\JH-SHARED\05_TASK_LOCKS\active\TASK_ID.json
G:\내 드라이브\JH-SHARED\05_TASK_LOCKS\done\YYYY-MM\TASK_ID.json
G:\내 드라이브\JH-SHARED\06_TASK_LOGS\YYYY-MM\TASK_ID.jsonl
```

작업 시작:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-task.ps1 -Owner claude -Mode implementation -Title "작업 제목" -Targets "D:\ai프로젝트\project\src"
```

충돌 확인:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-task-conflicts.ps1 -Targets "D:\ai프로젝트\project\src"
```

작업 기록:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\log-task.ps1 -TaskId "TASK_ID" -Speaker codex -Kind review -Body "검수 결과"
```

작업 완료:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\finish-task.ps1 -TaskId "TASK_ID" -Speaker claude
```

충돌 기준:

- 같은 대상 경로 또는 상하위 경로를 다른 active 작업이 사용 중이면 충돌로 판단합니다.
- 충돌 시 자동 진행하지 않고 사용자에게 보고합니다.
- `-Force`는 사용자가 명시 승인한 경우에만 사용합니다.
