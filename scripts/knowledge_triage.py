#!/usr/bin/env python3
"""
Knowledge Triage Gate — daily-plus-triage 파일의 항목을 분류하고 실행한다.

Usage:
    python knowledge_triage.py                    # pending 파일 목록 출력
    python knowledge_triage.py --list             # 상동
    python knowledge_triage.py --today            # 오늘 날짜 파일 처리
    python knowledge_triage.py --file <path>      # 특정 파일 처리
    python knowledge_triage.py --today --decide approve,implement,queue,archive
    python knowledge_triage.py --today --auto     # 키워드 기반 자동 분류
    python knowledge_triage.py --today --dry-run  # 미리보기 (파일 변경 없음)

결정 값:
    approve  — 즉시 시스템 반영 가능 (스크립트·설정·패턴)
    implement — 코드 작업 필요 → CL-XXX 태스크 생성
    queue    — 미래 착수 (인프라·의존성 필요)
    archive  — 현 시스템 무관
    skip     — 결정 보류 (항목 그대로 유지)
"""

import argparse
import re
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import checklist_store

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
VAULT      = ROOT / "ObsidianVault"
TRIAGE_DIR = VAULT / "00_Inbox" / "daily-plus-triage"
AUDIT_LOG  = VAULT / "00_System" / "triage-audit-log.md"

VALID_DECISIONS = {"approve", "implement", "queue", "archive", "skip"}

# ── 자동 분류 키워드 맵 ────────────────────────────────────────────────────────
AUTO_KEYWORDS = {
    "approve": [
        "template", "pattern", "config", "설정", "guard", "policy", "rule",
        "fail-safe", "integrity", "safeguard", "checklist", "protocol",
    ],
    "implement": [
        "script", "code", "implement", "api", "agent", "pipeline", "automation",
        "bot", "스크립트", "구현", "개발", "연동", "자동화", "대시보드", "dashboard",
        "poc", "estimator", "tracker", "monitor",
    ],
    "queue": [
        "infra", "인프라", "migration", "이관", "subscription", "구독",
        "vendor", "license", "procurement", "서버",
    ],
    "archive": [
        "service", "product", "external", "third-party", "startup",
        "별도", "외부", "서비스",
    ],
}


# ── 프론트매터 파싱 / 쓰기 ─────────────────────────────────────────────────────

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """--- ... --- 프론트매터를 파싱. 반환: (meta_dict, body_text)"""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if not match:
        return {}, text

    raw_fm = match.group(1)
    body   = match.group(2)

    meta: dict = {}
    for line in raw_fm.splitlines():
        kv = re.match(r"^(\w+):\s*(.*)", line)
        if kv:
            meta[kv.group(1)] = kv.group(2).strip()

    return meta, body


def rewrite_frontmatter(text: str, updates: dict) -> str:
    """프론트매터의 특정 키를 업데이트한다."""
    match = re.match(r"^(---\s*\n)(.*?)(\n---\s*\n)(.*)", text, re.DOTALL)
    if not match:
        return text

    opener, fm_text, closer, body = match.groups()
    new_lines = []
    updated_keys: set[str] = set()

    for line in fm_text.splitlines():
        kv = re.match(r"^(\w+)(:.*)", line)
        if kv and kv.group(1) in updates:
            key = kv.group(1)
            new_lines.append(f"{key}: {updates[key]}")
            updated_keys.add(key)
        else:
            new_lines.append(line)

    # 새 키 추가 (기존에 없었던 경우)
    for k, v in updates.items():
        if k not in updated_keys:
            new_lines.append(f"{k}: {v}")

    return opener + "\n".join(new_lines) + closer + body


# ── 트리아지 항목 파싱 ─────────────────────────────────────────────────────────

def parse_items(body: str) -> list[dict]:
    """
    '- [ ] N. **제목** — 설명' 또는 '- [x] N. [결정] **제목** — 설명' 패턴 파싱.
    반환: [{"idx": int, "title": str, "desc": str, "done": bool, "decision": str|None, "line_idx": int}]
    """
    items: list[dict] = []
    lines = body.splitlines()

    item_re = re.compile(
        r"^- \[( |x)\] (\d+)\."       # - [ ] N. 또는 - [x] N.
        r"(?:\s*\[(\w+)\])?"           # 선택: [결정]
        r"\s*\*\*(.+?)\*\*"            # **제목**
        r"(?:\s*[—–-]\s*(.+?))?\s*"    # 선택: — 설명 (trailing whitespace 허용, $ 제거)
    )

    for i, line in enumerate(lines):
        m = item_re.match(line.strip())
        if m:
            done     = m.group(1) == "x"
            idx      = int(m.group(2))
            decision = m.group(3)  # None if not set
            title    = m.group(4).strip()
            desc     = (m.group(5) or "").strip()
            items.append({
                "idx":      idx,
                "title":    title,
                "desc":     desc,
                "done":     done,
                "decision": decision,
                "line_idx": i,
                "raw":      line,
            })

    return items


def apply_decision_to_body(body: str, item: dict, decision: str) -> str:
    """body 텍스트에서 해당 항목 라인에 결정을 반영한다."""
    lines = body.splitlines()
    target = item["line_idx"]

    if target >= len(lines):
        return body

    # 새 라인 구성
    desc_part = f" — {item['desc']}" if item["desc"] else ""
    new_line  = f"- [x] {item['idx']}. [{decision}] **{item['title']}**{desc_part}"

    lines[target] = new_line
    return "\n".join(lines)


# ── 파일 탐색 ──────────────────────────────────────────────────────────────────

def find_pending_files() -> list[Path]:
    """triage: pending 인 파일 목록 반환 (날짜 내림차순)."""
    if not TRIAGE_DIR.exists():
        return []

    pending = []
    for md in sorted(TRIAGE_DIR.glob("*.md"), reverse=True):
        text = md.read_text(encoding="utf-8", errors="replace")
        meta, _ = parse_frontmatter(text)
        if meta.get("triage", "").strip() == "pending":
            pending.append(md)

    return pending


def find_today_file() -> Optional[Path]:
    today_str = date.today().strftime("%Y-%m-%d")
    candidate = TRIAGE_DIR / f"{today_str}-triage.md"
    if candidate.exists():
        return candidate

    # 오늘 날짜가 없으면 가장 최근 pending 파일 반환
    pending = find_pending_files()
    return pending[0] if pending else None


# ── 자동 분류 ──────────────────────────────────────────────────────────────────

def auto_classify(item: dict) -> str:
    """키워드 매칭으로 항목을 자동 분류한다."""
    text = (item["title"] + " " + item["desc"]).lower()

    scores: dict[str, int] = {d: 0 for d in ("approve", "implement", "queue", "archive")}
    for decision, keywords in AUTO_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                scores[decision] += 1

    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        return "queue"  # 기본값
    return best


# ── CL 태스크 생성 ──────────────────────────────────────────────────────────────

def next_cl_id(tasks: list[dict]) -> str:
    """user_checklist.json의 tasks 목록에서 다음 CL-XXX ID를 결정한다."""
    max_num = 0
    for t in tasks:
        m = re.match(r"CL-(\d+)", str(t.get("id", "")))
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"CL-{max_num + 1:03d}"


def create_cl_task(item: dict, triage_file: Path) -> dict:
    """implement 항목에서 CL-XXX 태스크 dict를 생성한다."""
    return {
        "id": "__PLACEHOLDER__",
        "title": item["title"],
        "description": item["desc"] or "",
        "priority": "P1",
        "category": "개발",
        "status": "pending",
        "added": date.today().isoformat(),
        "source": f"triage:{triage_file.name}",
        "refs": [],
    }


def append_cl_tasks(new_tasks: list[dict]) -> list[str]:
    """체크리스트에 새 태스크를 추가한다. 생성된 ID 목록 반환.

    checklist_store가 정본과 미러를 함께 갱신한다 — 예전엔 정본만 써서 대시보드가
    보는 미러가 점점 어긋났다. 체크리스트를 읽지 못하면 아무것도 쓰지 않고 건너뛴다.
    """
    try:
        data = checklist_store.load()
    except checklist_store.ChecklistUnavailable as exc:
        print(f"  [WARN] 체크리스트를 읽을 수 없음 — 태스크 생성 건너뜀: {exc}")
        return []

    tasks  = data.get("tasks", [])
    created: list[str] = []

    for task in new_tasks:
        task["id"] = next_cl_id(tasks)
        tasks.append(task)
        created.append(task["id"])
        print(f"  [CL] 태스크 생성: {task['id']} — {task['title']}")

    data["tasks"] = tasks
    meta = data.setdefault("meta", {})
    meta["last_completed"] = meta.get("last_completed", "")
    checklist_store.save(data)  # last_updated는 store가 찍는다
    return created


# ── 감사 로그 ──────────────────────────────────────────────────────────────────

def append_audit_log(triage_file: Path, decisions: list[dict]) -> None:
    """ObsidianVault/00_System/triage-audit-log.md에 트리아지 결과를 기록한다."""
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

    if not AUDIT_LOG.exists():
        AUDIT_LOG.write_text(
            "---\ntitle: Knowledge Triage Audit Log\ntags: [system, triage]\n---\n\n"
            "# Knowledge Triage 감사 로그\n\n",
            encoding="utf-8",
        )

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"\n## {now_str} — {triage_file.name}\n"]
    for d in decisions:
        cl_ref = f" → {d.get('cl_id')}" if d.get("cl_id") else ""
        lines.append(f"- [{d['decision']}]{cl_ref} **{d['title']}**")
    lines.append("")

    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  [AUDIT] {len(decisions)}건 기록 → {AUDIT_LOG.name}")


# ── 메인 처리 ──────────────────────────────────────────────────────────────────

def process_file(
    triage_path: Path,
    decisions_input: Optional[list[str]],
    auto: bool,
    dry_run: bool,
) -> int:
    """트리아지 파일 하나를 처리한다. 반환: 처리된 항목 수."""
    text = triage_path.read_text(encoding="utf-8", errors="replace")
    meta, body = parse_frontmatter(text)

    print(f"\n파일: {triage_path.name}")
    print(f"상태: {meta.get('triage', '?')}  |  카드: {meta.get('card_count', '?')}개")

    items     = parse_items(body)
    pending   = [it for it in items if not it["done"]]
    done_items= [it for it in items if it["done"]]

    if not pending:
        print("  → 미결정 항목 없음. 이미 모두 처리됨.")
        return 0

    print(f"\n  미결정 {len(pending)}개 / 완료 {len(done_items)}개\n")

    # 결정 목록 결정
    if decisions_input:
        if len(decisions_input) == 1 and decisions_input[0] in VALID_DECISIONS:
            # 동일 결정을 모든 항목에 적용
            resolved = [decisions_input[0]] * len(pending)
        elif len(decisions_input) == len(pending):
            resolved = decisions_input
        else:
            print(
                f"  [오류] --decide 값 수({len(decisions_input)})가 "
                f"미결정 항목 수({len(pending)})와 다릅니다.\n"
                f"  단일 값(예: --decide queue)이면 전체 적용됩니다."
            )
            return -1
    elif auto:
        resolved = [auto_classify(it) for it in pending]
    else:
        # 결정 없음 — 항목 목록만 출력
        for it in pending:
            print(f"  {it['idx']}. [{it['decision'] or '미결정'}] {it['title']}")
            if it["desc"]:
                print(f"      {it['desc'][:80]}")
        print(
            "\n  결정을 적용하려면:\n"
            "    --decide approve,implement,queue,...  (항목 순서대로)\n"
            "    --decide queue                        (전체 동일 결정)\n"
            "    --auto                                (키워드 자동 분류)"
        )
        return 0

    # 결정 유효성 검증
    for val in resolved:
        if val not in VALID_DECISIONS:
            print(f"  [오류] 유효하지 않은 결정값: '{val}'. 허용값: {VALID_DECISIONS}")
            return -1

    # 결정 적용
    audit_records: list[dict] = []
    new_cl_tasks:  list[dict] = []

    print("  적용 결과:")
    for item, decision in zip(pending, resolved):
        print(f"    {item['idx']}. [{decision}] {item['title']}")
        audit_entry = {"title": item["title"], "decision": decision}

        if decision == "implement":
            cl_task = create_cl_task(item, triage_path)
            new_cl_tasks.append(cl_task)
            audit_entry["cl_pending"] = True

        audit_records.append(audit_entry)

    if dry_run:
        print("\n  [DRY-RUN] 파일 변경 없음.")
        if new_cl_tasks:
            print(f"  [DRY-RUN] CL 태스크 생성 예정: {len(new_cl_tasks)}개")
        return len(pending)

    # CL 태스크 생성
    if new_cl_tasks:
        created_ids = append_cl_tasks(new_cl_tasks)
        for entry, cl_id in zip(
            [e for e in audit_records if e.get("cl_pending")],
            created_ids,
        ):
            entry["cl_id"] = cl_id
            del entry["cl_pending"]

    # 트리아지 파일 body 업데이트
    updated_body = body
    for item, decision in zip(pending, resolved):
        if decision == "skip":
            continue
        updated_body = apply_decision_to_body(updated_body, item, decision)

    # 프론트매터 업데이트
    # pending과 resolved는 같은 순서이므로 id() 기반 매핑으로 중복 dict 문제 방지
    skip_ids = {id(p) for p, d in zip(pending, resolved) if d == "skip"}
    all_done = not any(id(it) in skip_ids for it in items if not it["done"])
    fm_updates: dict = {}
    if all_done and not any(d == "skip" for d in resolved):
        fm_updates["triage"] = "done"
        fm_updates["triaged_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        fm_updates["status"] = "processed"

    # 파일 쓰기
    new_text = rewrite_frontmatter(text, fm_updates) if fm_updates else text
    # body 부분만 교체
    new_text = re.sub(
        r"(^---\s*\n.*?\n---\s*\n)(.*)",
        lambda m: m.group(1) + updated_body,
        new_text,
        flags=re.DOTALL,
    )
    triage_path.write_text(new_text, encoding="utf-8")
    print(f"\n  [OK] {triage_path.name} 업데이트 완료")
    if fm_updates.get("triage") == "done":
        print("       → triage: done 으로 완료 처리")

    # 감사 로그
    append_audit_log(triage_path, audit_records)

    return len([d for d in resolved if d != "skip"])


# ── CLI ────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Knowledge Triage Gate — daily-plus-triage 항목 분류 및 처리",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="pending 트리아지 파일 목록 출력",
    )
    parser.add_argument(
        "--today",
        action="store_true",
        help="오늘(또는 가장 최근) pending 파일 처리",
    )
    parser.add_argument(
        "--file", "-f",
        type=Path,
        metavar="PATH",
        help="처리할 트리아지 파일 경로",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="모든 pending 파일 처리",
    )
    parser.add_argument(
        "--decide", "-d",
        type=str,
        metavar="DECISIONS",
        help="콤마 구분 결정값 (항목 순서대로) 또는 단일 값(전체 적용)",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="키워드 기반 자동 분류",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 파일 변경 없이 결과 미리보기",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    decisions_input: Optional[list[str]] = None
    if args.decide:
        raw = [d.strip().lower() for d in args.decide.split(",")]
        decisions_input = raw

    # --list 또는 인수 없음 → 목록 출력
    if args.list or (not args.today and not args.file and not args.all):
        pending = find_pending_files()
        if not pending:
            print("pending 트리아지 파일 없음.")
            return 0

        print(f"pending 트리아지 파일 {len(pending)}개:\n")
        for p in pending:
            text = p.read_text(encoding="utf-8", errors="replace")
            meta, body = parse_frontmatter(text)
            items   = parse_items(body)
            undone  = [it for it in items if not it["done"]]
            print(f"  {p.name}  ({len(undone)}/{len(items)} 미결정)")
            for it in undone[:3]:
                print(f"    {it['idx']}. {it['title'][:60]}")
            if len(undone) > 3:
                print(f"    ... 외 {len(undone) - 3}개")

        print(
            f"\n처리하려면:\n"
            f"  python knowledge_triage.py --today --decide approve,queue,...\n"
            f"  python knowledge_triage.py --today --auto"
        )
        return 0

    # 대상 파일 결정
    targets: list[Path] = []
    if args.file:
        if not args.file.exists():
            print(f"[오류] 파일 없음: {args.file}")
            return 1
        targets = [args.file]
    elif args.today:
        f = find_today_file()
        if not f:
            print("[오류] 처리할 pending 파일 없음.")
            return 1
        targets = [f]
    elif args.all:
        targets = find_pending_files()
        if not targets:
            print("pending 트리아지 파일 없음.")
            return 0

    total = 0
    for target in targets:
        result = process_file(target, decisions_input, args.auto, args.dry_run)
        if result == -1:
            return 1
        total += result

    if total > 0:
        print(f"\n총 {total}개 항목 처리 완료.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
