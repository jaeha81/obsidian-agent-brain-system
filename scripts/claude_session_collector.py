#!/usr/bin/env python3
"""
Claude Session Collector
claude.ai 대화를 자동 수집하여 ObsidianVault에 저장.

Usage:
    python claude_session_collector.py --login          # 최초 1회 로그인
    python claude_session_collector.py --collect        # 증분 수집
    python claude_session_collector.py --collect --dry-run
    python claude_session_collector.py --collect --full # 전체 재수집
"""

import asyncio
import sys
import os
import json
import argparse
import re
import logging
from pathlib import Path
from datetime import datetime, timezone, date

VAULT_BASE = Path("G:/내 드라이브/obsidian-agent-brain-system/ObsidianVault")
OUTPUT_BASE = VAULT_BASE / "01_RAW" / "claude-sessions"
PROFILE_DIR = Path(os.environ.get("USERPROFILE", "~")) / ".playwright-claude-sessions"
STATE_FILE = Path(__file__).parent / ".claude_collector_state.json"

API_BASE = "https://claude.ai/api"
PAGE_SIZE = 50

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s", stream=sys.stdout)
log = logging.getLogger(__name__)


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning(f"상태 파일 읽기 실패: {e}")
    return {"last_collected_at": None, "collected_ids": [], "org_id": None}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def slugify(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[^\w\s가-힣\-]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "_", text)
    return text[:80].strip("_") or "untitled"


def parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def build_markdown(conv_meta: dict, messages: list[dict]) -> str:
    conv_id = conv_meta.get("uuid", conv_meta.get("id", "unknown"))
    title = conv_meta.get("name", "Untitled")
    created_raw = conv_meta.get("created_at")
    updated_raw = conv_meta.get("updated_at")

    created_dt = parse_iso(created_raw)
    updated_dt = parse_iso(updated_raw)

    date_str = created_dt.astimezone().strftime("%Y-%m-%d") if created_dt else date.today().isoformat()
    updated_str = updated_dt.astimezone().strftime("%Y-%m-%dT%H:%M:%S") if updated_dt else ""

    lines = [
        "---",
        "source: Claude",
        f"date: {date_str}",
        f"conversation_id: {conv_id}",
        f"message_count: {len(messages)}",
        "topics: []",
    ]
    if updated_str:
        lines.append(f"updated: {updated_str}")
    lines += ["---", "", f"# {title}", ""]

    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "").strip()
        if not content:
            continue
        label = "**Human**" if role == "human" else "**Assistant**"
        lines.append(f"{label}\n\n{content}\n\n---\n")

    lines.append("*자동 수집: claude_session_collector.py*")
    return "\n".join(lines)


async def get_org_id(page_ctx) -> str | None:
    """claude.ai 계정의 organization ID를 가져온다."""
    try:
        resp = await page_ctx.request.get(f"{API_BASE}/organizations")
        if resp.ok:
            orgs = await resp.json()
            if orgs:
                return orgs[0].get("uuid") or orgs[0].get("id")
    except Exception as e:
        log.error(f"org_id 조회 실패: {e}")
    return None


async def fetch_conversation_list(page_ctx, org_id: str, since: datetime | None = None) -> list[dict]:
    all_convs = []
    url = f"{API_BASE}/organizations/{org_id}/chat_conversations?limit={PAGE_SIZE}"

    while url:
        log.info(f"대화 목록 조회: {url[:80]}...")
        try:
            resp = await page_ctx.request.get(url)
            if not resp.ok:
                log.error(f"대화 목록 API 오류 {resp.status}")
                break
            data = await resp.json()
        except Exception as e:
            log.error(f"대화 목록 요청 실패: {e}")
            break

        items = data if isinstance(data, list) else data.get("conversations", [])
        if not items:
            break

        stop_early = False
        for item in items:
            updated_dt = parse_iso(item.get("updated_at"))
            if since and updated_dt:
                since_utc = since.replace(tzinfo=timezone.utc) if since.tzinfo is None else since
                if updated_dt.astimezone(timezone.utc) <= since_utc:
                    stop_early = True
                    break
            all_convs.append(item)

        if stop_early:
            break

        # 페이지네이션 처리
        next_cursor = data.get("next_page_token") if isinstance(data, dict) else None
        if next_cursor:
            url = f"{API_BASE}/organizations/{org_id}/chat_conversations?limit={PAGE_SIZE}&cursor={next_cursor}"
        else:
            break

    log.info(f"총 {len(all_convs)}개 대화 발견")
    return all_convs


async def fetch_conversation_messages(page_ctx, org_id: str, conv_id: str) -> list[dict]:
    url = f"{API_BASE}/organizations/{org_id}/chat_conversations/{conv_id}"
    try:
        resp = await page_ctx.request.get(url)
        if not resp.ok:
            log.error(f"대화 메시지 API 오류 {resp.status}: {conv_id}")
            return []
        data = await resp.json()
    except Exception as e:
        log.error(f"대화 메시지 요청 실패: {e}")
        return []

    chat_messages = data.get("chat_messages", [])
    messages = []
    for msg in chat_messages:
        role = msg.get("sender", msg.get("role", "unknown"))
        # content는 문자열이거나 리스트(블록)일 수 있음
        content_raw = msg.get("content", "")
        if isinstance(content_raw, list):
            parts = []
            for block in content_raw:
                if isinstance(block, dict):
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
            content = "\n".join(p for p in parts if p.strip())
        else:
            content = str(content_raw)
        if content.strip():
            messages.append({"role": role, "content": content})
    return messages


def save_conversation(conv_meta: dict, messages: list[dict], dry_run: bool = False) -> Path | None:
    conv_id = conv_meta.get("uuid", conv_meta.get("id", "unknown"))
    title = conv_meta.get("name", "Untitled")
    created_dt = parse_iso(conv_meta.get("created_at"))
    date_str = created_dt.astimezone().strftime("%Y-%m-%d") if created_dt else date.today().isoformat()

    slug = slugify(title)
    short_id = conv_id[:8]
    filename = f"{slug}_{short_id}.md"
    out_dir = OUTPUT_BASE / date_str
    out_path = out_dir / filename

    if dry_run:
        log.info(f"[DRY-RUN] 저장 예정: {out_path} ({len(messages)}개 메시지)")
        return out_path

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_text(build_markdown(conv_meta, messages), encoding="utf-8")
        log.info(f"저장 완료: {out_path} ({len(messages)}개 메시지)")
        return out_path
    except Exception as e:
        log.error(f"파일 저장 실패: {e}")
        return None


async def login_mode():
    from playwright.async_api import async_playwright

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    log.info(f"브라우저를 열어 claude.ai에 로그인하세요.")
    log.info(f"로그인 완료 후 이 창을 닫으면 세션이 저장됩니다.")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR), headless=False, channel="chromium"
        )
        page = await context.new_page()
        await page.goto("https://claude.ai/", wait_until="domcontentloaded")
        log.info("로그인 완료 후 브라우저를 닫으세요...")
        try:
            await context.wait_for_event("close", timeout=300000)
        except Exception:
            pass
        await context.close()
        log.info("세션 저장 완료.")


async def collect_mode(dry_run: bool = False, full: bool = False):
    from playwright.async_api import async_playwright

    if not PROFILE_DIR.exists():
        log.error("저장된 세션 없음. 먼저 --login으로 로그인하세요.")
        sys.exit(1)

    state = load_state()
    last_collected_str = state.get("last_collected_at")
    collected_ids: set[str] = set(state.get("collected_ids", []))
    org_id = state.get("org_id")

    since: datetime | None = None
    if last_collected_str and not full:
        since = parse_iso(last_collected_str)
        log.info(f"증분 수집 시작 (마지막: {last_collected_str})")
    else:
        log.info("전체 수집 시작")

    saved_paths: list[Path] = []
    now_utc = datetime.now(timezone.utc)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=True,
            channel="chromium",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await context.new_page()

        log.info("claude.ai 접속 중...")
        try:
            await page.goto("https://claude.ai/", wait_until="networkidle", timeout=60000)
        except Exception as e:
            log.error(f"접속 실패: {e}")
            await context.close()
            sys.exit(1)

        if "login" in page.url or "auth" in page.url:
            log.error("세션 만료됨. --login으로 다시 로그인하세요.")
            await context.close()
            sys.exit(1)

        # org_id 캐시
        if not org_id:
            org_id = await get_org_id(context)
            if not org_id:
                log.error("Organization ID 조회 실패")
                await context.close()
                sys.exit(1)
            state["org_id"] = org_id
            log.info(f"org_id: {org_id}")

        convs = await fetch_conversation_list(context, org_id, since=since)

        if not convs:
            log.info("새로운 대화 없음 — 종료")
            await context.close()
            return

        if not full:
            new_convs = [c for c in convs if c.get("uuid", c.get("id")) not in collected_ids]
            skipped = len(convs) - len(new_convs)
            if skipped:
                log.info(f"이미 수집된 {skipped}개 건너뜀")
            convs = new_convs

        log.info(f"수집 대상: {len(convs)}개 대화")

        for i, conv_meta in enumerate(convs, 1):
            conv_id = conv_meta.get("uuid", conv_meta.get("id", "unknown"))
            title = conv_meta.get("name", "Untitled")
            log.info(f"[{i}/{len(convs)}] {title[:50]} ({conv_id[:8]}...)")

            messages = await fetch_conversation_messages(context, org_id, conv_id)
            if not messages:
                log.warning(f"메시지 없음, 건너뜀: {conv_id}")
                continue

            saved = save_conversation(conv_meta, messages, dry_run=dry_run)
            if saved:
                saved_paths.append(saved)
                if not dry_run:
                    collected_ids.add(conv_id)

        await context.close()

    if not dry_run:
        state["last_collected_at"] = now_utc.isoformat()
        state["collected_ids"] = list(collected_ids)
        save_state(state)

    label = "[DRY-RUN] " if dry_run else ""
    log.info(f"{label}수집 완료: {len(saved_paths)}개 파일")
    for p in saved_paths:
        print(str(p))


def main():
    parser = argparse.ArgumentParser(description="Claude Session Collector — claude.ai 대화를 ObsidianVault에 저장")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--login", action="store_true")
    group.add_argument("--collect", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()

    try:
        if args.login:
            asyncio.run(login_mode())
        else:
            asyncio.run(collect_mode(dry_run=args.dry_run, full=args.full))
    except KeyboardInterrupt:
        log.info("사용자 중단")
    except Exception as e:
        log.error(f"예상치 못한 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
