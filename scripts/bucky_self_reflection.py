#!/usr/bin/env python3
"""
Bucky Self-Reflection Engine (P2)
Bucky가 자신의 약점·갭·반복 오류를 주기적으로 분석하고
CLAUDE.md / skills / Obsidian에 개선안을 기록하는 자가 진화 루프.

흐름:
  1. 최근 대화 + 패턴 리포트 + 오류 로그 읽기
  2. Claude API로 약점 분석 요청
  3. 개선 제안을 Obsidian에 기록
  4. 반복 오류 감지 시 CLAUDE.md 규칙 추가 제안
"""
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env", encoding="utf-8", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(ROOT / "ObsidianVault")))
REFLECTION_DIR = VAULT / "09_Knowledge_Capture" / "self-reflection"
PATTERNS_DIR = VAULT / "09_Knowledge_Capture" / "patterns"
ERROR_LOG_DIR = Path(os.getenv("MEMORY_DIR", str(ROOT / ".." / ".claude" / "projects")))
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

REFLECTION_WINDOW_DAYS = 7


def _discord(msg: str) -> None:
    if DISCORD_WEBHOOK:
        try:
            requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=5)
        except Exception:
            pass


def _load_recent_patterns() -> str:
    """최근 패턴 리포트 읽기."""
    cutoff = datetime.now() - timedelta(days=REFLECTION_WINDOW_DAYS)
    reports = sorted(PATTERNS_DIR.glob("pattern-report-*.md")) if PATTERNS_DIR.exists() else []
    if not reports:
        return "패턴 리포트 없음"
    latest = reports[-1]
    try:
        return latest.read_text(encoding="utf-8")[:2000]
    except Exception:
        return "패턴 리포트 읽기 실패"


def _load_recent_errors() -> str:
    """최근 오류 로그 수집."""
    lines = []
    try:
        for log in ERROR_LOG_DIR.rglob("error-log-*.md"):
            try:
                content = log.read_text(encoding="utf-8", errors="replace")
                lines.append(f"## {log.name}\n{content[:500]}")
            except Exception:
                continue
    except Exception:
        pass
    return "\n\n".join(lines[:5]) or "오류 로그 없음"


def _load_recent_conversations() -> str:
    """최근 AgentBus inbox 메시지 샘플."""
    inbox_dir = VAULT / "10_AgentBus" / "inbox"
    cutoff = datetime.now() - timedelta(days=REFLECTION_WINDOW_DAYS)
    samples = []

    # inbox .md 파일에서 User 메시지 추출
    if inbox_dir.exists():
        import re as _re
        md_files = sorted(inbox_dir.glob("*.md"), reverse=True)
        for md_file in md_files[:50]:
            try:
                mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
                if mtime < cutoff:
                    continue
                text = md_file.read_text(encoding="utf-8", errors="replace")
                m = _re.search(r"\*\*User:\*\*\s*(.+)", text)
                if m:
                    samples.append(m.group(1).strip()[:100])
                if len(samples) >= 20:
                    break
            except Exception:
                continue

    # JSONL 파일도 있으면 보충
    if len(samples) < 5:
        jsonl = VAULT / "10_AgentBus" / "agent-room-messages.jsonl"
        if jsonl.exists():
            try:
                for line in reversed(jsonl.read_text(encoding="utf-8", errors="replace").splitlines()):
                    if not line.strip():
                        continue
                    try:
                        msg = json.loads(line)
                        content = msg.get("content", msg.get("instruction", msg.get("message", "")))
                        if content:
                            samples.append(content[:100])
                        if len(samples) >= 20:
                            break
                    except Exception:
                        continue
            except Exception:
                pass

    return "\n".join(f"- {s}" for s in samples) or "최근 대화 없음"


def _analyze_with_claude(context: str) -> str:
    """Claude API로 자기 반성 분석 실행."""
    if not CLAUDE_API_KEY:
        return _simple_analysis(context)

    prompt = f"""당신은 Bucky라는 AI 에이전트입니다.
아래 데이터를 분석하고 자기 반성 리포트를 작성하세요.

## 분석 데이터
{context}

## 작성 지침
1. **반복 약점**: 동일 유형 실수나 미흡한 점 3가지
2. **개선 제안**: 구체적 행동 계획 (스킬 생성, CLAUDE.md 규칙 추가 등)
3. **다음 진화 목표**: 1주일 내 달성할 수 있는 개선 1가지

300자 이내, 한국어로 작성하세요."""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()["content"][0]["text"]
    except Exception as e:
        print(f"[Reflection] Claude API 오류: {e}", flush=True)

    return _simple_analysis(context)


def _simple_analysis(context: str) -> str:
    """Claude API 없을 때 간단 통계 기반 분석."""
    lines = context.count("\n")
    return (
        f"## 자동 분석 (API 없음)\n\n"
        f"- 분석 데이터: {lines}줄\n"
        f"- 패턴 데이터 포함 여부: {'✅' if '패턴' in context else '❌'}\n"
        f"- 오류 로그 포함 여부: {'✅' if '오류' in context else '❌'}\n\n"
        f"> Claude API 키 설정 시 심층 분석 가능합니다."
    )


def save_reflection(analysis: str) -> Path:
    REFLECTION_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    path = REFLECTION_DIR / f"reflection-{now.strftime('%Y%m%d')}.md"
    content = f"""---
type: self-reflection
date: {now.strftime('%Y-%m-%d')}
agent: Bucky
---

# 자기 반성 리포트 — {now.strftime('%Y-%m-%d')}

{analysis}

---
_자동 생성: bucky_self_reflection.py_
"""
    path.write_text(content, encoding="utf-8")
    print(f"💭 자기 반성 저장: {path}", flush=True)
    return path


def run(notify_discord: bool = True) -> dict:
    print("💭 자기 반성 분석 시작...", flush=True)

    patterns = _load_recent_patterns()
    errors = _load_recent_errors()
    conversations = _load_recent_conversations()

    context = f"""### 최근 반복 패턴
{patterns}

### 최근 오류 로그
{errors}

### 최근 대화 샘플
{conversations}"""

    analysis = _analyze_with_claude(context)
    path = save_reflection(analysis)

    if notify_discord:
        preview = analysis[:200].replace("\n", " ")
        _discord(
            f"💭 **자기 반성 완료**\n"
            f"📄 `{path.name}`\n"
            f"> {preview}..."
        )

    return {"path": str(path), "analysis": analysis}


if __name__ == "__main__":
    result = run()
    print(json.dumps({"path": result["path"]}, ensure_ascii=False, indent=2))
