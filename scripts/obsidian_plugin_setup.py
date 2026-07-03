#!/usr/bin/env python3
"""
Obsidian Community Plugin Setup

Writes ObsidianVault/.obsidian/community-plugins.json with 20 plugin IDs.
Optionally pre-creates plugin subdirectories so Obsidian detects them on launch.

Usage:
    python scripts/obsidian_plugin_setup.py
    python scripts/obsidian_plugin_setup.py --vault path/to/MyVault
    python scripts/obsidian_plugin_setup.py --no-dirs    # JSON only, skip dir creation
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

PLUGIN_IDS = [
    "calendar",
    "claudian",
    "dataview",
    "infranodus-graph-view",
    "jh-local-graph-view",
    "obsidian-claude-code-mcp",
    "obsidian-excalidraw-plugin",
    "obsidian-git",
    "obsidian-icon-folder",
    "obsidian-kanban",
    "obsidian-local-rest-api",
    "obsidian-shellcommands",
    "obsidian-style-settings",
    "obsidian-tasks-plugin",
    "omnisearch",
    "quickadd",
    "remotely-save",
    "smart-connections",
    "table-editor-obsidian",
    "templater-obsidian",
]


def setup_plugins(vault_path: Path, create_dirs: bool = True) -> None:
    obsidian_dir = vault_path / ".obsidian"
    if not obsidian_dir.exists():
        print(f"⚠️  .obsidian 디렉토리가 없습니다: {obsidian_dir}")
        print("    Obsidian에서 Vault를 한 번 열어 초기화하거나, --vault 경로를 확인하세요.")
        sys.exit(1)

    json_path = obsidian_dir / "community-plugins.json"

    # Preserve manually enabled plugins if file already exists
    existing: list = []
    if json_path.exists():
        try:
            existing = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = []

    merged = list(dict.fromkeys(existing + PLUGIN_IDS))  # dedup, preserve order
    json_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✅ community-plugins.json 작성: {json_path}")
    print(f"   총 {len(merged)}개 플러그인 ID ({len(PLUGIN_IDS)}개 신규 추가)")

    if create_dirs:
        plugins_dir = obsidian_dir / "plugins"
        plugins_dir.mkdir(exist_ok=True)
        created = 0
        for pid in PLUGIN_IDS:
            d = plugins_dir / pid
            if not d.exists():
                d.mkdir()
                created += 1
        if created:
            print(f"📁 플러그인 디렉토리 {created}개 사전 생성 완료: {plugins_dir}")
        else:
            print(f"📁 플러그인 디렉토리 이미 존재 — 스킵")

    print()
    print("📌 다음 단계:")
    print("   1. Obsidian을 완전히 종료한 후 다시 시작하세요.")
    print("   2. 설정(⚙) → 커뮤니티 플러그인 → '설치된 플러그인' 탭 확인")
    print("   3. 각 플러그인 옆 '켜기' 버튼을 눌러 활성화하세요.")
    print("   (자동 다운로드는 Obsidian이 인터넷 연결 시 처리합니다)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ObsidianVault community-plugins.json 생성 스크립트"
    )
    parser.add_argument(
        "--vault",
        type=Path,
        default=ROOT / "ObsidianVault",
        help="Obsidian Vault 경로 (기본: ./ObsidianVault)",
    )
    parser.add_argument(
        "--no-dirs",
        action="store_true",
        help="플러그인 디렉토리 사전 생성 스킵",
    )
    args = parser.parse_args()

    vault = args.vault.resolve()
    if not vault.exists():
        print(f"⚠️  Vault 경로가 존재하지 않습니다: {vault}")
        sys.exit(1)

    print(f"🔌 Obsidian 플러그인 설정 시작")
    print(f"   Vault: {vault}")
    print(f"   플러그인 수: {len(PLUGIN_IDS)}")
    print()
    setup_plugins(vault, create_dirs=not args.no_dirs)


if __name__ == "__main__":
    main()
