#!/usr/bin/env python3
"""
Legal Node Cleanup — Obsidian 그래프 법률 노드 중복 정리

문제: 법령 컨텍스트팩 파일 내부에 # 주택법 / # 건축법 등 H1 헤딩으로
법령 원문이 직접 임베드되어 Obsidian 그래프에서 동일 이름 노드 폭증.

해결 전략:
1. 임베드된 법령 원문 섹션을 04_Wiki/Legal/laws/ 개별 파일로 추출
2. 컨텍스트팩에서는 [[법령명]] 링크로 대체
3. 그래프에서 법령 = 단일 노드, 컨텍스트팩 = 해당 노드에 연결

사용법:
    python legal_node_cleanup.py --dry-run   # 변경 없이 분석만
    python legal_node_cleanup.py --analyze   # 중복 리포트 생성
    python legal_node_cleanup.py --extract   # 법령 원문 추출 및 재구성
"""

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path

VAULT     = Path("G:/내 드라이브/obsidian-agent-brain-system/ObsidianVault")
LEGAL_DIR = VAULT / "04_Wiki" / "Legal"
LAWS_DIR  = LEGAL_DIR / "laws"
PACKS_DIR = VAULT / "06_Context_Packs" / "Legal"
REPORT    = VAULT / "00_System" / "legal-node-analysis.md"
BACKUP    = VAULT / "09_Archive" / "legal-cleanup-backup"


def extract_law_sections(content: str) -> list[dict]:
    """컨텍스트팩에서 # 법령명 섹션 추출"""
    sections = []
    # H1 법령 섹션 패턴: "# 법령명" (Legal Context Pack 제목 제외)
    pattern = re.compile(r'^(# (?!Legal Context Pack)(.+?))\n(.*?)(?=^# |\Z)', re.MULTILINE | re.DOTALL)
    for m in pattern.finditer(content):
        title = m.group(2).strip()
        body  = m.group(3).strip()
        if body:
            sections.append({"title": title, "body": body, "raw": m.group(0)})
    return sections


def make_law_file(title: str, body: str) -> str:
    """법령 독립 노트 생성"""
    slug = title.replace(" ", "_").replace("/", "_")
    date = datetime.now().strftime("%Y-%m-%d")
    return f"""---
tags:
  - legal
  - law-reference
title: "{title}"
updated: {date}
---

# {title}

> 출처: LegalizeKR | [[Index|Legal Wiki Index]]

{body}
"""


def analyze(dry_run: bool = True):
    pack_files = list(PACKS_DIR.glob("*.md"))
    # 제목이 같은 H1 찾기
    title_map: dict[str, list[str]] = {}
    for pf in pack_files:
        content = pf.read_text(encoding="utf-8")
        for sec in extract_law_sections(content):
            title_map.setdefault(sec["title"], []).append(pf.name)

    duplicates = {t: files for t, files in title_map.items() if len(files) > 1}
    all_laws   = list(title_map.keys())

    print(f"\n=== 법률 노드 분석 결과 ===")
    print(f"컨텍스트팩 파일 수: {len(pack_files)}")
    print(f"임베드된 법령 제목: {len(all_laws)}개")
    print(f"중복 법령 제목:     {len(duplicates)}개")

    if duplicates:
        print("\n[중복 법령 목록]")
        for title, files in duplicates.items():
            print(f"  '{title}' → {files}")

    lines = [
        "# Legal Node 분석 리포트",
        f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 요약",
        f"- 컨텍스트팩 파일: {len(pack_files)}개",
        f"- 임베드 법령 수: {len(all_laws)}개",
        f"- 중복 법령: **{len(duplicates)}개**",
        "",
        "## 문제 원인",
        "컨텍스트팩 내부에 `# 법령명` H1 헤딩으로 법령 원문이 임베드되어",
        "Obsidian 그래프에서 동일 이름의 노드가 파일 수만큼 중복 생성됨.",
        "",
        "## 중복 법령 목록",
    ]
    for title, files in duplicates.items():
        lines.append(f"- **{title}**: {', '.join(files)}")

    lines += [
        "",
        "## 권장 조치",
        "1. `python legal_node_cleanup.py --extract` 실행",
        "2. 각 법령 → `04_Wiki/Legal/laws/[법령명].md` 독립 파일 생성",
        "3. 컨텍스트팩에서는 `[[법령명]]` 링크로 대체",
        "4. 그래프 새로고침 → 법령 = 단일 노드",
        "",
        "## 추출 대상 법령",
    ]
    for t in sorted(all_laws):
        lines.append(f"- [[laws/{t.replace(' ', '_')}|{t}]]")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n리포트 저장: {REPORT}")
    return title_map, duplicates


def extract_laws(dry_run: bool = False):
    """법령 원문을 개별 파일로 추출하고 컨텍스트팩을 링크로 대체"""
    title_map, _ = analyze(dry_run=True)

    if not dry_run:
        LAWS_DIR.mkdir(parents=True, exist_ok=True)
        BACKUP.mkdir(parents=True, exist_ok=True)

    pack_files = list(PACKS_DIR.glob("*.md"))

    # 1. 법령 독립 파일 생성 (중복 없이 1번만)
    created = set()
    for pf in pack_files:
        content = pf.read_text(encoding="utf-8")
        for sec in extract_law_sections(content):
            title = sec["title"]
            slug  = title.replace(" ", "_").replace("/", "_")
            law_file = LAWS_DIR / f"{slug}.md"
            if title not in created:
                print(f"  [CREATE] {law_file.name}")
                if not dry_run:
                    law_file.write_text(make_law_file(title, sec["body"]), encoding="utf-8")
                created.add(title)

    # 2. 컨텍스트팩에서 법령 원문 섹션 → 링크로 대체
    for pf in pack_files:
        content = pf.read_text(encoding="utf-8")
        new_content = content
        for sec in extract_law_sections(content):
            title = sec["title"]
            slug  = title.replace(" ", "_").replace("/", "_")
            replacement = f"\n> 📄 [[laws/{slug}|{title}]] — 원문 링크\n"
            new_content = new_content.replace(sec["raw"], replacement, 1)

        if new_content != content:
            print(f"  [UPDATE] {pf.name}")
            if not dry_run:
                # 백업
                shutil.copy2(pf, BACKUP / pf.name)
                pf.write_text(new_content, encoding="utf-8")

    print(f"\n{'[DRY-RUN 완료]' if dry_run else '[EXTRACT 완료]'}")
    print(f"  생성 예정 법령 파일: {len(created)}개")
    print(f"  수정 예정 컨텍스트팩: {len(pack_files)}개")
    if not dry_run:
        print(f"  백업 위치: {BACKUP}")


def main():
    p = argparse.ArgumentParser(description="Obsidian 법률 노드 중복 정리")
    p.add_argument("--analyze",  action="store_true", help="중복 분석 리포트 생성")
    p.add_argument("--extract",  action="store_true", help="법령 추출 및 컨텍스트팩 재구성")
    p.add_argument("--dry-run",  action="store_true", help="변경 없이 미리보기")
    args = p.parse_args()

    if args.extract:
        extract_laws(dry_run=args.dry_run)
    else:
        analyze(dry_run=True)


if __name__ == "__main__":
    main()
