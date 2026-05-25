#!/usr/bin/env python3
"""
GitHub Repo Scout — Bucky 서브에이전트
GitHub API로 레포 전수 조회 → 분류 → Vault 노드 저장

분류:
  active     — 최근 30일 내 커밋 있음
  stale      — 커밋 없이 30~180일
  archived   — GitHub archive 상태 or 180일 이상
  system     — bucky/brain/agent/obsidian 키워드 포함
  project    — README에 기능 설명, 의미 있는 구조

출력:
  ObsidianVault/03_Knowledge/github-repos/YYYY-MM-DD-github-repos.md
  - frontmatter: tags, updated, stats
  - 분류별 테이블
  - 프로젝트성 레포 상세 (기술스택, 설명, 마지막 커밋)

Discord webhook 알림: 요약 전송 (DISCORD_WEBHOOK_URL)

사용법:
  python github_repo_scout.py           # 전체 조회
  python github_repo_scout.py --dry-run # API 호출 없이 샘플 출력
  python github_repo_scout.py --user jaeha81  # 특정 유저
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
ENV_FILE = REPO_ROOT / ".env"

load_dotenv(ENV_FILE)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "jaeha81")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
VAULT_BASE_PATH = Path(
    os.getenv(
        "VAULT_BASE_PATH",
        str(REPO_ROOT / "ObsidianVault"),
    )
)

OUTPUT_DIR = VAULT_BASE_PATH / "03_Knowledge" / "github-repos"

# 분류 기준 (일수)
ACTIVE_DAYS = 30
STALE_MAX_DAYS = 180

SYSTEM_KEYWORDS = {"bucky", "brain", "agent", "obsidian"}
PROJECT_KEYWORDS = {"ai", "claude", "gpt", "bot", "api", "app", "web", "tool", "plugin"}


# ─────────────────────────────────────────────
# GitHub API
# ─────────────────────────────────────────────

def make_session() -> requests.Session:
    session = requests.Session()
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    session.headers.update(headers)
    return session


def fetch_all_repos(username: str, session: requests.Session) -> list[dict]:
    """페이지네이션으로 전체 레포 목록 조회."""
    repos: list[dict] = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{username}/repos"
        params = {"per_page": 100, "page": page, "sort": "updated", "direction": "desc"}
        resp = session.get(url, params=params, timeout=30)
        if resp.status_code == 404:
            print(f"[ERROR] 사용자 '{username}'를 찾을 수 없습니다.", file=sys.stderr)
            sys.exit(1)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
        # rate limit 방지
        time.sleep(0.3)
    return repos


def fetch_languages(repo: dict, session: requests.Session) -> list[str]:
    """레포의 주요 언어 목록 조회 (상위 3개)."""
    url = repo.get("languages_url", "")
    if not url:
        return []
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        langs = resp.json()
        # 바이트 수 기준 정렬, 상위 3개
        sorted_langs = sorted(langs.items(), key=lambda x: x[1], reverse=True)
        return [lang for lang, _ in sorted_langs[:3]]
    except Exception:
        return []


# ─────────────────────────────────────────────
# 분류 로직
# ─────────────────────────────────────────────

def classify_repo(repo: dict, now: datetime) -> str:
    """단일 레포를 분류 카테고리로 반환."""
    name_lower = repo.get("name", "").lower()
    desc_lower = (repo.get("description") or "").lower()
    combined = name_lower + " " + desc_lower

    # 1. GitHub archived 상태
    if repo.get("archived", False):
        return "archived"

    # 2. system 키워드 우선
    if any(kw in combined for kw in SYSTEM_KEYWORDS):
        return "system"

    # 3. 마지막 push 기준 활성도 분류
    pushed_at_str = repo.get("pushed_at") or repo.get("updated_at")
    if pushed_at_str:
        pushed_at = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
        delta_days = (now - pushed_at).days
        if delta_days <= ACTIVE_DAYS:
            return "active"
        elif delta_days <= STALE_MAX_DAYS:
            return "stale"
        else:
            return "archived"

    return "stale"


def is_project_repo(repo: dict) -> bool:
    """프로젝트성 레포 여부 판단."""
    name_lower = repo.get("name", "").lower()
    desc = (repo.get("description") or "").lower()
    combined = name_lower + " " + desc
    has_readme = bool(repo.get("has_wiki") or repo.get("description"))
    has_project_kw = any(kw in combined for kw in PROJECT_KEYWORDS)
    has_stars = (repo.get("stargazers_count") or 0) > 0
    return has_readme and (has_project_kw or has_stars)


# ─────────────────────────────────────────────
# 샘플 데이터 (dry-run)
# ─────────────────────────────────────────────

SAMPLE_REPOS = [
    {
        "name": "obsidian-agent-brain-system",
        "description": "Bucky AI brain with Obsidian vault integration",
        "pushed_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        "archived": False,
        "stargazers_count": 3,
        "language": "Python",
        "languages_url": "",
        "html_url": "https://github.com/jaeha81/obsidian-agent-brain-system",
        "has_wiki": True,
    },
    {
        "name": "claude-projects-jh",
        "description": "Claude Code global instructions and skills",
        "pushed_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
        "archived": False,
        "stargazers_count": 1,
        "language": "Markdown",
        "languages_url": "",
        "html_url": "https://github.com/jaeha81/claude-projects-jh",
        "has_wiki": False,
    },
    {
        "name": "old-experiment",
        "description": "Deprecated test project",
        "pushed_at": (datetime.now(timezone.utc) - timedelta(days=200)).isoformat(),
        "archived": False,
        "stargazers_count": 0,
        "language": "JavaScript",
        "languages_url": "",
        "html_url": "https://github.com/jaeha81/old-experiment",
        "has_wiki": False,
    },
    {
        "name": "archived-demo",
        "description": None,
        "pushed_at": (datetime.now(timezone.utc) - timedelta(days=400)).isoformat(),
        "archived": True,
        "stargazers_count": 0,
        "language": None,
        "languages_url": "",
        "html_url": "https://github.com/jaeha81/archived-demo",
        "has_wiki": False,
    },
]


# ─────────────────────────────────────────────
# Markdown 생성
# ─────────────────────────────────────────────

def format_date(iso_str: str | None) -> str:
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return iso_str[:10]


def build_markdown(
    username: str,
    repos: list[dict],
    classified: dict[str, list[dict]],
    lang_map: dict[str, list[str]],
    today: str,
) -> str:
    total = len(repos)
    counts = {cat: len(lst) for cat, lst in classified.items()}

    lines: list[str] = []

    # Frontmatter
    lines += [
        "---",
        f"tags: [github, repos, scout]",
        f"updated: {today}",
        f"username: {username}",
        f"total: {total}",
        f"active: {counts.get('active', 0)}",
        f"stale: {counts.get('stale', 0)}",
        f"archived: {counts.get('archived', 0)}",
        f"system: {counts.get('system', 0)}",
        "---",
        "",
        f"# GitHub 레포 현황 — {today}",
        "",
        f"> **{username}** 전체 레포 {total}개 분석 결과",
        "",
        "## 통계",
        "",
        "| 분류 | 수 |",
        "| --- | --- |",
        f"| ✅ active (30일 내 커밋) | {counts.get('active', 0)} |",
        f"| ⚠️ stale (30~180일) | {counts.get('stale', 0)} |",
        f"| 🗄️ archived (180일 초과·archived) | {counts.get('archived', 0)} |",
        f"| 🤖 system (brain/agent/bucky/obsidian) | {counts.get('system', 0)} |",
        "",
    ]

    # 분류별 테이블
    for cat, label, emoji in [
        ("active", "Active 레포", "✅"),
        ("system", "System 레포 (Bucky 관련)", "🤖"),
        ("stale", "Stale 레포", "⚠️"),
        ("archived", "Archived 레포", "🗄️"),
    ]:
        repo_list = classified.get(cat, [])
        if not repo_list:
            continue
        lines += [
            f"## {emoji} {label}",
            "",
            "| 레포 | 설명 | 언어 | 마지막 커밋 | 링크 |",
            "| --- | --- | --- | --- | --- |",
        ]
        for r in repo_list:
            name = r.get("name", "")
            desc = (r.get("description") or "—")[:60]
            langs = ", ".join(lang_map.get(name, [])) or (r.get("language") or "—")
            last_commit = format_date(r.get("pushed_at"))
            url = r.get("html_url", "")
            lines.append(f"| {name} | {desc} | {langs} | {last_commit} | [링크]({url}) |")
        lines.append("")

    # 프로젝트성 레포 상세
    project_repos = [r for r in repos if is_project_repo(r)]
    if project_repos:
        lines += [
            "## 📦 프로젝트성 레포 상세",
            "",
        ]
        for r in project_repos:
            name = r.get("name", "")
            url = r.get("html_url", "")
            desc = r.get("description") or "설명 없음"
            langs = ", ".join(lang_map.get(name, [])) or (r.get("language") or "—")
            last_commit = format_date(r.get("pushed_at"))
            stars = r.get("stargazers_count", 0)
            lines += [
                f"### [{name}]({url})",
                "",
                f"- **설명**: {desc}",
                f"- **기술스택**: {langs}",
                f"- **마지막 커밋**: {last_commit}",
                f"- **Stars**: {stars}",
                "",
            ]

    lines += [
        "---",
        f"*생성: {datetime.now().strftime('%Y-%m-%d %H:%M')} by github_repo_scout.py*",
    ]

    return "\n".join(lines)


# ─────────────────────────────────────────────
# Discord 알림
# ─────────────────────────────────────────────

def send_discord(summary: str) -> None:
    if not DISCORD_WEBHOOK_URL:
        print("[SKIP] DISCORD_WEBHOOK_URL 미설정 — 알림 생략")
        return
    payload = {"content": summary}
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        resp.raise_for_status()
        print("[OK] Discord 알림 전송 완료")
    except Exception as e:
        print(f"[WARN] Discord 알림 실패: {e}", file=sys.stderr)


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="GitHub Repo Scout — Bucky 서브에이전트")
    parser.add_argument("--dry-run", action="store_true", help="API 호출 없이 샘플 데이터로 출력")
    parser.add_argument("--user", default=GITHUB_USERNAME, help=f"GitHub 사용자명 (기본: {GITHUB_USERNAME})")
    parser.add_argument("--no-discord", action="store_true", help="Discord 알림 생략")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    username = args.user

    print(f"[github_repo_scout] 시작 — 대상: {username}, dry-run: {args.dry_run}")

    # 레포 목록 수집
    if args.dry_run:
        print("[DRY-RUN] 샘플 데이터 사용")
        repos = SAMPLE_REPOS
        lang_map: dict[str, list[str]] = {}
    else:
        if not GITHUB_TOKEN:
            print("[WARN] GITHUB_TOKEN 미설정 — 익명 API 사용 (rate limit 60회/시간)", file=sys.stderr)
        session = make_session()
        print(f"[INFO] GitHub API 조회 중...")
        repos = fetch_all_repos(username, session)
        print(f"[INFO] {len(repos)}개 레포 수집 완료")

        # 언어 정보 조회
        print("[INFO] 언어 정보 조회 중...")
        lang_map = {}
        for i, repo in enumerate(repos, 1):
            name = repo.get("name", "")
            langs = fetch_languages(repo, session)
            lang_map[name] = langs
            if i % 10 == 0:
                print(f"  {i}/{len(repos)} 처리...")
            time.sleep(0.2)

    # 분류
    classified: dict[str, list[dict]] = {"active": [], "stale": [], "archived": [], "system": []}
    for repo in repos:
        cat = classify_repo(repo, now)
        classified[cat].append(repo)

    # Markdown 생성
    md_content = build_markdown(username, repos, classified, lang_map, today)

    if args.dry_run:
        print("\n" + "=" * 60)
        print(md_content)
        print("=" * 60)
        print("[DRY-RUN] 파일 저장 생략")
        return

    # 출력 디렉토리 생성 및 저장
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / f"{today}-github-repos.md"
    out_file.write_text(md_content, encoding="utf-8")
    print(f"[OK] 저장 완료: {out_file}")

    # Discord 알림
    if not args.no_discord:
        counts = {cat: len(lst) for cat, lst in classified.items()}
        summary = (
            f"**GitHub Repo Scout 완료** ({today})\n"
            f"👤 {username} | 전체 {len(repos)}개\n"
            f"✅ active {counts['active']} | ⚠️ stale {counts['stale']} "
            f"| 🗄️ archived {counts['archived']} | 🤖 system {counts['system']}\n"
            f"📝 `{out_file.name}`"
        )
        send_discord(summary)


if __name__ == "__main__":
    main()
