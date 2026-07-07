# Archived watcher scripts (2026-07-07)

집 PC 봇 감시자 **canonical = `scripts/discord_bot_watchdog.py`** 하나로 단일화.
auto-start 체인: `BuckyDiscordWatchdog.lnk` → `scripts/start_watchdog_silent.vbs` → `discord_bot_watchdog.py`.

아래 파일들은 아무것도 auto-start 하지 않던 orphan/중복이라 여기로 이동:

| 파일 | 왜 아카이브했나 |
|------|----------------|
| `bucky_bot_supervisor.py` | `bot_restart.signal` 감시 기능이 죽음 — 봇의 `!restart`는 `os.execv` 자기재시작(discord_bot.py:4387)이라 슈퍼바이저 협조 불필요 |
| `bucky_bot_supervisor_patched.py` | 위 구버전. `start_bucky_supervisor_silent.vbs`가 가리키던 대상이나 startup 미등록 |
| `bucky_watchdog.py` | 웹훅+에스컬레이션판. Docker 지향, 어떤 런처도 참조 안 함 |
| `start_bucky_supervisor_silent.vbs` | 위 supervisor 런처. startup 폴더에 없음 |
| `discord_bot_watchdog.ps1` | 자신을 "canonical supervisor"라 칭하며 bucky_bot_supervisor.py를 가리킴 → 실제 실행(discord_bot_watchdog.py)과 모순되어 혼란 유발 |

> P1(Oracle 전면 이관, systemd) 시 이 Windows 감시 계층은 대체될 예정. 복구 필요 시 `git mv` 되돌리면 됨.
