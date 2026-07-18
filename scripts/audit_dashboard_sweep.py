#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""네비 전체 실측 감사 (로그인 1회 후 22개 페이지 순회).

각 페이지마다: HTTP상태 / 제목 / 죽은 API(4xx·5xx) / 콘솔에러 / 스크린샷 수집.
비밀번호는 환경변수 DASHBOARD_PASSWORD에서만 읽음(저장 안 함).

사용:
  python -X utf8 scripts/audit_dashboard_sweep.py --base https://obsidian-agent-brain-system.vercel.app --out _audit/sweep
"""
import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

NAV = [
    ("레포대시보드", "/repo/"),
    ("시스템상태", "/bucky-brain.html"),
    ("위시켓", "/wishket/"),
    ("오늘의플러스", "/daily-plus/"),
    ("태스크보드", "/task-board/"),
    ("Claude앱", "/claude-code/"),
    ("Codex", "/codex/"),
    ("Chris", "/chris/"),
    ("Charlie", "/charlie/"),
    ("내소개", "/my-dev/"),
    ("쇼츠", "/shorts/"),
    ("CHSH마이닝", "/chsh-mining/"),
    ("쓰레드자동화", "/threads/"),
    ("크몽", "/kmong/"),
    ("워크플로우", "/workflow/"),
    ("AI사용량", "/ai-usage.html"),
    ("Wiki Gate", "/wiki-gate.html"),
    ("견적분석", "/estimation-dashboard.html"),
    ("BuckyOS", "/bucky-os.html"),
    ("시스템강화", "/system-enhance.html"),
    ("시스템진화", "/system-evolution.html"),
]


def slugify(path: str) -> str:
    return path.strip("/").replace("/", "_").replace(".html", "") or "root"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://obsidian-agent-brain-system.vercel.app")
    ap.add_argument("--out", default="_audit/sweep")
    ap.add_argument("--wait", type=int, default=2500)
    args = ap.parse_args()

    password = os.environ.get("DASHBOARD_PASSWORD", "").strip()
    if not password:
        print("ERROR: 환경변수 DASHBOARD_PASSWORD 필요", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        cur = {"failed": [], "console_err": []}
        page.on("response", lambda r: cur["failed"].append({"status": r.status, "url": r.url}) if r.status >= 400 else None)
        page.on("console", lambda m: cur["console_err"].append(m.text) if m.type == "error" else None)

        # 로그인 1회
        login_url = f"{args.base}/login.html?redirect={quote('/', safe='')}"
        page.goto(login_url, wait_until="networkidle", timeout=45000)
        page.fill("#pw", password)
        with page.expect_navigation(wait_until="networkidle", timeout=45000):
            page.click(".login-btn")

        for label, path in NAV:
            cur["failed"] = []
            cur["console_err"] = []
            url = args.base + path
            try:
                resp = page.goto(url, wait_until="networkidle", timeout=45000)
                page.wait_for_timeout(args.wait)
                status = resp.status if resp else None
                title = page.title()
                shot = out_dir / f"{slugify(path)}.png"
                page.screenshot(path=str(shot), full_page=True)
                # 자기 자신 페이지 요청 중 404/5xx만 (파비콘 등 잡동사니 포함될 수 있어 api 우선표시)
                dead_api = [f for f in cur["failed"] if "/api/" in f["url"]]
                other_fail = [f for f in cur["failed"] if "/api/" not in f["url"]]
                results.append({
                    "label": label, "path": path, "status": status, "title": title,
                    "dead_api": dead_api, "other_failed": other_fail,
                    "console_errors": cur["console_err"], "screenshot": str(shot),
                })
                flag = "OK " if not dead_api else "API404"
                print(f"[{flag}] {label:12s} {path:26s} status={status} title={title[:40]!r} deadAPI={len(dead_api)}")
                for d in dead_api:
                    print(f"         └ {d['status']} {d['url']}")
            except Exception as e:
                results.append({"label": label, "path": path, "error": str(e)})
                print(f"[ERROR] {label:12s} {path:26s} {e}")

        browser.close()

    (out_dir / "sweep_report.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n리포트 저장: {out_dir / 'sweep_report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
