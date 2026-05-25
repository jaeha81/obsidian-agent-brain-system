FROM python:3.11-slim

# ── 빌드 환경 변수 ──────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# ── 시스템 패키지 ─────────────────────────────────────────
# cron: 주기적 작업 실행
# curl: 헬스체크 / 다운로드
# tzdata: 한국 시간대(Asia/Seoul) 설정
RUN apt-get update && apt-get install -y --no-install-recommends \
        cron \
        curl \
        tzdata \
        ca-certificates \
    && ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime \
    && echo "Asia/Seoul" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# ── 작업 디렉터리 ─────────────────────────────────────────
WORKDIR /workspace

# ── Python 의존성 설치 ────────────────────────────────────
# requirements.txt 를 먼저 복사해 레이어 캐시 활용
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ── 소스 코드 복사 ────────────────────────────────────────
COPY . /workspace

# ── cron 설정 ─────────────────────────────────────────────
# knowledge-distiller: 6시간마다 실행 (0,6,12,18시)
# collection-scheduler: 매일 새벽 6시 실행
RUN echo "0 0,6,12,18 * * * root cd /workspace && python scripts/knowledge_distiller.py --limit 20 >> /workspace/logs/distiller-cron.log 2>&1" \
        > /etc/cron.d/bucky-distiller \
    && echo "0 6 * * * root cd /workspace && python scripts/collection_scheduler.py --run >> /workspace/logs/collector-cron.log 2>&1" \
        > /etc/cron.d/bucky-collector \
    && chmod 0644 /etc/cron.d/bucky-distiller /etc/cron.d/bucky-collector \
    && crontab /etc/cron.d/bucky-distiller \
    && crontab /etc/cron.d/bucky-collector

# ── 로그 디렉터리 확보 ────────────────────────────────────
RUN mkdir -p /workspace/logs

# ── 기본 실행 (docker-compose 의 command 로 오버라이드 가능) ──
CMD ["python", "scripts/preflight_check.py", "--docker"]
