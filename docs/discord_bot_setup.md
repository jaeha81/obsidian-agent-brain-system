# Discord 실시간 봇 설정 가이드

## 1. Discord 봇 생성 및 토큰 발급

1. [Discord Developer Portal](https://discord.com/developers/applications) 접속
2. **New Application** → 이름 입력 (예: `AgentBus Bot`)
3. 왼쪽 메뉴 **Bot** → **Add Bot**
4. **Message Content Intent** 활성화 (Privileged Gateway Intents 섹션)
5. **Reset Token** → 토큰 복사 (한 번만 표시됨)

## 2. 봇을 서버에 초대

왼쪽 메뉴 **OAuth2 > URL Generator**:
- Scopes: `bot`
- Bot Permissions: `Read Messages/View Channels`, `Send Messages`
- 생성된 URL로 접속 → 서버 선택 → 인증

## 3. 채널/길드 ID 확인

Discord 설정 > 고급 > **개발자 모드** 활성화  
→ 서버 이름 우클릭 → **서버 ID 복사** (= Guild ID)  
→ 채널 이름 우클릭 → **채널 ID 복사**

## 4. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일 편집:
```
DISCORD_BOT_TOKEN=실제_봇_토큰
DISCORD_GUILD_ID=서버_ID
DISCORD_CHANNEL_IDS=채널ID_1,채널ID_2
VAULT_PATH=G:\내 드라이브\obsidian-agent-brain-system\ObsidianVault
```

## 5. 의존성 설치

```bash
pip install discord.py>=2.3 python-dotenv>=1.0
```

## 6. 봇 실행

**개발 모드 (포그라운드):**
```bash
python scripts/discord_bot.py
```

**백그라운드 실행 (Windows):**
```bash
pythonw scripts/discord_bot.py
```

**Windows 작업 스케줄러 자동 시작 등록:**
1. 작업 스케줄러 열기 → **기본 작업 만들기**
2. 트리거: **컴퓨터 시작 시**
3. 동작: `pythonw` 실행, 인수: `scripts\discord_bot.py`, 시작 위치: 프로젝트 루트

## 7. 동작 확인

봇이 실행되면:
1. Discord 채널에 10자 이상의 메시지 입력
2. `ObsidianVault/10_AgentBus/inbox/` 에 `.md` 파일 생성 확인
3. `!status` 명령어로 봇 응답 확인

## 8. 저장 포맷

생성 파일명: `YYYYMMDD_HHMMSS_discord_{channel}_{author}.md`

```markdown
---
type: discord_intake
source: realtime_bot
channel: general
author: username
created: 2026-05-22T10:30:00
status: pending
---

# Discord: #general — username

> 2026-05-22T10:30:00

메시지 내용...
```

## 9. 문제 해결

| 오류 | 원인 | 해결 |
|------|------|------|
| `Privileged Intent` 오류 | Message Content Intent 미활성화 | Developer Portal > Bot > Message Content Intent ON |
| 메시지가 저장 안 됨 | 채널 ID 불일치 | `.env`의 `DISCORD_CHANNEL_IDS` 확인 또는 비워서 모든 채널 감시 |
| `Token` 오류 | 토큰 만료/오기입 | Developer Portal에서 토큰 재발급 |
