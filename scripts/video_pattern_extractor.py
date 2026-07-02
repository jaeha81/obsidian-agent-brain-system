#!/usr/bin/env python3
"""
Video Pattern Extractor (Stage 1)

영상 지식 노트(03_Knowledge/*-yt-*.md)에서 패턴 후보를 추출해
Stage 2(승격 게이트)의 입력으로 넘긴다.

원칙:
- 읽기 전용. 원본 영상 노트는 절대 수정하지 않는다.
- 이미 처리한 영상은 .processed.json으로 중복 방지.
- LLM 호출 없음(키워드 사전 기반 분류). Stage 2에서 필요시 LLM 활용.
- 기존 bucky_pattern_extractor.py(Discord 메시지)와 충돌 없음 (입력 소스 분리).
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
VAULT = ROOT / "ObsidianVault"
KNOWLEDGE_DIR = VAULT / "03_Knowledge"
OUTPUT_DIR = VAULT / "09_Knowledge_Capture" / "video-patterns"
STATE_FILE = OUTPUT_DIR / ".processed.json"

CATEGORY_KEYWORDS = {
    "technique": ["기법", "방법", "트릭", "노하우", "활용법", "사용법", "팁"],
    "tool": ["도구", "툴", "skill", "스킬", "플러그인", "mcp", "에이전트", "agent", "라이브러리", "프레임워크"],
    "principle": ["원칙", "철학", "마인드", "전략", "사고", "관점", "본질"],
    "workflow": ["워크플로우", "프로세스", "파이프라인", "루프", "시스템", "자동화", "오케스트레이션"],
    "design": ["디자인", "ui", "ux", "스타일", "레이아웃", "비주얼"],
    "code": ["코드", "구현", "개발", "리팩터", "디버깅", "테스트"],
}


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"processed": [], "last_run": None}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_video_note(md_path: Path) -> dict | None:
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        print(f"⚠️ 읽기 실패: {md_path.name} ({exc})", file=sys.stderr)
        return None

    fm_match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not fm_match:
        return None

    fm_text = fm_match.group(1)

    def extract(key: str, default: str = "") -> str:
        m = re.search(rf"^{key}:\s*(.+)$", fm_text, re.MULTILINE)
        if not m:
            return default
        return m.group(1).strip().strip("'\"")

    title = extract("title", md_path.stem)
    source = extract("source")
    channel = extract("channel")
    date = extract("date")

    body = text[fm_match.end():]

    summary_match = re.search(r"##\s*요약\s*\n(.*?)(?=\n##|\Z)", body, re.DOTALL)
    summary = summary_match.group(1).strip() if summary_match else ""

    apply_match = re.search(
        r"##\s*우리\s*시스템\s*적용\s*포인트(.*?)(?=\n##|\Z)",
        body,
        re.DOTALL,
    )
    apply_text = apply_match.group(1).strip() if apply_match else ""
    boilerplate_markers = (
        "Bucky가 자동 캡처",
        "적용 아이디어를 아래에 추가",
    )
    apply_cleaned = apply_text
    for marker in boilerplate_markers:
        apply_cleaned = re.sub(rf"^.*{re.escape(marker)}.*$", "", apply_cleaned, flags=re.MULTILINE)
    apply_cleaned = re.sub(r"^\s*>\s*", "", apply_cleaned, flags=re.MULTILINE)
    apply_cleaned = re.sub(r"^\s*-\s*\[\s*\]\s*$", "", apply_cleaned, flags=re.MULTILINE)
    apply_cleaned = apply_cleaned.strip()
    has_user_notes = bool(apply_cleaned)

    full_text = (title + " " + summary).lower()
    categories = [cat for cat, kws in CATEGORY_KEYWORDS.items() if any(kw in full_text for kw in kws)]
    if not categories:
        categories = ["unclassified"]

    return {
        "file": md_path.name,
        "title": title,
        "source": source,
        "channel": channel,
        "date": date,
        "summary_preview": summary[:400],
        "user_applied_notes": apply_cleaned[:500] if has_user_notes else "",
        "categories": categories,
        "extracted_at": datetime.now().isoformat(),
    }


def render_report(patterns: list[dict], total_processed: int, today: str) -> str:
    cat_counter: dict[str, int] = {}
    for p in patterns:
        for c in p["categories"]:
            cat_counter[c] = cat_counter.get(c, 0) + 1

    lines = [
        "---",
        "type: video-patterns",
        f"date: {today}",
        f"extracted_count: {len(patterns)}",
        f"total_processed: {total_processed}",
        f"created_at: {datetime.now().isoformat()}",
        "stage: 1",
        "next_stage: video-promotion-gate",
        "---",
        "",
        f"# 영상 패턴 추출 - {today}",
        "",
        f"**신규 추출: {len(patterns)}건 / 누적 처리: {total_processed}건**",
        "",
        "## 카테고리별 분포",
        "",
    ]

    for cat, cnt in sorted(cat_counter.items(), key=lambda x: -x[1]):
        lines.append(f"- **{cat}**: {cnt}건")

    lines.extend(["", "## 추출된 패턴 후보", ""])

    for i, p in enumerate(patterns, 1):
        lines.append(f"### {i}. {p['title']}")
        lines.append("")
        lines.append(f"- 채널: {p['channel'] or '-'}")
        lines.append(f"- 출처: {p['source'] or '-'}")
        lines.append(f"- 날짜: {p['date'] or '-'}")
        lines.append(f"- 카테고리: {', '.join(f'`{c}`' for c in p['categories'])}")
        lines.append(f"- 원본: `{p['file']}`")
        if p["summary_preview"]:
            lines.append("")
            lines.append("**요약 발췌**:")
            preview = p["summary_preview"].replace("\n", " ")[:250]
            lines.append(f"> {preview}...")
        if p["user_applied_notes"]:
            lines.append("")
            lines.append("**사용자 적용 메모**:")
            lines.append(p["user_applied_notes"])
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Stage 2 진행 안내",
        "",
        "이 추출 결과는 Stage 2(승격 후보 분류) 입력값입니다.",
        "사용자 검토 후 진행 여부를 결정합니다.",
        "",
        "**다음 명령** (사용자 승인 시):",
        "",
        "```bash",
        "python -X utf8 scripts/video_promotion_gate.py",
        "```",
    ])

    return "\n".join(lines)


def main() -> int:
    if not KNOWLEDGE_DIR.exists():
        print(f"❌ 지식 폴더 없음: {KNOWLEDGE_DIR}", file=sys.stderr)
        return 1

    state = load_state()
    processed = set(state.get("processed", []))

    video_notes = sorted(KNOWLEDGE_DIR.glob("*-yt-*.md"))
    if not video_notes:
        print(f"⚠️ 영상 노트 없음: {KNOWLEDGE_DIR}")
        return 0

    new_patterns: list[dict] = []
    failed = 0
    for note in video_notes:
        if note.name in processed:
            continue
        parsed = parse_video_note(note)
        if parsed:
            new_patterns.append(parsed)
            processed.add(note.name)
        else:
            failed += 1

    if not new_patterns:
        print(f"✅ 신규 영상 노트 없음 (총 {len(video_notes)}개 모두 처리됨)")
        return 0

    today = datetime.now().strftime("%Y-%m-%d")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"{today}.md"
    output_file.write_text(render_report(new_patterns, len(processed), today), encoding="utf-8")

    state["processed"] = sorted(processed)
    state["last_run"] = datetime.now().isoformat()
    save_state(state)

    cat_counter: dict[str, int] = {}
    for p in new_patterns:
        for c in p["categories"]:
            cat_counter[c] = cat_counter.get(c, 0) + 1

    print("=" * 60)
    print("✅ Stage 1 (Video Pattern Extractor) 완료")
    print("=" * 60)
    print(f"  신규 추출   : {len(new_patterns)}건")
    print(f"  누적 처리   : {len(processed)}건")
    print(f"  실패        : {failed}건")
    print(f"  출력 파일   : {output_file}")
    print()
    print("카테고리 분포:")
    for cat, cnt in sorted(cat_counter.items(), key=lambda x: -x[1]):
        print(f"  - {cat:14s}: {cnt}건")
    print()
    print("➡️ 다음: 결과 검토 후 Stage 2 진행 여부 결정")
    return 0


if __name__ == "__main__":
    sys.exit(main())
