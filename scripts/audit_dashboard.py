#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""대시보드 실측 감사 도구.

주어진 URL을 실제 브라우저(Chrome)로 렌더링해서:
  1) 전체 화면 스크린샷 (screenshot.png)
  2) 콘솔 에러/경고 (JS 오류)
  3) 실패한 네트워크 요청 (4xx/5xx - 죽은 /api/* 등)
를 수집해 report.json + PNG로 저장한다.

사용:
  python -X utf8 scripts/audit_dashboard.py <URL> [--out DIR] [--wait MS]

예:
  python -X utf8 scripts/audit_dashboard.py https://obsidian-agent-brain-system.vercel.app/codex/ --out _audit/codex
"""
import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, quote

from playwright.sync_api import sync_playwright


def _login(page, target_url: str, password: str):
    """login.html 폼으로 로그인해 bucky_auth 쿠키를 획득한다."""
    parts = urlsplit(target_url)
    origin = urlunsplit((parts.scheme, parts.netloc, "", "", ""))
    path = parts.path or "/"
    login_url = f"{origin}/login.html?redirect={quote(path, safe='')}"
    page.goto(login_url, wait_until="networkidle", timeout=45000)
    page.fill("#pw", password)
    with page.expect_navigation(wait_until="networkidle", timeout=45000):
        page.click(".login-btn")


def audit(url: str, out_dir: Path, wait_ms: int, password: str | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    console_msgs = []
    page_errors = []
    failed_requests = []

    with sync_playwright() as p:
        # 시스템 Chrome 사용 (별도 브라우저 다운로드 불필요)
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        page.on("console", lambda m: console_msgs.append({"type": m.type, "text": m.text}))
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        def on_response(resp):
            if resp.status >= 400:
                failed_requests.append({"status": resp.status, "url": resp.url})

        page.on("response", on_response)

        if password:
            _login(page, url, password)

        resp = page.goto(url, wait_until="networkidle", timeout=45000)
        top_status = resp.status if resp else None
        page.wait_for_timeout(wait_ms)

        shot = out_dir / "screenshot.png"
        page.screenshot(path=str(shot), full_page=True)
        title = page.title()
        browser.close()

    report = {
        "url": url,
        "top_status": top_status,
        "title": title,
        "screenshot": str(shot),
        "console_errors": [m for m in console_msgs if m["type"] in ("error", "warning")],
        "console_all_count": len(console_msgs),
        "page_errors": page_errors,
        "failed_requests": failed_requests,
    }
    (out_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", default="_audit/out")
    ap.add_argument("--wait", type=int, default=3000, help="렌더 후 추가 대기(ms)")
    ap.add_argument("--login", action="store_true",
                    help="로그인 후 감사. 비밀번호는 환경변수 DASHBOARD_PASSWORD에서 읽음(저장 안 함)")
    args = ap.parse_args()

    password = None
    if args.login:
        password = os.environ.get("DASHBOARD_PASSWORD", "").strip()
        if not password:
            print("ERROR: --login 사용 시 환경변수 DASHBOARD_PASSWORD 필요", file=sys.stderr)
            return 2

    report = audit(args.url, Path(args.out), args.wait, password)

    print(f"URL           : {report['url']}")
    print(f"HTTP status   : {report['top_status']}")
    print(f"Title         : {report['title']}")
    print(f"Screenshot    : {report['screenshot']}")
    print(f"Console errors: {len(report['console_errors'])}")
    for m in report["console_errors"]:
        print(f"  [{m['type']}] {m['text'][:200]}")
    print(f"Page errors   : {len(report['page_errors'])}")
    for e in report["page_errors"]:
        print(f"  {e[:200]}")
    print(f"Failed reqs   : {len(report['failed_requests'])} (4xx/5xx)")
    for f in report["failed_requests"]:
        print(f"  {f['status']}  {f['url']}")


if __name__ == "__main__":
    sys.exit(main())
