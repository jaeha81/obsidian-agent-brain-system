"""
sync_system_enhance.py
──────────────────────
PostToolUse 훅으로 Write/Edit 직후 자동 실행.
stdin에서 Claude Code 훅 페이로드를 읽고,
career-strategy 파일이 수정됐을 때만 system_enhance.json 재생성 + git push.

수동 실행: python scripts/sync_system_enhance.py --force
"""

import sys, json, os, re, subprocess
from datetime import date, datetime
from pathlib import Path

ROOT   = Path(__file__).parent.parent
VAULT  = ROOT / "ObsidianVault"
STRAT  = VAULT / "03_Projects" / "career-strategy"
DATA   = ROOT / "docs" / "data" / "system_enhance.json"
MARKER = ROOT / ".sync_system_enhance_ts"   # 마지막 동기화 타임스탬프

TRIGGER_PATHS = [
    "career-strategy",
    "system_enhance",
    "시스템강화",
]

# ──────────────────────────────────────────
# 1. 실행 여부 판단 (stdin 의존 없이 파일 mtime 기반)
# ──────────────────────────────────────────
def should_run(payload: dict) -> bool:
    """
    우선순위:
    1. --force 플래그
    2. stdin 페이로드에 career-strategy 경로 포함
    3. (폴백) 전략 md 파일이 마지막 동기화 타임스탬프보다 최신
    """
    if "--force" in sys.argv:
        return True

    # stdin 페이로드 확인
    if payload:
        tool_name  = payload.get("tool_name", "")
        tool_input = payload.get("tool_input", {})
        if tool_name in ("Write", "Edit"):
            file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
            if any(t in file_path for t in TRIGGER_PATHS):
                return True
        # 다른 tool이거나 trigger path 아니면 False
        if payload:
            return False

    # 폴백: stdin 없이 호출된 경우 — 파일 mtime 비교
    strat_file = STRAT / "ai_interior_career_strategy.md"
    if not strat_file.exists():
        return False
    strat_mtime = strat_file.stat().st_mtime
    if MARKER.exists():
        try:
            last_sync = datetime.fromisoformat(MARKER.read_text().strip()).timestamp()
            return strat_mtime > last_sync
        except Exception:
            return True
    return True  # 마커 없으면 첫 실행 → 항상 실행


# ──────────────────────────────────────────
# 2. 전략 마크다운 파싱
# ──────────────────────────────────────────
def load_strategy_md() -> dict:
    main_file = STRAT / "ai_interior_career_strategy.md"
    if not main_file.exists():
        return {}
    text = main_file.read_text(encoding="utf-8")

    # 작성일 추출
    m = re.search(r"\*\*작성일\*\*[:：]\s*(\d{4}-\d{2}-\d{2})", text)
    started = m.group(1) if m else str(date.today())

    # 30/90일 리뷰날짜 — 작성일 기준 +30/+90일
    from datetime import timedelta
    start_dt  = datetime.strptime(started, "%Y-%m-%d").date()
    review_30 = str(start_dt + timedelta(days=30))
    review_90 = str(start_dt + timedelta(days=90))

    # KPI 체크박스 파싱 (- [x] / - [ ])
    kpi_pattern = re.compile(r"-\s*\[([xX ])\]\s*(.+)")
    kpis_raw = kpi_pattern.findall(text)

    # 단계 파싱
    phase_pattern = re.compile(
        r"###\s*(1단계|2단계|3단계)[^:：\n]*[:：]?\s*(.+?)\n"
    )
    phases_raw = phase_pattern.findall(text)

    return {
        "started":   started,
        "review_30": review_30,
        "review_90": review_90,
        "kpis_raw":  kpis_raw,
        "phases_raw": phases_raw,
        "text":      text,
    }


# ──────────────────────────────────────────
# 3. JSON 재생성
# ──────────────────────────────────────────
def build_json(md: dict, existing: dict) -> dict:
    today = str(date.today())

    # 기존 이니셔티브 로드 (없으면 기본값)
    existing_initiatives = existing.get("initiatives", [{}])
    ini = existing_initiatives[0] if existing_initiatives else {}

    # KPI — 마크다운에서 체크 상태 반영, 기존 done 값은 유지(true면 true 유지)
    kpis_raw = md.get("kpis_raw", [])
    existing_kpis = ini.get("kpis", [])
    new_kpis = []
    for i, (checked, label) in enumerate(kpis_raw):
        done_from_md = checked.lower() == "x"
        done_prev    = existing_kpis[i]["done"] if i < len(existing_kpis) else False
        new_kpis.append({
            "label": label.strip(),
            "done":  done_from_md or done_prev,
            "due":   existing_kpis[i]["due"] if i < len(existing_kpis) else "",
        })
    # 기존 kpis 수가 더 많으면 유지
    if not new_kpis and existing_kpis:
        new_kpis = existing_kpis

    # 단계 상태
    phases_map = {"1단계": 0, "2단계": 1, "3단계": 2}
    existing_phases = ini.get("phases", [
        {"label":"1단계 (1~30일): 기반 시스템 구축","status":"in_progress","start":md.get("started",today),"end":md.get("review_30","")},
        {"label":"2단계 (31~60일): 자동화 심화","status":"pending","start":md.get("review_30",""),"end":""},
        {"label":"3단계 (61~90일): 포트폴리오화","status":"pending","start":"","end":md.get("review_90","")},
    ])

    # today_tasks / week_tasks — 마크다운에서 "오늘 바로 할 일" 섹션 파싱
    today_tasks = _parse_section_list(md.get("text",""), "오늘 바로 할 일")
    week_tasks  = _parse_section_list(md.get("text",""), "이번 주 안에 끝낼 일")

    # TOP10 — 기존 데이터 유지 (마크다운 표 파싱은 복잡하므로 기존값 우선)
    top10 = ini.get("top10_priority", existing.get("top10_priority", []))

    return {
        "meta": {
            "last_updated": today,
            "version":      ini.get("version", existing.get("meta", {}).get("version", "1.0")),
        },
        "initiatives": [{
            "id":              ini.get("id", "career-strategy-v1"),
            "title":           ini.get("title", "AI 인테리어 커리어 전략 v1"),
            "category":        ini.get("category", "커리어"),
            "status":          ini.get("status", "active"),
            "started":         md.get("started", ini.get("started", today)),
            "review_30d":      md.get("review_30", ini.get("review_30d", "")),
            "review_90d":      md.get("review_90", ini.get("review_90d", "")),
            "source_doc":      "ObsidianVault/03_Projects/career-strategy/ai_interior_career_strategy.md",
            "prompt_template": "ObsidianVault/08_Templates/ai-prompts/career_strategy_prompt.md",
            "summary":         ini.get("summary", "AI 자동화 역량을 갖춘 인테리어 시공/운영 리더 목표 포지션 전략"),
            "target_position": ini.get("target_position", ""),
            "kpis":            new_kpis if new_kpis else existing_kpis,
            "phases":          existing_phases,
        }],
        "today_tasks":     today_tasks or existing.get("today_tasks", []),
        "this_week_tasks": week_tasks  or existing.get("this_week_tasks", []),
        "top10_priority":  top10,
    }


def _parse_section_list(text: str, section_title: str) -> list:
    """마크다운에서 ## 섹션 아래 - [ ] 체크리스트 또는 일반 리스트 항목 추출."""
    pattern = re.compile(
        r"##\s*" + re.escape(section_title) + r".*?\n(.*?)(?=\n##|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    m = pattern.search(text)
    if not m:
        return []
    block = m.group(1)
    items = re.findall(r"-\s*(?:\[[xX ]\]\s*)?(.+)", block)
    return [i.strip() for i in items if i.strip()]


# ──────────────────────────────────────────
# 4. Git commit + push (stash 보호 포함)
# ──────────────────────────────────────────
def run_git(args: list) -> tuple:
    """git 명령 실행 → (returncode, stdout+stderr)"""
    result = subprocess.run(
        ["git", "-C", str(ROOT)] + args,
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return result.returncode, (result.stdout + result.stderr).strip()

def git_push(changed: bool):
    if not changed:
        return

    # 1. stage + commit
    run_git(["add", "docs/data/system_enhance.json"])
    rc, out = run_git(["commit", "-m",
                        f"chore(system-enhance): 상태 자동 동기화 {date.today()}"])
    if rc != 0 and "nothing to commit" in out:
        return  # 실제 변경 없으면 종료

    # 2. unstaged 변경사항 stash (pull --rebase 실패 방지)
    _, stash_out = run_git(["stash", "--include-untracked",
                             "--message", "sync_system_enhance auto-stash"])
    stashed = "No local changes" not in stash_out

    # 3. pull --rebase
    rc, out = run_git(["pull", "--rebase", "origin", "master"])
    if rc != 0:
        # rebase 실패 시 abort 후 계속 진행
        run_git(["rebase", "--abort"])

    # 4. push
    run_git(["push", "origin", "master"])

    # 5. stash pop 복원
    if stashed:
        run_git(["stash", "pop"])


# ──────────────────────────────────────────
# 5. 메인
# ──────────────────────────────────────────
def main():
    # 훅 페이로드 읽기 (stdin JSON)
    payload = {}
    if not sys.stdin.isatty():
        try:
            payload = json.load(sys.stdin)
        except Exception:
            payload = {}

    if not should_run(payload):
        sys.exit(0)

    # 기존 JSON 로드
    existing = {}
    if DATA.exists():
        try:
            existing = json.loads(DATA.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 전략 마크다운 파싱
    md = load_strategy_md()
    if not md and not existing:
        sys.exit(0)

    # 새 JSON 생성
    new_data = build_json(md, existing)

    # 변경 여부 확인
    new_str = json.dumps(new_data, ensure_ascii=False, indent=2)
    old_str = json.dumps(existing, ensure_ascii=False, indent=2)
    changed = (new_str != old_str)

    # 저장
    DATA.write_text(new_str + "\n", encoding="utf-8")

    # 타임스탬프 기록
    MARKER.write_text(datetime.now().isoformat(), encoding="utf-8")

    # Git push
    git_push(changed)

    if changed:
        print(f"[sync_system_enhance] 동기화 완료 → {DATA.name}", flush=True)
    else:
        print(f"[sync_system_enhance] 변경 없음, 스킵", flush=True)


if __name__ == "__main__":
    main()
