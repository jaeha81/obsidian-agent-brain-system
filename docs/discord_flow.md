# Discord / Voice Input Flow
> Created: 2026-05-22

## Overview

Discord와 음성 입력을 통해 아이디어, 메모, 지시사항을 시스템에 주입하는 파이프라인.

## Flow

```
Discord 메시지 / 음성 입력
        ↓
RAW_IMPORT/Discord/ 또는 RAW_IMPORT/Voice/
        ↓
Hermes Agent가 AgentBus inbox에 작업 등록
        ↓
처리 후 01_RAW/ 또는 02_Processed/ 저장
        ↓
03_Projects/ 또는 04_Wiki/ 업데이트
```

## RAW_IMPORT Subfolders

| 폴더 | 내용 |
|------|------|
| `Voice/` | 음성 메모 (*.mp3, *.m4a) |
| `Discord/` | Discord 채널 덤프 |
| `Meetings/` | 미팅 녹음, 회의록 |
| `Client/` | 클라이언트 자료 |
| `AgentRoom_Legacy/` | 이전 에이전트룸 아카이브 |

## File Naming Convention

```
{YYYY-MM-DD}_{TYPE}_{DESCRIPTION}.{ext}
예: 2026-05-22_voice_project_idea.mp3
예: 2026-05-22_discord_dev_discussion.md
```

## Processing Rules

- 원본 파일은 RAW_IMPORT/ 에서 절대 삭제하지 않는다
- 처리 결과는 01_RAW/ 에 복사 후 02_Processed/ 에 요약/정제 버전 생성
- 음성 파일은 텍스트 변환 후 01_RAW/transcripts/ 에 저장

## Security

- RAW_IMPORT/ 는 GitHub에 커밋하지 않는다
- 클라이언트 자료, 개인 정보 포함 파일 주의
- Discord 덤프에서 API Key, 토큰 포함 여부 확인 후 저장
