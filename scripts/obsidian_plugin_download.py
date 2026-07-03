#!/usr/bin/env python3
"""
Obsidian 커뮤니티 플러그인 자동 다운로드

공식 레지스트리(obsidianmd/obsidian-releases)에서 플러그인 목록을 가져와
각 플러그인의 최신 릴리즈 파일(main.js, manifest.json, styles.css)을
ObsidianVault/.obsidian/plugins/<id>/ 에 다운로드합니다.

Usage:
    python -X utf8 scripts/obsidian_plugin_download.py
"""

import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent.parent
VAULT = ROOT / "ObsidianVault"
PLUGINS_DIR = VAULT / ".obsidian" / "plugins"
APP_JSON = VAULT / ".obsidian" / "app.json"

REGISTRY_URL = (
    "https://raw.githubusercontent.com/obsidianmd/obsidian-releases"
    "/HEAD/community-plugins.json"
)

PLUGIN_IDS = [
    "calendar", "claudian", "dataview",
    "infranodus-graph-view", "jh-local-graph-view",
    "obsidian-claude-code-mcp", "obsidian-excalidraw-plugin",
    "obsidian-git", "obsidian-icon-folder", "obsidian-kanban",
    "obsidian-local-rest-api", "obsidian-shellcommands",
    "obsidian-style-settings", "obsidian-tasks-plugin",
    "omnisearch", "quickadd", "remotely-save",
    "smart-connections", "table-editor-obsidian",
    "templater-obsidian",
]

HEADERS = {"User-Agent": "obsidian-plugin-installer/1.0"}


def fetch(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_json(url: str) -> dict | list:
    return json.loads(fetch(url))


def disable_safe_mode() -> None:
    """app.json에 restrictedMode: false 기록 (안전모드 OFF)."""
    try:
        existing = json.loads(APP_JSON.read_text(encoding="utf-8"))
    except Exception:
        existing = {}
    existing["restrictedMode"] = False
    APP_JSON.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    print("✅ app.json: restrictedMode = false (안전모드 OFF)")


def get_latest_release_tag(repo: str) -> str | None:
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        data = fetch_json(url)
        return data.get("tag_name")
    except Exception:
        return None


def download_file(url: str, dest: Path) -> bool:
    try:
        data = fetch(url)
        dest.write_bytes(data)
        return True
    except urllib.error.HTTPError:
        return False
    except Exception:
        return False


def install_plugin(plugin_id: str, repo: str) -> str:
    """단일 플러그인 설치. 반환값: 'ok' | 'skip' | 'fail'"""
    plugin_dir = PLUGINS_DIR / plugin_id
    plugin_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = plugin_dir / "manifest.json"
    main_path = plugin_dir / "main.js"

    # 이미 설치돼 있으면 스킵
    if manifest_path.exists() and main_path.exists():
        return "skip"

    tag = get_latest_release_tag(repo)
    if not tag:
        return "fail"

    base = f"https://github.com/{repo}/releases/download/{tag}"
    ok_main = download_file(f"{base}/main.js", main_path)
    ok_manifest = download_file(f"{base}/manifest.json", manifest_path)
    # styles.css는 선택 — 없어도 무방
    download_file(f"{base}/styles.css", plugin_dir / "styles.css")

    return "ok" if (ok_main and ok_manifest) else "fail"


def main() -> None:
    print("🔌 Obsidian 플러그인 다운로드 시작")
    print()

    # 1. 안전모드 OFF
    disable_safe_mode()
    print()

    # 2. 공식 레지스트리 로드
    print("📥 공식 레지스트리 로딩...", end=" ", flush=True)
    try:
        registry_raw = fetch_json(REGISTRY_URL)
        registry: dict[str, str] = {p["id"]: p["repo"] for p in registry_raw}
        print(f"{len(registry)}개 플러그인 목록 수신")
    except Exception as e:
        print(f"실패: {e}")
        sys.exit(1)

    print()

    # 3. 각 플러그인 다운로드
    results: dict[str, list[str]] = {"ok": [], "skip": [], "fail": [], "not_in_registry": []}

    for pid in PLUGIN_IDS:
        if pid not in registry:
            results["not_in_registry"].append(pid)
            print(f"  ⚠️  {pid:45s} 공식 레지스트리에 없음 (커스텀 플러그인)")
            continue

        repo = registry[pid]
        status = install_plugin(pid, repo)
        results[status].append(pid)

        icon = {"ok": "✅", "skip": "⏭️ ", "fail": "❌"}.get(status, "?")
        label = {"ok": "설치 완료", "skip": "이미 설치됨", "fail": "다운로드 실패"}.get(status, "")
        print(f"  {icon} {pid:45s} {label}")
        time.sleep(0.3)  # GitHub API rate limit 방지

    print()
    print("=" * 60)
    print(f"✅ 설치 완료 : {len(results['ok'])}개")
    print(f"⏭️  이미 설치  : {len(results['skip'])}개")
    print(f"❌ 실패       : {len(results['fail'])}개")
    print(f"⚠️  레지스트리 외: {len(results['not_in_registry'])}개  →  수동 설치 필요")

    if results["not_in_registry"]:
        print()
        print("수동 설치 필요 목록:")
        for pid in results["not_in_registry"]:
            print(f"  - {pid}")

    if results["fail"]:
        print()
        print("다운로드 실패 목록 (재시도 또는 수동 설치):")
        for pid in results["fail"]:
            print(f"  - {pid}")

    print()
    print("📌 다음 단계: Obsidian 재시작 → 커뮤니티 플러그인에서 각 플러그인 '켜기'")


if __name__ == "__main__":
    main()
