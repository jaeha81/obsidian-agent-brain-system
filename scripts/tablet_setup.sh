#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# tablet_setup.sh — BuckyOS 태블릿 음성 인테이크 원클릭 설치
#
# 대상: Samsung Galaxy Tab (Android 12+, Termux)
# 사용법:
#   curl -fsSL https://raw.githubusercontent.com/jaeha8104/obsidian-agent-brain-system/master/scripts/tablet_setup.sh | bash
#   또는:
#   bash tablet_setup.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

BUCKY_DIR="$HOME/bucky"
CONFIG_FILE="$HOME/.bucky_tablet_config.json"
REPO_RAW="https://raw.githubusercontent.com/jaeha8104/obsidian-agent-brain-system/master/scripts"

# ── 컬러 출력 헬퍼 ─────────────────────────────────────────────────────────
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
RESET="\033[0m"

ok()   { echo -e "${GREEN}  ✅ $*${RESET}"; }
warn() { echo -e "${YELLOW}  ⚠  $*${RESET}"; }
err()  { echo -e "${RED}  ❌ $*${RESET}"; exit 1; }

echo "══════════════════════════════════════════════"
echo " BuckyOS 태블릿 음성 인테이크 설치 스크립트"
echo " Phase 1 — 로컬 Whisper (무과금)"
echo "══════════════════════════════════════════════"
echo ""

# ── Step 1: Termux 패키지 업데이트 ──────────────────────────────────────────
echo "[1/6] Termux 패키지 업데이트..."
if command -v pkg &>/dev/null; then
    pkg update -y && pkg upgrade -y
    ok "pkg 업데이트 완료"
elif command -v apt-get &>/dev/null; then
    warn "Termux 외 환경 감지 (apt-get). 계속 진행..."
else
    warn "pkg/apt-get 없음. 수동 환경으로 간주."
fi

# ── Step 2: 시스템 의존성 설치 ──────────────────────────────────────────────
echo ""
echo "[2/6] 시스템 의존성 설치 (python, portaudio, ffmpeg)..."
if command -v pkg &>/dev/null; then
    pkg install -y python python-pip portaudio ffmpeg
    ok "시스템 패키지 설치 완료"
else
    warn "pkg 없음. Python, portaudio, ffmpeg 이미 설치됐다고 가정."
fi

# Python 확인
command -v python3 &>/dev/null || err "Python3 없음. 수동 설치 필요."
ok "Python3: $(python3 --version)"

# ── Step 3: Python 의존성 ────────────────────────────────────────────────────
echo ""
echo "[3/6] Python 의존성 설치 (sounddevice, numpy, scipy, requests, whisper)..."
python3 -m pip install --upgrade pip --quiet
python3 -m pip install sounddevice numpy scipy requests --quiet
ok "sounddevice, numpy, scipy, requests 설치 완료"

echo "  Whisper 설치 중 (~150MB 다운로드, 시간이 걸릴 수 있음)..."
python3 -m pip install openai-whisper --quiet
ok "openai-whisper 설치 완료"

# ── Step 4: Bucky 스크립트 다운로드 ─────────────────────────────────────────
echo ""
echo "[4/6] Bucky 스크립트 다운로드..."
mkdir -p "$BUCKY_DIR"

SCRIPT_URL="$REPO_RAW/tablet_voice_intake.py"
if command -v curl &>/dev/null; then
    curl -fsSL "$SCRIPT_URL" -o "$BUCKY_DIR/tablet_voice_intake.py"
elif command -v wget &>/dev/null; then
    wget -q "$SCRIPT_URL" -O "$BUCKY_DIR/tablet_voice_intake.py"
else
    err "curl/wget 없음. $SCRIPT_URL 을 $BUCKY_DIR/tablet_voice_intake.py 에 수동 복사하세요."
fi
chmod +x "$BUCKY_DIR/tablet_voice_intake.py"
ok "tablet_voice_intake.py → $BUCKY_DIR/"

# ── Step 5: 설정 파일 생성 ───────────────────────────────────────────────────
echo ""
echo "[5/6] 설정 파일 확인..."
if [ ! -f "$CONFIG_FILE" ]; then
    cat > "$CONFIG_FILE" <<'EOF'
{
  "bucky_server": "http://192.168.x.x:8765",
  "device_name": "galaxy-tab-jh",
  "vault_path": "04_SiteLog",
  "stt_mode": "local-whisper",
  "whisper_model": "base",
  "auto_upload": true,
  "upload_interval_sec": 30,
  "sample_rate": 16000,
  "channels": 1
}
EOF
    ok "설정 파일 생성됨: $CONFIG_FILE"
    warn "bucky_server 주소를 PC의 로컬 IP로 수정해주세요!"
    warn "확인 방법(PC): ipconfig | findstr IPv4   (Windows)"
    warn "              hostname -I               (Linux/Mac)"
else
    ok "설정 파일 이미 존재: $CONFIG_FILE"
fi

# ── Step 6: 의존성 최종 확인 ─────────────────────────────────────────────────
echo ""
echo "[6/6] 의존성 최종 확인..."
python3 "$BUCKY_DIR/tablet_voice_intake.py" --check

# ── 완료 메시지 ──────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo " 설치 완료! 다음 단계:"
echo ""
echo "  1. 설정 파일에서 Bucky 서버 주소 설정:"
echo "     nano $CONFIG_FILE"
echo "     → bucky_server 값을 PC의 로컬 IP로 변경"
echo "       예: \"bucky_server\": \"http://192.168.1.100:8765\""
echo ""
echo "  2. Bucky 서버가 PC에서 실행 중인지 확인:"
echo "     (PC) python scripts/bucky_chat_server.py --host 0.0.0.0"
echo ""
echo "  3. 음성 인테이크 시작:"
echo "     python3 $BUCKY_DIR/tablet_voice_intake.py --start"
echo ""
echo "  4. (선택) 더 정확한 모델 사용:"
echo "     python3 $BUCKY_DIR/tablet_voice_intake.py --start --model small"
echo "══════════════════════════════════════════════"
