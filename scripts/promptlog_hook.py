#!/usr/bin/env python3
"""UserPromptSubmit hook — JH 발화를 promptlog에 append.

ObsidianVault/09_Knowledge_Capture/promptlog/YYYY-MM-DD.md에
시간순으로 JH의 Claude Code 세션 발화를 기록한다.

설계 원칙 (memory-evolution-direction.md §3 P0):
- 전량 축적 (선별 없음) — 거울형 취지
- 중복 스킵: (날짜+HH:MM:SS+해시) 3-tuple 체크포인트
- 민감정보 redact: API 키 패턴, 주민번호 패턴 → [REDACTED]
- BUCKY_SUBPROCESS=1 환경 시 스킵 (루프 방지)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
VAULT = ROOT / "ObsidianVault"
PROMPTLOG_DIR = VAULT / "09_Knowledge_Capture" / "promptlog"

# 민감정보 redact 패턴 — 값이 캡처그룹 1, [REDACTED] 치환
_REDACT_PATTERNS: list[re.Pattern] = [
    # API 키류 (sk-, xai-, AIza, Bearer 토큰 등)
    re.compile(r"(sk-[A-Za-z0-9_\-]{20,})", re.IGNORECASE),
    re.compile(r"(xai-[A-Za-z0-9_\-]{20,})", re.IGNORECASE),
    re.compile(r"(AIza[A-Za-z0-9_\-]{35,})", re.IGNORECASE),
    re.compile(r"(Bearer\s+[A-Za-z0-9_\-\.]{20,})", re.IGNORECASE),
    re.compile(r"(?:api[_\-]?key|token|secret)[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9_\-\.]{16,})", re.IGNORECASE),
    # 주민등록번호 패턴: 6자리-7자리
    re.compile(r"\b(\d{6}[-\s]\d{7})\b"),
    # 신용카드: 4x4 형태
    re.compile(r"\b(\d{4}[\s\-]\d{4}[\s\-]\d{4}[\s\-]\d{4})\b"),
]


def _redact(text: str) -> str:
    for pat in _REDACT_PATTERNS:
        text = pat.sub("[REDACTED]", text)
    return text


def _dedup_key(date_str: str, ts_str: str, prompt_hash: str) -> str:
    return f"{date_str}:{ts_str}:{prompt_hash}"


def _load_seen(log_path: Path) -> set[str]:
    """날짜 파일에서 이미 기록된 (ts:hash) 목록 추출."""
    seen: set[str] = set()
    if not log_path.exists():
        return seen
    for line in log_path.read_text(encoding="utf-8").splitlines():
        # <!-- dedup: HH:MM:SS:hash8 --> 형태의 숨김 주석
        m = re.match(r"<!--\s*dedup:\s*(\S+)\s*-->", line)
        if m:
            seen.add(m.group(1))
    return seen


def _ensure_frontmatter(log_path: Path, date_str: str) -> None:
    if log_path.exists():
        return
    PROMPTLOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        f"---\ntype: promptlog\ndate: {date_str}\nstatus: active\n---\n\n"
        f"# JH Promptlog — {date_str}\n\n",
        encoding="utf-8",
    )


def main() -> None:
    if os.environ.get("BUCKY_SUBPROCESS") == "1":
        return

    hook_event = os.environ.get("CLAUDE_HOOK_EVENT", "")
    if hook_event != "UserPromptSubmit":
        return

    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        return

    prompt = data.get("prompt", "").strip()
    if not prompt:
        return

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    ts_str = now.strftime("%H:%M:%S")
    prompt_redacted = _redact(prompt)
    prompt_hash = hashlib.sha1(prompt_redacted.encode("utf-8")).hexdigest()[:8]

    log_path = PROMPTLOG_DIR / f"{date_str}.md"
    seen = _load_seen(log_path)
    dedup_key = f"{ts_str}:{prompt_hash}"

    if dedup_key in seen:
        return

    _ensure_frontmatter(log_path, date_str)

    entry = (
        f"<!-- dedup: {dedup_key} -->\n"
        f"## {ts_str}\n\n"
        f"{prompt_redacted}\n\n"
    )

    with log_path.open("a", encoding="utf-8") as f:
        f.write(entry)


if __name__ == "__main__":
    main()
