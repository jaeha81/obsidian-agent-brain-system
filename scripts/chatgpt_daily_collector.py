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
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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

    joined = "\n\n".join(sections)
    return f"""---
date: {date_str}
source: ChatGPT Pulse
source_url: {CHATGPT_URL}
collected_at: {collected_at}
card_count: {len(cards)}
tags: [pulse, daily-plus, knowledge, auto-collected]
---

# ChatGPT Pulse - {date_str}

{joined}

---
*Auto-collected by `chatgpt_daily_collector.py`.*
"""


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


def collect_mode(force: bool = False, evolve: bool = True) -> None:
    today = date.today()
    date_str = today.strftime("%Y-%m-%d")
    output_path = OUTPUT_DIR / f"{date_str}.md"

    if output_path.exists() and not force:
        print(f"[SKIP] Today's file already exists: {output_path}")
        if evolve:
            _run_pulse_evolution(output_path, force=False)
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _launch_chrome(CHATGPT_URL)
    value = _read_chatgpt_content()

    pulse_text = (value.get("overviewText") or "").strip()
    cards = value.get("cards") or []

    if not pulse_text:
        body = (value.get("bodyStart") or "").replace("\n", " ")[:500]
        if "login" in body.lower() or "sign in" in body.lower():
            raise RuntimeError(
                "ChatGPT login is required in the dedicated Chrome profile. "
                "Run with --login and complete sign-in."
            )
        raise RuntimeError(f"No Pulse content found. Page snippet: {body}")

    note_content = build_note(value, today)
    output_path.write_text(note_content, encoding="utf-8")

    print(f"[OK] Saved: {output_path}")
    print(f"[INFO] Title: {value.get('title')}")
    print(f"[INFO] URL: {value.get('href')}")
    print(f"[INFO] Overview characters: {len(pulse_text)}")
    print(f"[INFO] Cards: {len(cards)}")
    print(f"[INFO] Detail characters: {sum(len(card.get('detailText') or '') for card in cards)}")
    print(f"[PREVIEW]\n{pulse_text[:300]}...")
    if evolve:
        _run_pulse_evolution(output_path, force=force)


def main() -> None:
    parser = argparse.ArgumentParser(description="ChatGPT Pulse -> ObsidianVault")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--login", action="store_true", help="Open the dedicated Chrome login profile")
    group.add_argument("--collect", action="store_true", help="Collect today's Pulse note")
    parser.add_argument("--force", action="store_true", help="Overwrite today's file if it exists")
    parser.add_argument("--skip-evolve", action="store_true", help="Skip Pulse upgrade staging")
    args = parser.parse_args()

    try:
        if args.login:
            login_mode()
        else:
            collect_mode(force=args.force, evolve=not args.skip_evolve)
    except KeyboardInterrupt:
        print("\n[ABORT] Interrupted by user")
    except Exception as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
