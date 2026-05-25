#!/usr/bin/env python3
"""
Migration Crosscheck — G드라이브 → ObsidianVault 이관 갭 분석

G:/내 드라이브/JH-SHARED/ 의 파일 목록을 스캔하고,
gdrive_agent_room_migrator.py의 이관 로그와 비교하여
미이관 파일 목록을 ObsidianVault/00_System/migration-gap-report.md에 저장한다.

주의: 파일을 이동/복사하지 않는다. 갭 리포트 생성만 수행한다.

사용법:
    python migration_crosscheck.py              # 기본 실행
    python migration_crosscheck.py --verbose   # 이관 완료 파일도 출력
    python migration_crosscheck.py --dry-run   # 리포트 파일 저장 없이 콘솔 출력만
"""

import argparse
import json
import os
import re
import sys
import textwrap
from datetime import datetime
from pathlib import Path

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
_ROOT       = Path(__file__).parent.parent
VAULT_BASE  = _ROOT / "ObsidianVault"
GDRIVE_ROOT = Path("G:/내 드라이브/JH-SHARED")

# gdrive_agent_room_migrator.py 의 이관 로그
MIGRATION_LOG = VAULT_BASE / "10_AgentBus" / "gdrive-migration-log.json"

# 갭 리포트 출력 경로
GAP_REPORT = VAULT_BASE / "00_System" / "migration-gap-report.md"

# G드라이브 탐색 대상 폴더 (migrator의 MIGRATION_MAP 키와 동일)
GDRIVE_SCAN_FOLDERS = [
    "00_SYSTEM",
    "01_AGENT_ROOM",
    "02_HANDOFF",
    "03_LOGS",
    "04_DAILY_REPORTS",
    "05_TASK_LOCKS",
    "06_TASK_LOGS",
    "99_ARCHIVE",
]

# ObsidianVault 내 이관 완료 디렉터리 (migrator의 MIGRATION_MAP 값과 동일)
VAULT_DEST_MAP = {
    "00_SYSTEM":       VAULT_BASE / "00_System" / "gdrive-system",
    "01_AGENT_ROOM":   VAULT_BASE / "10_AgentBus" / "imported-agent-room",
    "02_HANDOFF":      VAULT_BASE / "10_AgentBus" / "handoffs",
    "03_LOGS":         VAULT_BASE / "05_Logs" / "gdrive-imported",
    "04_DAILY_REPORTS": VAULT_BASE / "05_Logs" / "daily-reports-gdrive",
    "05_TASK_LOCKS":   VAULT_BASE / "05_Logs" / "task-locks-gdrive",
    "06_TASK_LOGS":    VAULT_BASE / "05_Logs" / "task-logs-gdrive",
    "99_ARCHIVE":      VAULT_BASE / "09_Archive" / "gdrive-archive",
}

# .claudeignore 경로
CLAUDEIGNORE = _ROOT / ".claudeignore"

# 제외 패턴 (탐색할 필요 없는 확장자/파일명)
SKIP_EXTENSIONS = {".pyc", ".pyo", ".tmp", ".DS_Store"}
SKIP_NAMES      = {".gitkeep", ".gitignore", "Thumbs.db"}
# ─────────────────────────────────────────────────────────────────────────────


def load_migration_log() -> set[str]:
    """
    gdrive-migration-log.json에서 이미 이관된 소스 경로 집합을 반환한다.
    파일이 없으면 빈 집합 반환.
    """
    if not MIGRATION_LOG.exists():
        print(f"[WARN] 이관 로그 없음: {MIGRATION_LOG}")
        print("       gdrive_agent_room_migrator.py를 먼저 실행하거나 --skip-log 옵션을 사용하세요.")
        return set()

    try:
        data = json.loads(MIGRATION_LOG.read_text(encoding="utf-8"))
        migrated = {entry["src"] for entry in data.get("migrated", []) if "src" in entry}
        print(f"[INFO] 이관 로그 로드: {len(migrated)}개 완료 기록")
        return migrated
    except (json.JSONDecodeError, OSError) as e:
        print(f"[WARN] 이관 로그 파싱 실패: {e}")
        return set()


def scan_gdrive_folder(folder_name: str) -> list[dict]:
    """
    G드라이브의 특정 폴더를 재귀 스캔하여 파일 정보 목록을 반환한다.
    반환: [{"path": str, "rel": str, "size": int, "folder": str}, ...]
    """
    src = GDRIVE_ROOT / folder_name
    if not src.exists():
        print(f"  [SKIP] 경로 없음: {src}")
        return []

    files = []
    for item in src.rglob("*"):
        if item.is_dir():
            continue
        if item.suffix.lower() in SKIP_EXTENSIONS:
            continue
        if item.name in SKIP_NAMES:
            continue

        try:
            size = item.stat().st_size
        except OSError:
            size = -1

        files.append({
            "path": str(item),
            "rel":  str(item.relative_to(GDRIVE_ROOT)),
            "size": size,
            "folder": folder_name,
        })

    return files


def check_vault_dest_exists(folder_name: str, rel_path: str) -> bool:
    """
    ObsidianVault의 대응 이관 경로에 파일이 존재하는지 확인한다.
    rel_path는 GDRIVE_ROOT 기준 상대경로.
    """
    dest_base = VAULT_DEST_MAP.get(folder_name)
    if dest_base is None:
        return False

    # rel_path = "01_AGENT_ROOM/subdir/file.md"
    # 폴더명 prefix 제거 → "subdir/file.md"
    parts = Path(rel_path).parts
    if len(parts) > 1:
        sub_rel = Path(*parts[1:])
    else:
        sub_rel = Path(parts[0])

    dest_file = dest_base / sub_rel
    return dest_file.exists()


def verify_claudeignore() -> dict:
    """
    .claudeignore를 읽어 G드라이브 탐색 차단 여부를 검증한다.
    반환: {"ok": bool, "gdrive_blocked": bool, "issues": [str]}
    """
    result = {"ok": True, "gdrive_blocked": False, "issues": []}

    if not CLAUDEIGNORE.exists():
        result["ok"] = False
        result["issues"].append(".claudeignore 파일이 없습니다.")
        return result

    content = CLAUDEIGNORE.read_text(encoding="utf-8")

    # G드라이브 관련 차단 패턴 확인
    gdrive_indicators = [
        r"G[:\\\/]",
        r"JH.SHARED",
        r"gdrive",
        r"내\s*드라이브",
    ]
    gdrive_blocked = any(
        re.search(pat, content, re.IGNORECASE) for pat in gdrive_indicators
    )
    result["gdrive_blocked"] = gdrive_blocked

    # ObsidianVault/01_RAW 차단 확인 (원시 수집 데이터)
    raw_blocked = "ObsidianVault/01_RAW" in content or "01_RAW/" in content
    if not raw_blocked:
        result["issues"].append("ObsidianVault/01_RAW/ 가 .claudeignore에 명시되지 않았습니다.")

    # 보안 패턴 확인
    if ".env" not in content:
        result["issues"].append(".env 파일이 .claudeignore에 포함되지 않았습니다.")

    if result["issues"]:
        result["ok"] = False

    return result


def build_gap_report(
    all_files: list[dict],
    migrated_paths: set[str],
    claudeignore_result: dict,
    verbose: bool = False,
) -> tuple[str, list[dict], list[dict]]:
    """
    갭 리포트 마크다운을 생성한다.
    반환: (report_text, not_migrated_list, migrated_list)
    """
    not_migrated = []
    migrated     = []

    for f in all_files:
        # 이관 로그 기반 체크 (1차)
        in_log = f["path"] in migrated_paths
        # Vault 대상 경로 존재 여부 체크 (2차)
        in_vault = check_vault_dest_exists(f["folder"], f["rel"])

        if in_log or in_vault:
            migrated.append(f)
        else:
            not_migrated.append(f)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    total   = len(all_files)
    done    = len(migrated)
    gap     = len(not_migrated)

    # .claudeignore 상태 요약
    ci_status = "정상" if claudeignore_result["ok"] else "경고"
    ci_gdrive = "차단됨" if claudeignore_result["gdrive_blocked"] else "미차단 — G드라이브 노출 위험"
    ci_issues = "\n".join(
        f"  - {issue}" for issue in claudeignore_result["issues"]
    ) or "  - 없음"

    # 미이관 파일을 폴더별로 분류
    by_folder: dict[str, list[dict]] = {}
    for f in not_migrated:
        by_folder.setdefault(f["folder"], []).append(f)

    # 미이관 목록 섹션 생성
    gap_sections = []
    for folder in sorted(by_folder.keys()):
        items = by_folder[folder]
        lines = [f"### {folder} ({len(items)}개 미이관)\n"]
        for item in sorted(items, key=lambda x: x["rel"]):
            size_str = f"{item['size']:,}B" if item["size"] >= 0 else "크기 불명"
            lines.append(f"- `{item['rel']}` ({size_str})")
        gap_sections.append("\n".join(lines))

    gap_section_text = "\n\n".join(gap_sections) if gap_sections else "_미이관 파일 없음 — 이관 완료_"

    # 이관 완료 목록 (verbose 시)
    done_section_text = ""
    if verbose and migrated:
        done_lines = [f"### 이관 완료 목록 ({len(migrated)}개)\n"]
        for f in sorted(migrated, key=lambda x: x["rel"]):
            done_lines.append(f"- `{f['rel']}`")
        done_section_text = "\n\n## 이관 완료 파일\n\n" + "\n".join(done_lines)

    report = textwrap.dedent(f"""
        ---
        title: G드라이브 Migration Gap Report
        generated_at: {now_str}
        gdrive_root: "{GDRIVE_ROOT}"
        vault_root: "{VAULT_BASE}"
        tags: [system, migration, gap-report]
        ---

        # G드라이브 → ObsidianVault 이관 갭 리포트

        > 생성: `migration_crosscheck.py` — {now_str}
        > 이 파일은 실제 이동/복사 없이 갭만 분석합니다.

        ## 요약

        | 항목 | 수치 |
        |------|------|
        | G드라이브 전체 파일 | {total}개 |
        | 이관 완료 | {done}개 |
        | **미이관 (갭)** | **{gap}개** |
        | 이관율 | {done / total * 100:.1f}% |

        ## .claudeignore 검증

        | 항목 | 상태 |
        |------|------|
        | 전체 상태 | {ci_status} |
        | G드라이브 탐색 차단 | {ci_gdrive} |

        **이슈:**
        {ci_issues}

        ## 미이관 파일 목록

        {gap_section_text}
        {done_section_text}

        ---
        *다음 단계: `python gdrive_agent_room_migrator.py` 실행으로 이관 진행*
        *이관 완료 후 G드라이브는 읽기 전용 아카이브로 전환*
    """).lstrip()

    return report, not_migrated, migrated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="G드라이브 → ObsidianVault 이관 갭 분석 (파일 이동 없음)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="이관 완료 파일 목록도 리포트에 포함",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="리포트 파일을 저장하지 않고 콘솔 출력만",
    )
    parser.add_argument(
        "--skip-log",
        action="store_true",
        help="이관 로그 파일 없어도 Vault 경로 존재 여부만으로 체크",
    )
    parser.add_argument(
        "--folder",
        type=str,
        default=None,
        metavar="FOLDER",
        help="특정 폴더만 체크 (예: 01_AGENT_ROOM)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    print(f"[INFO] G드라이브 경로: {GDRIVE_ROOT}")
    print(f"[INFO] Vault 경로:    {VAULT_BASE}")

    if not GDRIVE_ROOT.exists():
        print(f"[ERROR] G드라이브 경로에 접근할 수 없습니다: {GDRIVE_ROOT}")
        print("        G드라이브가 마운트되어 있는지 확인하세요.")
        return 1

    # ── 이관 로그 로드 ────────────────────────────────────────────────────────
    migrated_paths = set() if args.skip_log else load_migration_log()

    # ── G드라이브 스캔 ────────────────────────────────────────────────────────
    scan_folders = [args.folder] if args.folder else GDRIVE_SCAN_FOLDERS
    all_files: list[dict] = []

    print(f"\n[SCAN] G드라이브 스캔 시작: {len(scan_folders)}개 폴더")
    for folder in scan_folders:
        print(f"  → {folder} ...", end=" ")
        files = scan_gdrive_folder(folder)
        print(f"{len(files)}개 파일")
        all_files.extend(files)

    print(f"\n[INFO] 총 {len(all_files)}개 파일 발견")

    if not all_files:
        print("[WARN] G드라이브에서 파일을 찾을 수 없습니다.")
        print("       G드라이브 연결 상태 및 경로를 확인하세요.")
        return 0

    # ── .claudeignore 검증 ────────────────────────────────────────────────────
    print(f"\n[CHECK] .claudeignore 검증 중...")
    ci_result = verify_claudeignore()
    status_icon = "OK" if ci_result["ok"] else "WARN"
    print(f"  [{status_icon}] G드라이브 차단: {ci_result['gdrive_blocked']}")
    if ci_result["issues"]:
        for issue in ci_result["issues"]:
            print(f"  [WARN] {issue}")

    # ── 갭 분석 ──────────────────────────────────────────────────────────────
    print(f"\n[ANALYZE] 이관 갭 분석 중...")
    report_text, not_migrated, migrated = build_gap_report(
        all_files, migrated_paths, ci_result, verbose=args.verbose
    )

    gap   = len(not_migrated)
    total = len(all_files)
    done  = len(migrated)
    pct   = done / total * 100 if total > 0 else 0.0

    print(f"  전체: {total}  완료: {done}  미이관: {gap}  이관율: {pct:.1f}%")

    if gap > 0:
        print(f"\n[GAP] 미이관 파일 {gap}개:")
        for f in not_migrated[:20]:
            print(f"  - {f['rel']}")
        if gap > 20:
            print(f"  ... 외 {gap - 20}개 (리포트 참조)")

    # ── 리포트 저장 ────────────────────────────────────────────────────────────
    if args.dry_run:
        print("\n[DRY-RUN] 리포트 내용 미리보기:")
        print("─" * 60)
        print(report_text[:2000])
        if len(report_text) > 2000:
            print(f"... (총 {len(report_text)}자)")
        print("─" * 60)
        print("[DRY-RUN] 파일 저장 생략")
    else:
        GAP_REPORT.parent.mkdir(parents=True, exist_ok=True)
        GAP_REPORT.write_text(report_text, encoding="utf-8")
        print(f"\n[DONE] 갭 리포트 저장 완료: {GAP_REPORT}")

    return 0 if gap == 0 else 2  # exit 2 = gap exists (경고)


if __name__ == "__main__":
    sys.exit(main())
