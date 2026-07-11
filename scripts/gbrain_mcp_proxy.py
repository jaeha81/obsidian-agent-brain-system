#!/usr/bin/env python3
"""GBrain MCP stdio<->HTTP bridge.

Forwards JSON-RPC requests to gbrain's Streamable HTTP endpoint.
Notifications (no 'id') are forwarded but responses are suppressed.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

# 토큰 하드코딩 제거 (Stage 10 동반 핫픽스 — current_state_audit.md §4 S1).
# override=False — 호출측이 이미 설정한 env가 .env보다 우선 (bucky_client와 동일 정책).
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env", encoding="utf-8-sig", override=False)
except Exception:
    pass

GBRAIN_URL = "http://localhost:8787/mcp"
_token = os.environ.get("GBRAIN_TOKEN", "").strip()
if not _token:
    print("[gbrain_mcp_proxy] GBRAIN_TOKEN 없음 — .env에 GBRAIN_TOKEN=<token> 설정 필요", file=sys.stderr)
    sys.exit(1)
GBRAIN_TOKEN = _token if _token.startswith("Bearer ") else f"Bearer {_token}"


def send_to_gbrain(msg: dict) -> list[dict]:
    data = json.dumps(msg).encode("utf-8")
    req = urllib.request.Request(
        GBRAIN_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": GBRAIN_TOKEN,
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            ct = resp.headers.get("Content-Type", "")
            raw = resp.read().decode("utf-8")
            responses = []
            if "text/event-stream" in ct:
                for line in raw.splitlines():
                    if line.startswith("data: "):
                        try:
                            responses.append(json.loads(line[6:]))
                        except json.JSONDecodeError:
                            pass
            else:
                try:
                    responses.append(json.loads(raw))
                except json.JSONDecodeError:
                    pass
            return responses
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return [{"jsonrpc": "2.0", "error": {"code": -32000, "message": f"HTTP {e.code}: {body}"}, "id": msg.get("id")}]
    except Exception as e:
        return [{"jsonrpc": "2.0", "error": {"code": -32000, "message": str(e)}, "id": msg.get("id")}]


def main():
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        is_notification = "id" not in msg

        responses = send_to_gbrain(msg)

        if is_notification:
            # Notifications must not receive a response per JSON-RPC spec
            continue

        for resp in responses:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
