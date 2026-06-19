#!/usr/bin/env python3
"""
위시켓 공고 스크래퍼 (Playwright 로그인 세션)

.env의 WISHKET_EMAIL + WISHKET_PASSWORD로 로그인 후 전체 공고를 수집한다.
쿠키는 .cache/wishket_session.json에 24시간 캐시해 재로그인을 최소화한다.
로그인 실패 시 스크린샷을 .cache/wishket_debug.png에 저장한다.
"""

from __future__ import annotations

import json
import os
import re
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from wishket_filters import classify_project, is_collectable_development_request
try:
    from wishket_scorer import score_projects as _score_projects
except ImportError:
    _score_projects = None

_ROOT = Path(__file__).parent.parent
INBOX = _ROOT / "ObsidianVault" / "10_AgentBus" / "wishket_inbox"
INBOX.mkdir(parents=True, exist_ok=True)
TRACKER_FILE = _ROOT / "ObsidianVault" / "10_AgentBus" / "wishket_tracker.json"
CACHE_DIR = _ROOT / ".cache"

WISHKET_BASE = "https://www.wishket.com"
WISHKET_LOGIN = "https://auth.wishket.com/login"
WISHKET_PROJECTS = f"{WISHKET_BASE}/project/"

WISHKET_EMAIL = os.getenv("WISHKET_EMAIL", "")
WISHKET_PASSWORD = os.getenv("WISHKET_PASSWORD", "")

KEYWORDS = os.getenv(
    "WISHKET_KEYWORDS",
    "Python,AI,자동화,Discord,봇,FastAPI,웹개발,Claude,GPT,크롤링,데이터",
).split(",")

_SESSION_CACHE = CACHE_DIR / "wishket_session.json"
_SESSION_TTL = 86400  # 24시간


# ── 유틸리티 ────────────────────────────────────────────────

def _parse_budget(text: str) -> int:
    """예산 텍스트 → 만원 정수 변환.

    지원 형식: "150만원", "4,000,000원", "월 금액 4,000,000원 /월", "150만"
    """
    clean = text.replace(",", "").replace(" ", "")
    # "N만원" 또는 "N만"
    m = re.search(r"(\d+)만", clean)
    if m:
        return int(m.group(1))
    # "NNNNNN원" — 6자리 이상이면 원 단위로 간주
    m = re.search(r"(\d{5,})원", clean)
    if m:
        return int(m.group(1)) // 10000
    # fallback: 숫자만
    m = re.search(r"(\d+)", clean)
    if m:
        val = int(m.group(1))
        return val // 10000 if val > 9999 else val
    return 0


def _is_relevant(title: str, description: str) -> bool:
    return is_collectable_development_request(title, description, keywords=KEYWORDS)


def _get_seen_links() -> set[str]:
    seen: set[str] = set()
    if TRACKER_FILE.exists():
        try:
            data = json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
            for bid in data.get("bids", []):
                link = bid.get("link", "")
                if link:
                    seen.add(link.rstrip("/"))
        except Exception:
            pass
    for f in sorted(INBOX.glob("wishket_*.json"), reverse=True)[:5]:
        try:
            for item in json.loads(f.read_text(encoding="utf-8")):
                link = item.get("link", "")
                if link:
                    seen.add(link.rstrip("/"))
        except Exception:
            pass
    return seen


def _load_cached_cookies() -> list[dict] | None:
    if _SESSION_CACHE.exists():
        try:
            data = json.loads(_SESSION_CACHE.read_text(encoding="utf-8"))
            if time.time() - data.get("saved_at", 0) < _SESSION_TTL:
                return data.get("cookies", [])
        except Exception:
            pass
    return None


def _save_cookies(cookies: list[dict]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _SESSION_CACHE.write_text(
        json.dumps({"saved_at": time.time(), "cookies": cookies}, ensure_ascii=False),
        encoding="utf-8",
    )


# ── 로그인 ────────────────────────────────────────────────

def _is_logged_in(page) -> bool:
    """현재 페이지가 로그인 상태인지 확인 (로그인 버튼 미존재 = 로그인 상태)."""
    try:
        # "로그인" 텍스트를 가진 링크/버튼이 있으면 비로그인
        login_btn = page.query_selector("a:text('로그인'), button:text('로그인')")
        return login_btn is None
    except Exception:
        return False


def _do_login(page) -> bool:
    """위시켓 로그인 수행. 성공하면 True."""
    from playwright.sync_api import TimeoutError as PWTimeout

    print(f"[Wishket] 로그인 시도 → {WISHKET_LOGIN}")
    try:
        page.goto(WISHKET_LOGIN, wait_until="networkidle", timeout=30000)
    except PWTimeout:
        # networkidle 실패해도 폼이 있을 수 있으니 계속 진행
        pass

    _save_screenshot(page, "login_loaded")
    print(f"[Wishket] 로그인 페이지 로드 완료 → {page.url}")

    try:
        # auth.wishket.com/login 폼: name 속성 기반 (placeholder 없음)
        email_sel = "input[name='emailOrId']"
        pw_sel = "input[name='password'], input[type='password']"
        btn_sel = "button[type='submit'], form[data-testid='login-form-contents'] button"

        page.wait_for_selector(email_sel, timeout=15000)
        page.fill(email_sel, WISHKET_EMAIL)
        time.sleep(0.4)
        page.fill(pw_sel, WISHKET_PASSWORD)
        time.sleep(0.4)
        page.click(btn_sel)
        page.wait_for_load_state("networkidle", timeout=25000)

    except PWTimeout as e:
        _save_screenshot(page, "login_fail")
        print(f"[Wishket] 로그인 폼 타임아웃: {e}")
        return False
    except Exception as e:
        _save_screenshot(page, "login_error")
        print(f"[Wishket] 로그인 오류: {e}")
        return False

    if not _is_logged_in(page):
        _save_screenshot(page, "login_failed")
        print(f"[Wishket] 로그인 실패 (URL: {page.url})")
        return False

    print(f"[Wishket] 로그인 성공 → {page.url}")
    return True


def _save_screenshot(page, tag: str) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = CACHE_DIR / f"wishket_{tag}.png"
        page.screenshot(path=str(path))
        print(f"[Wishket] 스크린샷: {path}")
    except Exception:
        pass


# ── 공고 파싱 ───────────────────────────────────────────────

# 위시켓 공고 카드 선택자 — 렌더링 방식 변경 대응을 위해 여러 후보
_CARD_SELECTORS = [
    ".project-item",
    ".project-list-item",
    "[class*='ProjectItem']",
    "[class*='project_item']",
    "[class*='project-item']",
    "article[class*='project']",
    "li[class*='project']",
    "[data-testid*='project']",
]

_TITLE_SEL = (
    "h3, h4, h5, "
    "[class*='title'], [class*='Title'], "
    "[class*='name'], [class*='Name']"
)
_BUDGET_SEL = (
    "[class*='budget'], [class*='Budget'], "
    "[class*='price'], [class*='Price'], "
    "[class*='pay'], [class*='Pay'], "
    "[class*='cost'], [class*='Cost'], "
    "[class*='money'], [class*='Money']"
)
_DESC_SEL = (
    "[class*='desc'], [class*='Desc'], "
    "[class*='summary'], [class*='Summary'], "
    "[class*='content'], p"
)


def _parse_cards(page, page_num: int) -> list[tuple]:
    """페이지에서 (title, href, budget_text, description) 튜플 목록 반환.

    위시켓은 React/CSS모듈을 사용해 클래스명이 동적이므로
    /project/<숫자>/ 패턴의 링크를 기준으로 부모 컨테이너를 파싱한다.
    """
    raw = page.evaluate("""() => {
        const seen = new Set();
        const results = [];
        const links = document.querySelectorAll('a[href]');
        links.forEach(a => {
            const href = a.getAttribute('href') || '';
            if (!/\\/project\\/\\d+\\//.test(href)) return;
            if (seen.has(href)) return;
            seen.add(href);

            // 부모 카드 컨테이너 찾기 (충분히 큰 div/article/section)
            let container = a;
            for (let i = 0; i < 6; i++) {
                const p = container.parentElement;
                if (!p) break;
                const rect = p.getBoundingClientRect();
                if (rect.width > 400 && rect.height > 80) { container = p; break; }
                container = p;
            }

            const text = (container.innerText || '').trim();
            const lines = text.split('\\n').map(l => l.trim()).filter(Boolean);

            // 첫 번째 의미있는 줄 = 제목
            const title = lines.find(l => l.length > 5 && !/^모집|^마감|^지원자|^등록일/.test(l)) || '';

            // 예산: "원" 포함 줄
            const budgetLine = lines.find(l => l.includes('원') && /\\d/.test(l)) || '미정';

            // 설명: 제목 이후 줄 (태그/뱃지 제외)
            const titleIdx = lines.indexOf(title);
            const desc = lines
                .slice(titleIdx + 1)
                .filter(l => l.length > 10 && !l.includes('원') && !/^\\d+$/.test(l))
                .slice(0, 3)
                .join(' ');

            results.push([title, href, budgetLine, desc]);
        });
        return results;
    }""")

    if not raw:
        _save_screenshot(page, f"page{page_num}_no_cards")
        print(f"[Wishket] p{page_num}: 공고 링크 미발견 (스크린샷 저장됨)")
        return []

    print(f"[Wishket] p{page_num}: {len(raw)}개 공고 링크 발견")
    return [(r[0], r[1], r[2], r[3]) for r in raw]


# ── 메인 수집 ───────────────────────────────────────────────

def fetch_projects(max_pages: int = 5) -> list[dict]:
    """Playwright 로그인 세션으로 위시켓 공고 수집."""
    if not WISHKET_EMAIL or not WISHKET_PASSWORD:
        print("[Wishket] 오류: .env에 WISHKET_EMAIL, WISHKET_PASSWORD가 없습니다.")
        return []

    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    seen_links = _get_seen_links()
    projects: list[dict] = []
    seen_in_batch: set[str] = set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="ko-KR",
            viewport={"width": 1280, "height": 900},
        )
        # webdriver 속성 숨기기
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        # 캐시된 쿠키 복원
        cached = _load_cached_cookies()
        if cached:
            context.add_cookies(cached)
            print(f"[Wishket] 캐시 쿠키 {len(cached)}개 복원")

        page = context.new_page()

        # 프로젝트 페이지 접근
        try:
            page.goto(WISHKET_PROJECTS, wait_until="domcontentloaded", timeout=20000)
        except PWTimeout:
            print("[Wishket] 프로젝트 페이지 접근 실패")
            browser.close()
            return []

        # 로그인 버튼 존재 여부로 로그인 상태 판단
        if not _is_logged_in(page):
            print("[Wishket] 미로그인 상태 — 자동 로그인 시도")
            login_ok = _do_login(page)
            if not login_ok:
                # 캐시 세션이 오염됐을 수 있으므로 삭제 후 1회 재시도
                print("[Wishket] 로그인 실패 — 캐시 삭제 후 재시도")
                if _SESSION_CACHE.exists():
                    _SESSION_CACHE.unlink()
                try:
                    page.goto(WISHKET_LOGIN, wait_until="domcontentloaded", timeout=20000)
                except PWTimeout:
                    pass
                login_ok = _do_login(page)
            if not login_ok:
                print("[Wishket] 자동 로그인 2회 실패 — 수동 로그인 필요 (python scripts/wishket_scraper.py --manual-login)")
                browser.close()
                return []
            _save_cookies(context.cookies())
            # 로그인 후 프로젝트 페이지 재이동
            try:
                page.goto(WISHKET_PROJECTS, wait_until="domcontentloaded", timeout=20000)
            except PWTimeout:
                pass
        else:
            print(f"[Wishket] 로그인 상태 확인 — 공고 수집 시작")

        # 페이지별 수집
        for page_num in range(1, max_pages + 1):
            if page_num > 1:
                try:
                    page.goto(
                        f"{WISHKET_PROJECTS}?page={page_num}",
                        wait_until="networkidle",
                        timeout=15000,
                    )
                except PWTimeout:
                    try:
                        page.wait_for_load_state("domcontentloaded", timeout=5000)
                    except PWTimeout:
                        print(f"[Wishket] p{page_num}: 로드 실패 — 중단")
                        break
            else:
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except PWTimeout:
                    pass

            raw_cards = _parse_cards(page, page_num)
            if not raw_cards:
                break

            page_new = 0
            for title, href, budget_text, description in raw_cards:
                if not title:
                    continue

                link = (WISHKET_BASE + href) if href and href.startswith("/") else href
                budget_wan = _parse_budget(budget_text)

                classification = classify_project({"title": title, "description": description}, keywords=KEYWORDS)
                if not classification["accepted"]:
                    print(f"[Wishket] skip {classification['reason']}: {title[:60]}")
                    continue

                norm_link = link.rstrip("/") if link else ""
                if not norm_link:
                    continue
                if norm_link in seen_links or norm_link in seen_in_batch:
                    continue
                seen_in_batch.add(norm_link)

                projects.append({
                    "title": title,
                    "link": link,
                    "budget": budget_text,
                    "budget_wan": budget_wan,
                    "description": description,
                    "source": "wishket_login",
                    "classification": classification["reason"],
                    "scraped_at": datetime.now().isoformat(),
                })
                page_new += 1

            print(f"[Wishket] p{page_num}: {page_new}개 신규 수집 (누적 {len(projects)}개)")
            time.sleep(2)

        # 쿠키 갱신 저장
        _save_cookies(context.cookies())
        browser.close()

    return projects


def save_projects(projects: list[dict]) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = INBOX / f"wishket_{ts}.json"
    out.write_text(json.dumps(projects, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Wishket] {len(projects)}개 저장 → {out}")
    return out


def run() -> tuple[list[dict], Path]:
    print("[Wishket] 공고 수집 시작 (로그인 세션)...")
    projects = fetch_projects()
    if not projects:
        print("[Wishket] 수집된 공고 없음")
        return [], Path("")
    if _score_projects:
        projects = _score_projects(projects)
        for p in projects[:3]:
            print(f"  [{p.get('priority','?')}] {p.get('score', 0):3d}점  {p['title'][:40]}")
    out = save_projects(projects)
    return projects, out


def manual_login() -> None:
    """헤드리스 OFF로 브라우저를 띄워 사용자가 수동으로 로그인한 뒤 쿠키를 저장한다."""
    from playwright.sync_api import sync_playwright

    print("[Wishket] 수동 로그인 모드 — 브라우저가 열립니다. 로그인 후 Enter 키를 누르세요.")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="ko-KR",
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()
        page.goto(WISHKET_LOGIN)
        input("로그인 완료 후 Enter 키를 누르세요...")
        cookies = context.cookies()
        _save_cookies(cookies)
        print(f"[Wishket] 쿠키 {len(cookies)}개 저장 완료 → {_SESSION_CACHE}")
        browser.close()



def _resolve_google_chrome_exe() -> str:
    candidates = (
        os.getenv("WISHKET_CHROME_EXE", ""),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "chrome.exe",
        "chrome",
    )
    for candidate in candidates:
        if candidate:
            if candidate in {"chrome", "chrome.exe"}:
                return candidate
            if Path(candidate).exists():
                return candidate
    raise RuntimeError("Google Chrome executable not found. Set WISHKET_CHROME_EXE.")


def open_chrome_handoff() -> bool:
    """Open visible Chrome for Wishket login/profile completion handoff."""
    chrome = _resolve_google_chrome_exe()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    profile_dir = CACHE_DIR / "wishket_chrome_profile"
    urls = [WISHKET_LOGIN, WISHKET_PROFILE_EDIT]
    args = [chrome, f"--user-data-dir={profile_dir}", "--new-window", *urls]
    subprocess.Popen(args, cwd=str(_ROOT))
    print(f"[Wishket] Chrome handoff opened: {WISHKET_LOGIN} / {WISHKET_PROFILE_EDIT}")
    print("[Wishket] Continue in visible Chrome with the Claude Code web extension or user login.")
    return True

WISHKET_PROFILE_EDIT = f"{WISHKET_BASE}/partner/profile/edit/"

PROFILE_DATA = {
    "headline": "AI 자동화 개발자 · Python · LangChain · 인테리어건축",
    "bio": (
        "Python 기반 AI 에이전트 및 업무 자동화 개발 전문가입니다.\n\n"
        "• LangChain / GPT / Claude API 기반 에이전트·봇 개발\n"
        "• Playwright 자동화, 웹 스크래핑, Discord 봇 개발\n"
        "• FastAPI 백엔드, RESTful API 설계\n"
        "• 인테리어·건축 설계 10년+ 현장 경험\n\n"
        "AI 자동화로 반복 업무를 줄이고 수익을 극대화하는 맞춤 솔루션을 제공합니다."
    ),
}


def update_profile() -> bool:
    """위시켓 프로필 페이지에 접속해 소개글·헤드라인을 자동으로 업데이트한다."""
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="ko-KR",
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        # 저장된 세션 쿠키 로드, 없으면 자동 로그인
        cookies = _load_cached_cookies()
        if cookies:
            context.add_cookies(cookies)
        else:
            if not _do_login(page):
                print("[Profile] 로그인 실패")
                browser.close()
                return False

        try:
            print(f"[Profile] 프로필 편집 페이지 이동: {WISHKET_PROFILE_EDIT}")
            page.goto(WISHKET_PROFILE_EDIT, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)

            if not _is_logged_in(page):
                print("[Profile] 세션 만료 — 재로그인 시도")
                if not _do_login(page):
                    print("[Profile] 재로그인 실패")
                    browser.close()
                    return False
                page.goto(WISHKET_PROFILE_EDIT, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=15000)

            _save_screenshot(page, "profile_before")

            # 헤드라인 (한 줄 소개) 입력 시도
            headline_selectors = [
                'input[name="headline"]',
                'input[placeholder*="한 줄"]',
                'input[placeholder*="소개"]',
                'input[id*="headline"]',
                'input[id*="introduce"]',
            ]
            for sel in headline_selectors:
                el = page.query_selector(sel)
                if el:
                    el.triple_click()
                    el.fill(PROFILE_DATA["headline"])
                    print(f"[Profile] 헤드라인 입력 완료 ({sel})")
                    break
            else:
                print("[Profile] 헤드라인 필드 미발견 — 스킵")

            # 자기소개 textarea 입력 시도
            bio_selectors = [
                'textarea[name="introduce"]',
                'textarea[name="bio"]',
                'textarea[name="description"]',
                'textarea[placeholder*="소개"]',
                'textarea[placeholder*="경력"]',
                'textarea[id*="introduce"]',
                'textarea[id*="bio"]',
            ]
            for sel in bio_selectors:
                el = page.query_selector(sel)
                if el:
                    el.triple_click()
                    el.fill(PROFILE_DATA["bio"])
                    print(f"[Profile] 자기소개 입력 완료 ({sel})")
                    break
            else:
                print("[Profile] 자기소개 필드 미발견 — 스킵")

            # 저장 버튼 클릭
            save_selectors = [
                'button[type="submit"]',
                'button:has-text("저장")',
                'button:has-text("완료")',
                'input[type="submit"]',
            ]
            saved = False
            for sel in save_selectors:
                el = page.query_selector(sel)
                if el:
                    el.click()
                    page.wait_for_timeout(2000)
                    print(f"[Profile] 저장 버튼 클릭 ({sel})")
                    saved = True
                    break

            _save_screenshot(page, "profile_after")
            browser.close()
            return saved

        except PWTimeout as e:
            _save_screenshot(page, "profile_error")
            print(f"[Profile] 타임아웃: {e}")
            browser.close()
            return False
        except Exception as e:
            _save_screenshot(page, "profile_error")
            print(f"[Profile] 오류: {e}")
            browser.close()
            return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="위시켓 공고 스크래퍼")
    parser.add_argument("--manual-login", action="store_true", help="브라우저를 열어 수동 로그인 후 쿠키 저장")
    parser.add_argument("--clear-cache", action="store_true", help="저장된 세션 쿠키 삭제 후 재로그인")
    parser.add_argument("--update-profile", action="store_true", help="위시켓 프로필 자동 업데이트")
    parser.add_argument("--chrome-handoff", action="store_true", help="보이는 Chrome으로 위시켓 로그인/프로필 완성 handoff")
    args = parser.parse_args()

    if args.clear_cache and _SESSION_CACHE.exists():
        _SESSION_CACHE.unlink()
        print(f"[Wishket] 세션 캐시 삭제: {_SESSION_CACHE}")

    if args.manual_login:
        manual_login()
    elif args.chrome_handoff:
        open_chrome_handoff()
    elif args.update_profile:
        ok = update_profile()
        print("[Profile] 업데이트 완료" if ok else "[Profile] 업데이트 실패 — .cache/wishket_debug_profile_*.png 확인")
    else:
        projects, path = run()
        print(f"\n수집 결과: {len(projects)}개")
        for p in projects[:5]:
            print(f"  - {p['title']} | {p['budget']} | {p['link']}")
