# CHSH Mining Bot — Bucky Context Pack

> 상태: **활성**  
> 갱신일: 2026-06-19  
> 귀속: Bucky 오케스트레이터

---

## 프로젝트 정보

| 항목 | 값 |
|---|---|
| **project** | `AI-mining-CHSHAUTOMATION` |
| **repo** | `https://github.com/jaeha81/AI-mining-CHSHAUTOMATION` |
| **local path** | `D:\ai프로젝트\AI-mining-CHSHAUTOMATION` |
| **Python** | `C:\Python314\python.exe` |
| **운영 모드** | 쇼츠자동화 동일 아키텍처 (Windows Task Scheduler + Discord 채널 허브) |

---

## goal

AI가 금융/주식/재테크 콘텐츠를 자동 생성하고 YouTube·X·TikTok·Instagram에 업로드하여 광고 수익을 자동으로 집계·관리하는 수익형 자동화 시스템.

---

## baseline (2026-06-19 기준)

- ✅ 저장소 클론 완료
- ✅ 패키지 설치 완료 (requirements.txt)
- ✅ `.env` 생성 완료 (API 키 미입력)
- ✅ 쇼츠자동화 운영방식 적용 완료:
  - Windows Task Scheduler 스크립트 (`setup_scheduler.ps1`)
  - Evolution 에이전트 (`core/evolution_agent.py`)
  - 실제 에이전트 상태 추적 (`analytics/models.py` → `agent_states`, `workflow_jobs`, `evolution_logs`)
  - Discord 4채널 Webhook 분리 (`notifications/discord_webhook.py`)
- ⚠️ `.env`에 실제 API 키 미입력 상태
- ⚠️ Discord 서버에 채널 미생성 상태
- ⚠️ `setup_scheduler.ps1` 미실행 상태

---

## target_state

```
01:30 KST → Evolution 에이전트 → #chsh-status 알림
02:00 KST → 일일 파이프라인 → #chsh-status 알림
07/12/18시 → 업로드 실행
23:00 KST → 수익 집계 → #chsh-revenue 리포트
Discord 슬래시 커맨드 → 실제 DB 데이터 응답
```

---

## scope

```
D:\ai프로젝트\AI-mining-CHSHAUTOMATION\
├── main.py                    # 진입점 (--evolve --upload --revenue-sync 추가됨)
├── core/
│   ├── scheduler.py           # APScheduler + Discord 알림 훅
│   ├── evolution_agent.py     # 신규 — Claude CLI subprocess
│   ├── trend_collector.py
│   └── content_generator.py
├── discord_bot/
│   ├── bot.py                 # /에이전트 → 실제 DB 조회
│   └── embeds.py
├── analytics/
│   └── models.py              # agent_states, workflow_jobs, evolution_logs 추가됨
├── notifications/
│   ├── discord_webhook.py     # 신규 — 4채널 webhook
│   └── telegram_bot.py
├── config/settings.py         # DISCORD_WEBHOOK_* 4개 추가됨
├── .env                       # API 키 입력 필요
└── setup_scheduler.ps1        # 신규 — Task Scheduler 등록
```

---

## Discord 채널 구조

버키 Discord 서버(Guild: `1507232437154091122`)에 단일 채널로 귀속:

```
JH Agent System Discord Server
└── #jh-chsh-mining  → 모든 알림 + 제어 커맨드
```

**제어 커맨드 (채널에 직접 입력):**
```
!mining status       → python main.py --status
!mining run          → python main.py --run-now (파이프라인 즉시)
!mining evolve       → python main.py --evolve
!mining upload       → python main.py --upload
!mining revenue      → python main.py --revenue-sync

또는 JSON 형식:
[CHSH_CMD] {"action": "run"}
[CHSH_CMD] {"action": "status"}
```

**버키 `.env` 필수 항목:**
```
JH_CHSH_MINING_CHANNEL_ID=<채널 ID>
CHSH_MINING_DISCORD_WEBHOOK=<webhook URL>
```

Discord 슬래시 커맨드(봇 직접 실행 시): `/상태` `/실행` `/수익` `/주간수익` `/테스트` `/에이전트` `/입금현황` `/세금현황` `/도움말`

---

## role

- **Claude Code**: 구현, 파일 수정, 기능 추가
- **Codex**: 독립 검수 (read-only)
- **Bucky**: 오케스트레이터, 프로젝트 지침 관리

---

## constraints

- `.env` 파일 내용 노출 금지 (API 키, 토큰)
- `data/revenue.db` DROP 금지
- `git push` 전 사용자 명시 승인 필요
- 파이프라인 수정 시 반드시 테스트 모드 (`python main.py --test`) 먼저 실행

---

## references

| 파일 | 역할 |
|---|---|
| `core/evolution_agent.py` | Claude CLI evolution 패턴 |
| `core/scheduler.py` | 스케줄 + 에이전트 상태 훅 |
| `discord_bot/bot.py` | Discord 슬래시 커맨드 |
| `analytics/models.py` | DB 모델 + 헬퍼 |
| `notifications/discord_webhook.py` | 채널별 알림 |
| `setup_scheduler.ps1` | Windows Task Scheduler 등록 |
| `D:\ai프로젝트\쇼츠자동화\shorts-local-agent\` | 벤치마킹 레퍼런스 |

---

## verification

```powershell
# 1. DB 테이블 확인
python -c "from analytics.models import init_db; init_db(); print('DB OK')"

# 2. 상태 출력
python main.py --status

# 3. Evolution 테스트 (Claude API 키 필요)
python main.py --evolve

# 4. Task Scheduler 등록 (관리자 권한)
.\setup_scheduler.ps1
Get-ScheduledTask | Where-Object {$_.TaskName -like "MiningBot*"}

# 5. Discord 봇 테스트 (DISCORD_BOT_TOKEN 필요)
python main.py --discord
```

---

## done_when

- [ ] `.env`에 `ANTHROPIC_API_KEY` + `DISCORD_BOT_TOKEN` 입력
- [ ] Discord 서버에 `💰 CHSH Mining` 카테고리 + 4채널 생성
- [ ] 채널별 Webhook URL을 `.env`에 입력
- [ ] `setup_scheduler.ps1` 관리자 권한으로 실행
- [ ] `python main.py --full` 실행 후 Discord `/상태` 응답 확인

---

## record_path

`G:\내 드라이브\obsidian-agent-brain-system\ObsidianVault\03_Projects\agents\chsh-mining.md`

---

## 쇼츠자동화 vs CHSH Mining 운영방식 비교

| 항목 | 쇼츠자동화 | CHSH Mining |
|---|---|---|
| DB | Turso (cloud) | SQLite (local) |
| Dashboard | Next.js + Vercel | FastAPI (localhost:8000) |
| 스케줄 | Vercel Cron + Task Scheduler | APScheduler + Task Scheduler |
| Evolution | Claude CLI subprocess | Claude CLI subprocess (동일) |
| Discord 알림 | 단일 webhook | 4채널 webhook 분리 |
| 에이전트 추적 | agent_states 테이블 | agent_states 테이블 (동일) |

*Related: [[agents-hub]]*

