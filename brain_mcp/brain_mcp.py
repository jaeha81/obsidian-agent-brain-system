#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gbrain — 브레인 시스템 MCP (표준 라이브러리만 사용, 추가 설치 0)

Claude Code 등 MCP 클라이언트가 stdio(JSON-RPC 2.0, 줄단위)로 연결한다.
기록은 옵시디언 볼트 안 마크다운 파일로 저장돼 옵시디언에서도 그대로 보인다.

도구:
  - recall(entity)                : 주제/프로젝트로 과거 타임라인을 불러온다
  - add_timeline_entry(slug, summary) : 배운 것/결정을 날짜와 함께 기록한다 (진화 루프)
  - search(query)                 : 모든 기록에서 검색한다

stdout에는 JSON-RPC만 출력한다. 로그는 전부 stderr로 보낸다.
"""
import sys
import os
import io
import json
import re
import datetime

# ── 저장 위치 (환경변수로 덮어쓸 수 있음) ─────────────────────────────
DEFAULT_DIR = r"D:\ai프로젝트\obsidian-agent-brain-system\ObsidianVault\03_Projects\_agent_timeline"
DATA_DIR = os.environ.get("BRAIN_MCP_DIR", DEFAULT_DIR)
SERVER_NAME = "gbrain"
SERVER_VERSION = "1.0.0"
PROTOCOL_FALLBACK = "2024-11-05"

# ── stdio를 UTF-8 + \n 줄바꿈으로 고정 (Windows 한글 안전) ───────────
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", newline="\n")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")


def log(msg):
    print(f"[gbrain] {msg}", file=sys.stderr, flush=True)


def ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def safe_slug(slug):
    """파일명으로 안전한 슬러그만 허용 (경로 탈출 차단). 한글 허용."""
    slug = (slug or "").strip()
    slug = slug.replace("/", "-").replace("\\", "-")
    slug = re.sub(r"[^0-9A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ._\- ]", "", slug)
    slug = slug.strip(" .")
    return slug or "untitled"


def slug_path(slug):
    return os.path.join(DATA_DIR, safe_slug(slug) + ".md")


def now_stamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


# ── 도구 구현 ────────────────────────────────────────────────────────
def tool_add_timeline_entry(args):
    slug = args.get("slug") or args.get("project") or ""
    summary = (args.get("summary") or "").strip()
    if not slug or not summary:
        return "오류: slug(프로젝트)과 summary(요약)가 모두 필요합니다.", True
    ensure_dir()
    path = slug_path(slug)
    new_file = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        if new_file:
            f.write(f"# {safe_slug(slug)} — 타임라인\n\n")
            f.write("> gbrain MCP가 자동 기록. 최신 항목이 아래에 추가됩니다.\n\n")
        f.write(f"- [{now_stamp()}] {summary}\n")
    return f"기록 완료 → {path}\n- [{now_stamp()}] {summary}", False


def tool_recall(args):
    entity = (args.get("entity") or args.get("slug") or "").strip()
    if not entity:
        return "오류: entity(주제/프로젝트)가 필요합니다.", True
    ensure_dir()
    # 1) 정확히 그 슬러그 파일이 있으면 통째로 (너무 길면 뒤쪽 우선)
    exact = slug_path(entity)
    if os.path.exists(exact):
        text = open(exact, encoding="utf-8").read()
        if len(text) > 6000:
            text = "…(앞부분 생략)…\n" + text[-6000:]
        return f"[{os.path.basename(exact)}]\n{text}", False
    # 2) 아니면 파일명/내용에 그 단어가 있는 파일들에서 관련 줄 모으기
    low = entity.lower()
    hits = []
    for name in sorted(os.listdir(DATA_DIR)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(DATA_DIR, name)
        try:
            text = open(path, encoding="utf-8").read()
        except Exception:
            continue
        if low in name.lower() or low in text.lower():
            lines = [ln for ln in text.splitlines() if low in ln.lower()]
            snippet = "\n".join(lines[-15:]) if lines else text[-1500:]
            hits.append(f"[{name}]\n{snippet}")
    if not hits:
        return f"'{entity}'에 대한 기록이 아직 없습니다.", False
    return "\n\n".join(hits[:10]), False


def tool_search(args):
    query = (args.get("query") or "").strip()
    if not query:
        return "오류: query(검색어)가 필요합니다.", True
    ensure_dir()
    low = query.lower()
    out = []
    for name in sorted(os.listdir(DATA_DIR)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(DATA_DIR, name)
        try:
            lines = open(path, encoding="utf-8").read().splitlines()
        except Exception:
            continue
        for ln in lines:
            if low in ln.lower():
                out.append(f"{name}: {ln.strip()}")
    if not out:
        return f"'{query}' 검색 결과 없음.", False
    return "\n".join(out[:50]), False


TOOLS = [
    {
        "name": "recall",
        "description": "주제나 프로젝트 이름으로 과거 결정·타임라인 기록을 불러온다. 개발 착수 전 이전 맥락 복원용.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity": {"type": "string", "description": "주제 또는 프로젝트 슬러그 (예: local-coding-agent-kr)"}
            },
            "required": ["entity"],
        },
    },
    {
        "name": "add_timeline_entry",
        "description": "배운 것·결정·버그 패턴을 날짜와 함께 프로젝트 타임라인에 기록한다 (진화 루프).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string", "description": "프로젝트 슬러그 (파일명이 됨)"},
                "summary": {"type": "string", "description": "핵심 결정/패턴 한두 줄 요약"},
            },
            "required": ["slug", "summary"],
        },
    },
    {
        "name": "search",
        "description": "모든 타임라인 기록에서 검색어가 들어간 줄을 찾는다.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "검색어"}},
            "required": ["query"],
        },
    },
]

DISPATCH = {
    "recall": tool_recall,
    "add_timeline_entry": tool_add_timeline_entry,
    "search": tool_search,
}


# ── JSON-RPC 처리 ────────────────────────────────────────────────────
def send(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def reply(msg_id, result):
    send({"jsonrpc": "2.0", "id": msg_id, "result": result})


def reply_error(msg_id, code, message):
    send({"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}})


def handle(msg):
    method = msg.get("method")
    msg_id = msg.get("id")
    is_notification = "id" not in msg

    if method == "initialize":
        params = msg.get("params") or {}
        proto = params.get("protocolVersion") or PROTOCOL_FALLBACK
        reply(msg_id, {
            "protocolVersion": proto,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })
        return

    if method in ("notifications/initialized", "initialized"):
        return  # 알림 → 응답 없음

    if method == "ping":
        if not is_notification:
            reply(msg_id, {})
        return

    if method == "tools/list":
        reply(msg_id, {"tools": TOOLS})
        return

    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        fn = DISPATCH.get(name)
        if not fn:
            reply_error(msg_id, -32601, f"알 수 없는 도구: {name}")
            return
        try:
            text, is_error = fn(args)
        except Exception as e:
            log(f"도구 실행 오류 {name}: {e}")
            reply(msg_id, {"content": [{"type": "text", "text": f"도구 오류: {e}"}], "isError": True})
            return
        reply(msg_id, {"content": [{"type": "text", "text": text}], "isError": bool(is_error)})
        return

    # 그 외
    if not is_notification:
        reply_error(msg_id, -32601, f"지원하지 않는 메서드: {method}")


def main():
    log(f"start · DATA_DIR={DATA_DIR}")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception as e:
            log(f"JSON 파싱 실패: {e}")
            continue
        try:
            handle(msg)
        except Exception as e:
            log(f"handle 예외: {e}")
    log("stdin EOF · 종료")


if __name__ == "__main__":
    main()
