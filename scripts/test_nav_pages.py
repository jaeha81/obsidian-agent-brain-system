"""nav 페이지 auth + nav.js 전수 점검"""
from pathlib import Path

DOCS = Path(r"D:\ai프로젝트\obsidian-agent-brain-system\docs")

PAGES = [
    ("repo/index.html",          "repo"),
    ("wishket/index.html",       "wishket"),
    ("daily-plus/index.html",    "daily-plus"),
    ("task-board/index.html",    "task-board"),
    ("claude-code/index.html",   "claude-code"),
    ("codex/index.html",         "codex"),
    ("chris/index.html",         "chris"),
    ("charlie/index.html",       "charlie"),
    ("my-dev/index.html",        "my-dev"),
    ("shorts/index.html",        "shorts"),
    ("chsh-mining/index.html",   "chsh-mining"),
    ("threads/index.html",       "threads"),
    ("kmong/index.html",         "kmong"),
    ("workflow/index.html",      "workflow"),
    ("ai-usage.html",            "ai-usage"),
    ("wiki-gate.html",           "wiki-gate"),
    ("bucky-agent-os.html",      "bucky-os"),
]

print(f"{'label':<16} {'auth':<8} {'nav.js':<8} result")
print("-" * 44)

fails = []
for rel, label in PAGES:
    path = DOCS / rel.replace("/", "\\")
    try:
        c = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"{label:<16} READ-ERR")
        fails.append(label)
        continue

    auth = "OK" if ("bucky_auth" in c or "auth.js" in c) else "MISS"
    nav  = "OK" if "nav.js" in c else "MISS"
    ok   = auth == "OK" and nav == "OK"
    if not ok:
        fails.append(label)
    result = "PASS" if ok else "FAIL"
    print(f"{label:<16} {auth:<8} {nav:<8} {result}")

print("-" * 44)
print("ALL PASS" if not fails else f"FAIL: {fails}")
