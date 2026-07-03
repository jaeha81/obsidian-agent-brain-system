#!/usr/bin/env python3
"""
Wishket 네이버 메일 스크래퍼 (Playwright 웹 스크래핑)

IMAP 대신 Playwright로 네이버 메일 웹을 직접 스크래핑.
네이버 IMAP 보안 차단 문제를 우회.

Usage:
    python wishket_gmail_scraper.py --login     # 최초 1회 로그인
    python wishket_gmail_scraper.py             # 위시켓 메일 수집 (기본)
"""

import asyncio
import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# .env 파일 수동 로드
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            _v = _v.strip().strip('"').strip("'")
            os.environ.setdefault(_k.strip(), _v)

NAVER_USER = os.getenv("NAVER_EMAIL", "")
NAVER_PW = os.getenv("NAVER_PASSWORD", "")

PROFILE_DIR = Path(os.environ.get("USERPROFILE", "~")) / ".playwright-naver-sessions"
WISHKET_BASE = "https://www.wishket.com"
_LINK_RE = re.compile(r"https?://(?:www\.)?wishket\.com/project/(\d+)/?")
_BUDGET_RE = re.compile(r"([\d,]+)\s*만?\s*원")


def _parse_budget_wan(text: str) -> tuple[str, int]:
    m = re.search(r"예산[^\d]*([\d,]+\s*만?\s*원[^\s]*)", text)
    budget_text = m.group(1).strip() if m else "미정"
    raw = budget_text.replace(",", "").replace(" ", "")
    m2 = re.search(r"(\d+)만", raw)
    if m2:
        return budget_text, int(m2.group(1))
    m3 = _BUDGET_RE.search(raw)
    if m3:
        val = int(m3.group(1).replace(",", ""))
        return budget_text, val // 10000 if val > 9999 else val
    return budget_text, 0


def _parse_mail_content(subject: str, body: str) -> dict | None:
    combined = subject + " " + body
    link_m = _LINK_RE.search(combined)
    if not link_m:
        return None

    project_id = link_m.group(1)
    link = f"{WISHKET_BASE}/project/{project_id}/"
    title = re.sub(r"^\[위시켓\]\s*", "", subject).strip()
    title = re.sub(r"\s*(공고|프로젝트|알림|안내|이\s*도착했습니다).*$", "", title).strip() or subject.strip()

    budget_text, budget_wan = _parse_budget_wan(combined)
    clean_body = re.sub(r"\s+", " ", body).strip()
    description = clean_body[:200] if clean_body else ""

    return {
        "title": title[:200],
        "link": link,
        "budget": budget_text,
        "budget_wan": budget_wan,
        "description": description,
        "source": "naver_mail_playwright",
        "scraped_at": datetime.now().isoformat(),
    }


async def login_and_save_session():
    """브라우저를 열어 네이버 로그인 후 세션 저장."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[NaverScraper] playwright 미설치: pip install playwright && playwright install msedge")
        return

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    print("[NaverScraper] 브라우저 열기 — 네이버 메일에 로그인하세요")
    print(f"[NaverScraper] 로그인 완료 후 브라우저를 닫으면 세션이 저장됩니다")

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="msedge",
            headless=False,
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        await page.goto("https://mail.naver.com/")
        print("[NaverScraper] 브라우저가 열렸습니다. 로그인하고 받은메일함까지 이동 후 닫으세요.")
        await browser.wait_for_event("close", timeout=0)  # 무제한 대기
    print(f"[NaverScraper] 세션 저장 완료: {PROFILE_DIR}")


async def fetch_wishket_emails_playwright(limit: int = 30) -> list[dict]:
    """Playwright로 네이버 메일 웹을 직접 스크래핑해 Wishket 공고 수집."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[NaverScraper] playwright 미설치: pip install playwright && playwright install msedge")
        return []

    if not PROFILE_DIR.exists():
        print("[NaverScraper] 세션 없음 — 먼저 --login 실행하세요")
        return []

    projects: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="msedge",
            headless=True,
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()

        try:
            # 네이버 메일 받은편지함
            await page.goto("https://mail.naver.com/", timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=15000)

            # 로그인 확인
            if "login" in page.url or "nid.naver.com" in page.url:
                print("[NaverScraper] 로그인 세션 만료 — --login 다시 실행 필요")
                await browser.close()
                return []

            # 위시켓 메일 검색
            print("[NaverScraper] 위시켓 메일 검색 중...")
            await page.goto("https://mail.naver.com/search/result?query=wishket.com&searchField=from", timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=15000)

            # 메일 목록 추출 — 네이버 메일 DOM 구조
            mail_items = await page.query_selector_all(".mail_item, .item, [class*='mail-item'], [role='row']")

            if not mail_items:
                # 대안: 제목 링크로 찾기
                mail_items = await page.query_selector_all("a[class*='subject'], .subject a, td.subject")

            print(f"[NaverScraper] 검색된 메일 항목: {len(mail_items)}개")

            count = 0
            for item in mail_items[:limit]:
                if count >= limit:
                    break
                try:
                    # 메일 클릭해서 내용 읽기
                    await item.click()
                    await page.wait_for_load_state("networkidle", timeout=10000)
                    await asyncio.sleep(0.5)

                    # 제목 추출
                    subject_el = await page.query_selector(".mail_subject, .subject, h2, [class*='subject']")
                    subject = await subject_el.inner_text() if subject_el else ""

                    # 본문 추출
                    body_el = await page.query_selector(".mail_body, .body, [class*='mail-body'], iframe")
                    body = ""
                    if body_el:
                        tag = await body_el.evaluate("el => el.tagName.toLowerCase()")
                        if tag == "iframe":
                            frame = await body_el.content_frame()
                            if frame:
                                body = await frame.inner_text() if frame else ""
                        else:
                            body = await body_el.inner_text()

                    project = _parse_mail_content(subject, body)
                    if project:
                        projects.append(project)
                        count += 1

                    # 뒤로가기
                    await page.go_back()
                    await page.wait_for_load_state("networkidle", timeout=10000)

                except Exception as e:
                    print(f"[NaverScraper] 메일 파싱 오류: {e}")
                    try:
                        await page.go_back()
                        await page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception:
                        pass

        except Exception as e:
            print(f"[NaverScraper] 스크래핑 오류: {e}")
        finally:
            await browser.close()

    print(f"[NaverScraper] 네이버 메일에서 {len(projects)}개 공고 수집 (Playwright)")
    return projects


def fetch_wishket_emails(limit: int = 30) -> list[dict]:
    """동기 래퍼 — 기존 코드 호환."""
    return asyncio.run(fetch_wishket_emails_playwright(limit))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wishket 네이버 메일 스크래퍼")
    parser.add_argument("--login", action="store_true", help="브라우저 열어 네이버 로그인 후 세션 저장")
    parser.add_argument("--limit", type=int, default=30, help="수집 최대 개수")
    args = parser.parse_args()

    if args.login:
        asyncio.run(login_and_save_session())
    else:
        items = fetch_wishket_emails(args.limit)
        print(f"\n수집: {len(items)}개")
        for it in items:
            print(f"  - {it['title']} | {it['budget']} | {it['link']}")
