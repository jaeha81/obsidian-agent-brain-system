#!/usr/bin/env python3
"""
modality_check.py — InfraNodus Modality Score 기반 지식 그래프 건강도 측정

매주 월요일 09:00 실행 (Windows Task Scheduler 또는 collection_scheduler.py에서 호출).
graphify-out/INFRANODUS_REPORT.md 에서 modality score를 읽거나,
InfraNodus API에서 직접 수신하여 경보를 출력.

사용법:
  python scripts/modality_check.py
  python scripts/modality_check.py --alert-only  # 경보 있을 때만 출력
  python scripts/modality_check.py --notify      # Discord webhook 알림 (DISCORD_WEBHOOK_URL 필요)
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).parent.parent
VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
GRAPHIFY_DIR = VAULT / "graphify-out"
REPORT_PATH = GRAPHIFY_DIR / "INFRANODUS_REPORT.md"
ALERT_LOG = GRAPHIFY_DIR / "modality_alerts.jsonl"

INFRANODUS_API_KEY = os.getenv("INFRANODUS_API_KEY", "")
INFRANODUS_GRAPH_NAME = os.getenv("INFRANODUS_GRAPH_NAME", "oabs-knowledge")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

ALERT_LOW = 0.3   # 과집중 경계
ALERT_HIGH = 0.6  # 파편화 경계


def read_score_from_report() -> tuple[float | None, str]:
    """INFRANODUS_REPORT.md에서 modality score 파싱."""
    if not REPORT_PATH.exists():
        return None, "리포트 없음 — infranodus_sync.py 먼저 실행"
    text = REPORT_PATH.read_text(encoding="utf-8", errors="ignore")
    # "**0.45**" 또는 "**N/A**" 패턴
    match = re.search(r"\*\*([0-9.]+)\*\*", text)
    if match:
        return float(match.group(1)), "리포트에서 읽음"
    return None, "리포트에 수치 없음"


def fetch_score_from_api() -> tuple[float | None, str]:
    """InfraNodus REST API에서 직접 수신."""
    if not INFRANODUS_API_KEY:
        return None, "API 키 없음"
    try:
        import urllib.request
        import urllib.parse
        url = f"https://infranodus.com/api/v1/graphs/{urllib.parse.quote(INFRANODUS_GRAPH_NAME)}/analysis"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {INFRANODUS_API_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        score = data.get("modularity") or data.get("modality")
        if score is not None:
            return float(score), "API에서 수신"
        return None, "API 응답에 score 없음"
    except Exception as e:
        return None, f"API 오류: {e}"


def evaluate(score: float) -> tuple[str, str]:
    """점수 평가 → (상태, 권고사항)."""
    if score < ALERT_LOW:
        return "OVER-CONCENTRATED", f"지식이 특정 도메인에 집중됨 (score={score:.3f} < {ALERT_LOW}). 새 도메인 노트 추가 권장."
    if score > ALERT_HIGH:
        return "FRAGMENTED", f"지식이 파편화됨 (score={score:.3f} > {ALERT_HIGH}). 도메인 간 연결 노트 작성 권장."
    return "HEALTHY", f"정상 다양성 (score={score:.3f}). 계속 유지."


def log_alert(score: float, status: str, recommendation: str):
    ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "score": score,
        "status": status,
        "recommendation": recommendation,
    }
    with open(ALERT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def send_discord_alert(score: float, status: str, recommendation: str):
    if not DISCORD_WEBHOOK_URL:
        return
    emoji = {"HEALTHY": "✅", "OVER-CONCENTRATED": "⚠️", "FRAGMENTED": "🔴"}.get(status, "📊")
    payload = {
        "content": f"{emoji} **[Bucky OS] Modality Check** ({datetime.now().strftime('%Y-%m-%d')})\n"
                   f"Score: **{score:.3f}** | 상태: **{status}**\n"
                   f"→ {recommendation}"
    }
    try:
        import urllib.request
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            DISCORD_WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10):
            pass
        print("[modality_check] Discord 알림 전송 완료")
    except Exception as e:
        print(f"[modality_check] Discord 전송 실패: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="InfraNodus Modality Score 건강도 체크")
    parser.add_argument("--alert-only", action="store_true", help="경보 있을 때만 출력")
    parser.add_argument("--notify", action="store_true", help="Discord webhook 알림")
    parser.add_argument("--api", action="store_true", help="API에서 직접 수신 (리포트 파싱 대신)")
    args = parser.parse_args()

    # Score 수집
    if args.api:
        score, source = fetch_score_from_api()
    else:
        score, source = read_score_from_report()
        if score is None and INFRANODUS_API_KEY:
            score, source = fetch_score_from_api()

    if score is None:
        print(f"[modality_check] score 수집 불가: {source}")
        print("  → infranodus_sync.py --dry-run 으로 먼저 동기화하거나, INFRANODUS_API_KEY 설정 필요")
        sys.exit(0)

    status, recommendation = evaluate(score)
    is_alert = status != "HEALTHY"

    if not args.alert_only or is_alert:
        icon = {"HEALTHY": "✅", "OVER-CONCENTRATED": "⚠️", "FRAGMENTED": "🔴"}.get(status, "📊")
        print(f"[modality_check] {icon} {status}")
        print(f"  Score: {score:.3f} (출처: {source})")
        print(f"  권고: {recommendation}")

    if is_alert:
        log_alert(score, status, recommendation)
        print(f"[modality_check] 경보 기록: {ALERT_LOG}")

    if args.notify and is_alert:
        send_discord_alert(score, status, recommendation)

    sys.exit(1 if is_alert else 0)


if __name__ == "__main__":
    main()
