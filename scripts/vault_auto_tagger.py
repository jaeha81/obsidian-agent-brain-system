# vault_auto_tagger.py
# 기존 Vault 노트에 #area/ #status/ 태그 자동 추가
# --dry-run: 변경 없이 통계만 출력
# --apply: 실제 파일 수정

import sys
import os
import re
import argparse
from pathlib import Path

VAULT_ROOT = Path(__file__).parent.parent / "ObsidianVault"

# 폴더명 → 추가할 area 태그 목록
FOLDER_AREA_MAP = {
    "10_AgentBus":          ["#area/ai_automation"],
    "06_Context_Packs":     ["#area/ai_automation"],
    "05_Frameworks":        ["#area/ai_automation"],
    "05_Logs":              ["#area/ai_automation"],
    "03_Projects":          ["#area/business_model"],
    "02_Project":           ["#area/business_model"],
    "07_Reports":           ["#area/gpt_feedback"],
    "04_DAILY_REPORTS":     ["#area/gpt_feedback"],
    "04_Wiki":              ["#area/research"],
    "03_Knowledge":         ["#area/research"],
    "09_Knowledge_Capture": ["#area/research"],
    "11_Interior_Business":  ["#area/interior_design", "#status/active"],
    "12_Client_Consulting":  ["#area/client_consulting", "#status/active"],
    "00_Inbox":             ["#status/inbox"],
    "01_RAW":               ["#status/inbox"],
    "02_Processed":         ["#status/review_needed"],
    "09_Archive":           ["#status/archive"],
    # 시스템 폴더 — 태그 없음
    "00_System":            [],
    "00_Dashboard":         [],
    "00_UPGRADE":           [],
    "08_Templates":         [],
    "_templates":           [],
    "graphify-out":         [],
    ".obsidian":            [],
    ".smart-env":           [],
}

# 파일명/YAML title 키워드 → 추가할 area 태그
# 파일명(stem)과 frontmatter title 필드만 검사 — body 스캔은 오탐이 많아 제외
KEYWORD_AREA_MAP = [
    # (키워드 목록, 추가할 태그)  — 키워드는 소문자, 언더스코어/하이픈 포함 가능
    (
        ["interior-design", "interior_design", "spaceplanner", "인테리어_견적", "인테리어-견적", "견적시스템"],
        "#area/interior_design",
    ),
    (
        ["client_project", "client-project", "11_client"],
        "#area/client_consulting",
    ),
    (
        ["시공관리", "현장관리", "field_management"],
        "#area/construction",
    ),
]


def _extract_yaml_title(text: str) -> str:
    """frontmatter의 title 값만 추출 (소문자). 없으면 빈 문자열."""
    if not text.startswith("---"):
        return ""
    lines = text.splitlines()
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r'^title:\s*["\']?(.+?)["\']?\s*$', line, re.IGNORECASE)
        if m:
            return m.group(1).lower()
    return ""


def get_keyword_area_tags(path: Path, text: str) -> list[str]:
    """파일명과 YAML title 키워드로 추가 area 태그 반환 (오탐 최소화)."""
    filename_lower = path.stem.lower()
    title_lower = _extract_yaml_title(text)
    search_targets = [filename_lower, title_lower]
    tags = []
    for keywords, tag in KEYWORD_AREA_MAP:
        for kw in keywords:
            kw_lower = kw.lower()
            if any(kw_lower in target for target in search_targets):
                tags.append(tag)
                break
    return tags


# YAML status 필드값 → status 태그 매핑
STATUS_TAG_MAP = {
    "active":       "#status/active",
    "inbox":        "#status/inbox",
    "draft":        "#status/inbox",
    "review":       "#status/review_needed",
    "review_needed":"#status/review_needed",
    "waiting":      "#status/waiting",
    "done":         "#status/completed",
    "completed":    "#status/completed",
    "hold":         "#status/hold",
    "archive":      "#status/archive",
    "archived":     "#status/archive",
}


def get_top_folder(path: Path) -> str:
    """파일의 Vault 기준 최상위 폴더명 반환."""
    try:
        rel = path.relative_to(VAULT_ROOT)
        parts = rel.parts
        return parts[0] if len(parts) > 1 else ""
    except ValueError:
        return ""


def parse_frontmatter(text: str):
    """(frontmatter_dict, fm_end_line) 반환. frontmatter 없으면 ({}, -1)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, -1
    end = -1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end = i
            break
    if end == -1:
        return {}, -1

    fm_lines = lines[1:end]
    fm = {}
    current_key = None
    list_items = []
    for line in fm_lines:
        list_match = re.match(r"^  - (.+)$", line)
        key_match = re.match(r"^(\w+):\s*(.*)", line)
        if list_match and current_key:
            list_items.append(list_match.group(1).strip())
            fm[current_key] = list_items[:]
        elif key_match:
            if current_key and list_items:
                fm[current_key] = list_items[:]
            current_key = key_match.group(1)
            val = key_match.group(2).strip()
            list_items = []
            fm[current_key] = val if val else []
    return fm, end


def create_frontmatter(path: Path, tags: list[str]) -> str:
    """frontmatter 없는 노트에 최소 YAML 생성 후 원본 내용 붙임."""
    import datetime
    today = datetime.date.today().isoformat()
    tag_lines = "".join(f"  - {t}\n" for t in tags)
    header = f"---\ntitle: {path.stem}\ndate: {today}\nstatus: inbox\ntags:\n{tag_lines}---\n\n"
    return header


def inject_tags(text: str, new_tags: list[str]) -> str | None:
    """frontmatter tags 필드에 new_tags 추가. 변경 없으면 None 반환."""
    if not new_tags:
        return None

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None

    # frontmatter 범위
    end = -1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end = i
            break
    if end == -1:
        return None

    fm_text = "".join(lines[1:end])
    # 기존 tags 추출
    existing = set()
    tag_block_start = -1
    tag_block_end = -1
    in_tags = False
    for i, line in enumerate(lines[1:end], 1):
        if re.match(r"^tags:\s*$", line.strip()) or re.match(r"^tags:\s*\[", line.strip()):
            tag_block_start = i
            in_tags = True
        elif in_tags and re.match(r"^  - (.+)", line):
            existing.add(re.match(r"^  - (.+)", line).group(1).strip())
            tag_block_end = i
        elif in_tags and not line.startswith("  "):
            in_tags = False

    to_add = [t for t in new_tags if t not in existing]
    if not to_add:
        return None  # 이미 모두 있음

    result = list(lines)

    if tag_block_start != -1:
        # tags 블록 있음 — 마지막 태그 줄 뒤에 추가
        insert_at = tag_block_end if tag_block_end != -1 else tag_block_start
        for tag in reversed(to_add):
            result.insert(insert_at + 1, f"  - {tag}\n")
    else:
        # tags 블록 없음 — frontmatter 닫는 --- 앞에 삽입
        tag_block = "tags:\n" + "".join(f"  - {t}\n" for t in to_add)
        result.insert(end, tag_block)

    return "".join(result)


def process_file(path: Path, dry_run: bool) -> dict:
    """파일 처리. 결과 dict 반환."""
    result = {"path": str(path), "added": [], "skipped": False, "error": None}

    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        result["error"] = str(e)
        return result

    top_folder = get_top_folder(path)
    area_tags = FOLDER_AREA_MAP.get(top_folder, None)

    if area_tags is None:
        result["skipped"] = True
        return result

    # status 필드에서 status 태그 결정
    fm, _ = parse_frontmatter(text)
    status_val = fm.get("status", "")
    status_tag = STATUS_TAG_MAP.get(str(status_val).lower().strip(), "")

    tags_to_add = list(area_tags)
    if status_tag:
        tags_to_add.append(status_tag)

    # 키워드 기반 추가 태그 (폴더 태그가 없거나 있어도 추가)
    keyword_tags = get_keyword_area_tags(path, text)
    for t in keyword_tags:
        if t not in tags_to_add:
            tags_to_add.append(t)

    if not tags_to_add:
        result["skipped"] = True
        return result

    new_text = inject_tags(text, tags_to_add)
    if new_text is None:
        # frontmatter 없는 노트 → 자동 생성 (Inbox / 새 폴더만)
        if top_folder in ("00_Inbox", "01_RAW", "11_Interior_Business", "12_Client_Consulting"):
            new_text = create_frontmatter(path, tags_to_add) + text
        else:
            result["skipped"] = True
            return result

    result["added"] = tags_to_add
    if not dry_run:
        path.write_text(new_text, encoding="utf-8")

    return result


def main():
    parser = argparse.ArgumentParser(description="Vault 노트 자동 태거")
    parser.add_argument("--dry-run", action="store_true", help="변경 없이 통계만 출력")
    parser.add_argument("--apply", action="store_true", help="실제 파일 수정")
    parser.add_argument("--folder", default=None, help="특정 폴더만 처리 (예: 10_AgentBus)")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("--dry-run 또는 --apply 지정 필요")
        sys.exit(1)

    dry_run = not args.apply

    if args.folder:
        target = VAULT_ROOT / args.folder
        files = list(target.rglob("*.md"))
    else:
        files = list(VAULT_ROOT.rglob("*.md"))

    total = len(files)
    modified = 0
    skipped = 0
    errors = 0
    tag_counts: dict[str, int] = {}

    for f in files:
        r = process_file(f, dry_run)
        if r["error"]:
            errors += 1
        elif r["skipped"]:
            skipped += 1
        elif r["added"]:
            modified += 1
            for t in r["added"]:
                tag_counts[t] = tag_counts.get(t, 0) + 1
            if dry_run:
                print(f"[DRY] {f.relative_to(VAULT_ROOT)} → {r['added']}")

    mode = "DRY RUN" if dry_run else "APPLIED"
    print(f"\n=== {mode} 완료 ===")
    print(f"전체: {total}  수정: {modified}  스킵: {skipped}  오류: {errors}")
    print("\n태그별 추가 예정:")
    for tag, cnt in sorted(tag_counts.items(), key=lambda x: -x[1]):
        print(f"  {tag}: {cnt}개")


if __name__ == "__main__":
    main()
