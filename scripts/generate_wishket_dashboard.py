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

ROOT = Path(__file__).parent.parent
INBOX_DIR = ROOT / "ObsidianVault" / "10_AgentBus" / "wishket_inbox"
TRACKER_PATH = ROOT / "ObsidianVault" / "10_AgentBus" / "wishket_tracker.json"
DASHBOARD_PATH = ROOT / "docs" / "wishket.html"
PROPOSALS_DIR = ROOT / "ObsidianVault" / "03_Projects" / "wishket-proposals"


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
    # 근무/직원 공고 제외 (채용형 공고 필터)
    EXCLUDE_KEYWORDS = ["근무지", "직원 모집", "직원 채용", "정규직", "계약직", "아르바이트"]
    EXCLUDE_TITLE_ONLY = ["직원"]
    def _is_employment(p: dict) -> bool:
        text = (p.get("title", "") + " " + p.get("description", "")).lower()
        if any(kw in text for kw in EXCLUDE_KEYWORDS):
            return True
        title = p.get("title", "")
        if any(kw in title for kw in EXCLUDE_TITLE_ONLY):
            return True
        return False
    before = len(result)
    result = [p for p in result if not _is_employment(p)]
    excluded = before - len(result)
    if excluded:
        print(f"근무/직원 공고 제외: {excluded}개")

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
