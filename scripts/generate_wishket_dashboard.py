"""
위시켓 대시보드 데이터 갱신 스크립트.

wishket_inbox/ 폴더의 모든 JSON을 읽어 중복 제거 후
docs/wishket.html의 PROJECTS 배열을 업데이트한다.
"""
import json
import re
import glob
import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
INBOX_DIR = ROOT / "ObsidianVault" / "10_AgentBus" / "wishket_inbox"
TRACKER_PATH = ROOT / "ObsidianVault" / "10_AgentBus" / "wishket_tracker.json"
DASHBOARD_PATH = ROOT / "docs" / "wishket.html"


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
                }
    return list(projects.values())


def projects_to_js(projects: list[dict]) -> str:
    lines = []
    for p in projects:
        desc = p["description"].replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
        lines.append(
            f"  {{\n"
            f"    id: '{p['id']}',\n"
            f"    title: '{p['title'].replace(chr(39), chr(92)+chr(39))}',\n"
            f"    link: '{p['link']}',\n"
            f"    budget: '{p['budget']}',\n"
            f"    budget_wan: {p['budget_wan']},\n"
            f"    description: '{desc[:200]}',\n"
            f"    source: '{p['source']}',\n"
            f"    scraped_at: '{p['scraped_at']}'\n"
            f"  }}"
        )
    return "[\n" + ",\n".join(lines) + "\n]"


def _load_env_webhook() -> str:
    """프로젝트 .env에서 DISCORD_WEBHOOK_URL 읽기."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DISCORD_WEBHOOK_URL="):
            return line.split("=", 1)[1].strip()
    return ""


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

    # 2) DEFAULT_WEBHOOK 주입 (.env 값으로)
    webhook_url = _load_env_webhook()
    if webhook_url:
        updated = re.sub(
            r"const DEFAULT_WEBHOOK = '.*?';",
            f"const DEFAULT_WEBHOOK = '{webhook_url}';",
            updated,
        )

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
