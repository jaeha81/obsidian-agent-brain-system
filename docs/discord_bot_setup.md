# Discord 봇 시작하기

## 준비 (최초 1회)

### 1단계 — 봇 토큰 발급
1. https://discord.com/developers/applications → **New Application**
2. 왼쪽 **Bot** → **Add Bot** → **Message Content Intent** 켜기
3. **Reset Token** → 토큰 복사

### 2단계 — 채널/서버 ID 확인
Discord 설정 → 고급 → **개발자 모드** ON  
→ 서버 우클릭 → **서버 ID 복사**  
→ 채널 우클릭 → **채널 ID 복사**

### 3단계 — 봇을 내 서버에 초대
왼쪽 **OAuth2 → URL Generator** → Scopes: `bot` → Permissions: `Read Messages`, `Send Messages`  
→ 생성된 URL 브라우저에서 열어 서버 선택

### 4단계 — .env 설정
```bash
copy .env.example .env
```
`.env` 열어서 값 채우기:
```
DISCORD_BOT_TOKEN=여기에_토큰
DISCORD_GUILD_ID=서버_ID
DISCORD_CHANNEL_IDS=채널_ID   # 여러 개면 쉼표로 구분, 비워두면 전체 채널
```

### 5단계 — 의존성 설치
```bash
pip install discord.py python-dotenv
```

---

## 실행

```bash
python scripts/discord_bot.py
```

콘솔에 `Bot ready:` 뜨면 정상. 이후 채널에 메시지 보내면 `ObsidianVault/10_AgentBus/inbox/` 에 `.md` 파일이 쌓입니다.

**백그라운드 실행** (창 없이):
```bash
pythonw scripts/discord_bot.py
```

---

## 봇 명령어

| 명령어 | 동작 |
|--------|------|
| `!status` | 봇이 살아있는지 확인 |
| `!help` | 명령어 목록 출력 |
| 그 외 메시지 | inbox에 자동 저장 |

---

## 안 되면

| 증상 | 해결 |
|------|------|
| `Privileged Intent` 오류 | Developer Portal → Bot → Message Content Intent ON |
| 메시지가 저장 안 됨 | `.env`의 `DISCORD_CHANNEL_IDS` 확인, 또는 비워서 전체 채널 감시 |
| 토큰 오류 | Developer Portal에서 토큰 재발급 후 `.env` 업데이트 |
