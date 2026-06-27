#!/usr/bin/env python3
"""GBrain MCP stdio<->HTTP bridge.

Forwards JSON-RPC requests to gbrain's Streamable HTTP endpoint.
Notifications (no 'id') are forwarded but responses are suppressed.
"""

import sys
import json
import urllib.request
import urllib.error

GBRAIN_URL = "http://localhost:8787/mcp"
GBRAIN_TOKEN = "Bearer gbrain_b23f8acb6163232e66cdb10394aea8b79e205794334a5bbe0cde14873bd16d25"


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
