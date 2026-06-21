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
import urllib.request as _urllib_req

VAULT_BASE = Path("G:/내 드라이브/obsidian-agent-brain-system/ObsidianVault")
OUTPUT_BASE = VAULT_BASE / "01_RAW" / "gpt-sessions"

# 독립 전용 프로파일 (fallback — CDP가 없을 때 사용)
_DEDICATED_PROFILE = Path(__file__).resolve().parent.parent / ".gpt_collector_profile"
PROFILE_DIR = Path(os.environ.get("GPT_COLLECTOR_PROFILE_DIR", str(_DEDICATED_PROFILE)))

# Pulse 수집기와 동일한 CDP 포트 (기존 Chrome에 연결 — 프로파일 잠금 없음)
CDP_PORT = int(os.environ.get("GPT_COLLECTOR_DEBUG_PORT", "9222"))
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"

STATE_FILE = Path(__file__).parent / ".gpt_collector_state.json"
BROWSER_CHANNEL = "chrome"

# ChatGPT 비공식 API 엔드포인트
API_BASE = "https://chatgpt.com/backend-api"
CONVERSATIONS_URL = f"{API_BASE}/conversations"
CONVERSATION_URL = f"{API_BASE}/conversation"

# 페이지당 대화 수 (최대 100)
PAGE_SIZE = 100

# 런타임에 캡처된 Bearer 토큰 (route 인터셉터로 획득)
_bearer_token: str | None = None


def _cdp_available() -> bool:
    """CDP가 실행 중인지 확인."""
    try:
        _urllib_req.urlopen(f"{CDP_URL}/json/version", timeout=2)
        return True
    except Exception:
        return False
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

def slugify(text: str | None) -> str:
    """제목을 파일명 안전 슬러그로 변환."""
    text = (text or "").strip()
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

async def _api_get(url: str, *, page=None, ctx=None) -> dict | None:
    """chatgpt.com API GET 헬퍼.

    CDP 경로에서는 page.evaluate(fetch()) 우선 — 브라우저 실제 쿠키 + Bearer 토큰 사용.
    page가 없으면 ctx.request 로 폴백.
    """
    global _bearer_token
    if page is not None:
        try:
            data = await page.evaluate(
                """async ([u, token]) => {
                    const headers = token ? {Authorization: 'Bearer ' + token} : {};
                    const r = await fetch(u, {credentials: 'include', headers});
                    if (!r.ok) return {__error__: r.status};
                    return await r.json();
                }""",
                [url, _bearer_token],
            )
            if isinstance(data, dict) and "__error__" in data:
                log.warning(f"API HTTP {data['__error__']}: {url[-60:]}")
                return None
            return data  # None이면 호출부에서 처리
        except Exception as e:
            log.warning(f"page.evaluate 실패, ctx.request로 폴백: {e}")
    if ctx is not None:
        try:
            headers = {"Authorization": f"Bearer {_bearer_token}"} if _bearer_token else {}
            resp = await ctx.request.get(url, timeout=15000, headers=headers)
            if resp.ok:
                return await resp.json()
        except Exception as e:
            log.warning(f"ctx.request 실패: {e}")
    return None


async def fetch_conversation_list(
    page_ctx, since: datetime | None = None, *, page=None
) -> list[dict]:
    """
    비공식 /conversations API를 페이지네이션으로 전체 조회.
    since 가 주어지면 해당 시각 이후 업데이트된 대화만 반환.
    page 인자가 있으면 page.evaluate(fetch())로 요청 (CDP 쿠키 보장).
    """
    all_convs = []
    offset = 0

    while True:
        url = f"{CONVERSATIONS_URL}?offset={offset}&limit={PAGE_SIZE}&order=updated"
        log.info(f"대화 목록 조회: offset={offset}")

        try:
            data = await _api_get(url, page=page, ctx=page_ctx)
            if data is None:
                log.error(f"대화 목록 API 오류 (None 응답): {url}")
                break
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


async def fetch_conversation_messages(page_ctx, conv_id: str, *, page=None) -> list[dict]:
    """
    비공식 /conversation/{id} API로 단일 대화의 전체 메시지를 수집한다.
    반환: [{"role": "user"|"assistant", "content": "..."}]
    429 Rate Limit 시 60초 대기 후 1회 재시도.
    """
    import asyncio as _aio
    url = f"{CONVERSATION_URL}/{conv_id}"

    for attempt in range(2):
        try:
            data = await _api_get(url, page=page, ctx=page_ctx)
            if data is None:
                if attempt == 0:
                    log.warning(f"대화 메시지 429/오류 — 60초 대기 후 재시도: {conv_id}")
                    await _aio.sleep(60)
                    continue
                log.error(f"대화 메시지 API 오류 (재시도 후도 실패): {conv_id}")
                return []
            break
        except Exception as e:
            log.error(f"대화 메시지 요청 실패 ({conv_id}): {e}")
            return []
    else:
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
    """전용 Playwright 프로파일로 ChatGPT 로그인 후 세션을 저장한다."""
    from playwright.async_api import async_playwright

    log.info(f"전용 프로파일 경로: {PROFILE_DIR}")
    log.info("Chrome을 열어 ChatGPT에 로그인하세요.")
    log.info("로그인 완료 후 이 창을 닫으면 세션이 저장됩니다.")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            channel=BROWSER_CHANNEL,
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
    """ChatGPT 대화를 증분 수집한다.

    우선순위:
    1. CDP 경로: Pulse 수집기가 열어둔 Chrome(포트 9222)에 연결 — 프로파일 잠금 없음
    2. 전용 프로파일 경로: CDP 없을 때 headless Playwright 사용
    """
    from playwright.async_api import async_playwright

    use_cdp = _cdp_available()

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
        if use_cdp:
            log.info(f"CDP 경로: 기존 Chrome에 연결 ({CDP_URL})")
            browser = await p.chromium.connect_over_cdp(CDP_URL)
            contexts = browser.contexts
            context = contexts[0] if contexts else await browser.new_context()
        else:
            log.info("전용 프로파일 경로: headless Chrome 시작")
            if not PROFILE_DIR.exists():
                log.error(f"전용 프로파일이 없습니다: {PROFILE_DIR}")
                log.error("먼저 --login 플래그로 ChatGPT 로그인을 완료하세요.")
                sys.exit(1)
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                headless=True,
                channel=BROWSER_CHANNEL,
                args=["--disable-blink-features=AutomationControlled"],
            )

        # ── chatgpt.com 열린 탭 탐색 + Bearer 토큰 캡처
        global _bearer_token
        _bearer_token = None
        chatgpt_page = None
        if use_cdp:
            for _ctx in browser.contexts:
                for _pg in _ctx.pages:
                    if "chatgpt.com" in _pg.url:
                        chatgpt_page = _pg
                        break
                if chatgpt_page:
                    break
            if chatgpt_page:
                log.info(f"chatgpt.com 탭 발견: {chatgpt_page.url[:60]}")
                # route 인터셉터로 Bearer 토큰 캡처
                async def _capture_token(route, request):
                    global _bearer_token
                    auth = request.headers.get("authorization", "")
                    if auth.startswith("Bearer ") and not _bearer_token:
                        _bearer_token = auth[7:]
                        log.info(f"Bearer 토큰 캡처 완료 ({len(_bearer_token)}자)")
                    await route.continue_()
                await chatgpt_page.route("**/backend-api/**", _capture_token)
                # 페이지 새로고침 → 토큰 포함 요청 발생
                log.info("chatgpt.com/pulse 새로고침 — Bearer 토큰 대기 중...")
                await chatgpt_page.goto("https://chatgpt.com/pulse", wait_until="domcontentloaded")
                await chatgpt_page.wait_for_timeout(4000)
                if _bearer_token:
                    log.info("Bearer 토큰 확보 완료")
                else:
                    log.warning("Bearer 토큰 미확보 — 일부 API 접근 제한될 수 있음")
            else:
                log.warning("chatgpt.com 탭 없음 — context.request 폴백 (쿠키 미보장)")

        async def _refresh_bearer_token() -> bool:
            """Bearer 토큰 만료 시 chatgpt.com/pulse 재방문으로 갱신."""
            global _bearer_token
            if chatgpt_page is None:
                return False
            old_token = _bearer_token
            _bearer_token = None
            try:
                log.info("Bearer 토큰 갱신 시도: chatgpt.com/pulse 재방문...")
                await chatgpt_page.goto("https://chatgpt.com/pulse", wait_until="domcontentloaded")
                await chatgpt_page.wait_for_timeout(4000)
                if _bearer_token:
                    log.info(f"Bearer 토큰 갱신 완료 ({len(_bearer_token)}자)")
                    return True
                _bearer_token = old_token
                log.warning("Bearer 토큰 갱신 실패 — 이전 토큰 유지")
                return False
            except Exception as e:
                _bearer_token = old_token
                log.error(f"Bearer 토큰 갱신 오류: {e}")
                return False

        # ── 세션 확인: /api/auth/session 우선 (NextAuth), 폴백은 /backend-api/me
        log.info("ChatGPT 세션 확인 중...")
        api_ok = False
        try:
            _sess = await _api_get("https://chatgpt.com/api/auth/session", page=chatgpt_page, ctx=context)
            if _sess and _sess.get("user", {}).get("email"):
                _user = _sess["user"]
                api_ok = True
                log.info(f"세션 확인 OK (NextAuth): {_user.get('email')} / {_user.get('id','')[:20]}")
            else:
                # 폴백: /backend-api/me (구형 체크 — ua- 접두사 아닌 경우만 ok)
                _me = await _api_get(f"{API_BASE}/me", page=chatgpt_page, ctx=context)
                if _me:
                    api_ok = bool(_me.get("email")) or not str(_me.get("id", "")).startswith("ua-")
                    if api_ok:
                        log.info(f"세션 확인 OK (backend-api/me): {_me.get('email')}")
                    else:
                        log.warning(f"게스트 세션 감지 (id={_me.get('id','')[:12]}, email 없음)")
                else:
                    log.warning("세션 확인 실패 (응답 없음)")
        except Exception as _e:
            log.warning(f"세션 확인 오류: {_e}")

        if not api_ok:
            # 세션 만료 — 자동 재로그인 시도하지 않음 (Google OAuth 자동화 불안정)
            if use_cdp:
                log.error(
                    "ChatGPT 세션 없음: Chrome에서 chatgpt.com 에 로그인하세요.\n"
                    "로그인 후 다시 실행하면 됩니다."
                )
            else:
                log.error(
                    "ChatGPT 세션 만료: 전용 프로파일에 재로그인이 필요합니다.\n"
                    "  python scripts/gpt_session_collector.py --login\n"
                    "브라우저에서 ChatGPT 로그인 후 창을 닫으면 자동 저장됩니다."
                )
            if not use_cdp:
                await context.close()
            sys.exit(1)

        # API 요청: page.evaluate 우선 (CDP 쿠키 보장), 폴백은 context.request
        try:
            convs = await fetch_conversation_list(context, since=since, page=chatgpt_page)
        except Exception as e:
            log.error(f"대화 목록 조회 실패: {e}")
            if not use_cdp:
                await context.close()
            sys.exit(1)

        if not convs:
            log.info("새로운 대화 없음 — 종료")
            if not use_cdp:
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

        consecutive_errors = 0
        MAX_CONSECUTIVE_ERRORS = 5
        REQUEST_DELAY = 1.5  # 요청 간 딜레이(초) — 429 Rate Limit 방지

        for i, conv_meta in enumerate(convs, 1):
            if i > 1:
                await asyncio.sleep(REQUEST_DELAY)
            conv_id = conv_meta.get("id", "unknown")
            title = conv_meta.get("title", "Untitled")
            log.info(f"[{i}/{len(convs)}] 수집 중: {title[:50]} ({conv_id[:8]}...)")

            try:
                messages = await fetch_conversation_messages(context, conv_id, page=chatgpt_page)
            except Exception as e:
                log.error(f"메시지 수집 실패 ({conv_id}): {e} — 건너뜀")
                consecutive_errors += 1
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    log.warning(f"연속 {consecutive_errors}회 오류 — Bearer 토큰 갱신 시도")
                    if await _refresh_bearer_token():
                        consecutive_errors = 0
                continue

            if not messages:
                log.warning(f"메시지 없음, 건너뜀: {conv_id}")
                consecutive_errors += 1
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    log.warning(f"연속 {consecutive_errors}회 빈 응답 — Bearer 토큰 갱신 시도")
                    if await _refresh_bearer_token():
                        consecutive_errors = 0
                continue

            consecutive_errors = 0
            saved = save_conversation(conv_meta, messages, dry_run=dry_run)
            if saved:
                saved_paths.append(saved)
                if not dry_run:
                    collected_ids.add(conv_id)

        if not use_cdp:
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
            asyncio.run(collect_mode(
                dry_run=args.dry_run,
                full=args.full,
            ))
    except KeyboardInterrupt:
        log.info("사용자 중단")
    except Exception as e:
        log.error(f"예상치 못한 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
