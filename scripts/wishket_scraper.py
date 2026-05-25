#!/usr/bin/env python3
"""
Wishket 공고 스크래퍼

Wishket 프리랜서 플랫폼에서 공고를 수집해 JSON으로 저장.
로그인 없이 공개 공고만 수집 (selenium 없이 requests 기반).
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

_ROOT = Path(__file__).parent.parent
INBOX = _ROOT / "ObsidianVault" / "10_AgentBus" / "wishket_inbox"
INBOX.mkdir(parents=True, exist_ok=True)

WISHKET_BASE = "https://www.wishket.com"
WISHKET_PROJECTS = f"{WISHKET_BASE}/project/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": WISHKET_BASE,
}

# 관심 키워드 (필터링용)
KEYWORDS = os.getenv(
    "WISHKET_KEYWORDS",
    "Python,AI,자동화,Discord,봇,FastAPI,웹개발,Claude,GPT,크롤링,데이터",
).split(",")

# 최소 예산 (만원)
MIN_BUDGET_WAN = int(os.getenv("WISHKET_MIN_BUDGET", "50"))


def _parse_budget(text: str) -> int:
    """예산 텍스트 → 만원 단위 정수. 파싱 불가 시 0."""
    text = text.replace(",", "").replace(" ", "")
    m = re.search(r"(\d+)만", text)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)", text)
    if m:
        val = int(m.group(1))
        # 숫자가 크면 원 단위로 간주
        return val // 10000 if val > 9999 else val
    return 0


def _is_relevant(title: str, description: str) -> bool:
    combined = (title + " " + description).lower()
    return any(kw.lower() in combined for kw in KEYWORDS)


def fetch_projects(max_pages: int = 3) -> list[dict]:
    """공개 공고 목록 수집."""
    projects = []
    for page in range(1, max_pages + 1):
        try:
            resp = requests.get(
                WISHKET_PROJECTS,
                params={"page": page},
                headers=HEADERS,
                timeout=15,
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"[Wishket] 페이지 {page} 요청 실패: {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # Wishket 공고 카드 파싱 (구조 변경 대비 다중 셀렉터)
        cards = (
            soup.select(".project-item")
            or soup.select(".project-list-item")
            or soup.select("[class*='project']")
        )

        if not cards:
            print(f"[Wishket] 페이지 {page}: 공고 카드 없음 (구조 변경 가능성)")
            break

        for card in cards:
            title_el = card.select_one("h3, h4, .title, [class*='title']")
            title = title_el.get_text(strip=True) if title_el else ""

            link_el = card.select_one("a[href]")
            link = WISHKET_BASE + link_el["href"] if link_el else ""

            budget_el = card.select_one("[class*='budget'], [class*='price'], [class*='pay']")
            budget_text = budget_el.get_text(strip=True) if budget_el else "미정"
            budget_wan = _parse_budget(budget_text)

            desc_el = card.select_one("[class*='desc'], [class*='summary'], p")
            description = desc_el.get_text(strip=True) if desc_el else ""

            if not title:
                continue
            if budget_wan and budget_wan < MIN_BUDGET_WAN:
                continue
            if not _is_relevant(title, description):
                continue

            projects.append(
                {
                    "title": title,
                    "link": link,
                    "budget": budget_text,
                    "budget_wan": budget_wan,
                    "description": description,
                    "scraped_at": datetime.now().isoformat(),
                }
            )

        time.sleep(1.5)  # 서버 부하 방지

    return projects


def save_projects(projects: list[dict]) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = INBOX / f"wishket_{ts}.json"
    out.write_text(json.dumps(projects, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Wishket] {len(projects)}개 공고 저장: {out}")
    return out


def run() -> tuple[list[dict], Path]:
    print("[Wishket] 공고 수집 시작...")
    projects = fetch_projects()
    if not projects:
        print("[Wishket] 관련 공고 없음")
        return [], Path("")
    out = save_projects(projects)
    return projects, out


if __name__ == "__main__":
    projects, path = run()
    print(f"\n수집 결과: {len(projects)}개")
    for p in projects[:5]:
        print(f"  - {p['title']} | {p['budget']} | {p['link']}")
