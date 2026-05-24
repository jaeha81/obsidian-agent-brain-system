#!/usr/bin/env python3
"""
Stop Hook - 컨텍스트 사용량 임계값 초과 시 경고 출력.
stderr 출력 → 사용자 화면에 표시됨.
"""
import json
import sys
from pathlib import Path

THRESHOLDS = {90: "CRITICAL", 75: "WARNING", 50: "CAUTION"}
DEFAULT_LIMIT = 200_000


def get_tokens(transcript_path: str) -> int:
    path = Path(transcript_path)
    if not path.exists():
        return 0
    latest = 0
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if '"usage"' not in line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                usage = (
                    event.get("message", {}).get("usage")
                    or event.get("usage")
                    or {}
                )
                if isinstance(usage, dict):
                    total = sum(
                        usage.get(k, 0) or 0
                        for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
                    )
                    if total:
                        latest = total
    except OSError:
        pass
    return latest


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        data = {}

    transcript = data.get("transcript_path", "")
    tokens = get_tokens(transcript)
    if not tokens:
        return

    pct = round((tokens / DEFAULT_LIMIT) * 100)

    for threshold, level in sorted(THRESHOLDS.items(), reverse=True):
        if pct >= threshold:
            msgs = {
                "CRITICAL": f"CONTEXT {pct}% - 새 세션 시작 필요 (/compact 사용 금지)",
                "WARNING":  f"CONTEXT {pct}% - 새 세션 시작을 권장합니다",
                "CAUTION":  f"CONTEXT {pct}% - 컨텍스트 50% 초과, 모니터링 필요",
            }
            print(f"[Context {level}] {msgs[level]}", file=sys.stderr)
            break


if __name__ == "__main__":
    main()
