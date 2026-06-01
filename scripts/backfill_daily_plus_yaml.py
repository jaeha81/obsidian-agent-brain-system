"""
backfill_daily_plus_yaml.py
기존 daily-plus 노트에 category/summary/next_action/status 필드 추가 (없는 것만)
"""
import re
from pathlib import Path

DAILY_PLUS_DIR = Path(__file__).parent.parent / "ObsidianVault" / "04_Wiki" / "daily-plus"

FIELDS_TO_ADD = ["category", "summary", "next_action", "status"]


def parse_frontmatter_end(lines: list[str]) -> int:
    if not lines or lines[0].strip() != "---":
        return -1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            return i
    return -1


def extract_overview(lines: list[str], fm_end: int) -> str:
    body = "\n".join(lines[fm_end + 1:])
    m = re.search(r"## Overview\s*\n+(.+?)(?:\n\n|\n##)", body, re.DOTALL)
    if m:
        return m.group(1).replace("\n", " ").strip()[:200]
    date_m = re.search(r"# ChatGPT Pulse - (\d{4}-\d{2}-\d{2})", body)
    date_str = date_m.group(1) if date_m else "unknown"
    return f"ChatGPT Pulse {date_str}"


def backfill_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    fm_end = parse_frontmatter_end([l.rstrip("\n") for l in lines])
    if fm_end == -1:
        print(f"[SKIP] no frontmatter: {path.name}")
        return False

    fm_block = "".join(lines[1:fm_end])
    existing_keys = set(re.findall(r"^(\w+):", fm_block, re.M))
    missing = [f for f in FIELDS_TO_ADD if f not in existing_keys]
    if not missing:
        print(f"[OK]   already complete: {path.name}")
        return False

    overview = extract_overview([l.rstrip("\n") for l in lines], fm_end)
    inserts = []
    if "category" in missing:
        inserts.append("category: gpt_feedback\n")
    if "summary" in missing:
        inserts.append(f'summary: "{overview}"\n')
    if "next_action" in missing:
        inserts.append("next_action: review\n")
    if "status" in missing:
        inserts.append("status: inbox\n")

    result = list(lines)
    for line in reversed(inserts):
        result.insert(fm_end, line)
    path.write_text("".join(result), encoding="utf-8")
    print(f"[ADD]  {path.name} ← {missing}")
    return True


def main():
    files = sorted(DAILY_PLUS_DIR.glob("*.md"))
    changed = sum(backfill_file(f) for f in files)
    print(f"\n완료: {changed}/{len(files)} 파일 업데이트")


if __name__ == "__main__":
    main()
