#!/usr/bin/env python3
"""패턴 추출기 — 반복 요청 패턴 감지 → 스킬 자동화 제안

대화 로그에서 반복 패턴을 감지하고 자동화 스킬 생성을 제안합니다.
같은 유형의 요청이 2회 이상 → 스킬 생성 권고.

사용법:
    python scripts/pattern_extractor.py          # 오늘 로그 분석
    python scripts/pattern_extractor.py --days 7 # 최근 7일 분석
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
VAULT = ROOT / "ObsidianVault"
INBOX = VAULT / "10_AgentBus" / "inbox"
SKILLS_DIR = ROOT / ".claude" / "skills"
PATTERN_DB = ROOT / "ObsidianVault" / "00_System" / "pattern_db.json"


# ── 패턴 카테고리 ─────────────────────────────────────────────────────────────

PATTERN_RULES: list[dict] = [
    {
        "id": "deploy_request",
        "name": "배포 요청",
        "keywords": ["배포해", "배포해줘", "vercel", "올려줘"],
        "skill_suggestion": "jh-deploy",
        "threshold": 2,
    },
    {
        "id": "landing_page",
        "name": "랜딩 페이지 생성",
        "keywords": ["랜딩", "랜딩페이지", "landing page"],
        "skill_suggestion": "bucky-landing-generator",
        "threshold": 2,
    },
    {
        "id": "knowledge_save",
        "name": "지식 저장",
        "keywords": ["저장해", "기록해", "obsidian에", "노트로"],
        "skill_suggestion": "jh-capture",
        "threshold": 3,
    },
    {
        "id": "graph_view",
        "name": "그래프 조회",
        "keywords": ["그래프", "graphify", "그래플", "지식 그래프"],
        "skill_suggestion": "bucky-graphify",
        "threshold": 2,
    },
    {
        "id": "code_review",
        "name": "코드 리뷰",
        "keywords": ["리뷰", "검토해", "확인해줘", "코드 봐줘"],
        "skill_suggestion": "jh-code-review",
        "threshold": 2,
    },
    {
        "id": "briefing",
        "name": "브리핑/상태 확인",
        "keywords": ["브리핑", "상태", "진행상황", "어디까지"],
        "skill_suggestion": "jh-resume",
        "threshold": 3,
    },
    {
        "id": "stt_voice",
        "name": "음성 인식",
        "keywords": ["음성", "voice", "stt", "들어줘"],
        "skill_suggestion": "bucky-voice-enhanced",
        "threshold": 3,
    },
    {
        "id": "skill_create",
        "name": "스킬 생성",
        "keywords": ["스킬 만들어", "스킬 생성", "자동화해줘"],
        "skill_suggestion": "jh-skill-creator",
        "threshold": 2,
    },
    {
        "id": "payment_setup",
        "name": "결제 연동",
        "keywords": ["결제", "stripe", "toss", "payment"],
        "skill_suggestion": "bucky-payment-template",
        "threshold": 2,
    },
]


def load_pattern_db() -> dict:
    """패턴 DB 로드 (없으면 빈 dict)."""
    if PATTERN_DB.exists():
        try:
            return json.loads(PATTERN_DB.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"patterns": {}, "last_updated": None}


def save_pattern_db(db: dict) -> None:
    """패턴 DB 저장."""
    PATTERN_DB.parent.mkdir(parents=True, exist_ok=True)
    db["last_updated"] = datetime.now().isoformat()
    PATTERN_DB.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")


def read_inbox_messages(days: int = 7) -> list[dict]:
    """AgentBus inbox에서 최근 N일 메시지 읽기."""
    messages = []
    if not INBOX.exists():
        return messages

    cutoff = datetime.now() - timedelta(days=days)

    for f in INBOX.glob("*.md"):
        try:
            stat = f.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime)
            if mtime < cutoff:
                continue
            content = f.read_text(encoding="utf-8", errors="replace")
            messages.append({
                "file": f.name,
                "content": content,
                "mtime": mtime.isoformat(),
            })
        except Exception:
            pass

    return messages


def read_session_state() -> str:
    """session-state.md 읽기."""
    state_file = ROOT / "ObsidianVault" / "00_System" / "session-state.md"
    if state_file.exists():
        return state_file.read_text(encoding="utf-8", errors="replace")
    return ""


def extract_patterns(texts: list[str]) -> list[dict]:
    """텍스트 목록에서 패턴 매칭 및 카운팅."""
    pattern_counts: Counter = Counter()
    pattern_examples: defaultdict[str, list[str]] = defaultdict(list)

    for text in texts:
        text_lower = text.lower()
        for rule in PATTERN_RULES:
            for kw in rule["keywords"]:
                if kw.lower() in text_lower:
                    pattern_counts[rule["id"]] += 1
                    # 컨텍스트 저장 (최대 3개)
                    if len(pattern_examples[rule["id"]]) < 3:
                        snippet = text[:100].strip()
                        if snippet not in pattern_examples[rule["id"]]:
                            pattern_examples[rule["id"]].append(snippet)
                    break

    results = []
    for rule in PATTERN_RULES:
        count = pattern_counts.get(rule["id"], 0)
        if count > 0:
            results.append({
                "id": rule["id"],
                "name": rule["name"],
                "count": count,
                "threshold": rule["threshold"],
                "exceeded": count >= rule["threshold"],
                "skill_suggestion": rule["skill_suggestion"],
                "examples": pattern_examples[rule["id"]],
            })

    return sorted(results, key=lambda x: x["count"], reverse=True)


def generate_skill_recommendations(patterns: list[dict]) -> list[dict]:
    """임계값 초과 패턴 → 스킬 생성 권고."""
    recommendations = []
    for p in patterns:
        if p["exceeded"]:
            skill_path = SKILLS_DIR / f"{p['skill_suggestion']}.md"
            already_exists = skill_path.exists()
            recommendations.append({
                "pattern": p["name"],
                "count": p["count"],
                "skill": p["skill_suggestion"],
                "exists": already_exists,
                "action": "업데이트 권고" if already_exists else "신규 생성 권고",
            })
    return recommendations


def update_pattern_db(patterns: list[dict]) -> dict:
    """패턴 DB 업데이트 (누적)."""
    db = load_pattern_db()
    now = datetime.now().isoformat()

    for p in patterns:
        pid = p["id"]
        if pid not in db["patterns"]:
            db["patterns"][pid] = {
                "name": p["name"],
                "total_count": 0,
                "sessions": [],
            }
        db["patterns"][pid]["total_count"] += p["count"]
        db["patterns"][pid]["sessions"].append({
            "date": now[:10],
            "count": p["count"],
        })
        # 최근 30개 세션만 유지
        db["patterns"][pid]["sessions"] = db["patterns"][pid]["sessions"][-30:]

    save_pattern_db(db)
    return db


def generate_pattern_report(patterns: list[dict], recommendations: list[dict]) -> str:
    """Obsidian 저장용 패턴 리포트 생성."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# 패턴 분석 리포트 — {now}",
        "",
        "## 감지된 패턴",
        "",
    ]

    if patterns:
        for p in patterns:
            icon = "🔴" if p["exceeded"] else "🟡"
            lines.append(f"{icon} **{p['name']}** — {p['count']}회 (임계값: {p['threshold']})")
            for ex in p["examples"]:
                lines.append(f"   - _{ex[:80]}_")
    else:
        lines.append("_감지된 패턴 없음_")

    lines.extend(["", "## 스킬 생성 권고", ""])

    if recommendations:
        for r in recommendations:
            lines.append(f"- **{r['pattern']}** → `{r['skill']}` {r['action']} ({r['count']}회)")
    else:
        lines.append("_임계값 초과 패턴 없음_")

    return "\n".join(lines)


def save_report_to_vault(report: str) -> Path:
    """패턴 리포트를 Obsidian Vault에 저장."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    report_dir = VAULT / "03_Knowledge" / "patterns"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"pattern-report-{date_str}.md"
    report_path.write_text(report, encoding="utf-8")
    return report_path


def run_analysis(days: int = 7, verbose: bool = True) -> dict:
    """전체 패턴 분석 실행."""
    # 텍스트 수집
    texts: list[str] = []
    inbox_msgs = read_inbox_messages(days=days)
    for msg in inbox_msgs:
        texts.append(msg["content"])
    session_text = read_session_state()
    if session_text:
        texts.append(session_text)

    # 패턴 추출
    patterns = extract_patterns(texts)
    recommendations = generate_skill_recommendations(patterns)
    db = update_pattern_db(patterns)
    report = generate_pattern_report(patterns, recommendations)
    report_path = save_report_to_vault(report)

    if verbose:
        print(f"\n📊 패턴 분석 완료 ({days}일)")
        print(f"   메시지 수: {len(texts)}")
        print(f"   패턴 수: {len(patterns)}")
        print(f"   스킬 권고: {len(recommendations)}개")
        if recommendations:
            print("\n🔔 스킬 생성 권고:")
            for r in recommendations:
                print(f"   - {r['pattern']} → {r['skill']} ({r['action']})")
        print(f"\n📄 리포트 저장: {report_path}")

    return {
        "patterns": patterns,
        "recommendations": recommendations,
        "report_path": str(report_path),
        "total_messages": len(texts),
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="패턴 추출기")
    parser.add_argument("--days", type=int, default=7, help="분석 기간 (일)")
    args = parser.parse_args()

    result = run_analysis(days=args.days)
    print(f"\n완료. 리포트: {result['report_path']}")
