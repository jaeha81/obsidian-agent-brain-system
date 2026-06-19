"""
위시켓 대시보드 데이터 갱신 스크립트.

wishket_inbox/ 폴더의 모든 JSON을 읽어 중복 제거 후
docs/wishket.html의 PROJECTS 배열을 업데이트한다.
"""
import json
import os
import re
import sys
import glob
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from wishket_filters import is_collectable_development_request

ROOT = Path(__file__).parent.parent
INBOX_DIR = ROOT / "ObsidianVault" / "10_AgentBus" / "wishket_inbox"
TRACKER_PATH = ROOT / "ObsidianVault" / "10_AgentBus" / "wishket_tracker.json"
DASHBOARD_PATH = ROOT / "docs" / "wishket.html"
PROPOSALS_DIR = ROOT / "ObsidianVault" / "03_Projects" / "wishket-proposals"
WORKFLOW_ROOT = ROOT / "ObsidianVault" / "10_AgentBus" / "wishket_dev"


def load_inbox_projects() -> list[dict]:
    projects = {}
    for path in sorted(glob.glob(str(INBOX_DIR / "*.json"))):
        try:
            items = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            continue
        for item in items:
            link = (item.get("link") or "").strip()
            if not link:
                continue
            if link not in projects:
                raw_budget = item.get("budget", "미정")
                wan = item.get("budget_wan", 0)
                budget_display = f"월 {wan}만원" if wan > 0 else raw_budget
                pid = "project-" + re.sub(r"[^a-zA-Z0-9]", "-", link.rstrip("/").split("/")[-1])
                projects[link] = {
                    "id": pid,
                    "title": item.get("title", "제목 없음"),
                    "link": link,
                    "budget": budget_display,
                    "budget_wan": wan,
                    "description": item.get("description", ""),
                    "source": item.get("source", "web"),
                    "scraped_at": item.get("scraped_at", ""),
                    "score": item.get("score", 0),
                    "priority": item.get("priority", "P4"),
                }
    result = list(projects.values())
    # Shared defense: keep only outsourced development requests, never recruiting posts.
    before = len(result)
    result = [
        p for p in result
        if is_collectable_development_request(p.get("title", ""), p.get("description", ""))
    ]
    excluded = before - len(result)
    if excluded:
        print(f"Wishket non-development/recruiting posts excluded: {excluded}")


    # 점수 없는 구 항목 동적 채점
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from wishket_scorer import score_project  # type: ignore
        for p in result:
            if not p.get("score"):
                scored = score_project(p)
                p["score"] = scored["score"]
                p["priority"] = scored["priority"]
    except Exception:
        pass
    # 점수 내림차순 정렬 (동점 시 budget_wan 폴백)
    result.sort(key=lambda p: (p["score"], p["budget_wan"]), reverse=True)
    return result


def projects_to_js(projects: list[dict]) -> str:
    lines = []
    for p in projects:
        desc = p["description"].replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
        score = p.get("score", 0)
        priority = p.get("priority", "P4")
        lines.append(
            f"  {{\n"
            f"    id: '{p['id']}',\n"
            f"    title: '{p['title'].replace(chr(39), chr(92)+chr(39))}',\n"
            f"    link: '{p['link']}',\n"
            f"    budget: '{p['budget']}',\n"
            f"    budget_wan: {p['budget_wan']},\n"
            f"    description: '{desc[:200]}',\n"
            f"    source: '{p['source']}',\n"
            f"    scraped_at: '{p['scraped_at']}',\n"
            f"    score: {score},\n"
            f"    priority: '{priority}'\n"
            f"  }}"
        )
    return "[\n" + ",\n".join(lines) + "\n]"


def load_proposals() -> dict:
    proposals = {}
    if not PROPOSALS_DIR.exists():
        return proposals
    for path in sorted(glob.glob(str(PROPOSALS_DIR / "*.md"))):
        try:
            content = Path(path).read_text(encoding="utf-8")
        except Exception:
            continue
        # Extract link from YAML frontmatter
        link_match = re.search(r'^link:\s*(.+)$', content, re.MULTILINE)
        if not link_match:
            continue
        link = link_match.group(1).strip()
        # Strip YAML frontmatter block
        fm_match = re.match(r'^---\n.*?\n---\n(.*)', content, re.DOTALL)
        body = fm_match.group(1).strip() if fm_match else content.strip()
        pid = "project-" + re.sub(r"[^a-zA-Z0-9]", "-", link.rstrip("/").split("/")[-1])
        proposals[pid] = body
    return proposals


def load_workflow_statuses() -> dict:
    statuses = {}
    if not WORKFLOW_ROOT.exists():
        return statuses
    for path in sorted(glob.glob(str(WORKFLOW_ROOT / "*" / "status.json"))):
        try:
            status = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            continue
        project_id = str(status.get("project_id") or "").strip()
        if project_id:
            statuses[project_id] = status
    return statuses


def update_dashboard(projects: list[dict]) -> bool:
    html = DASHBOARD_PATH.read_text(encoding="utf-8")

    # 1) PROJECTS 데이터 업데이트
    new_js = projects_to_js(projects)
    pattern = r"(// ── 공고 데이터.*?──\n)const PROJECTS = \[[\s\S]*?\];"
    replacement = r"\g<1>const PROJECTS = " + new_js + ";"
    updated, n = re.subn(pattern, replacement, html)
    if n == 0:
        print("ERROR: PROJECTS 블록을 찾을 수 없습니다.")
        return False

    # 2) DEFAULT_WEBHOOK 주입
    updated = re.sub(r"const DEFAULT_WEBHOOK = '.*?';", "const DEFAULT_WEBHOOK = '';", updated)

    # 3) PROPOSALS 데이터 업데이트
    proposals = load_proposals()
    if proposals:
        proposals_js = json.dumps(proposals, ensure_ascii=False, indent=2)
        pat2 = r"(// ── 제안서 데이터.*?──\n)const PROPOSALS = \{[\s\S]*?\};"
        def _rep(m):
            return m.group(1) + "const PROPOSALS = " + proposals_js + ";"
        updated, n2 = re.subn(pat2, _rep, updated)
        if n2 == 0:
            print("WARNING: PROPOSALS 블록을 찾을 수 없습니다.")
        else:
            print(f"제안서 주입: {len(proposals)}개")

    # 4) TRACKER_STATES 주입 — wishket_tracker.json의 응찰 상태를 HTML에 반영
    workflow_status = load_workflow_statuses()
    workflow_js = json.dumps(workflow_status, ensure_ascii=False, indent=2)
    updated, n3 = re.subn(
        r"(// .*status\.json.*\n)const WORKFLOW_STATUS = \{[\s\S]*?\};",
        lambda m: m.group(1) + "const WORKFLOW_STATUS = " + workflow_js + ";",
        updated,
    )
    if n3 == 0:
        print("WARNING: WORKFLOW_STATUS 블록을 찾을 수 없습니다.")
    else:
        print(f"워크플로우 상태 주입: {len(workflow_status)}개")

    try:
        tracker_data = json.loads(TRACKER_PATH.read_text(encoding="utf-8")) if TRACKER_PATH.exists() else {}
        states = {}
        for bid in tracker_data.get("bids", []):
            link = bid.get("link", "").rstrip("/")
            status = bid.get("status", "submitted")
            if link:
                states[link] = "bid" if status == "submitted" else status
        states_js = json.dumps(states, ensure_ascii=False)
        updated = re.sub(r"const TRACKER_STATES = \{[^}]*\};", f"const TRACKER_STATES = {states_js};", updated)
        print(f"응찰 상태 주입: {len(states)}건")
    except Exception as e:
        print(f"WARNING: TRACKER_STATES 주입 실패: {e}")

    DASHBOARD_PATH.write_text(updated, encoding="utf-8")
    return True


def main():
    projects = load_inbox_projects()
    print(f"수집된 공고 (중복 제거): {len(projects)}개")
    for p in projects:
        print(f"  - {p['title']} ({p['budget_wan']}만원)")

    if not projects:
        print("공고가 없습니다. 업데이트를 건너뜁니다.")
        return

    if update_dashboard(projects):
        print(f"대시보드 업데이트 완료: {DASHBOARD_PATH}")
    else:
        print("대시보드 업데이트 실패")


if __name__ == "__main__":
    main()
