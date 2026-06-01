"""
enrich_yaml_summary.py
지정 폴더의 .md 노트에 summary/category/status/next_action 자동 추가.
본문에서 smart extract: blockquote > 역할/개요 섹션 > 첫 단락.
--dry-run: 미리보기  --apply: 실제 수정
"""
import argparse
import re
from pathlib import Path

VAULT_ROOT = Path(__file__).parent.parent / "ObsidianVault"

FOLDER_DEFAULTS = {
    "05_Frameworks":    {"category": "ai_automation",    "status": "active"},
    "06_Context_Packs": {"category": "ai_automation",    "status": "active"},
    "03_Projects":      {"category": "business_model",   "status": "active"},
    "06_Projects":      {"category": "business_model",   "status": "active"},
    "04_Wiki":          {"category": "research",         "status": "active"},
    "03_Knowledge":     {"category": "research",         "status": "active"},
    "06_Knowledge":     {"category": "research",         "status": "active"},
    "06_Resources":     {"category": "reference",        "status": "active"},
}

SECTION_KEYWORDS = ["역할", "개요", "목적", "overview", "summary", "description", "소개"]


def get_top_folder(path: Path) -> str:
    try:
        return path.relative_to(VAULT_ROOT).parts[0]
    except (ValueError, IndexError):
        return ""


def extract_summary(text: str) -> str:
    lines = text.splitlines()
    fm_end = -1
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                fm_end = i
                break
    body_lines = lines[fm_end + 1:] if fm_end != -1 else lines

    # 1. blockquote 바로 아래 (> 텍스트)
    for line in body_lines:
        stripped = line.strip()
        if stripped.startswith(">"):
            text_part = stripped.lstrip(">").strip()
            if len(text_part) > 10:
                return text_part[:200]

    # 2. 역할/개요/목적 섹션 첫 단락
    in_section = False
    for line in body_lines:
        if re.match(r"^#{1,3}\s+", line):
            heading = re.sub(r"^#{1,3}\s+", "", line).lower().strip()
            in_section = any(kw in heading for kw in SECTION_KEYWORDS)
            continue
        if in_section and line.strip() and not line.startswith("#") and not line.startswith("|"):
            clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line.strip())
            clean = re.sub(r"\[\[([^\]|]+).*?\]\]", r"\1", clean)
            if len(clean) > 15:
                return clean[:200]

    # 3. 첫 비어있지 않은 단락 (heading/table/code 제외)
    for line in body_lines:
        stripped = line.strip()
        if (stripped and not stripped.startswith("#") and not stripped.startswith("|")
                and not stripped.startswith("```") and not stripped.startswith("![")):
            clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", stripped)
            clean = re.sub(r"\[\[([^\]|]+).*?\]\]", r"\1", clean)
            if len(clean) > 15:
                return clean[:200]

    return ""


def parse_fm_end(lines: list[str]) -> int:
    if not lines or lines[0].strip() != "---":
        return -1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            return i
    return -1


def has_field(fm_block: str, field: str) -> bool:
    return bool(re.search(rf"^{field}:", fm_block, re.M))


def inject_fields(text: str, fields: dict[str, str]) -> str | None:
    lines = text.splitlines(keepends=True)
    fm_end = parse_fm_end([l.rstrip("\n") for l in lines])

    if fm_end == -1:
        # frontmatter 없음 → 생성
        inserts = "".join(f'{k}: "{v}"\n' if k == "summary" else f"{k}: {v}\n"
                         for k, v in fields.items())
        return f"---\n{inserts}---\n\n" + text

    fm_block = "".join(lines[1:fm_end])
    to_add = {k: v for k, v in fields.items() if not has_field(fm_block, k)}
    if not to_add:
        return None

    result = list(lines)
    inserts = []
    for k, v in to_add.items():
        inserts.append(f'{k}: "{v}"\n' if k == "summary" else f"{k}: {v}\n")
    for line in reversed(inserts):
        result.insert(fm_end, line)
    return "".join(result)


def process_file(path: Path, defaults: dict, dry_run: bool) -> dict:
    result = {"path": str(path), "added": [], "skipped": False, "error": None}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        result["error"] = str(e)
        return result

    lines = text.splitlines()
    fm_end = parse_fm_end(lines)
    fm_block = "".join(lines[1:fm_end]) if fm_end != -1 else ""

    fields = {}
    if not has_field(fm_block, "summary"):
        summary = extract_summary(text)
        if summary:
            fields["summary"] = summary
    if not has_field(fm_block, "category") and "category" in defaults:
        fields["category"] = defaults["category"]
    if not has_field(fm_block, "status") and "status" in defaults:
        fields["status"] = defaults["status"]
    if not has_field(fm_block, "next_action"):
        fields["next_action"] = "review"

    if not fields:
        result["skipped"] = True
        return result

    new_text = inject_fields(text, fields)
    if new_text is None:
        result["skipped"] = True
        return result

    result["added"] = list(fields.keys())
    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--folder", required=True, help="대상 폴더명 (예: 05_Frameworks)")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("--dry-run 또는 --apply 필요")
        return

    dry_run = not args.apply
    defaults = FOLDER_DEFAULTS.get(args.folder, {})
    target = VAULT_ROOT / args.folder
    files = [f for f in target.rglob("*.md")
             if not any(skip in str(f) for skip in ["inbox", "outbox", "completed", "failed"])]

    modified = skipped = errors = 0
    for f in files:
        r = process_file(f, defaults, dry_run)
        if r["error"]:
            errors += 1
            print(f"[ERR] {Path(r['path']).name}: {r['error']}")
        elif r["skipped"]:
            skipped += 1
        else:
            modified += 1
            if dry_run:
                rel = Path(r["path"]).relative_to(VAULT_ROOT)
                print(f"[DRY] {rel} ← {r['added']}")

    mode = "DRY RUN" if dry_run else "APPLIED"
    print(f"\n=== {mode} ===  전체:{len(files)}  수정:{modified}  스킵:{skipped}  오류:{errors}")


if __name__ == "__main__":
    main()
