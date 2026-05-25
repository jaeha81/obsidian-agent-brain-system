# Bucky Brain — Docker 3-PC 동기화 환경

## 서비스 구성

| 서비스 | 컨테이너명 | 역할 | 프로파일 |
|--------|-----------|------|---------|
| bucky-core | bucky-core | Discord 봇 + 에이전트 매니저 | 기본 (항상 실행) |
| knowledge-distiller | knowledge-distiller | 지식 정제기 (6시간마다 실행) | `distiller` / `full` |
| collection-scheduler | collection-scheduler | 데이터 수집 스케줄러 | `collector` / `full` |
| redis | bucky-redis | AgentBus 상태 공유 | `redis` / `full` |

## PC별 초기 설정 (공통 절차)

```bash
# 1. PC 환경 자동 감지 후 docker/.env 생성
python scripts/docker_sync.py --setup

# 2. docker/.env 열어서 API 키 입력 (DISCORD_BOT_TOKEN, ANTHROPIC_API_KEY)
#    절대 커밋하지 마세요 — .gitignore 에 이미 등록됨

# 3. 서비스 시작 (bucky-core 만)
python scripts/docker_sync.py --start

# 4. 전체 서비스 시작 (지식 정제기 + 수집기 + Redis 포함)
python scripts/docker_sync.py --start --profile full
```

## PC별 경로 매핑

| PC | PC_TYPE | LOCAL_AI_PATH | VAULT_BASE_PATH |
|----|---------|---------------|-----------------|
| 집 PC | `home` | `D:/ai프로젝트` | G드라이브 자동 |
| 노트북 | `laptop` | `C:/ai프로젝트` | G드라이브 자동 |
| 사무실 | `office` | `C:/ai프로젝트` | G드라이브 자동 |

> `VAULT_BASE_PATH` 와 `GDRIVE_PATH` 는 3개 PC 모두 G드라이브를 공유하므로 동일합니다.
> `LOCAL_AI_PATH` 만 PC에 따라 다릅니다. `--setup` 으로 자동 설정됩니다.

## 자주 쓰는 명령

```bash
python scripts/docker_sync.py --status          # 실행 중인 서비스 확인
python scripts/docker_sync.py --logs            # 전체 로그 스트리밍
python scripts/docker_sync.py --logs --service bucky-core   # 특정 서비스 로그
python scripts/docker_sync.py --stop            # 전체 중단
python scripts/docker_sync.py --setup --force  # .env 강제 재생성
```

## 볼륨 마운트 구조

```
호스트                              컨테이너
─────────────────────────────────  ─────────────────
VAULT_BASE_PATH (G드라이브)    →   /vault
LOCAL_AI_PATH   (D 또는 C)    →   /ai-project
GDRIVE_PATH     (G드라이브)    →   /gdrive (읽기 전용)
scripts/, configs/             →   /workspace/scripts, /workspace/configs (읽기 전용)
bucky-logs (named volume)      →   /workspace/logs
```

## 주의사항

- `docker/.env` 는 `.gitignore` 에 포함됩니다. 절대 커밋하지 마세요.
- G드라이브 동기화가 활성화된 상태에서 실행해야 볼륨 마운트가 정상 작동합니다.
- Docker Desktop → Settings → Resources → File Sharing 에 G드라이브 경로를 추가하세요.
