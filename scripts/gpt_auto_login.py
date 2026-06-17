#!/usr/bin/env python3
"""
GPT Auto-Login — ChatGPT 세션 자동 재연결 모듈.

Chrome 프로필에 저장된 Google 계정으로 자동 OAuth 로그인을 시도한다.
실패 시 Discord 알림을 전송하고, #jh-코덱스앱 !gpt-login 에스컬레이션 경로를 안내한다.

사용법:
  from gpt_auto_login import try_auto_login

  success = await try_auto_login(profile_dir, discord_webhook_url)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.request
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# 로그인 성공 판단 URL 패턴
_LOGIN_URL_PATTERNS = ("login", "auth", "accounts.google", "openid")
_SUCCESS_URL_PREFIX = "https://chatgpt.com/"

# 자동 로그인 타임아웃 (초)
AUTO_LOGIN_TIMEOUT_MS = 45_000

# 클릭 대상 텍스트 (ChatGPT 로그인 페이지)
_LOGIN_BTN_SELECTORS = [
    "button:has-text('Log in')",
    "a:has-text('Log in')",
    "[data-testid='login-button']",
]
_GOOGLE_BTN_SELECTORS = [
    "button:has-text('Continue with Google')",
    "button:has-text('Google로 계속')",
    "[data-provider='google']",
]


async def _is_login_page(page) -> bool:
    """현재 페이지가 로그인 페이지인지 확인."""
    url = page.url
    return any(p in url for p in _LOGIN_URL_PATTERNS)


async def _click_first_visible(page, selectors: list[str]) -> bool:
    """주어진 셀렉터 목록 중 첫 번째로 보이는 버튼을 클릭."""
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=3_000):
                await btn.click()
                return True
        except Exception:
            continue
    return False


async def try_google_oauth_login(profile_dir: Path) -> bool:
    """
    Playwright를 사용하여 Chrome 프로필의 Google 계정으로 ChatGPT 자동 로그인 시도.

    Returns:
        True  — 로그인 성공 (chatgpt.com으로 리다이렉트 완료)
        False — 로그인 실패 (수동 개입 필요)
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        log.error("[AUTO-LOGIN] playwright 미설치. pip install playwright 필요.")
        return False

    log.info("[AUTO-LOGIN] Google OAuth 자동 로그인 시도 중...")

    try:
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=True,
                channel="chrome",
                args=["--disable-blink-features=AutomationControlled"],
            )

            page = await context.new_page()

            try:
                await page.goto(
                    "https://chatgpt.com/",
                    wait_until="domcontentloaded",
                    timeout=30_000,
                )
            except Exception as e:
                log.error(f"[AUTO-LOGIN] chatgpt.com 접속 실패: {e}")
                await context.close()
                return False

            # 이미 로그인되어 있으면 성공
            if not await _is_login_page(page):
                log.info("[AUTO-LOGIN] 세션이 이미 유효합니다.")
                await context.close()
                return True

            # Step 1: "Log in" 버튼 클릭
            clicked = await _click_first_visible(page, _LOGIN_BTN_SELECTORS)
            if not clicked:
                log.warning("[AUTO-LOGIN] 'Log in' 버튼을 찾지 못했습니다.")
                await context.close()
                return False

            await page.wait_for_timeout(1_500)

            # Step 2: "Continue with Google" 버튼 클릭
            clicked = await _click_first_visible(page, _GOOGLE_BTN_SELECTORS)
            if not clicked:
                log.warning("[AUTO-LOGIN] 'Continue with Google' 버튼을 찾지 못했습니다.")
                await context.close()
                return False

            # Step 3: chatgpt.com으로 리다이렉트 대기
            try:
                await page.wait_for_url(
                    "https://chatgpt.com/**",
                    timeout=AUTO_LOGIN_TIMEOUT_MS,
                )
                final_url = page.url
                if await _is_login_page(page):
                    log.warning(f"[AUTO-LOGIN] 리다이렉트 후에도 로그인 페이지: {final_url}")
                    await context.close()
                    return False

                log.info(f"[AUTO-LOGIN] 자동 로그인 성공: {final_url}")
                await context.close()
                return True

            except Exception as e:
                log.warning(f"[AUTO-LOGIN] 리다이렉트 타임아웃: {e}")
                await context.close()
                return False

    except Exception as e:
        log.error(f"[AUTO-LOGIN] 예기치 않은 오류: {e}")
        return False


def send_discord_alert(webhook_url: str, message: str) -> None:
    """Discord 웹훅으로 알림 전송 (동기)."""
    if not webhook_url:
        log.warning("[AUTO-LOGIN] Discord 웹훅 URL 미설정 — 알림 생략")
        return
    try:
        payload = json.dumps({"content": message}).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10):
            pass
        log.info("[AUTO-LOGIN] Discord 알림 전송 완료")
    except Exception as e:
        log.warning(f"[AUTO-LOGIN] Discord 알림 전송 실패: {e}")


async def auto_reconnect(
    profile_dir: Path,
    discord_webhook_url: Optional[str] = None,
    context_label: str = "GPT 수집",
) -> bool:
    """
    GPT 세션 자동 재연결 메인 진입점.

    1. Google OAuth 자동 로그인 시도
    2. 실패 시 Discord 알림 + !gpt-login 안내
    3. 결과 반환

    Args:
        profile_dir: Chrome 전용 프로필 디렉토리
        discord_webhook_url: Discord 웹훅 URL (환경변수 BUCKY_DISCORD_WEBHOOK 또는 None)
        context_label: 로그/알림에 표시할 컨텍스트 이름

    Returns:
        True  — 재연결 성공
        False — 수동 개입 필요
    """
    webhook = discord_webhook_url or os.environ.get("BUCKY_DISCORD_WEBHOOK", "")

    success = await try_google_oauth_login(profile_dir)

    if success:
        log.info(f"[AUTO-LOGIN] {context_label} — 자동 재연결 성공")
        return True

    # 자동 로그인 실패 → Discord 알림
    fail_msg = (
        f"⚠️ **[{context_label}] GPT 자동 로그인 실패**\n"
        "Chrome 프로필의 Google 세션이 만료되었습니다.\n"
        "**#jh-코덱스앱 채널에서 아래 명령어를 실행하세요:**\n"
        "```\n!gpt-login\n```\n"
        "로그인 후 수집이 자동 재시작됩니다."
    )
    send_discord_alert(webhook, fail_msg)
    log.error(f"[AUTO-LOGIN] {context_label} — 자동 재연결 실패. 수동 개입 필요.")
    return False
