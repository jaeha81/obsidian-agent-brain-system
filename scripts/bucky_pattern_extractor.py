#!/usr/bin/env python3
"""
Bucky Pattern Extractor (P1)
반복 요청 패턴 감지 → 스킬 자동 생성 제안 → 버키 진화 트리거
"""
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env", encoding="utf-8", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(ROOT / "ObsidianVault")))
AGENTBUS_INBOX = VAULT / "10_AgentBus" / "inbox"
AGENTBUS_MESSAGES = VAULT / "10_AgentBus" / "agent-room-messages.jsonl"
PATTERNS_DIR = VAULT / "09_Knowledge_Capture" / "patterns"
SKILLS_SUGGESTION_DIR = ROOT / ".claude" / "skills" / "suggested"
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")

MIN_REPEAT_COUNT = 2  # 이 횟수 이상 반복 시 패턴으로 인식
PATTERN_WINDOW_DAYS = 30  # 최근 N일 내 메시지만 분석


SUGGEST_SKILL_TEMPLATE = """---
name: {skill_name}
description: {description} (패턴 감지로 자동 제안됨, 승인 후 활성화)
trigger: {trigger_keywords}
status: suggested
detected_at: {detected_at}
repeat_count: {repeat_count}
---

# {skill_name} (제안됨)

## 감지된 패턴
{pattern_examples}

## 제안 스킬 내용

이 패턴이 {repeat_count}회 감지되었습니다.
아래 내용을 스킬로 등록하면 Bucky가 자동으로 처리할 수 있습니다:

{suggested_content}

## 활성화 방법
1. 이 파일을 `.claude/skills/jh-{skill_slug}.md`로 복사
2. `status: suggested` → `status: active` 변경
3. Claude Code 재시작

## 거부 방법
이 파일을 삭제하면 제안이 무시됩니다.
"""


def load_messages(days: int = PATTERN_WINDOW_DAYS) -> list[dict]:
    cutoff = datetime.now() - timedelta(days=days)
    messages = []

    # 1) inbox .md 파일들에서 Discord 메시지 추출
    if AGENTBUS_INBOX.exists():
        try:
            for md_file in sorted(AGENTBUS_INBOX.glob("*.md")):
                try:
                    mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
                    if mtime < cutoff:
                        continue
                    text = md_file.read_text(encoding="utf-8", errors="replace")
                    # **User:** 뒤 내용 추출
                    import re as _re
                    m = _re.search(r"\*\*User:\*\*\s*(.+)", text)
                    if m:
                        messages.append({
                            "content": m.group(1).strip(),
                            "timestamp": mtime.isoformat(),
                        })
                except Exception:
                    continue
        except Exception as e:
            print(f"⚠️ inbox 읽기 실패: {e}")

    # 2) JSONL 파일도 있으면 추가
    if AGENTBUS_MESSAGES.exists():
        try:
            for line in AGENTBUS_MESSAGES.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    ts_str = msg.get("timestamp", msg.get("created_at", ""))
                    if ts_str:
                        ts = datetime.fromisoformat(ts_str[:19])
                        if ts >= cutoff:
                            messages.append(msg)
                except Exception:
                    continue
        except Exception as e:
            print(f"⚠️ JSONL 로드 실패: {e}")

    return messages


def extract_intent_keywords(text: str) -> list[str]:
    """텍스트에서 의도 키워드 추출"""
    action_words = [
        "만들어", "생성해", "작성해", "구현해", "추가해", "수정해", "삭제해",
        "분석해", "검토해", "배포해", "연결해", "설정해", "가져와", "보여줘",
        "create", "build", "make", "add", "fix", "deploy", "analyze", "review",
    ]
    keywords = []
    text_lower = text.lower()
    for word in action_words:
        if word in text_lower:
            # 앞뒤 맥락 단어 포함
            idx = text_lower.find(word)
            context = text[max(0, idx-10):idx+len(word)+15]
            keywords.append(context.strip())
    return keywords or [text[:30]]


def detect_patterns(messages: list[dict]) -> list[dict]:
    """반복 패턴 감지"""
    all_intents = []
    for msg in messages:
        content = msg.get("content", msg.get("instruction", msg.get("message", "")))
        if not content or len(content) < 10:
            continue
        intents = extract_intent_keywords(content)
        for intent in intents:
            all_intents.append({
                "intent": intent,
                "full_content": content[:200],
                "timestamp": msg.get("timestamp", ""),
            })

    # 유사 패턴 그룹핑 (단순 키워드 매칭)
    pattern_groups: dict[str, list] = {}
    for item in all_intents:
        grouped = False
        for key in pattern_groups:
            # 70% 이상 단어 겹침 시 같은 패턴
            words1 = set(item["intent"].split())
            words2 = set(key.split())
            if words1 & words2 and len(words1 & words2) / max(len(words1 | words2), 1) > 0.4:
                pattern_groups[key].append(item)
                grouped = True
                break
        if not grouped:
            pattern_groups[item["intent"]] = [item]

    patterns = []
    for key, items in pattern_groups.items():
        if len(items) >= MIN_REPEAT_COUNT:
            patterns.append({
                "pattern_key": key,
                "count": len(items),
                "examples": [i["full_content"] for i in items[:3]],
                "first_seen": items[0].get("timestamp", ""),
                "last_seen": items[-1].get("timestamp", ""),
            })

    return sorted(patterns, key=lambda x: x["count"], reverse=True)


def generate_skill_suggestion(pattern: dict) -> dict:
    """패턴을 기반으로 스킬 제안 생성"""
    examples = pattern["examples"]
    key = pattern["pattern_key"]

    # 스킬 이름 생성
    clean = re.sub(r'[^\w가-힣\s]', '', key)[:30].strip()
    slug = re.sub(r'\s+', '-', clean.lower())[:20]
    skill_name = f"auto-{slug}" if slug else f"auto-pattern-{pattern['count']}"

    suggested_content = f"""사용자가 다음과 같은 요청을 {pattern['count']}회 했습니다:

{chr(10).join(f"- {e[:100]}" for e in examples[:3])}

이 패턴을 처리하는 표준 절차:
1. 요청 의도 파악
2. 필요한 파일/리소스 확인
3. 자동 실행 또는 확인 후 진행
4. 결과 Discord 보고"""

    return {
        "skill_name": skill_name,
        "skill_slug": slug,
        "description": f"패턴 감지: {key[:50]}",
        "trigger_keywords": key[:100],
        "detected_at": datetime.now().isoformat(),
        "repeat_count": pattern["count"],
        "pattern_examples": "\n".join(f"- {e[:100]}" for e in examples[:3]),
        "suggested_content": suggested_content,
    }


def save_suggestion(suggestion: dict) -> Path:
    SKILLS_SUGGESTION_DIR.mkdir(parents=True, exist_ok=True)
    PATTERNS_DIR.mkdir(parents=True, exist_ok=True)

    filepath = SKILLS_SUGGESTION_DIR / f"{suggestion['skill_name']}.md"
    content = SUGGEST_SKILL_TEMPLATE.format(**suggestion)
    filepath.write_text(content, encoding="utf-8")
    print(f"💡 스킬 제안 저장: {filepath}")
    return filepath


def save_pattern_report(patterns: list[dict]) -> Path:
    PATTERNS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    report_path = PATTERNS_DIR / f"pattern-report-{now.strftime('%Y%m%d')}.md"

    lines = [
        f"# 패턴 분석 리포트 — {now.strftime('%Y-%m-%d')}",
        "",
        f"총 {len(patterns)}개 반복 패턴 감지됨",
        "",
        "| 순위 | 패턴 | 횟수 | 마지막 발생 |",
        "|------|------|------|------------|",
    ]
    for i, p in enumerate(patterns[:20], 1):
        lines.append(f"| {i} | {p['pattern_key'][:40]} | {p['count']} | {p['last_seen'][:10]} |")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def run(notify_discord: bool = True) -> dict:
    print("🔍 패턴 분석 시작...")
    messages = load_messages()
    print(f"   → {len(messages)}개 메시지 로드")

    if not messages:
        print("⚠️ 분석할 메시지 없음")
        return {"patterns": [], "suggestions": []}

    patterns = detect_patterns(messages)
    print(f"   → {len(patterns)}개 패턴 감지")

    suggestions = []
    for p in patterns[:5]:  # 상위 5개만 스킬 제안
        suggestion = generate_skill_suggestion(p)
        path = save_suggestion(suggestion)
        suggestions.append({"skill": suggestion["skill_name"], "path": str(path), "count": p["count"]})

    report_path = save_pattern_report(patterns)

    if notify_discord and DISCORD_WEBHOOK and patterns:
        top = patterns[0]
        msg = (
            f"🔄 **패턴 분석 완료**\n"
            f"📊 {len(patterns)}개 반복 패턴 감지\n"
            f"🥇 최다 패턴: `{top['pattern_key'][:40]}` ({top['count']}회)\n"
            f"💡 {len(suggestions)}개 스킬 자동 제안 생성됨\n"
            f"📄 `{report_path.name}`"
        )
        try:
            requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=5)
        except Exception:
            pass

    return {"patterns": patterns[:5], "suggestions": suggestions, "report": str(report_path)}


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
