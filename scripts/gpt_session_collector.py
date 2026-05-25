#!/usr/bin/env python3
"""
GPT Session Collector
ChatGPT 대화 전체를 자동 수집하여 ObsidianVault에 저장.

첫 실행: --login 플래그로 브라우저를 열어 ChatGPT 로그인 후 세션 저장.
이후 실행: 저장된 세션으로 비공식 API를 통해 증분 수집 (headless).

Usage:
    python gpt_session_collector.py --login          # 최초 1회 로그인
    python gpt_session_collector.py --collect        # 증분 수집
    python gpt_session_collector.py --collect --dry-run  # 실제 저장 없이 테스트
    python gpt_session_collector.py --collect --full # 전체 재수집
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

# ── 설정 ──────────────────────────────────────────────────────────────────────
VAULT_BASE = Path("G:/내 드라이브/obsidian-agent-brain-system/ObsidianVault")
OUTPUT_BASE = VAULT_BASE / "01_RAW" / "gpt-sessions"
PROFILE_DIR = Path(os.environ.get("USERPROFILE", "~")) / ".playwright-gpt-sessions"
STATE_FILE = Path(__file__).parent / ".gpt_collector_state.json"

# ChatGPT 비공식 API 엔드포인트
API_BASE = "https://chatgpt.com/backend-api"
CONVERSATIONS_URL = f"{API_BASE}/conversations"
CONVERSATION_URL = f"{API_BASE}/conversation"

# 페이지당 대화 수 (최대 100)
PAGE_SIZE = 100
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


# ── 상태 관리 ─────────────────────────────────────────────────────────────────

def load_state() -> dict:
    """마지막 수집 시각 및 메타 정보를 불러온다."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning(f"상태 파일 읽기 실패 (초기화): {e}")
    return {"last_collected_at": None, "collected_ids": []}


def save_state(state: dict) -> None:
    """상태를 저장한다."""
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── 유틸리티 ──────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """제목을 파일명 안전 슬러그로 변환."""
    text = text.strip()
    # 한글·영문·숫자·공백·하이픈·언더스코어만 유지
    text = re.sub(r"[^\w\s가-힣\-]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "_", text)
    # 길이 제한 (80자)
    return text[:80].strip("_") or "untitled"


def parse_iso(ts: str | None) -> datetime | None:
    """ISO 8601 타임스탬프 문자열을 파싱한다."""
    if not ts:
        return None
    try:
        # Python 3.11+ 에서는 fromisoformat이 Z를 처리하지만 하위 호환성 확보
        ts = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def extract_topics_from_messages(messages: list[dict]) -> list[str]:
    """메시지 내용에서 간단한 토픽 리스트를 추출한다 (빈 리스트로 초기화)."""
    return []


# ── 마크다운 빌더 ──────────────────────────────────────────────────────────────

def build_markdown(conv_meta: dict, messages: list[dict]) -> str:
    """대화 메타와 메시지 목록으로 Obsidian 마크다운 노트를 생성한다."""
    conv_id = conv_meta.get("id", "unknown")
    title = conv_meta.get("title", "Untitled")
    created_raw = conv_meta.get("create_time")
    updated_raw = conv_meta.get("update_time")

    created_dt = parse_iso(str(created_raw)) if created_raw else None
    updated_dt = parse_iso(str(updated_raw)) if updated_raw else None

    date_str = (
        created_dt.astimezone().strftime("%Y-%m-%d")
        if created_dt
        else date.today().isoformat()
    )
    updated_str = (
        updated_dt.astimezone().strftime("%Y-%m-%dT%H:%M:%S")
        if updated_dt
        else ""
    )

    topics = extract_topics_from_messages(messages)
    topics_yaml = json.dumps(topics, ensure_ascii=False)

    # frontmatter
    lines = [
        "---",
        f"source: ChatGPT",
        f"date: {date_str}",
        f"conversation_id: {conv_id}",
        f"message_count: {len(messages)}",
        f"topics: {topics_yaml}",
    ]
    if updated_str:
        lines.append(f"updated: {updated_str}")
    lines += ["---", "", f"# {title}", ""]

    # 메시지 본문
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "").strip()
        if not content:
            continue
        role_label = "**User**" if role == "user" else "**Assistant**"
        lines.append(f"{role_label}\n\n{content}\n\n---\n")

    lines.append(f"*자동 수집: gpt_session_collector.py*")
    return "\n".join(lines)


# ── API 수집 ──────────────────────────────────────────────────────────────────

async def fetch_conversation_list(
    page_ctx, since: datetime | None = None
) -> list[dict]:
    """
    비공식 /conversations API를 페이지네이션으로 전체 조회.
    since 가 주어지면 해당 시각 이후 업데이트된 대화만 반환.
    """
    all_convs = []
    offset = 0

    while True:
        url = f"{CONVERSATIONS_URL}?offset={offset}&limit={PAGE_SIZE}&order=updated"
        log.info(f"대화 목록 조회: offset={offset}")

        try:
            response = await page_ctx.request.get(url)
            if not response.ok:
                log.error(f"대화 목록 API 오류 {response.status}: {url}")
                break

            data = await response.json()
        except Exception as e:
            log.error(f"대화 목록 요청 실패: {e}")
            break

        items = data.get("items", [])
        if not items:
            break

        stop_early = False
        for item in items:
            updated_raw = item.get("update_time")
            updated_dt = parse_iso(str(updated_raw)) if updated_raw else None

            if since and updated_dt:
                # since 는 UTC, updated_dt 도 UTC
                since_utc = since.replace(tzinfo=timezone.utc) if since.tzinfo is None else since
                if updated_dt.astimezone(timezone.utc) <= since_utc:
                    stop_early = True
                    break

            all_convs.append(item)

        if stop_early:
            log.info(f"증분 경계 도달 → 조기 종료 (수집: {len(all_convs)}개)")
            break

        total = data.get("total", 0)
        offset += len(items)
        if offset >= total:
            break

    log.info(f"총 {len(all_convs)}개 대화 발견")
    return all_convs


async def fetch_conversation_messages(page_ctx, conv_id: str) -> list[dict]:
    """
    비공식 /conversation/{id} API로 단일 대화의 전체 메시지를 수집한다.
    반환: [{"role": "user"|"assistant", "content": "..."}]
    """
    url = f"{CONVERSATION_URL}/{conv_id}"

    try:
        response = await page_ctx.request.get(url)
        if not response.ok:
            log.error(f"대화 메시지 API 오류 {response.status}: {conv_id}")
            return []
        data = await response.json()
    except Exception as e:
        log.error(f"대화 메시지 요청 실패 ({conv_id}): {e}")
        return []

    # 메시지 트리 파싱
    mapping = data.get("mapping", {})
    if not mapping:
        return []

    messages = []
    try:
        messages = _flatten_message_tree(mapping)
    except Exception as e:
        log.error(f"메시지 트리 파싱 실패 ({conv_id}): {e}")

    return messages


def _flatten_message_tree(mapping: dict) -> list[dict]:
    """
    ChatGPT 대화 매핑(트리 구조)을 시간 순서 메시지 리스트로 변환한다.
    """
    # 루트 노드 탐색 (parent가 없는 노드)
    root_id = None
    for node_id, node in mapping.items():
        if node.get("parent") is None:
            root_id = node_id
            break

    if not root_id:
        return []

    # BFS로 순서대로 방문
    messages = []
    queue = [root_id]
    visited = set()

    while queue:
        current_id = queue.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)

        node = mapping.get(current_id, {})
        message = node.get("message")

        if message:
            role = message.get("author", {}).get("role", "")
            content_obj = message.get("content", {})
            content_type = content_obj.get("content_type", "")

            content_text = ""
            if content_type == "text":
                parts = content_obj.get("parts", [])
                content_text = "\n".join(
                    p for p in parts if isinstance(p, str) and p.strip()
                )
            elif content_type == "tether_browsing_display":
                # 웹 검색 결과 등 — 스킵
                pass

            if role in ("user", "assistant") and content_text:
                messages.append({"role": role, "content": content_text})

        # 자식 노드 추가 (children 배열)
        children = node.get("children", [])
        queue.extend(children)

    return messages


# ── 저장 ─────────────────────────────────────────────────────────────────────

def save_conversation(
    conv_meta: dict, messages: list[dict], dry_run: bool = False
) -> Path | None:
    """
    대화를 ObsidianVault에 마크다운 파일로 저장한다.
    dry_run=True 이면 경로 계산만 하고 실제 저장은 생략.
    """
    conv_id = conv_meta.get("id", "unknown")
    title = conv_meta.get("title", "Untitled")
    created_raw = conv_meta.get("create_time")

    created_dt = parse_iso(str(created_raw)) if created_raw else None
    date_str = (
        created_dt.astimezone().strftime("%Y-%m-%d")
        if created_dt
        else date.today().isoformat()
    )

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
        content = build_markdown(conv_meta, messages)
        out_path.write_text(content, encoding="utf-8")
        log.info(f"저장 완료: {out_path} ({len(messages)}개 메시지)")
        return out_path
    except Exception as e:
        log.error(f"파일 저장 실패 ({conv_id}): {e}")
        return None


# ── 로그인 모드 ──────────────────────────────────────────────────────────────

async def login_mode():
    """브라우저를 열어 ChatGPT 로그인 후 세션을 저장한다."""
    from playwright.async_api import async_playwright

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    log.info(f"브라우저를 열어 ChatGPT에 로그인하세요.")
    log.info(f"로그인 완료 후 이 창을 닫으면 세션이 저장됩니다.")
    log.info(f"프로파일 경로: {PROFILE_DIR}")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            channel="chromium",
        )
        page = await context.new_page()
        await page.goto("https://chatgpt.com/", wait_until="domcontentloaded")
        log.info("로그인 완료 후 브라우저를 닫으세요 (Ctrl+W 또는 창 닫기)...")

        try:
            await context.wait_for_event("close", timeout=300000)
        except Exception:
            pass

        await context.close()
        log.info("세션 저장 완료. 이제 --collect 모드로 자동 수집 가능합니다.")


# ── 수집 모드 ─────────────────────────────────────────────────────────────────

async def collect_mode(dry_run: bool = False, full: bool = False):
    """저장된 세션으로 ChatGPT 대화를 증분 수집한다."""
    from playwright.async_api import async_playwright

    if not PROFILE_DIR.exists():
        log.error("저장된 세션 없음. 먼저 --login으로 로그인하세요:")
        log.error("  python gpt_session_collector.py --login")
        sys.exit(1)

    state = load_state()
    last_collected_str = state.get("last_collected_at")
    collected_ids: set[str] = set(state.get("collected_ids", []))

    since: datetime | None = None
    if last_collected_str and not full:
        since = parse_iso(last_collected_str)
        log.info(f"증분 수집 시작 (마지막 수집: {last_collected_str})")
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

        # ChatGPT 접속 및 로그인 확인
        log.info("ChatGPT 접속 중...")
        try:
            await page.goto("https://chatgpt.com/", wait_until="networkidle", timeout=60000)
        except Exception as e:
            log.error(f"ChatGPT 접속 실패: {e}")
            await context.close()
            sys.exit(1)

        if "login" in page.url or "auth" in page.url:
            log.error("세션 만료됨. --login으로 다시 로그인하세요.")
            await context.close()
            sys.exit(1)

        # API 요청은 page context를 통해 쿠키가 자동 포함됨
        try:
            convs = await fetch_conversation_list(context, since=since)
        except Exception as e:
            log.error(f"대화 목록 조회 실패: {e}")
            await context.close()
            sys.exit(1)

        if not convs:
            log.info("새로운 대화 없음 — 종료")
            await context.close()
            return

        # 이미 수집된 대화 제외 (full 모드가 아닐 때)
        if not full:
            new_convs = [c for c in convs if c.get("id") not in collected_ids]
            skipped = len(convs) - len(new_convs)
            if skipped:
                log.info(f"이미 수집된 {skipped}개 대화 건너뜀")
            convs = new_convs

        log.info(f"수집 대상: {len(convs)}개 대화")

        for i, conv_meta in enumerate(convs, 1):
            conv_id = conv_meta.get("id", "unknown")
            title = conv_meta.get("title", "Untitled")
            log.info(f"[{i}/{len(convs)}] 수집 중: {title[:50]} ({conv_id[:8]}...)")

            try:
                messages = await fetch_conversation_messages(context, conv_id)
            except Exception as e:
                log.error(f"메시지 수집 실패 ({conv_id}): {e} — 건너뜀")
                continue

            if not messages:
                log.warning(f"메시지 없음, 건너뜀: {conv_id}")
                continue

            saved = save_conversation(conv_meta, messages, dry_run=dry_run)
            if saved:
                saved_paths.append(saved)
                if not dry_run:
                    collected_ids.add(conv_id)

        await context.close()

    # 상태 업데이트
    if not dry_run:
        state["last_collected_at"] = now_utc.isoformat()
        state["collected_ids"] = list(collected_ids)
        save_state(state)
        log.info(f"상태 저장 완료: {STATE_FILE}")

    # 결과 요약
    mode_label = "[DRY-RUN] " if dry_run else ""
    log.info(f"{mode_label}수집 완료: {len(saved_paths)}개 파일")
    for p in saved_paths:
        print(str(p))

    return saved_paths


# ── 진입점 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="GPT Session Collector — ChatGPT 대화 전체를 ObsidianVault에 저장"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--login", action="store_true", help="브라우저로 ChatGPT 로그인 (최초 1회)"
    )
    group.add_argument(
        "--collect", action="store_true", help="자동 수집 (기본값)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 저장 없이 수집만 테스트 (경로·메시지 수 출력)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="마지막 수집 시각 무시하고 전체 재수집",
    )
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
