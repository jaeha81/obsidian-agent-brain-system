"""
fix_l002_graph_cluster.py
L002 오류(graph_cluster 미설정) 240건을 파일명 패턴으로 자동 추론·패치.
"""
import os, re, glob, yaml, sys

VAULT = r"D:\ai프로젝트\obsidian-agent-brain-system\ObsidianVault"
KNOWLEDGE_DIR = os.path.join(VAULT, "03_Knowledge")

# 파일명 prefix → graph_cluster 매핑
PREFIX_TO_CLUSTER = {
    "dp":          "daily-practice",
    "yt":          "youtube-learning",
    "claude":      "claude-ai",
    "session":     "session-log",
    "discord":     "discord-ops",
    "github":      "github-catalog",
    "infranodus":  "knowledge-graph",
    "jh":          "jh-system",
    "bucky":       "bucky-agent",
    "proposal":    "client-proposal",
    "spaceplanner":"space-planner",
    "oabs":        "oabs-system",
    "shorts":      "content-shorts",
    "wiki":        "wiki-knowledge",
    "tiktok":      "tiktok-content",
    "chatgpt":     "chatgpt-logs",
    "youtube":     "youtube-learning",
    "obsidian":    "obsidian-system",
    "ai":          "ai-ops",
    "bni":         "bni-network",
    "google":      "google-tools",
    "skill":       "skill-library",
    "codex":       "codex-agent",
    "parallel":    "agent-patterns",
    "llm":         "llm-research",
    "loop":        "agent-patterns",
    "mrnotion":    "notion-tools",
    "planswift":   "planswift",
    "dashboard":   "dashboard",
    "revenue":     "revenue-ops",
    "cta":         "marketing",
    "outreach":    "marketing",
    "daily":       "daily-log",
    "goalmode":    "goalmode",
    "brain":       "brain-system",
    "typeless":    "typeless-voice",
    "never":       "misc",
    "httpsseou":   "web-capture",
    "httpsweb":    "web-capture",
    "httpsdash":   "web-capture",
}

FALLBACK_CLUSTER = "misc"

def infer_cluster(filename: str) -> str:
    name = os.path.basename(filename)
    # 날짜 패턴 뒤 prefix: YYYY-MM-DD-PREFIX-...
    m = re.match(r"\d{4}-\d{2}-\d{2}-([a-z]+)-", name)
    if m:
        p = m.group(1)
        return PREFIX_TO_CLUSTER.get(p, FALLBACK_CLUSTER)
    # prefix 없는 경우 파일명 첫 단어
    first = re.split(r"[-_.]", name)[0].lower()
    return PREFIX_TO_CLUSTER.get(first, FALLBACK_CLUSTER)

def parse_frontmatter(content: str):
    if not content.startswith("---"):
        return None, content
    end = content.find("\n---", 3)
    if end == -1:
        return None, content
    fm_str = content[3:end].strip()
    body = content[end+4:]
    try:
        fm = yaml.safe_load(fm_str) or {}
    except Exception:
        fm = {}
    return fm, body

def rebuild_content(fm: dict, body: str) -> str:
    fm_str = yaml.dump(fm, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{fm_str}\n---{body}"

def process_file(path: str, dry_run: bool = False) -> bool:
    with open(path, encoding="utf-8", errors="replace") as f:
        content = f.read()

    fm, body = parse_frontmatter(content)
    if fm is None:
        return False  # L001: frontmatter 없음, 건너뜀
    if fm.get("graph_cluster"):
        return False  # 이미 설정됨

    cluster = infer_cluster(path)
    fm["graph_cluster"] = cluster

    if not dry_run:
        new_content = rebuild_content(fm, body)
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
        changed = process_file(path, dry_run=dry_run)
        if changed:
            cluster = infer_cluster(path)
            if verbose or dry_run:
                rel = os.path.relpath(path, VAULT)
                print(f"  {'[DRY]' if dry_run else '[FIX]'} {rel} → {cluster}")
            patched += 1
        else:
            skipped += 1

    mode = "DRY RUN" if dry_run else "적용 완료"
    print(f"\n[fix_l002] {mode}: {patched}건 패치, {skipped}건 스킵")

if __name__ == "__main__":
    main()
