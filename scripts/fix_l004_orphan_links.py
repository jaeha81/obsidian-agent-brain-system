#!/usr/bin/env python3
"""
fix_l004_orphan_links.py
L004 오류(wikilink 없는 고립 노트) 87건을 graph_cluster 기반으로 허브 링크 자동 추가.

전략:
  - graph_cluster → 관련 허브 노트 매핑
  - 노트 끝에 "## 관련 노트" 섹션 추가 (이미 있으면 스킵)
  - 기존 내용 변경 없음 (append-only)
"""
import os
import re
import glob
import sys
import yaml

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT = os.path.join(_ROOT, "ObsidianVault")
KNOWLEDGE_DIR = os.path.join(VAULT, "03_Knowledge")

# graph_cluster → 허브 wikilink 매핑
CLUSTER_TO_HUBS = {
    "daily-practice":   ["hubs/JH System"],
    "youtube-learning": ["hubs/JH System"],
    "claude-ai":        ["hubs/Claude Code"],
    "session-log":      ["hubs/JH System"],
    "discord-ops":      ["hubs/AgentBus"],
    "github-catalog":   ["hubs/JH System"],
    "knowledge-graph":  ["hubs/Graphify"],
    "jh-system":        ["hubs/JH System"],
    "bucky-agent":      ["hubs/AgentBus"],
    "client-proposal":  ["hubs/JH System"],
    "space-planner":    ["hubs/JH System"],
    "oabs-system":      ["hubs/Obsidian"],
    "content-shorts":   ["hubs/JH System"],
    "wiki-knowledge":   ["hubs/Obsidian"],
    "tiktok-content":   ["hubs/JH System"],
    "chatgpt-logs":     ["hubs/JH System"],
    "obsidian-system":  ["hubs/Obsidian"],
    "ai-ops":           ["hubs/AgentBus", "hubs/Claude Code"],
    "bni-network":      ["hubs/JH System"],
    "google-tools":     ["hubs/JH System"],
    "skill-library":    ["hubs/Claude Code"],
    "codex-agent":      ["hubs/Codex"],
    "agent-patterns":   ["hubs/AgentBus"],
    "llm-research":     ["hubs/Graphify"],
    "goalmode":         ["hubs/JH System"],
    "brain-system":     ["hubs/Obsidian"],
    "typeless-voice":   ["hubs/AgentBus"],
    "web-capture":      ["hubs/JH System"],
    "marketing":        ["hubs/JH System"],
    "revenue-ops":      ["hubs/JH System"],
    "dashboard":        ["hubs/JH System"],
    "planswift":        ["hubs/JH System"],
    "misc":             ["hubs/JH System"],
}

DEFAULT_HUB = "hubs/JH System"


def get_cluster(fm: dict) -> str:
    return str(fm.get("graph_cluster", "misc")).strip()


def has_wikilink(content: str) -> bool:
    return bool(re.search(r"\[\[.+?\]\]", content))


def has_related_section(content: str) -> bool:
    return "## 관련 노트" in content


def parse_frontmatter(content: str):
    if not content.startswith("---"):
        return None, content
    end = content.find("\n---", 3)
    if end == -1:
        return None, content
    fm_str = content[3:end].strip()
    body = content[end + 4:]
    try:
        fm = yaml.safe_load(fm_str) or {}
    except Exception:
        fm = {}
    return fm, body


def append_links(path: str, hubs: list[str], dry_run: bool = False) -> bool:
    with open(path, encoding="utf-8", errors="replace") as f:
        content = f.read()

    if has_wikilink(content):
        return False  # 이미 wikilink 있음

    if has_related_section(content):
        return False  # 이미 관련 노트 섹션 있음

    link_lines = "\n".join(f"- [[{h}]]" for h in hubs)
    section = f"\n\n## 관련 노트\n{link_lines}\n"
    new_content = content.rstrip() + section

    if dry_run:
        return True

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True


def main():
    dry_run = "--dry-run" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    files = glob.glob(KNOWLEDGE_DIR + "/**/*.md", recursive=True)
    patched = 0
    skipped = 0

    for path in sorted(files):
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read()

        if has_wikilink(content):
            skipped += 1
            continue

        fm, _ = parse_frontmatter(content)
        if fm is None:
            skipped += 1
            continue

        cluster = get_cluster(fm)
        hubs = CLUSTER_TO_HUBS.get(cluster, [DEFAULT_HUB])

        changed = append_links(path, hubs, dry_run=dry_run)
        if changed:
            if verbose or dry_run:
                rel = os.path.relpath(path, KNOWLEDGE_DIR)
                print(f"  {'[DRY]' if dry_run else '[FIX]'} {rel} → {hubs}")
            patched += 1
        else:
            skipped += 1

    mode = "DRY RUN" if dry_run else "적용 완료"
    print(f"\n[fix_l004] {mode}: {patched}건 패치, {skipped}건 스킵")


if __name__ == "__main__":
    main()
