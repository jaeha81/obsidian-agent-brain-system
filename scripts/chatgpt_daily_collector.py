#!/usr/bin/env python3
"""
ChatGPT Daily Plus Collector
매일 ChatGPT 대화에서 오늘의 콘텐츠를 수집해 ObsidianVault에 저장.

첫 실행: --login 플래그로 브라우저를 열어 ChatGPT 로그인 후 세션 저장.
이후 실행: 저장된 세션으로 자동 수집 (headless).
"""

import asyncio
import sys
import os
import argparse
from pathlib import Path
from datetime import date
import re

# ── 설정 ──────────────────────────────────────────────────────────────────────
CHATGPT_URL = "https://chatgpt.com/c/6a13070b-b458-8324-ac34-1ae2efd70a4c"
VAULT_BASE = Path("G:/내 드라이브/obsidian-agent-brain-system/ObsidianVault")
OUTPUT_DIR = VAULT_BASE / "04_Wiki" / "daily-plus"
PROFILE_DIR = Path(os.environ.get("USERPROFILE", "~")) / ".playwright-gpt-sessions"
BROWSER_CHANNEL = os.environ.get("GPT_COLLECTOR_BROWSER_CHANNEL", "msedge")
HEADLESS = os.environ.get("GPT_COLLECTOR_HEADLESS", "0").lower() in ("1", "true", "yes")
# ─────────────────────────────────────────────────────────────────────────────


def build_note(content_blocks: list[str], today: date) -> str:
    date_str = today.strftime("%Y-%m-%d")
    joined = "\n\n".join(content_blocks)
    return f"""---
date: {date_str}
source: ChatGPT Daily Plus
tags: [daily-plus, knowledge, auto-collected]
---

# 오늘의 플러스 — {date_str}

{joined}

---
*자동 수집: chatgpt_daily_collector.py*
"""


async def login_mode():
    """첫 실행: 브라우저 열어서 ChatGPT 로그인 후 세션 저장."""
    from playwright.async_api import async_playwright

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[LOGIN] 브라우저를 열어 ChatGPT에 로그인하세요.")
    print(f"[LOGIN] 로그인 완료 후 이 창을 닫으면 세션이 저장됩니다.")
    print(f"[LOGIN] 프로파일 경로: {PROFILE_DIR}")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            channel=BROWSER_CHANNEL,
        )
        page = await context.new_page()
        await page.goto("https://chatgpt.com/", wait_until="domcontentloaded")
        print("[LOGIN] 로그인 완료 후 브라우저를 닫으세요 (Ctrl+W 또는 창 닫기)...")

        # 브라우저가 닫힐 때까지 대기
        try:
            await context.wait_for_event("close", timeout=300000)
        except Exception:
            pass

        await context.close()
        print("[LOGIN] 세션 저장 완료. 이제 --collect 모드로 자동 수집 가능합니다.")


async def collect_mode(force: bool = False):
    """자동 수집: 저장된 세션으로 ChatGPT 접속 후 콘텐츠 추출."""
    from playwright.async_api import async_playwright

    if not PROFILE_DIR.exists():
        print("[ERROR] 저장된 세션 없음. 먼저 --login으로 로그인하세요:")
        print("        python chatgpt_daily_collector.py --login")
        sys.exit(1)

    today = date.today()
    date_str = today.strftime("%Y-%m-%d")
    output_path = OUTPUT_DIR / f"{date_str}.md"

    if output_path.exists() and not force:
        print(f"[SKIP] 오늘 파일 이미 존재: {output_path}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] 세션 프로파일: {PROFILE_DIR}")
    print(f"[INFO] 대상 URL: {CHATGPT_URL}")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=HEADLESS,
            channel=BROWSER_CHANNEL,
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = await context.new_page()

        print("[INFO] 페이지 로드 중...")
        await page.goto(CHATGPT_URL, wait_until="networkidle", timeout=60000)

        # 로그인 확인
        if "login" in page.url or "auth" in page.url:
            print("[ERROR] 세션 만료됨. --login으로 다시 로그인하세요.")
            await context.close()
            sys.exit(1)

        # 대화 메시지 로드 대기
        try:
            await page.wait_for_selector(
                '[data-message-author-role="assistant"]', timeout=30000
            )
        except Exception:
            print("[ERROR] 메시지 로드 실패 — 페이지 구조가 변경되었을 수 있습니다.")
            # 스크린샷 저장 (디버깅용)
            screenshot_path = PROFILE_DIR / "debug_screenshot.png"
            await page.screenshot(path=str(screenshot_path))
            print(f"[DEBUG] 스크린샷 저장: {screenshot_path}")
            await context.close()
            sys.exit(1)

        # 모든 assistant 메시지 추출
        messages = await page.query_selector_all('[data-message-author-role="assistant"]')

        if not messages:
            print("[ERROR] 메시지를 찾을 수 없습니다.")
            await context.close()
            sys.exit(1)

        print(f"[INFO] 총 {len(messages)}개 메시지 발견")

        # 마지막 assistant 메시지 (오늘의 콘텐츠)
        last_msg = messages[-1]
        raw_text = (await last_msg.inner_text()).strip()

        # 너무 짧으면 마지막 2개 합치기
        if len(raw_text) < 100 and len(messages) >= 2:
            prev_text = (await messages[-2].inner_text()).strip()
            blocks = [t for t in [prev_text, raw_text] if t]
        else:
            blocks = [raw_text]

        note_content = build_note(blocks, today)
        output_path.write_text(note_content, encoding="utf-8")

        print(f"[OK] 저장 완료: {output_path}")
        print(f"[미리보기]\n{blocks[-1][:300]}...")

        await context.close()


def main():
    parser = argparse.ArgumentParser(description="ChatGPT Daily Plus → ObsidianVault")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--login", action="store_true", help="브라우저로 ChatGPT 로그인 (최초 1회)")
    group.add_argument("--collect", action="store_true", help="자동 수집 (기본값)")
    parser.add_argument("--force", action="store_true", help="오늘 파일 존재해도 덮어쓰기")
    args = parser.parse_args()

    try:
        if args.login:
            asyncio.run(login_mode())
        else:
            asyncio.run(collect_mode(force=args.force))
    except KeyboardInterrupt:
        print("\n[ABORT] 사용자 중단")
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
