#!/usr/bin/env python3
"""
Wishket 공고 스크래퍼

Wishket 프리랜서 플랫폼에서 공고를 수집해 JSON으로 저장.
WISHKET_EMAIL + WISHKET_PASSWORD 설정 시 로그인 후 전체 공고 접근.
미설정 시 공개 공고만 수집 (selenium 없이 requests 기반).
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

TRACKER_FILE = _ROOT / "ObsidianVault" / "10_AgentBus" / "wishket_tracker.json"

WISHKET_BASE = "https://www.wishket.com"
WISHKET_PROJECTS = f"{WISHKET_BASE}/project/"
WISHKET_LOGIN = f"{WISHKET_BASE}/accounts/login/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": WISHKET_BASE,
}

KEYWORDS = os.getenv(
    "WISHKET_KEYWORDS",
    "Python,AI,자동화,Discord,봇,FastAPI,웹개발,Claude,GPT,크롤링,데이터",
).split(",")

MIN_BUDGET_WAN = int(os.getenv("WISHKET_MIN_BUDGET", "50"))

WISHKET_EMAIL = os.getenv("WISHKET_EMAIL", "")
WISHKET_PASSWORD = os.getenv("WISHKET_PASSWORD", "")


def _parse_budget(text: str) -> int:
    text = text.replace(",", "").replace(" ", "")
    m = re.search(r"(\d+)만", text)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)", text)
    if m:
        val = int(m.group(1))
        return val // 10000 if val > 9999 else val
    return 0


def _is_relevant(title: str, description: str) -> bool:
    combined = (title + " " + description).lower()
    return any(kw.lower() in combined for kw in KEYWORDS)


def _get_seen_links() -> set[str]:
    """tracker.json + inbox 파일에서 이미 처리된 링크 목록 로드."""
    seen: set[str] = set()

    # tracker.json의 bids에서 링크 추출
    if TRACKER_FILE.exists():
        try:
            data = json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
            for bid in data.get("bids", []):
                link = bid.get("link", "")
                if link:
                    seen.add(link.rstrip("/"))
        except Exception:
            pass

    # 오늘 inbox 파일에서도 중복 체크
    for f in sorted(INBOX.glob("wishket_*.json"), reverse=True)[:5]:
        try:
            items = json.loads(f.read_text(encoding="utf-8"))
            for item in items:
                link = item.get("link", "")
                if link:
                    seen.add(link.rstrip("/"))
        except Exception:
            pass

    return seen


def _create_session() -> requests.Session:
    """로그인 세션 생성. 자격증명 없으면 익명 세션 반환."""
    session = requests.Session()
    session.headers.update(HEADERS)

    if not WISHKET_EMAIL or not WISHKET_PASSWORD:
        print("[Wishket] 로그인 정보 없음 — 공개 공고만 수집")
        return session

    try:
        # CSRF 토큰 획득
        resp = session.get(WISHKET_LOGIN, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        csrf_input = soup.select_one("input[name='csrfmiddlewaretoken']")
        csrf_token = csrf_input["value"] if csrf_input else ""

        if not csrf_token:
            # 쿠키에서 CSRF 추출 시도
            csrf_token = session.cookies.get("csrftoken", "")

        login_data = {
            "csrfmiddlewaretoken": csrf_token,
            "login": WISHKET_EMAIL,
            "password": WISHKET_PASSWORD,
        }
        headers_with_referer = {"Referer": WISHKET_LOGIN}
        login_resp = session.post(
            WISHKET_LOGIN,
            data=login_data,
            headers=headers_with_referer,
            timeout=15,
            allow_redirects=True,
        )

        # 로그인 성공 여부: 로그인 페이지로 돌아오지 않으면 성공으로 간주
        if "login" not in login_resp.url and login_resp.status_code == 200:
            print(f"[Wishket] 로그인 성공: {WISHKET_EMAIL}")
        else:
            print("[Wishket] 로그인 실패 — 공개 공고로 폴백")
    except Exception as e:
        print(f"[Wishket] 로그인 오류: {e} — 공개 공고로 폴백")

    return session


def fetch_projects(max_pages: int = 3) -> list[dict]:
    """공고 목록 수집 (로그인 세션 + 중복 제거 포함)."""
    seen_links = _get_seen_links()
    session = _create_session()
    projects: list[dict] = []
    seen_in_batch: set[str] = set()  # 이번 배치 내 중복 방지

    for page in range(1, max_pages + 1):
        try:
            resp = session.get(
                WISHKET_PROJECTS,
                params={"page": page},
                timeout=15,
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"[Wishket] 페이지 {page} 요청 실패: {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
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
            href = link_el["href"] if link_el else ""
            link = (WISHKET_BASE + href) if href.startswith("/") else href

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

            # 중복 제거 (tracker + 오늘 inbox + 이번 배치)
            norm_link = link.rstrip("/")
            if norm_link in seen_links or norm_link in seen_in_batch:
                continue
            seen_in_batch.add(norm_link)

            projects.append(
                {
                    "title": title,
                    "link": link,
                    "budget": budget_text,
                    "budget_wan": budget_wan,
                    "description": description,
                    "source": "web",
                    "scraped_at": datetime.now().isoformat(),
                }
            )

        time.sleep(1.5)

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
