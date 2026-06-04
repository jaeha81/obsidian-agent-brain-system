#!/usr/bin/env python3
"""
ChatGPT Pulse collector.

Collects the daily ChatGPT Pulse overview plus every visible Pulse card detail
from a dedicated Chrome profile, then saves the result as an Obsidian note.

Login model:
  1. Run with --login once.
  2. Sign in inside the dedicated Chrome profile that opens.
  3. Future --collect runs reuse that profile.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except ValueError:
    pass

try:
    import websocket
except ImportError:  # pragma: no cover - environment diagnostic
    websocket = None


ROOT = Path(__file__).resolve().parents[1]
CHATGPT_URL = os.environ.get("GPT_COLLECTOR_URL", "https://chatgpt.com/pulse")
VAULT_BASE = ROOT / "ObsidianVault"
OUTPUT_DIR = VAULT_BASE / "04_Wiki" / "daily-plus"
PROFILE_DIR = Path(
    os.environ.get(
        "GPT_COLLECTOR_PROFILE_DIR",
        str(Path.home() / ".chatgpt-daily-chrome-profile"),
    )
)
DEBUG_PORT = int(os.environ.get("GPT_COLLECTOR_DEBUG_PORT", "9222"))
CHROME_EXE = os.environ.get("GPT_COLLECTOR_CHROME_EXE") or (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe"
)


def build_note(capture: dict[str, Any], today: date) -> str:
    date_str = today.strftime("%Y-%m-%d")
    collected_at = datetime.now().astimezone().isoformat(timespec="seconds")
    source = capture.get("source") or "ChatGPT Pulse"
    source_url = capture.get("source_url") or CHATGPT_URL
    collection_status = capture.get("collectionStatus") or "collected"
    source_error = (capture.get("sourceError") or "").strip()
    overview = (capture.get("overviewText") or "").strip()
    cards = capture.get("cards") or []

    sections: list[str] = []
    if overview:
        sections.append(f"## Overview\n\n{overview}")

    if cards:
        card_sections = ["## Pulse Cards"]
        for idx, card in enumerate(cards, start=1):
            title = (card.get("title") or f"Card {idx}").strip()
            summary = (card.get("summary") or "").strip()
            detail = (card.get("detailText") or "").strip()
            body_parts = [f"### {idx}. {title}"]
            if summary:
                body_parts.append(summary)
            if detail:
                body_parts.append(f"#### Detail\n\n{detail}")
            else:
                body_parts.append("#### Detail\n\n[Detail extraction failed]")
            card_sections.append("\n\n".join(body_parts))
        sections.append("\n\n".join(card_sections))

    summary_text = overview[:200].replace("\n", " ").strip() if overview else f"ChatGPT Pulse {date_str}"
    joined = "\n\n".join(sections)
    return f"""---
date: {date_str}
source: {source}
source_url: {source_url}
collected_at: {collected_at}
collection_status: {collection_status}
card_count: {len(cards)}
category: gpt_feedback
summary: "{summary_text}"
next_action: review
status: inbox
tags:
  - pulse
  - daily-plus
  - knowledge
  - auto-collected
  - "#area/gpt_feedback"
  - "#area/research"
---

# ChatGPT Pulse - {date_str}

{f"## Source Error\n\n{source_error}\n\n" if source_error else ""}{joined}

---
*Auto-collected by `chatgpt_daily_collector.py`.*
"""


def build_recovery_capture(source_error: str) -> dict[str, Any]:
    clean_error = " ".join(str(source_error).split())
    overview = (
        "OABS Daily Plus recovery capture. Official ChatGPT Pulse was not "
        "available during collection, so Bucky records an operational Daily Plus "
        "snapshot instead of leaving the day empty."
    )
    cards = [
        {
            "title": "Daily Plus source availability guard",
            "summary": "공식 Pulse가 404/빈 카드일 때 빈 대시보드를 만들지 않도록 수집 실패를 차단한다.",
            "detailText": (
                "ChatGPT Pulse 직접 접근 또는 카드 추출이 실패하면 해당 실패를 명확한 운영 이벤트로 "
                "남긴다. 404 Not Found, 로그인 필요, 카드 0개 상태는 정상 수집으로 저장하지 않는다."
            ),
        },
        {
            "title": "Bucky 09시 보고 fail-safe",
            "summary": "오늘의 플러스가 비어도 Bucky가 사용자에게 실패 원인과 다음 조치를 보고한다.",
            "detailText": (
                "daily_plus_morning_report.py는 빈/오류 캡처를 감지하면 needs-attention 보고서를 "
                "남긴다. 공식 Pulse가 정상일 때는 대시보드와 후보 비교표를 갱신하고, 실패할 때는 "
                "기존 정상 대시보드를 보호한다."
            ),
        },
        {
            "title": "Tomorrow automation continuity",
            "summary": "내일부터 매일 실행될 자동화는 OABS 경로에서 수집, 진화 리포트, Bucky 보고를 순차 실행한다.",
            "detailText": (
                "BuckyDailyPlus는 Obsidian Agent Brain System 기준으로만 동작해야 한다. "
                "이전 시스템 경로를 실행 백엔드로 사용하지 않고, 수집 실패 시 복구 캡처를 "
                "남겨 다음 단계가 완전히 끊기지 않게 한다."
            ),
        },
        {
            "title": "Public dashboard integrity",
            "summary": "실패 수집이 docs/daily-plus.html을 오염시키지 않도록 생성 전 후보 존재를 검증한다.",
            "detailText": (
                "대시보드는 Pulse Evolution 후보가 있는 날짜만 정상 생성한다. 복구 캡처는 후보를 "
                "제공하므로 오늘 상태를 사용자에게 설명할 수 있고, 단순 404 스텁은 대시보드를 덮지 못한다."
            ),
        },
    ]
    return {
        "source": "OABS Daily Plus Recovery",
        "source_url": CHATGPT_URL,
        "collectionStatus": "fallback",
        "sourceError": clean_error,
        "overviewText": overview,
        "cards": cards,
    }


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_triage_note(capture: dict[str, Any], today: date, manifest_sha256: str) -> None:
    """Card 6/7 패턴: 오늘의_플러스 수집 후 Bucky 트리아지 노트 자동 생성."""
    triage_dir = VAULT_BASE / "00_Inbox" / "daily-plus-triage"
    triage_dir.mkdir(parents=True, exist_ok=True)
    date_str = today.strftime("%Y-%m-%d")
    triage_path = triage_dir / f"{date_str}-triage.md"

    cards = capture.get("cards") or []
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    card_lines = []
    for i, card in enumerate(cards, 1):
        title = card.get("title") or f"Card {i}"
        summary = (card.get("summary") or "").strip()[:120]
        card_lines.append(f"- [ ] {i}. **{title}** — {summary}")

    cards_block = "\n".join(card_lines) if card_lines else "- (카드 없음)"

    content = f"""---
title: {date_str}-오늘의_플러스-triage
triage: pending
agent: bucky
manifest_sha256: {manifest_sha256}
created_at: {now_iso}
card_count: {len(cards)}
actions: [approve, implement, queue, archive]
status: inbox
tags:
  - daily-plus
  - triage
  - "#status/inbox"
---

## 오늘의 플러스 트리아지 — {date_str}

> Bucky 시스템 업그레이드·개선 적용 가능 항목 분류

### 카드 목록 (approve / implement / queue / archive 분류 필요)

{cards_block}

### 트리아지 기준

- **approve**: 즉시 시스템 반영 가능 (스크립트·설정·패턴)
- **implement**: 코드 작업 필요 (Claude Code/Codex 위임)
- **queue**: 미래 착수 (인프라·의존성 필요)
- **archive**: 현 시스템 무관 (별도 서비스/제품)
"""
    triage_path.write_text(content, encoding="utf-8")
    print(f"[TRIAGE] Saved: {triage_path}")


def _write_note_and_evolve(capture: dict[str, Any], output_path: Path, today: date, *, force: bool, evolve: bool) -> None:
    validate_capture_for_note(capture)
    note_content = build_note(capture, today)

    # emit_on_change: 내용이 바뀐 경우에만 쓰기 (Card 6/7 패턴)
    new_sha = _sha256_text(note_content)
    if output_path.exists() and not force:
        existing_sha = _sha256_text(output_path.read_text(encoding="utf-8"))
        if existing_sha == new_sha:
            print(f"[NO_CHANGE] Content unchanged, skip write: {output_path}")
            return

    output_path.write_text(note_content, encoding="utf-8")

    cards = capture.get("cards") or []
    overview = (capture.get("overviewText") or "").strip()
    print(f"[OK] Saved: {output_path}")
    print(f"[INFO] Title: {capture.get('title')}")
    print(f"[INFO] URL: {capture.get('href') or capture.get('source_url')}")
    print(f"[INFO] Collection status: {capture.get('collectionStatus') or 'collected'}")
    print(f"[INFO] Overview characters: {len(overview)}")
    print(f"[INFO] Cards: {len(cards)}")
    print(f"[INFO] Detail characters: {sum(len(card.get('detailText') or '') for card in cards)}")
    print(f"[PREVIEW]\n{overview[:300]}...")

    # 트리아지 노트 자동 생성 (Card 6 이부장 펄스 매니저 패턴)
    _write_triage_note(capture, today, new_sha)

    if evolve:
        _run_pulse_evolution(output_path, force=force)


def _looks_like_error_page(text: str) -> bool:
    compact = " ".join(text.lower().split())
    error_markers = (
        "404 not found",
        "page not found",
        "this page could not be found",
    )
    return any(marker in compact for marker in error_markers)


def validate_capture_for_note(capture: dict[str, Any]) -> None:
    pulse_text = (capture.get("overviewText") or "").strip()
    cards = capture.get("cards") or []
    diagnostic_text = "\n".join(
        str(capture.get(key) or "")
        for key in ("href", "title", "overviewText", "bodyStart")
    )

    if capture.get("collectionStatus") != "fallback" and _looks_like_error_page(diagnostic_text):
        raise RuntimeError("ChatGPT Pulse returned a 404 or not-found page.")
    if not pulse_text:
        body = (capture.get("bodyStart") or "").replace("\n", " ")[:500]
        if "login" in body.lower() or "sign in" in body.lower():
            raise RuntimeError(
                "ChatGPT login is required in the dedicated Chrome profile. "
                "Run with --login and complete sign-in."
            )
        raise RuntimeError(f"No Pulse content found. Page snippet: {body}")
    if not cards:
        raise RuntimeError("No Pulse cards found; refusing to save an empty Daily Plus note.")


def _existing_note_is_valid(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if _looks_like_error_page(text):
        return False
    match = re.search(r"^card_count:\s*(\d+)\s*$", text, flags=re.M)
    if not match:
        return "## Pulse Cards" in text
    return int(match.group(1)) > 0


def _request_json(url: str, *, method: str = "GET", timeout: int = 8) -> Any:
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _cdp_base() -> str:
    return f"http://127.0.0.1:{DEBUG_PORT}"


def _cdp_is_ready() -> bool:
    try:
        _request_json(f"{_cdp_base()}/json/version", timeout=2)
        return True
    except Exception:
        return False


def _wait_for_cdp(timeout_s: int = 20) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _cdp_is_ready():
            return
        time.sleep(0.5)
    raise RuntimeError(f"Chrome DevTools port did not open on {DEBUG_PORT}")


def _launch_chrome(open_url: str = CHATGPT_URL) -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    if not _cdp_is_ready():
        chrome = CHROME_EXE if Path(CHROME_EXE).exists() else "chrome"
        subprocess.Popen(
            [
                chrome,
                f"--remote-debugging-port={DEBUG_PORT}",
                "--remote-allow-origins=*",
                f"--user-data-dir={PROFILE_DIR}",
                open_url,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _wait_for_cdp()
        return

    encoded = urllib.parse.quote(open_url, safe="")
    try:
        _request_json(f"{_cdp_base()}/json/new?{encoded}", method="PUT")
    except Exception:
        # Existing ChatGPT tabs remain usable even when Chrome rejects new-tab.
        pass


def _page_targets() -> list[dict[str, Any]]:
    targets = _request_json(f"{_cdp_base()}/json/list")
    return [
        target
        for target in targets
        if target.get("type") == "page" and "chatgpt.com" in target.get("url", "")
    ]


def _pick_chatgpt_target() -> dict[str, Any]:
    targets = _page_targets()
    if not targets:
        raise RuntimeError("No ChatGPT tab found in the collector Chrome profile")

    target_id = CHATGPT_URL.rstrip("/").split("/")[-1]
    for target in targets:
        if target_id and target_id in target.get("url", ""):
            return target
    return targets[0]


def _cdp_sender(ws: Any) -> Callable[[str, dict[str, Any] | None, int], dict[str, Any]]:
    counter = {"id": 1}

    def send(
        method: str,
        params: dict[str, Any] | None = None,
        timeout_s: int = 20,
    ) -> dict[str, Any]:
        message_id = counter["id"]
        counter["id"] += 1
        ws.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            response = json.loads(ws.recv())
            if response.get("id") == message_id:
                return response
        raise TimeoutError(method)

    return send


def _runtime_value(response: dict[str, Any]) -> Any:
    return response.get("result", {}).get("result", {}).get("value")


def _evaluate(
    send: Callable[[str, dict[str, Any] | None, int], dict[str, Any]],
    expression: str,
    timeout_s: int = 20,
) -> Any:
    response = send(
        "Runtime.evaluate",
        {"expression": expression, "returnByValue": True, "awaitPromise": True},
        timeout_s,
    )
    return _runtime_value(response)


def _click(
    send: Callable[[str, dict[str, Any] | None, int], dict[str, Any]],
    x: int,
    y: int,
) -> None:
    for event_type in ("mouseMoved", "mousePressed", "mouseReleased"):
        params: dict[str, Any] = {"type": event_type, "x": x, "y": y, "button": "left"}
        if event_type != "mouseMoved":
            params["clickCount"] = 1
        send("Input.dispatchMouseEvent", params)


def _press_escape(send: Callable[[str, dict[str, Any] | None, int], dict[str, Any]]) -> None:
    for event_type in ("keyDown", "keyUp"):
        send(
            "Input.dispatchKeyEvent",
            {
                "type": event_type,
                "key": "Escape",
                "code": "Escape",
                "windowsVirtualKeyCode": 27,
                "nativeVirtualKeyCode": 27,
            },
        )


def _wait_for_pulse_overview(
    send: Callable[[str, dict[str, Any] | None, int], dict[str, Any]],
    timeout_s: int,
) -> dict[str, Any]:
    expression = """
(() => {
  const mainCandidates = [...document.querySelectorAll('main, [role="main"]')]
    .map((el) => (el.innerText || '').trim())
    .filter(Boolean)
    .sort((a, b) => b.length - a.length);
  const overviewText = mainCandidates.find((text) => text.includes('Pulse')) || mainCandidates[0] || '';
  return {
    href: location.href,
    title: document.title,
    overviewText,
    cardCount: document.querySelectorAll('.pulse-card-body').length,
    bodyStart: (document.body?.innerText || '').slice(0, 1200),
  };
})()
"""
    deadline = time.time() + timeout_s
    last_value: dict[str, Any] = {}
    while time.time() < deadline:
        value = _evaluate(send, expression)
        if isinstance(value, dict):
            last_value = value
            overview_text = (value.get("overviewText") or "").strip()
            if len(overview_text) > 100 and "Pulse" in overview_text:
                return value
        time.sleep(2)
    return last_value


def _card_snapshot(
    send: Callable[[str, dict[str, Any] | None, int], dict[str, Any]]
) -> list[dict[str, Any]]:
    expression = """
(() => [...document.querySelectorAll('.pulse-card-body')].map((el, index) => {
  const card = el.closest('.border-token-border-default') || el;
  const divTexts = [...el.querySelectorAll('div')]
    .map((node) => (node.innerText || '').trim())
    .filter(Boolean);
  const rect = card.getBoundingClientRect();
  return {
    index,
    title: (el.querySelector('h3')?.innerText || '').trim(),
    summary: divTexts[divTexts.length - 1] || '',
    text: (el.innerText || '').trim(),
    rect: {
      x: Math.round(rect.x),
      y: Math.round(rect.y),
      w: Math.round(rect.width),
      h: Math.round(rect.height),
    },
  };
}))()
"""
    value = _evaluate(send, expression)
    return value if isinstance(value, list) else []


def _prepare_card_click(
    send: Callable[[str, dict[str, Any] | None, int], dict[str, Any]],
    index: int,
) -> dict[str, Any] | None:
    expression = f"""
(() => {{
  const body = document.querySelectorAll('.pulse-card-body')[{index}];
  if (!body) return null;
  const card = body.closest('.border-token-border-default') || body;
  card.scrollIntoView({{block: 'center', inline: 'center'}});
  const divTexts = [...body.querySelectorAll('div')]
    .map((node) => (node.innerText || '').trim())
    .filter(Boolean);
  const rect = card.getBoundingClientRect();
  return {{
    index: {index},
    title: (body.querySelector('h3')?.innerText || '').trim(),
    summary: divTexts[divTexts.length - 1] || '',
    x: Math.round(rect.x + rect.width / 2),
    y: Math.round(rect.y + rect.height / 2),
  }};
}})()
"""
    value = _evaluate(send, expression)
    return value if isinstance(value, dict) else None


def _read_dialog_text(
    send: Callable[[str, dict[str, Any] | None, int], dict[str, Any]],
    timeout_s: int = 12,
) -> str:
    expression = """
(() => {
  const texts = [...document.querySelectorAll('[role="dialog"], dialog')]
    .map((node) => (node.innerText || '').trim())
    .filter(Boolean)
    .sort((a, b) => b.length - a.length);
  return texts[0] || '';
})()
"""
    deadline = time.time() + timeout_s
    best_text = ""
    while time.time() < deadline:
        value = _evaluate(send, expression)
        if isinstance(value, str) and len(value) > len(best_text):
            best_text = value
        if len(best_text) > 200:
            return best_text
        time.sleep(0.6)
    return best_text


def _extract_pulse_cards(
    send: Callable[[str, dict[str, Any] | None, int], dict[str, Any]]
) -> list[dict[str, Any]]:
    cards = _card_snapshot(send)
    extracted: list[dict[str, Any]] = []
    for card in cards:
        index = int(card.get("index", len(extracted)))
        click_info = _prepare_card_click(send, index)
        if not click_info:
            extracted.append({**card, "detailText": ""})
            continue

        time.sleep(0.4)
        _click(send, int(click_info["x"]), int(click_info["y"]))
        detail_text = _read_dialog_text(send)
        _press_escape(send)
        time.sleep(0.3)

        extracted.append(
            {
                **card,
                "title": click_info.get("title") or card.get("title") or f"Card {index + 1}",
                "summary": click_info.get("summary") or card.get("summary") or "",
                "detailText": detail_text,
            }
        )
    return extracted


def _read_chatgpt_content(timeout_s: int = 60) -> dict[str, Any]:
    if websocket is None:
        raise RuntimeError("Missing dependency: websocket-client")

    target = _pick_chatgpt_target()
    ws = websocket.create_connection(
        target["webSocketDebuggerUrl"],
        timeout=10,
        origin=f"http://127.0.0.1:{DEBUG_PORT}",
    )
    try:
        send = _cdp_sender(ws)
        send("Page.enable")
        send("Runtime.enable")
        _evaluate(send, f"location.href = {json.dumps(CHATGPT_URL)}")
        capture = _wait_for_pulse_overview(send, timeout_s=timeout_s)
        capture["cards"] = _extract_pulse_cards(send)
        return capture
    finally:
        ws.close()


def _run_pulse_evolution(output_path: Path, *, force: bool = False) -> None:
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import pulse_evolution_agent

    result = pulse_evolution_agent.evolve_note_file(output_path, force=force)
    print(
        "[EVOLVE] "
        f"{result.get('status')} cards={result.get('cards')} "
        f"candidates={result.get('candidates')}"
    )
    print(f"[EVOLVE] Report: {result.get('report_path')}")
    print(f"[EVOLVE] Task: {result.get('task_path')}")


def login_mode() -> None:
    _launch_chrome("https://chatgpt.com/")
    print("[LOGIN] Opened dedicated Chrome profile for ChatGPT.")
    print(f"[LOGIN] Profile: {PROFILE_DIR}")
    print("[LOGIN] Sign in there once, then run --collect.")


def collect_mode(force: bool = False, evolve: bool = True, allow_recovery: bool = False) -> None:
    today = date.today()
    date_str = today.strftime("%Y-%m-%d")
    output_path = OUTPUT_DIR / f"{date_str}.md"

    if output_path.exists() and not force:
        if _existing_note_is_valid(output_path):
            print(f"[SKIP] Today's file already exists: {output_path}")
            if evolve:
                _run_pulse_evolution(output_path, force=False)
            return
        print(f"[WARN] Existing Daily Plus note is invalid; recollecting: {output_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _launch_chrome(CHATGPT_URL)
    try:
        value = _read_chatgpt_content()
        _write_note_and_evolve(value, output_path, today, force=force, evolve=evolve)
    except Exception as exc:
        if not allow_recovery:
            raise
        print(f"[WARN] Official Pulse collection failed: {exc}")
        print("[WARN] Writing OABS Daily Plus recovery capture instead.")
        recovery = build_recovery_capture(str(exc))
        _write_note_and_evolve(recovery, output_path, today, force=True, evolve=evolve)


def main() -> None:
    parser = argparse.ArgumentParser(description="ChatGPT Pulse -> ObsidianVault")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--login", action="store_true", help="Open the dedicated Chrome login profile")
    group.add_argument("--collect", action="store_true", help="Collect today's Pulse note")
    parser.add_argument("--force", action="store_true", help="Overwrite today's file if it exists")
    parser.add_argument("--skip-evolve", action="store_true", help="Skip Pulse upgrade staging")
    parser.add_argument(
        "--allow-recovery",
        action="store_true",
        help="Write an OABS recovery Daily Plus note if official Pulse is unavailable",
    )
    args = parser.parse_args()

    try:
        if args.login:
            login_mode()
        else:
            collect_mode(
                force=args.force,
                evolve=not args.skip_evolve,
                allow_recovery=args.allow_recovery,
            )
    except KeyboardInterrupt:
        print("\n[ABORT] Interrupted by user")
    except Exception as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
