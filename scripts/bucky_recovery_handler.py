#!/usr/bin/env python3
"""
Bucky Recovery Handler — ClaudeCode/Codex 긴급 복구 실행기

역할:
  - AgentBus inbox의 emergency_recovery 메시지 감시
  - 메시지 수신 시:
    1. 오류 로그 분석
    2. 일반적인 원인 자동 수정 (env 누락, 포트 충돌, lock 파일 등)
    3. Bucky 재시작 시도
    4. 수정 불가 시 Discord로 사용자 에스컬레이션

실행: python scripts/bucky_recovery_handler.py
  보통 ClaudeCode 프로필 또는 Docker codex 서비스로 구동
"""

import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8")

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")
AGENTBUS_INBOX = _ROOT / "ObsidianVault" / "10_AgentBus" / "inbox"
AGENTBUS_PROCESSED = _ROOT / "ObsidianVault" / "10_AgentBus" / "processed"
GIT_LOCK = _ROOT / ".git" / "index.lock"

POLL_INTERVAL = 10  # inbox 폴링 주기(초)


def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"[RECOVERY {ts()}] {msg}", flush=True)


def send_webhook(text: str) -> None:
    if not DISCORD_WEBHOOK:
        return
    try:
        import urllib.request
        data = json.dumps({"content": text}).encode()
        req = urllib.request.Request(
            DISCORD_WEBHOOK,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


# ── 자동 수정 규칙 ─────────────────────────────────────────────────────────────

KNOWN_ERRORS = [
    {
        "pattern": "index.lock",
        "description": "git index.lock 고착",
        "fix": lambda: GIT_LOCK.unlink(missing_ok=True),
    },
    {
        "pattern": "ModuleNotFoundError",
        "description": "Python 패키지 누락",
        "fix": lambda: subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r",
             str(_ROOT / "requirements.txt")],
            timeout=120, check=False
        ),
    },
    {
        "pattern": "DISCORD_BOT_TOKEN",
        "description": "Discord 토큰 미설정",
        "fix": None,  # 사용자 개입 필요
    },
    {
        "pattern": "Address already in use",
        "description": "포트 충돌",
        "fix": None,  # 포트 번호 파악 필요
    },
    {
        "pattern": "ConnectionRefusedError",
        "description": "연결 거부 — 외부 서비스 다운",
        "fix": None,
    },
]


def analyze_error_log(log_path: str) -> list[dict]:
    """오류 로그에서 알려진 패턴 탐색 → 수정 가능한 항목 반환"""
    matches = []
    try:
        content = Path(log_path).read_text(encoding="utf-8", errors="replace")
        for rule in KNOWN_ERRORS:
            if rule["pattern"] in content:
                matches.append(rule)
    except Exception:
        pass
    return matches


def attempt_auto_fixes(matches: list[dict]) -> list[str]:
    """자동 수정 가능한 항목 실행 → 수행한 작업 목록 반환"""
    done = []
    for m in matches:
        if m["fix"] is not None:
            try:
                m["fix"]()
                done.append(m["description"])
                log(f"자동 수정: {m['description']}")
            except Exception as e:
                log(f"수정 실패 ({m['description']}): {e}")
    return done


def restart_bucky() -> bool:
    """Bucky Discord 봇 재시작 시도"""
    script = str(_ROOT / "scripts" / "discord_bot.py")
    try:
        # 기존 프로세스 종료
        if platform.system() == "Windows":
            subprocess.run(
                ["taskkill", "/F", "/FI", "WINDOWTITLE eq discord_bot*"],
                capture_output=True, timeout=5
            )
        else:
            subprocess.run(["pkill", "-f", "discord_bot.py"],
                           capture_output=True, timeout=5)
        time.sleep(2)

        # 재시작
        proc = subprocess.Popen(
            [sys.executable, script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(3)
        running = proc.poll() is None
        log(f"Bucky 재시작 {'성공' if running else '실패'} (PID {proc.pid})")
        return running
    except Exception as e:
        log(f"재시작 실패: {e}")
        return False


# ── 메시지 처리 ───────────────────────────────────────────────────────────────

def process_recovery_message(msg_file: Path) -> None:
    try:
        msg = json.loads(msg_file.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"메시지 파싱 실패: {e}")
        return

    if msg.get("type") != "emergency_recovery":
        return

    payload = msg.get("payload", {})
    agent = payload.get("agent", "unknown")
    failures = payload.get("consecutive_failures", 0)
    log_path = payload.get("error_log", "")

    log(f"긴급 복구 요청 수신: agent={agent}, failures={failures}")
    send_webhook(f"🔧 **Recovery Handler 시작** — `{agent}` 복구 시도 중...")

    # 1. 오류 분석
    matches = analyze_error_log(log_path)
    fixable = [m for m in matches if m["fix"] is not None]
    manual = [m for m in matches if m["fix"] is None]

    # 2. 자동 수정
    fixed = attempt_auto_fixes(fixable)

    # 3. 재시작
    if agent == "bucky":
        success = restart_bucky()
    else:
        success = False  # 다른 에이전트는 향후 확장

    # 4. 결과 보고
    if success:
        result_lines = [f"✅ **`{agent}` 복구 완료**"]
        if fixed:
            result_lines.append("자동 수정: " + ", ".join(fixed))
        send_webhook("\n".join(result_lines))
    else:
        escalation = [f"🆘 **자동 복구 실패 — 사용자 개입 필요**"]
        escalation.append(f"에이전트: `{agent}` | 연속 실패: {failures}회")
        if manual:
            escalation.append("수동 처리 필요:")
            for m in manual:
                escalation.append(f"  • {m['description']}")
        escalation.append(f"오류 로그: `{Path(log_path).name if log_path else 'N/A'}`")
        send_webhook("\n".join(escalation))

    # 5. 처리 완료 이동
    AGENTBUS_PROCESSED.mkdir(parents=True, exist_ok=True)
    dest = AGENTBUS_PROCESSED / msg_file.name
    msg_file.rename(dest)
    log(f"메시지 처리 완료: {msg_file.name}")


# ── 메인 루프 ─────────────────────────────────────────────────────────────────

def main() -> None:
    log("Recovery Handler 시작 — inbox 감시 중")
    AGENTBUS_INBOX.mkdir(parents=True, exist_ok=True)

    while True:
        for msg_file in sorted(AGENTBUS_INBOX.glob("*.json")):
            try:
                raw = json.loads(msg_file.read_text(encoding="utf-8"))
                if raw.get("type") == "emergency_recovery":
                    process_recovery_message(msg_file)
            except Exception:
                pass
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
