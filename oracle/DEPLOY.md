# Bucky Core API — 라이브 배포 런북 (Oracle #2)

> **상태: 절차 설계(준비)만 완료. 실제 실행은 승인 게이트 대상.**
> CLAUDE.md 게이트 ③(시크릿 #2 배치)·⑥(systemd 등록)은 **사용자 승인 후에만** 실행한다.
> 이 문서에는 실제 토큰·비밀을 절대 넣지 않는다(플레이스홀더·생성 명령만).
>
> 대상 호스트: Oracle Cloud #2 `161.33.204.158` (aarch64, PyYAML 없음 → stdlib 전용 서버)
> 검증 상태: 로컬 종단 테스트 통과 — `test_api_server`(38) + `test_client`(9) + `test_pipeline_e2e`(10).

---

## 0. 배포 대상 구성요소

| 구성요소 | 위치 | 실행 주체 |
|---|---|---|
| API 서버 | `oracle/core/api_server.py` (:8700, stdlib) | #2 (systemd) |
| Agent Registry | `oracle/core/agents.yaml` | #2 (기동 시 로드) |
| Task Queue DB | `<repo>/data/bucky_tasks.db` (SQLite WAL) | #2 (자동 생성) |
| submit 클라이언트 | `oracle/core/client.py` | Discord 봇(집PC/로컬) |
| 집PC 폴링 워커 | `oracle/core/worker.py` (구현 완료) | 집PC (pull) |

집PC는 인바운드 포트가 필요 없다(`/claim` 폴링 pull). #2만 공개 엔드포인트를 연다.

> **실배포 방식(2026-07-15 확정)**: 공개 엔드포인트를 열지 않고 **집PC→#2 SSH 포워드 터널**로 연결한다.
> 집PC에서 `ssh -i <key> -N -L 127.0.0.1:8700:127.0.0.1:8700 ubuntu@161.33.204.158` 를 상시 띄우고,
> 워커는 `ORACLE_API_URL=http://127.0.0.1:8700` 로 폴링한다. 도메인·TLS·OCI 인그레스 변경 불필요(SSH가 암호화).

---

## 1. 코드 배치 (승인 불필요 — 일반 배포)

```bash
# #2에서
cd /opt/ai-os            # 또는 운영 repo 경로
git fetch origin && git checkout master && git pull --ff-only
python3 --version        # 3.11+ 권장 (UPDATE…RETURNING = SQLite 3.35+ 필요)
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"   # 3.35.0 이상 확인
```

⚠️ `/claim`의 원자 선점은 `UPDATE … RETURNING`(SQLite ≥ 3.35)에 의존한다. 구버전이면 기동은 되나 claim이 실패하므로 **버전 확인 필수**.

---

## 2. 🔒 [게이트 ③] 인증 토큰 배치 — **승인 후 실행**

```bash
# 토큰 생성 (32바이트 hex). 출력값을 저장소·로그·채팅에 남기지 않는다.
sudo mkdir -p /etc/ai-os
sudo chmod 755 /etc/ai-os                     # 서비스 계정이 디렉터리를 traverse 해야 함(mkdir 기본 700이면 못 읽음)
python3 -c "import secrets; print(secrets.token_hex(32))" | sudo tee /etc/ai-os/bucky_api_token >/dev/null
sudo chown <서비스계정>:<서비스계정> /etc/ai-os/bucky_api_token   # ⚠️ systemd User= 와 동일 계정(예: ubuntu). root 소유면 비root 서비스가 못 읽어 기동 실패
sudo chmod 600 /etc/ai-os/bucky_api_token     # 소유자만 읽기(내용은 여전히 보호)
```

> ⚠️ **실배포 검증(2026-07-15)**: 토큰을 `root:600`으로 두면 `User=ubuntu` 서비스가 `PermissionError`로 기동 실패한다. 토큰 소유자를 **systemd `User=`와 같은 계정**으로 맞추고, `/etc/ai-os` 디렉터리는 그 계정이 통과할 수 있게 `755`로 둔다.

- 서버 기본 경로 `BUCKY_API_TOKEN_FILE=/etc/ai-os/bucky_api_token` 를 그대로 사용(env로 토큰 노출 회피 — env는 `/proc`로 샐 수 있음).
- **동일 토큰**을 submit 측(Discord 봇 호스트)의 `BUCKY_API_TOKEN`에 배치해야 호출이 인증된다. 전달은 안전 채널로만.

---

## 3. 🔒 [게이트 ⑥] systemd 등록 — **승인 후 실행**

`/etc/systemd/system/bucky-api.service` (템플릿 — 경로/User는 호스트에 맞게 수정):

```ini
[Unit]
Description=Bucky Core API (Oracle #2)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=aiops
WorkingDirectory=/opt/ai-os
Environment=BUCKY_API_TOKEN_FILE=/etc/ai-os/bucky_api_token
Environment=BUCKY_API_PORT=8700
# 기본 127.0.0.1 바인드 유지 → 역프록시(4장) 뒤에 둔다. 직접 노출 시에만 --host 0.0.0.0.
ExecStart=/usr/bin/python3 -X utf8 /opt/ai-os/oracle/core/api_server.py --host 127.0.0.1 --port 8700
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/ai-os/data /opt/ai-os/logs
ProtectHome=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bucky-api
systemctl status bucky-api --no-pager
```

---

## 4. 공개 노출 — 역프록시 + TLS (권장)

토큰이 `Authorization: Bearer`로 평문 전송되므로 공개망에는 **TLS 필수**. API는 127.0.0.1에 두고 역프록시로만 노출한다.

- Caddy 예: `api.<도메인> { reverse_proxy 127.0.0.1:8700 }` (Let's Encrypt 자동)
- OCI Security List / firewall: 443만 인그레스 허용. 8700은 외부 차단.
- `GET /health`는 무인증 — 모니터링/로드밸런서 헬스체크에 사용.

> 최소 대안(도메인 없이): `--host 0.0.0.0` + OCI로 특정 IP만 허용. 단 집PC IP가 유동이면 취약 → 역프록시+TLS 권장.

---

## 5. 배포 검증 (연결 후)

```bash
# 헬스 (무인증)
curl -s https://api.<도메인>/health           # {"status":"ok"}
# 레지스트리 (인증)
curl -s -H "Authorization: Bearer $TOK" https://api.<도메인>/api/v1/agents | python3 -m json.tool
# submit 왕복 (client.py)
ORACLE_API_URL=https://api.<도메인> BUCKY_API_TOKEN=$TOK \
  python3 -c "import sys; sys.path.insert(0,'oracle/core'); from client import submit_task,get_task; \
r=submit_task('chat',payload={'instruction':'ping'}); print(r); print(get_task(r['task_id']))"
```

기대: submit → `{"task_id","status":"pending"}`, get → 동일 태스크 pending.

---

## 6. Discord 봇 연동 (submit 측 호스트)

`/oracle` 명령이 라이브로 동작하려면 봇 호스트 `.env`에 추가:

```dotenv
ORACLE_API_URL=https://api.<도메인>
BUCKY_API_TOKEN=<2장에서 배치한 동일 토큰>
```

미설정 시 `client.py`는 기본 `http://127.0.0.1:8700`로 시도하고, 토큰 없으면 `OracleClientError`로 명확히 실패한다(봇은 크래시 없이 오류 메시지 응답).

---

## 7. 남은 후속 (별도 Phase)

- ~~**집PC 폴링 워커**~~ **완료**: `oracle/core/worker.py`(claim 루프+실행+status 보고), `client.py`에 `claim_task`/`update_status` 구현됨. 2026-07-15 실배포·종단 검증(submit→claim→completed).
- **[미결] 공개 대시보드 실데이터 연결**: `scripts/generate_brain_status.py`는 **집PC 로컬** `data/bucky_tasks.db`를 읽는데, 라이브 태스크는 **#2의** `bucky_tasks.db`에 쌓인다(split-brain). 대시보드에 오라클 라이브 데이터를 반영하려면 생성기를 #2에서 돌리거나, 파이프라인이 터널로 #2 DB/usage를 당겨오게 해야 한다.
- **[미결] usage(by_model) 실데이터**: echo 스텁은 usage 원장에 기록하지 않는다. `config/bucky.yaml features.worker_adapter_dispatch: true` + 실제 provider 호출 시에만 `records`/`by_model`이 찬다.
- **[미결] 상시화**: 집PC의 SSH 터널 + `worker.py`를 예약작업/시작프로그램으로 등록(현재는 세션 임시 기동).
- 로그 로테이션(`logs/api/api_YYYYMMDD.jsonl` 일자별 append), DB 백업 정책.
- Scheduler·MCP Server는 Phase 5.
