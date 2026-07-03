"""
pattern_scanner.py — Goal-completion pattern detector.

Scans ObsidianVault/goals/ and memory/ files to detect:
  1. Repeated tasks (same keyword ≥3 times across goal records)
  2. Repeated failure steps (keyword appears in multiple FAILED/blocked states)
  3. Similar goals (cosine-like keyword overlap ≥ 60%)

Usage:
  python -X utf8 scripts/pattern_scanner.py
  python -X utf8 scripts/pattern_scanner.py --goals-dir ObsidianVault/goals
  python -X utf8 scripts/pattern_scanner.py --verbose
"""

import re
import sys
import argparse
from pathlib import Path
from collections import Counter, defaultdict

VAULT_ROOT = Path(__file__).parent.parent / "ObsidianVault"
MEMORY_ROOT = Path(__file__).parent.parent / "memory"
GOALS_DIR = VAULT_ROOT / "goals"
REPEAT_THRESHOLD = 3
SIMILARITY_THRESHOLD = 0.6

STOP_WORDS = {
    "의", "을", "를", "이", "가", "은", "는", "에", "에서", "로", "으로",
    "과", "와", "및", "또는", "그", "이것", "것", "수", "있", "없", "됨",
    "완료", "구현", "작업", "파일", "스크립트", "폴더", "노트", "vault",
    "obsidian", "claude", "bucky", "codex", "the", "a", "an", "of", "in",
    "to", "for", "and", "or", "is", "are", "was", "with", "from",
}


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[가-힣a-zA-Z0-9_\-\.]{2,}", text.lower())
    return [t for t in tokens if t not in STOP_WORDS and len(t) >= 2]


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def read_goal_files(goals_dir: Path) -> list[dict]:
    records = []
    for f in sorted(goals_dir.glob("*.md")):
        text = f.read_text(encoding="utf-8", errors="ignore")
        # extract frontmatter status
        status_match = re.search(r"status:\s*(\S+)", text)
        status = status_match.group(1).upper() if status_match else "UNKNOWN"
        # extract step lines (checkbox items or numbered steps)
        steps = re.findall(r"(?:^|\n)\s*(?:\d+\.|[-*]|\[.\])\s+(.+)", text)
        failed_steps = [
            s for s in steps
            if (
                any(w in s.lower() for w in ("fail", "실패", "blocked", "block", "오류", "에러", "error"))
                and "없음" not in s  # skip "X: 없음" summary lines
            )
        ]
        records.append({
            "file": f.name,
            "status": status,
            "tokens": tokenize(text),
            "steps": steps,
            "failed_steps": failed_steps,
            "raw": text,
        })
    return records


def read_memory_files(memory_dir: Path) -> list[dict]:
    records = []
    if not memory_dir.exists():
        return records
    for f in sorted(memory_dir.glob("*.md")):
        if f.name == "MEMORY.md":
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        records.append({"file": f.name, "tokens": tokenize(text)})
    return records


def detect_repeated_tasks(goal_records: list[dict]) -> list[tuple]:
    token_counter: Counter = Counter()
    token_files: defaultdict = defaultdict(list)
    for rec in goal_records:
        seen = set()
        for tok in rec["tokens"]:
            if tok not in seen:
                token_counter[tok] += 1
                token_files[tok].append(rec["file"])
                seen.add(tok)
    repeated = [
        (tok, count, token_files[tok])
        for tok, count in token_counter.most_common()
        if count >= REPEAT_THRESHOLD
    ]
    return repeated


def detect_repeated_failures(goal_records: list[dict]) -> list[dict]:
    failures = []
    for rec in goal_records:
        if rec["failed_steps"]:
            failures.append({"file": rec["file"], "failed_steps": rec["failed_steps"]})
    return failures


def detect_similar_goals(goal_records: list[dict]) -> list[tuple]:
    similar_pairs = []
    recs = goal_records
    for i in range(len(recs)):
        for j in range(i + 1, len(recs)):
            a_tokens = set(recs[i]["tokens"])
            b_tokens = set(recs[j]["tokens"])
            sim = jaccard(a_tokens, b_tokens)
            if sim >= SIMILARITY_THRESHOLD:
                similar_pairs.append((recs[i]["file"], recs[j]["file"], round(sim, 2)))
    return similar_pairs


def print_report(
    goal_records: list[dict],
    repeated: list[tuple],
    failures: list[dict],
    similar: list[tuple],
    verbose: bool = False,
) -> None:
    print("=" * 60)
    print("  Pattern Scanner Report")
    print("=" * 60)
    print(f"  Goals scanned : {len(goal_records)}")
    print()

    print("── [1] Repeated Tasks (keyword ≥ 3 goal files) ──")
    if repeated:
        for tok, count, files in repeated[:10]:
            file_list = ", ".join(files) if verbose else f"{len(files)} files"
            print(f"  '{tok}'  x{count}  [{file_list}]")
    else:
        print("  (없음)")
    print()

    print("── [2] Repeated Failure Steps ──")
    if failures:
        for rec in failures:
            print(f"  {rec['file']}")
            for step in rec["failed_steps"][:3]:
                print(f"    → {step.strip()[:80]}")
    else:
        print("  (없음)")
    print()

    print("── [3] Similar Goals (Jaccard ≥ 60%) ──")
    if similar:
        for a, b, sim in similar:
            print(f"  {a}  ↔  {b}  ({int(sim*100)}%)")
    else:
        print("  (없음)")
    print()
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pattern Scanner for ObsidianVault goals")
    parser.add_argument(
        "--goals-dir",
        default=str(GOALS_DIR),
        help="Path to goals directory",
    )
    parser.add_argument(
        "--memory-dir",
        default=str(MEMORY_ROOT),
        help="Path to memory directory",
    )
    parser.add_argument("--verbose", action="store_true", help="Show file names per pattern")
    args = parser.parse_args()

    goals_dir = Path(args.goals_dir)
    if not goals_dir.exists():
        print(f"[pattern_scanner] goals_dir not found: {goals_dir}")
        sys.exit(1)

    goal_records = read_goal_files(goals_dir)
    if not goal_records:
        print("[pattern_scanner] No goal files found. Nothing to scan.")
        sys.exit(0)

    repeated = detect_repeated_tasks(goal_records)
    failures = detect_repeated_failures(goal_records)
    similar = detect_similar_goals(goal_records)

    print_report(goal_records, repeated, failures, similar, verbose=args.verbose)


if __name__ == "__main__":
    main()
