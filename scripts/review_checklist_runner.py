#!/usr/bin/env python3
"""
review_checklist_runner.py — 검수 자동화 CLI
IMPL-RA-01~06: 변경 감지, 이슈 기록, OPEN 필터, 세션 스냅샷, 로그 append, CLI 통합
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
VAULT = ROOT / "ObsidianVault"
UPGRADE = VAULT / "00_UPGRADE"
REVIEW_ISSUES = UPGRADE / "review-issues.md"
UPGRADE_LOG = UPGRADE / "upgrade-log.md"
SESSION_RESUME = UPGRADE / "session-resume.md"


# IMPL-RA-01: git diff --name-only HEAD로 변경 파일 감지
def get_changed_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        capture_output=True, text=True, cwd=ROOT
    )
    changed = [f.strip() for f in result.stdout.splitlines() if f.strip()]

    untracked_result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        capture_output=True, text=True, cwd=ROOT
    )
    untracked = [f.strip() for f in untracked_result.stdout.splitlines() if f.strip()]
    return changed + untracked


# IMPL-RA-03: review-issues.md OPEN 항목 필터링
# "## OPEN 이슈" 섹션의 데이터 행을 반환하되, "## 상태 변경 기록"에서 RESOLVED인 ID는 제외
def get_open_issues() -> list[str]:
    if not REVIEW_ISSUES.exists():
        return []
    content = REVIEW_ISSUES.read_text(encoding="utf-8")
    lines = content.splitlines()

    # 상태 변경 기록에서 RESOLVED ID 수집
    resolved_ids: set[str] = set()
    in_status_section = False
    for line in lines:
        stripped = line.strip()
        if stripped == "## 상태 변경 기록":
            in_status_section = True
            continue
        if in_status_section:
            if stripped.startswith("## "):
                break
            if stripped.startswith("|") and "RESOLVED" in stripped:
                # ID 컬럼은 두 번째 | 사이에 있음 (| 날짜 | 이슈 ID | 상태 ...)
                parts = [p.strip() for p in stripped.split("|")]
                if len(parts) >= 4:
                    # parts[0]='', parts[1]=날짜, parts[2]=이슈ID, parts[3]=상태
                    rev_ids = re.findall(r"REV-\d{8}-\d{3}", parts[2])
                    resolved_ids.update(rev_ids)

    in_open_section = False
    results: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == "## OPEN 이슈":
            in_open_section = True
            continue
        if in_open_section:
            if stripped.startswith("## "):
                break
            if stripped.startswith("|") and not re.match(r"^\|\s*[-|]+\s*$", stripped) and not stripped.startswith("| ID"):
                rev_match = re.search(r"REV-\d{8}-\d{3}", stripped)
                if rev_match and rev_match.group() in resolved_ids:
                    continue
                results.append(stripped)
    return results


def resolve_issue(rev_id: str, note: str = "-", resolver: str = "Claude") -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    row = f"| {today} | {rev_id} | RESOLVED | {resolver} | {note} |\n"
    if not REVIEW_ISSUES.exists():
        return
    content = REVIEW_ISSUES.read_text(encoding="utf-8")
    status_header = "## 상태 변경 기록"
    if status_header in content:
        pos = content.find(status_header)
        table_start = content.find("\n|", pos)
        if table_start != -1:
            next_row = content.find("\n", table_start + 1)
            if next_row != -1:
                content = content[:next_row + 1] + row + content[next_row + 1:]
            else:
                content += "\n" + row
        else:
            content += "\n" + row
    else:
        content += f"\n\n{status_header}\n\n| 날짜 | 이슈 ID | 상태 | 기록자 | 내용 |\n|------|---------|------|--------|------|\n{row}"
    REVIEW_ISSUES.write_text(content, encoding="utf-8")


# IMPL-RA-02: review-issues.md에 REV- 항목 자동 append
def append_review_issue(severity: str, description: str, project: str = "-", target: str = "-", reporter: str = "Claude", followup: str = "-") -> str:
    today_str = datetime.now().strftime("%Y%m%d")
    today_display = datetime.now().strftime("%Y-%m-%d")

    existing_ids: list[str] = []
    if REVIEW_ISSUES.exists():
        existing_ids = re.findall(rf"REV-{today_str}-(\d{{3}})", REVIEW_ISSUES.read_text(encoding="utf-8"))
    n = len(existing_ids) + 1
    rev_id = f"REV-{today_str}-{n:03d}"

    row = f"| {rev_id} | {today_display} | {project} | {target} | {severity} | {reporter} | {description} | {followup} |\n"

    if not REVIEW_ISSUES.exists():
        REVIEW_ISSUES.write_text(
            "---\ntype: review-log\nappend_only: true\n---\n\n"
            "# review-issues - 검수 이슈 장부\n\n"
            "## OPEN 이슈\n\n"
            "| ID | 날짜 | 프로젝트 | 대상 | 등급 | 발견자 | 요약 | 후속 조치 |\n"
            "|----|------|----------|------|------|--------|------|----------|\n",
            encoding="utf-8"
        )

    content = REVIEW_ISSUES.read_text(encoding="utf-8")
    if "## OPEN 이슈" in content:
        # Find the next ## section after OPEN 이슈, insert row before it
        open_pos = content.find("## OPEN 이슈")
        next_section = content.find("\n## ", open_pos + 1)
        if next_section != -1:
            new_content = content[:next_section] + row + content[next_section:]
        else:
            new_content = content.rstrip("\n") + "\n" + row
        REVIEW_ISSUES.write_text(new_content, encoding="utf-8")
    else:
        with open(REVIEW_ISSUES, "a", encoding="utf-8") as f:
            f.write(row)

    return rev_id


# IMPL-RA-05: upgrade-log.md 한 줄 요약 자동 append (맨 위 새 섹션)
def append_upgrade_log(summary: str, agent: str = "Claude") -> None:
    if not UPGRADE_LOG.exists():
        return
    content = UPGRADE_LOG.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    new_entry = (
        f"\n---\n\n## {today} | 자동 기록\n\n"
        f"| 항목 | 결과 | 담당 |\n"
        f"|------|------|------|\n"
        f"| {summary} | ✅ 완료 | {agent} |\n"
    )
    # Insert after frontmatter block (first ---...--- block)
    fm_end = content.find("\n---\n", content.find("---") + 3)
    if fm_end != -1:
        insert_pos = content.find("\n", fm_end + 1)
        if insert_pos == -1:
            insert_pos = len(content)
        content = content[:insert_pos] + new_entry + content[insert_pos:]
    else:
        content += new_entry
    UPGRADE_LOG.write_text(content, encoding="utf-8")


# IMPL-RA-04: session-resume.md 자동 스냅샷
def snapshot_session_resume(note: str) -> None:
    if not SESSION_RESUME.exists():
        print("  ⚠️  session-resume.md 없음 — 스냅샷 건너뜀")
        return
    content = SESSION_RESUME.read_text(encoding="utf-8")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    marker = "## 마지막 자동 스냅샷"
    snapshot_block = f"\n{marker}\n{now_str} — {note}\n"
    if marker in content:
        content = re.sub(
            rf"\n{re.escape(marker)}\n.*?(?=\n##|\Z)",
            snapshot_block,
            content,
            flags=re.DOTALL
        )
    else:
        content += snapshot_block
    SESSION_RESUME.write_text(content, encoding="utf-8")


# --- CLI Commands ---

def cmd_start(args):
    print("=" * 52)
    print("  세션 시작 체크리스트")
    print("=" * 52)

    # 1. preflight
    print("\n[1/5] preflight_check.py 실행 중...")
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(ROOT / "scripts" / "preflight_check.py")],
        capture_output=True, text=True, cwd=ROOT
    )
    combined = result.stdout + result.stderr
    if "bucky_os_gate: ok" in combined:
        print("  ✅ bucky_os_gate: ok")
    else:
        print("  ⚠️  preflight 경고 — 직접 확인 필요")
        print(combined[-600:] if combined else "(출력 없음)")

    # 2. session-resume 요약
    print("\n[2/5] session-resume.md (상위 20줄):")
    if SESSION_RESUME.exists():
        for line in SESSION_RESUME.read_text(encoding="utf-8").splitlines()[:20]:
            print(f"  {line}")
    else:
        print("  (파일 없음)")

    # 3. 변경 파일 (IMPL-RA-01)
    print("\n[3/5] 변경 파일 목록:")
    changed = get_changed_files()
    if changed:
        for f in changed:
            print(f"  M  {f}")
    else:
        print("  ✅ 변경 없음")

    # 4. OPEN 이슈 (IMPL-RA-03)
    print("\n[4/5] OPEN 이슈:")
    open_issues = get_open_issues()
    if open_issues:
        for issue in open_issues:
            print(f"  ⚠️  {issue}")
    else:
        print("  ✅ OPEN 이슈 없음")

    # 5. 안내
    print("\n[5/5] 오늘 작업 범위를 확정하고 시작하세요.")
    print("=" * 52)


def cmd_close(args):
    note = args.note or "세션 종료"
    print("=" * 52)
    print("  세션 종료 체크리스트")
    print("=" * 52)

    # IMPL-RA-04
    snapshot_session_resume(note)
    print(f"\n[1/3] session-resume.md 스냅샷 완료: {note}")

    # IMPL-RA-05
    if args.summary:
        append_upgrade_log(args.summary, agent=args.agent or "Claude")
        print(f"[2/3] upgrade-log.md 기록 완료: {args.summary}")
    else:
        print("[2/3] --summary 없음, upgrade-log 기록 건너뜀")

    print("[3/3] 세션 종료 완료")
    print("=" * 52)


def cmd_issues(args):
    open_issues = get_open_issues()
    if open_issues:
        print(f"OPEN 이슈 {len(open_issues)}건:")
        for issue in open_issues:
            print(f"  {issue}")
    else:
        print("✅ OPEN 이슈 없음")


def cmd_resolve(args):
    resolve_issue(rev_id=args.id, note=args.note or "-", resolver=args.resolver or "Claude")
    print(f"✅ {args.id} → RESOLVED")


def cmd_add_issue(args):
    # IMPL-RA-02
    rev_id = append_review_issue(
        severity=args.severity,
        description=args.description,
        project=args.project or "-",
        target=args.target or "-",
        reporter=args.reporter or "Claude",
        followup=args.followup or "-",
    )
    print(f"이슈 등록 완료: {rev_id}")


def main():
    parser = argparse.ArgumentParser(
        prog="review_checklist_runner",
        description="검수 자동화 CLI (IMPL-RA-01~06)"
    )
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("start", help="세션 시작 체크리스트 실행")

    p_close = sub.add_parser("close", help="세션 종료 스냅샷 + 로그 기록")
    p_close.add_argument("--note", help="스냅샷 메모 (기본: '세션 종료')")
    p_close.add_argument("--summary", help="upgrade-log.md에 기록할 완료 요약")
    p_close.add_argument("--agent", help="담당 에이전트 (기본: Claude)")

    sub.add_parser("issues", help="OPEN 이슈 목록 출력 (RESOLVED 제외)")

    p_resolve = sub.add_parser("resolve", help="이슈를 RESOLVED로 상태 변경")
    p_resolve.add_argument("--id", required=True, help="REV-YYYYMMDD-NNN")
    p_resolve.add_argument("--note", help="해결 내용")
    p_resolve.add_argument("--resolver", help="처리자 (기본: Claude)")

    p_add = sub.add_parser("add-issue", help="review-issues.md에 이슈 추가 (IMPL-RA-02)")
    p_add.add_argument("--severity", required=True, choices=["CRITICAL", "WARN", "INFO"])
    p_add.add_argument("--description", required=True, help="이슈 요약")
    p_add.add_argument("--project", help="프로젝트명")
    p_add.add_argument("--target", help="파일:라인 등 대상")
    p_add.add_argument("--reporter", help="발견자 (기본: Claude)")
    p_add.add_argument("--followup", help="후속 조치")

    args = parser.parse_args()

    dispatch = {
        "start": cmd_start,
        "close": cmd_close,
        "issues": cmd_issues,
        "resolve": cmd_resolve,
        "add-issue": cmd_add_issue,
    }

    if args.cmd in dispatch:
        dispatch[args.cmd](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
