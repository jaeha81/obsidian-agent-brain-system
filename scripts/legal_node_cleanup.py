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

VAULT     = Path("D:/ai프로젝트/obsidian-agent-brain-system/ObsidianVault")
LEGAL_DIR = VAULT / "04_Wiki" / "Legal"
LAWS_DIR  = LEGAL_DIR / "laws"
PACKS_DIR = VAULT / "06_Context_Packs" / "Legal"
REPORT    = VAULT / "00_System" / "legal-node-analysis.md"
BACKUP    = VAULT / "09_Archive" / "legal-cleanup-backup"
ARCHIVE   = VAULT / "09_Archive"

# 그래프에서 제외해야 할 아카이브 디렉터리
GRAPH_POLLUTING_DIRS = [
    VAULT / "09_Archive" / "legal-cleanup-backup",
    VAULT / "09_Archive" / "migration-conflicts",
]


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


def scan_orphans():
    """09_Archive 등 비활성 디렉터리에서 그래프를 오염시키는 법령 H1 노드 탐지"""
    H1_LAW = re.compile(r'^# (.+)$', re.MULTILINE)
    WIKILINK = re.compile(r'\[\[laws/([^\]|]+)')

    print("\n=== 그래프 오염 파일 스캔 ===")
    polluters: list[dict] = []

    for pollute_dir in GRAPH_POLLUTING_DIRS:
        if not pollute_dir.exists():
            continue
        for md in pollute_dir.rglob("*.md"):
            content = md.read_text(encoding="utf-8", errors="ignore")
            h1s = H1_LAW.findall(content)
            links = WIKILINK.findall(content)
            if h1s or links:
                polluters.append({
                    "file": str(md.relative_to(VAULT)),
                    "h1_headings": h1s,
                    "wiki_links": links,
                })

    if polluters:
        print(f"\n[경고] 그래프 오염 가능 파일: {len(polluters)}개")
        for p in polluters:
            print(f"\n  파일: {p['file']}")
            if p["h1_headings"]:
                print(f"    H1 헤딩 (중복 노드 생성): {p['h1_headings']}")
            if p["wiki_links"]:
                print(f"    [[laws/]] 링크: {p['wiki_links']}")
        print("\n[권장 조치]")
        print("  Obsidian Settings > Files and links > Excluded files에 추가:")
        for d in GRAPH_POLLUTING_DIRS:
            if d.exists():
                rel = d.relative_to(VAULT)
                print(f"    {rel}")
    else:
        print("  그래프 오염 파일 없음.")

    return polluters


def check_duplicates():
    """동일 laws/ 링크를 참조하는 Context Pack 중복 감지 + 내용 유사도 분석"""
    WIKILINK = re.compile(r'\[\[laws/([^\]|]+)')

    print("\n=== Context Pack 중복/유사도 분석 ===")

    pack_files = [f for f in PACKS_DIR.glob("*.md")
                  if f.name != "legal_context_pack_template.md"]

    # 각 팩의 법령 링크 수집
    pack_links: dict[str, set[str]] = {}
    for pf in pack_files:
        content = pf.read_text(encoding="utf-8", errors="ignore")
        links = set(WIKILINK.findall(content))
        pack_links[pf.name] = links

    # 동일 법령 링크를 공유하는 팩 쌍 찾기
    pack_names = list(pack_links.keys())
    duplicate_pairs = []
    for i in range(len(pack_names)):
        for j in range(i + 1, len(pack_names)):
            a, b = pack_names[i], pack_names[j]
            shared = pack_links[a] & pack_links[b]
            if shared:
                duplicate_pairs.append((a, b, shared))

    if duplicate_pairs:
        print(f"\n[중복 링크 쌍]: {len(duplicate_pairs)}쌍")
        for a, b, shared in duplicate_pairs:
            print(f"\n  '{a}' ↔ '{b}'")
            print(f"    공유 법령 링크: {sorted(shared)}")
            # 유사도 점수: Jaccard
            union = pack_links[a] | pack_links[b]
            jaccard = len(shared) / len(union) if union else 0
            print(f"    유사도 (Jaccard): {jaccard:.0%}")
            if jaccard >= 0.8:
                print(f"    ⚠️ HIGH 유사도 — 통합 또는 차별화 필요")
            elif jaccard >= 0.5:
                print(f"    ⚡ MEDIUM 유사도 — 공통 법령 앵커 링크 분리 권장")
    else:
        print("  중복 링크 쌍 없음.")

    # laws/ 파일 참조 없는 팩 탐지
    print("\n[laws/ 링크 없는 Context Pack]:")
    no_link_packs = [name for name, links in pack_links.items() if not links]
    if no_link_packs:
        for name in no_link_packs:
            print(f"  ⚠️ {name} — laws/ 링크 없음 (원문 임베드 가능성)")
    else:
        print("  모든 팩이 laws/ 링크 보유. 정상.")

    return duplicate_pairs


def main():
    p = argparse.ArgumentParser(description="Obsidian 법률 노드 중복 정리")
    p.add_argument("--analyze",          action="store_true", help="중복 분석 리포트 생성")
    p.add_argument("--extract",          action="store_true", help="법령 추출 및 컨텍스트팩 재구성")
    p.add_argument("--scan-orphans",     action="store_true", help="그래프 오염 아카이브 파일 탐지")
    p.add_argument("--check-duplicates", action="store_true", help="Context Pack 중복/유사도 분석")
    p.add_argument("--full",             action="store_true", help="모든 분석 실행 (analyze + scan-orphans + check-duplicates)")
    p.add_argument("--dry-run",          action="store_true", help="변경 없이 미리보기")
    args = p.parse_args()

    if args.extract:
        extract_laws(dry_run=args.dry_run)
    elif args.scan_orphans:
        scan_orphans()
    elif args.check_duplicates:
        check_duplicates()
    elif args.full:
        analyze(dry_run=True)
        scan_orphans()
        check_duplicates()
    else:
        analyze(dry_run=True)


if __name__ == "__main__":
    main()
