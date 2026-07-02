#!/usr/bin/env python3
"""
Bucky Daily Briefing — AI/기술 뉴스 수집기

오늘 날짜 기준 AI·기술·정보 브리핑 생성 후 Obsidian 저장 + Discord 반환용 텍스트 제공.

Sources:
    - Hacker News API (무료, 키 불필요)
    - RSS: OpenAI, Anthropic, Google DeepMind, MIT Tech Review AI

Usage:
    python scripts/bucky_briefing.py           # 단독 실행
    from bucky_briefing import generate_briefing  # Discord bot에서 호출
"""

import json
import os
import sys
import io
from datetime import datetime, timezone
from pathlib import Path

import requests

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_ROOT = Path(__file__).parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env", encoding="utf-8")
except ImportError:
    pass

VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
BRIEFING_DIR = VAULT / "04_DAILY_REPORTS" / "briefings"

# AI/기술 키워드 필터
AI_KEYWORDS = {
    "ai", "llm", "gpt", "claude", "gemini", "openai", "anthropic", "deepmind",
    "machine learning", "deep learning", "neural", "transformer", "model",
    "chatgpt", "copilot", "mistral", "llama", "agent", "rag", "embedding",
    "diffusion", "stable diffusion", "midjourney", "sora", "robotics",
    "autonomous", "inference", "fine-tune", "benchmark", "multimodal",
    "reasoning", "o1", "o3", "gemini", "grok", "perplexity",
}

TECH_KEYWORDS = {
    "python", "rust", "golang", "typescript", "react", "nextjs", "wasm",
    "kubernetes", "docker", "cloud", "aws", "gcp", "azure", "serverless",
    "blockchain", "crypto", "startup", "funding", "vc", "yc", "security",
    "opensource", "github", "database", "api", "sdk", "framework",
}

# RSS 피드 목록 (feedparser 없이 requests로 직접 파싱)
RSS_FEEDS = [
    {
        "name": "OpenAI Blog",
        "url": "https://openai.com/news/rss.xml",
        "category": "AI 모델/연구",
    },
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog/feed.xml",
        "category": "AI 모델/연구",
    },
    {
        "name": "Google DeepMind",
        "url": "https://deepmind.google/blog/rss.xml",
        "category": "AI 모델/연구",
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/feed/",
        "category": "AI 동향",
    },
    {
        "name": "The Verge",
        "url": "https://www.theverge.com/rss/index.xml",
        "category": "AI 동향",
    },
]

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "BuckyBriefing/1.0 (+https://github.com/jaeha81)"})
_TIMEOUT = 8


def _fetch_hn_ai_stories(limit: int = 10) -> list[dict]:
    """Hacker News 상위 스토리 중 AI/기술 관련 필터링."""
    try:
        resp = _SESSION.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        story_ids: list[int] = resp.json()[:60]
    except Exception as e:
        print(f"[Briefing] HN topstories 실패: {e}", flush=True)
        return []

    stories = []
    for sid in story_ids:
        if len(stories) >= limit:
            break
        try:
            r = _SESSION.get(
                f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                timeout=_TIMEOUT,
            )
            item = r.json()
            if not item or item.get("type") != "story":
                continue
            title_lower = (item.get("title") or "").lower()
            if any(kw in title_lower for kw in AI_KEYWORDS | TECH_KEYWORDS):
                stories.append({
                    "title": item.get("title", ""),
                    "url": item.get("url") or f"https://news.ycombinator.com/item?id={sid}",
                    "score": item.get("score", 0),
                    "comments": item.get("descendants", 0),
                    "category": "Hacker News",
                })
        except Exception:
            continue

    return sorted(stories, key=lambda x: x["score"], reverse=True)[:limit]


def _parse_rss_simple(xml_text: str, source_name: str, category: str, limit: int = 5) -> list[dict]:
    """feedparser 없이 정규식으로 RSS item 파싱."""
    import re
    items = []
    # item 또는 entry 태그 추출
    blocks = re.findall(r"<(?:item|entry)>(.*?)</(?:item|entry)>", xml_text, re.DOTALL)
    for block in blocks[:limit]:
        title_m = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.DOTALL)
        link_m = re.search(r"<(?:link|id)>([^<]+)</(?:link|id)>", block) or \
                 re.search(r'<link[^>]+href=["\']([^"\']+)["\']', block)
        title = title_m.group(1).strip() if title_m else ""
        url = link_m.group(1).strip() if link_m else ""
        if title:
            items.append({
                "title": title,
                "url": url,
                "category": category,
                "source": source_name,
            })
    return items


def _fetch_rss_stories(limit_per_feed: int = 5) -> list[dict]:
    """RSS 피드에서 최신 뉴스 수집."""
    all_items = []
    for feed in RSS_FEEDS:
        try:
            resp = _SESSION.get(feed["url"], timeout=_TIMEOUT)
            resp.raise_for_status()
            items = _parse_rss_simple(
                resp.text, feed["name"], feed["category"], limit_per_feed
            )
            all_items.extend(items)
        except Exception as e:
            print(f"[Briefing] RSS 실패 ({feed['name']}): {e}", flush=True)
    return all_items


def _format_briefing(
    rss_items: list[dict],
    hn_items: list[dict],
    date_str: str,
) -> tuple[str, str]:
    """브리핑 Markdown + Discord용 텍스트 반환 (full_md, discord_text)."""
    now_kst = datetime.now().strftime("%Y-%m-%d %H:%M")

    # RSS를 카테고리별 그룹화
    categories: dict[str, list[dict]] = {}
    for item in rss_items:
        cat = item["category"]
        categories.setdefault(cat, []).append(item)

    # Obsidian용 전체 Markdown
    lines_md = [
        f"---",
        f"type: daily-briefing",
        f"date: {date_str}",
        f"generated: {now_kst}",
        f"tags: [briefing, AI, tech, daily]",
        f"---",
        f"",
        f"# 📡 AI/기술 일일 브리핑 — {date_str}",
        f"",
        f"> 생성: {now_kst} | Bucky 자동 수집",
        f"",
    ]

    # RSS 섹션
    for cat, items in categories.items():
        lines_md.append(f"## {cat}")
        lines_md.append("")
        for item in items:
            src = item.get("source", "")
            lines_md.append(f"- **[{item['title']}]({item['url']})** — _{src}_")
        lines_md.append("")

    # HN 섹션
    if hn_items:
        lines_md.append("## Hacker News 주목 스토리")
        lines_md.append("")
        for item in hn_items:
            lines_md.append(
                f"- **[{item['title']}]({item['url']})** "
                f"↑{item['score']} 💬{item['comments']}"
            )
        lines_md.append("")

    full_md = "\n".join(lines_md)

    # Discord용 압축 텍스트 (2000자 이내)
    discord_lines = [f"**📡 AI/기술 브리핑 — {date_str}**\n"]

    for cat, items in categories.items():
        discord_lines.append(f"**{cat}**")
        for item in items[:3]:
            title = item["title"][:70] + ("…" if len(item["title"]) > 70 else "")
            discord_lines.append(f"• {title}")
        discord_lines.append("")

    if hn_items:
        discord_lines.append("**🔥 HN 핫 스토리**")
        for item in hn_items[:5]:
            title = item["title"][:65] + ("…" if len(item["title"]) > 65 else "")
            discord_lines.append(f"• {title} ↑{item['score']}")
        discord_lines.append("")

    total = len(rss_items) + len(hn_items)
    discord_lines.append(f"_총 {total}개 항목 수집. Obsidian 브리핑 노트에 전체 저장됨._")

    discord_text = "\n".join(discord_lines)
    if len(discord_text) > 1900:
        discord_text = discord_text[:1900] + "\n…(이하 생략)"

    return full_md, discord_text


def generate_briefing() -> tuple[str, str]:
    """브리핑 생성 + Obsidian 저장.

    Returns:
        (discord_text, obsidian_path_str) — Discord 전송용 텍스트, 저장 경로
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    print(f"[Briefing] 수집 시작 — {date_str}", flush=True)

    rss_items = _fetch_rss_stories(limit_per_feed=5)
    hn_items = _fetch_hn_ai_stories(limit=10)

    print(f"[Briefing] RSS {len(rss_items)}개 / HN {len(hn_items)}개 수집 완료", flush=True)

    full_md, discord_text = _format_briefing(rss_items, hn_items, date_str)

    # Obsidian 저장
    BRIEFING_DIR.mkdir(parents=True, exist_ok=True)
    out_path = BRIEFING_DIR / f"{date_str}-briefing.md"
    out_path.write_text(full_md, encoding="utf-8")
    print(f"[Briefing] 저장 완료: {out_path}", flush=True)

    return discord_text, str(out_path)


if __name__ == "__main__":
    text, path = generate_briefing()
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)
    print(f"\n저장: {path}")
