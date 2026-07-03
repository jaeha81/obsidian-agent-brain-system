#!/usr/bin/env python3
"""
VS Code 컨텍스트 캡처 스크립트
Claude Code가 현재 VS Code 작업 상태를 인지할 수 있도록 구조화된 컨텍스트를 반환한다.

사용법:
  python scripts/vscode_context.py              # 현재 상태 출력
  python scripts/vscode_context.py --open FILE  # VS Code에서 파일 열기
  python scripts/vscode_context.py --json       # JSON 형식 출력
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from urllib.parse import unquote
from datetime import datetime


APPDATA = os.environ.get("APPDATA", "")
STORAGE_PATH = Path(APPDATA) / "Code" / "User" / "globalStorage" / "storage.json"
WORKSPACE_STORAGE = Path(APPDATA) / "Code" / "User" / "workspaceStorage"
HISTORY_DIR = Path(APPDATA) / "Code" / "User" / "History"


def decode_vscode_uri(uri: str) -> str:
    """file:///g%3A/... 형태의 VS Code URI를 Windows 경로로 변환"""
    if uri.startswith("file:///"):
        path = uri[8:]
        path = unquote(path)
        # /g:/path → G:/path
        if len(path) >= 2 and path[1] == ":":
            path = path[0].upper() + path[1:]
        elif len(path) >= 3 and path[0] == "/" and path[2] == ":":
            path = path[1].upper() + path[2:]
        return path.replace("/", "\\")
    return uri


def get_active_window() -> dict:
    """현재 VS Code 활성 창 정보 반환"""
    if not STORAGE_PATH.exists():
        return {}
    with open(STORAGE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    windows_state = data.get("windowsState", {})
    last = windows_state.get("lastActiveWindow", {})
    result = {}
    if "folder" in last:
        result["workspace"] = decode_vscode_uri(last["folder"])
    elif "workspace" in last:
        ws_uri = last["workspace"].get("configPath", "")
        result["workspace"] = decode_vscode_uri(ws_uri)
    result["raw"] = last
    return result


def get_recent_history_files(limit: int = 10) -> list:
    """VS Code History에서 최근 편집된 파일 목록 반환"""
    if not HISTORY_DIR.exists():
        return []
    entries = []
    for entry_dir in HISTORY_DIR.iterdir():
        if not entry_dir.is_dir():
            continue
        entries_file = entry_dir / "entries.json"
        if not entries_file.exists():
            continue
        try:
            with open(entries_file, encoding="utf-8") as f:
                meta = json.load(f)
            resource = decode_vscode_uri(meta.get("resource", ""))
            entries_list = meta.get("entries", [])
            if entries_list:
                latest = entries_list[-1]
                ts = latest.get("timestamp", 0)
                entries.append({"file": resource, "timestamp": ts, "dir": str(entry_dir)})
        except Exception:
            continue
    entries.sort(key=lambda x: x["timestamp"], reverse=True)
    return entries[:limit]


def get_workspace_recent_files(workspace_path: str, limit: int = 20) -> list:
    """주어진 워크스페이스 경로 기준 최근 수정 파일 목록"""
    if not workspace_path or not os.path.exists(workspace_path):
        return []
    recent = []
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "dist", "build", ".next"}
    try:
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    mtime = os.path.getmtime(fpath)
                    recent.append({"file": fpath, "mtime": mtime})
                except OSError:
                    continue
        recent.sort(key=lambda x: x["mtime"], reverse=True)
        return [
            {"file": r["file"], "modified": datetime.fromtimestamp(r["mtime"]).strftime("%Y-%m-%d %H:%M:%S")}
            for r in recent[:limit]
        ]
    except Exception:
        return []


def open_in_vscode(file_path: str, line: int = None):
    """VS Code에서 파일 열기 (선택적으로 특정 라인으로 이동)"""
    if line:
        target = f"{file_path}:{line}"
        subprocess.run(["code", "-g", target], check=False)
    else:
        subprocess.run(["code", file_path], check=False)
    print(f"VS Code에서 열림: {file_path}" + (f":{line}" if line else ""))


def build_context() -> dict:
    """전체 VS Code 컨텍스트 딕셔너리 구성"""
    active = get_active_window()
    workspace = active.get("workspace", "")
    history = get_recent_history_files(10)
    workspace_files = get_workspace_recent_files(workspace, 15) if workspace else []

    return {
        "captured_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "active_workspace": workspace,
        "recent_edited_files": [h["file"] for h in history],
        "workspace_recent_files": [f["file"] for f in workspace_files],
    }


def print_context(ctx: dict):
    """사람이 읽기 쉬운 형태로 출력"""
    print("=" * 60)
    print(f"VS Code 컨텍스트 캡처 — {ctx['captured_at']}")
    print("=" * 60)
    print(f"\n📁 활성 워크스페이스:\n  {ctx['active_workspace'] or '(없음)'}")

    print(f"\n🕐 최근 편집 파일 (History 기준):")
    for f in ctx["recent_edited_files"]:
        print(f"  {f}")

    print(f"\n📄 워크스페이스 내 최근 수정 파일:")
    for f in ctx["workspace_recent_files"]:
        print(f"  {f}")
    print()


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--open" in args:
        idx = args.index("--open")
        target = args[idx + 1] if idx + 1 < len(args) else None
        if target:
            parts = target.rsplit(":", 1)
            if len(parts) == 2 and parts[1].isdigit():
                open_in_vscode(parts[0], int(parts[1]))
            else:
                open_in_vscode(target)
        else:
            print("사용법: --open <파일경로[:라인번호]>")
        sys.exit(0)

    ctx = build_context()

    if "--json" in args:
        print(json.dumps(ctx, ensure_ascii=False, indent=2))
    else:
        print_context(ctx)
