#!/usr/bin/env python3
"""
GitHub Repo Cataloger — jaeha81 GitHub 레포 분석 및 ObsidianVault 카탈로그 생성

기능:
  - GitHub API 또는 gh CLI로 레포 목록 조회
  - 레포 분류: active / stale / archived / project / system
  - ObsidianVault/03_Projects/github-catalog.md 생성 (Obsidian frontmatter 포함)
  - 개별 레포 노드: ObsidianVault/03_Projects/repos/[repo-name].md

환경변수:
  GITHUB_TOKEN  — GitHub Personal Access Token (선택, 미설정 시 공개 API 사용)
  VAULT_PATH    — ObsidianVault 경로 (기본: 스크립트 루트의 ObsidianVault)
  GITHUB_USER   — GitHub 사용자명 (기본: jaeha81)

사용법:
    python github_repo_cataloger.py
    python github_repo_cataloger.py --user jaeha81 --dry-run
    python github_repo_cataloger.py --no-individual   # 개별 노드 생성 안함
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8", override=True)

GITHUB_USER: str = os.getenv("GITHUB_USER", "jaeha81")
GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN") or None
VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
CATALOG_PATH = VAULT / "03_Projects" / "github-catalog.md"
REPOS_DIR = VAULT / "03_Projects" / "repos"

# 분류 기준 (일 단위)
ACTIVE_DAYS = 90
STALE_DAYS = 365

# 레포 성격 분류 키워드
PROJECT_KEYWORDS = {"app", "system", "api", "bot", "tool", "web", "server", "service",
                    "platform", "framework", "plugin", "extension", "client", "dashboard"}
SYSTEM_KEYWORDS = {"brain", "agent", "infra", "infrastructure", "obsidian", "vault",
                   "automation", "pipeline", "manager", "orchestrator", "workflow",
                   "scheduler", "monitor", "deploy", "devops", "ci", "cd"}


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _days_since(iso_str: Optional[str]) -> Optional[int]:
    """ISO8601 문자열 → 경과일 수. 파싱 실패 시 None."""
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (now - dt).days
    except Exception:
        return None


def _classify_activity(days: Optional[int], is_archived: bool) -> str:
    """활동 기간 기준 분류 반환."""
    if is_archived:
        return "archived"
    if days is None:
        return "unknown"
    if days <= ACTIVE_DAYS:
        return "active"
    if days <= STALE_DAYS:
        return "stale"
    return "archived"


def _classify_type(name: str, description: str, topics: list[str]) -> str:
    """레포 이름·설명·토픽으로 성격 분류 반환."""
    combined = " ".join([name, description or "", *topics]).lower()
    for kw in SYSTEM_KEYWORDS:
        if kw in combined:
            return "system"
    for kw in PROJECT_KEYWORDS:
        if kw in combined:
            return "project"
    return "general"


def _fetch_via_api(user: str, token: Optional[str]) -> list[dict]:
    """GitHub REST API로 레포 목록 조회. 페이지네이션 지원."""
    repos: list[dict] = []
    page = 1
    headers = {"Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    while True:
        url = f"https://api.github.com/users/{user}/repos?per_page=100&page={page}&sort=pushed"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            print(f"[Cataloger] API 오류 {e.code}: {e.reason}", flush=True)
            if e.code == 403:
                print("[Cataloger] Rate limit 초과. GITHUB_TOKEN을 설정하거나 나중에 재시도하세요.", flush=True)
            break
        except Exception as e:
            print(f"[Cataloger] 요청 실패: {e}", flush=True)
            break

        if not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1

    return repos


def _fetch_via_gh_cli(user: str) -> list[dict]:
    """gh CLI를 사용하여 레포 목록 조회."""
    try:
        result = subprocess.run(
            ["gh", "repo", "list", user, "--json",
             "name,description,pushedAt,updatedAt,isArchived,url,topics,primaryLanguage,stargazerCount,forkCount,isPrivate",
             "--limit", "200"],
            capture_output=True, text=True, encoding="utf-8", timeout=30
        )
        if result.returncode != 0:
            print(f"[Cataloger] gh CLI 실패: {result.stderr.strip()}", flush=True)
            return []
        return json.loads(result.stdout or "[]")
    except FileNotFoundError:
        print("[Cataloger] gh CLI 미설치. API 방식으로 전환.", flush=True)
        return []
    except Exception as e:
        print(f"[Cataloger] gh CLI 오류: {e}", flush=True)
        return []


def _normalize_repo(raw: dict, source: str) -> dict:
    """API/gh CLI 응답을 통일된 형태로 변환."""
    if source == "gh":
        # gh CLI JSON 필드명 매핑
        pushed_at = raw.get("pushedAt") or raw.get("updatedAt")
        topics = [t.get("name", t) if isinstance(t, dict) else t
                  for t in (raw.get("topics") or [])]
        lang = raw.get("primaryLanguage") or {}
        lang_name = lang.get("name", "") if isinstance(lang, dict) else str(lang or "")
        return {
            "name": raw.get("name", ""),
            "description": raw.get("description") or "",
            "html_url": raw.get("url", ""),
            "pushed_at": pushed_at,
            "archived": raw.get("isArchived", False),
            "topics": topics,
            "language": lang_name,
            "stargazers_count": raw.get("stargazerCount", 0),
            "forks_count": raw.get("forkCount", 0),
            "private": raw.get("isPrivate", False),
        }
    else:
        # GitHub REST API 필드명 그대로
        topics = raw.get("topics") or []
        return {
            "name": raw.get("name", ""),
            "description": raw.get("description") or "",
            "html_url": raw.get("html_url", ""),
            "pushed_at": raw.get("pushed_at"),
            "archived": raw.get("archived", False),
            "topics": topics,
            "language": raw.get("language") or "",
            "stargazers_count": raw.get("stargazers_count", 0),
            "forks_count": raw.get("forks_count", 0),
            "private": raw.get("private", False),
        }


def fetch_repos(user: str, token: Optional[str] = None, prefer_gh: bool = True) -> list[dict]:
    """레포 목록 조회 — gh CLI 우선, 실패 시 API 폴백."""
    raw: list[dict] = []
    source = "api"

    if prefer_gh:
        raw = _fetch_via_gh_cli(user)
        if raw:
            source = "gh"

    if not raw:
        print("[Cataloger] GitHub API로 조회 중...", flush=True)
        raw = _fetch_via_api(user, token)
        source = "api"

    repos = [_normalize_repo(r, source) for r in raw]
    print(f"[Cataloger] {len(repos)}개 레포 조회 완료 (source={source})", flush=True)
    return repos


def analyze_repo(repo: dict) -> dict:
    """레포 분석 — 분류 라벨 추가."""
    days = _days_since(repo["pushed_at"])
    activity = _classify_activity(days, repo["archived"])
    repo_type = _classify_type(repo["name"], repo["description"], repo["topics"])

    return {
        **repo,
        "days_since_push": days,
        "activity": activity,
        "repo_type": repo_type,
    }


def _emoji_for_activity(activity: str) -> str:
    return {"active": "🟢", "stale": "🟡", "archived": "🔴", "unknown": "⚪"}.get(activity, "⚪")


def _emoji_for_type(repo_type: str) -> str:
    return {"project": "📦", "system": "⚙️", "general": "📁"}.get(repo_type, "📁")


def generate_catalog_md(repos: list[dict], user: str) -> str:
    """github-catalog.md 내용 생성."""
    now = _iso_now()
    total = len(repos)

    # 통계
    by_activity: dict[str, list[dict]] = {}
    by_type: dict[str, list[dict]] = {}
    for r in repos:
        by_activity.setdefault(r["activity"], []).append(r)
        by_type.setdefault(r["repo_type"], []).append(r)

    active_count = len(by_activity.get("active", []))
    stale_count = len(by_activity.get("stale", []))
    archived_count = len(by_activity.get("archived", []))

    lines = [
        "---",
        "tags:",
        "  - github",
        "  - catalog",
        "  - dev-status",
        f"generated: \"{now}\"",
        f"github_user: \"{user}\"",
        f"total_repos: {total}",
        f"active: {active_count}",
        f"stale: {stale_count}",
        f"archived: {archived_count}",
        "---",
        "",
        f"# GitHub 레포 카탈로그 — {user}",
        "",
        f"> 생성: {now}  |  전체: **{total}개**  |  🟢 활성: {active_count}  |  🟡 지연: {stale_count}  |  🔴 보관: {archived_count}",
        "",
        "## 요약 통계",
        "",
        f"| 분류 | 개수 |",
        f"|------|------|",
        f"| 🟢 active (90일 이내) | {active_count} |",
        f"| 🟡 stale (90~365일) | {stale_count} |",
        f"| 🔴 archived (1년 이상) | {archived_count} |",
        f"| 📦 project 유형 | {len(by_type.get('project', []))} |",
        f"| ⚙️ system 유형 | {len(by_type.get('system', []))} |",
        f"| 📁 general 유형 | {len(by_type.get('general', []))} |",
        "",
    ]

    # 활성 레포 섹션
    for activity_label, header in [
        ("active", "## 🟢 활성 레포 (90일 이내)"),
        ("stale", "## 🟡 지연 레포 (90~365일)"),
        ("archived", "## 🔴 보관/비활성 레포"),
        ("unknown", "## ⚪ 알 수 없음"),
    ]:
        group = by_activity.get(activity_label, [])
        if not group:
            continue
        lines.append(header)
        lines.append("")
        for r in sorted(group, key=lambda x: x.get("days_since_push") or 9999):
            type_emoji = _emoji_for_type(r["repo_type"])
            days_str = f"{r['days_since_push']}일 전" if r["days_since_push"] is not None else "날짜 불명"
            lang = f" · `{r['language']}`" if r["language"] else ""
            stars = f" · ⭐{r['stargazers_count']}" if r["stargazers_count"] else ""
            priv = " · 🔒" if r["private"] else ""
            desc = f" — {r['description'][:80]}" if r["description"] else ""
            lines.append(
                f"- {type_emoji} [[{r['name']}]]{desc}{lang}{stars}{priv} "
                f"({days_str})"
            )
        lines.append("")

    lines += [
        "## 개별 레포 노드",
        "",
        "> 각 레포의 상세 정보: [[03_Projects/repos/]] 폴더 참조",
        "",
        "---",
        f"*자동 생성 by github_repo_cataloger.py — {now}*",
    ]

    return "\n".join(lines) + "\n"


def generate_repo_md(repo: dict, user: str) -> str:
    """개별 레포 노드 MD 내용 생성."""
    now = _iso_now()
    act_emoji = _emoji_for_activity(repo["activity"])
    type_emoji = _emoji_for_type(repo["repo_type"])
    topics_str = ", ".join(repo["topics"]) if repo["topics"] else "없음"
    days_str = f"{repo['days_since_push']}일 전" if repo["days_since_push"] is not None else "알 수 없음"

    lines = [
        "---",
        "tags:",
        "  - github-repo",
        f"  - {repo['activity']}",
        f"  - {repo['repo_type']}",
        f"repo: \"{repo['name']}\"",
        f"github_user: \"{user}\"",
        f"url: \"{repo['html_url']}\"",
        f"language: \"{repo['language']}\"",
        f"activity: \"{repo['activity']}\"",
        f"repo_type: \"{repo['repo_type']}\"",
        f"stars: {repo['stargazers_count']}",
        f"forks: {repo['forks_count']}",
        f"private: {str(repo['private']).lower()}",
        f"generated: \"{now}\"",
        "---",
        "",
        f"# {act_emoji} {type_emoji} {repo['name']}",
        "",
    ]

    if repo["description"]:
        lines += [f"> {repo['description']}", ""]

    lines += [
        f"**GitHub:** [{repo['name']}]({repo['html_url']})",
        f"**마지막 푸시:** {days_str}",
        f"**언어:** {repo['language'] or '미지정'}",
        f"**토픽:** {topics_str}",
        f"**Stars:** {repo['stargazers_count']}  |  **Forks:** {repo['forks_count']}",
        f"**공개 여부:** {'비공개' if repo['private'] else '공개'}",
        "",
        "## 분류",
        "",
        f"- 활동 상태: `{repo['activity']}` ({days_str})",
        f"- 레포 유형: `{repo['repo_type']}`",
        "",
        "## 관련 링크",
        "",
        f"- [[github-catalog]] — 전체 카탈로그로 돌아가기",
        "",
        "---",
        f"*자동 생성 by github_repo_cataloger.py — {now}*",
    ]

    return "\n".join(lines) + "\n"


def write_catalog(repos: list[dict], user: str, dry_run: bool = False,
                  no_individual: bool = False) -> dict:
    """카탈로그 및 개별 노드 파일 기록. dry_run=True면 실제 기록 안 함."""
    results = {"catalog": str(CATALOG_PATH), "repos_written": 0, "repos_skipped": 0}

    catalog_content = generate_catalog_md(repos, user)

    if dry_run:
        print(f"[DryRun] 카탈로그 → {CATALOG_PATH} ({len(catalog_content)} chars)", flush=True)
    else:
        CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CATALOG_PATH.write_text(catalog_content, encoding="utf-8")
        print(f"[Cataloger] 카탈로그 저장 → {CATALOG_PATH}", flush=True)

    if not no_individual:
        REPOS_DIR.mkdir(parents=True, exist_ok=True)
        for repo in repos:
            repo_path = REPOS_DIR / f"{repo['name']}.md"
            repo_content = generate_repo_md(repo, user)
            if dry_run:
                print(f"[DryRun] 레포 노드 → {repo_path}", flush=True)
                results["repos_written"] += 1
            else:
                repo_path.write_text(repo_content, encoding="utf-8")
                results["repos_written"] += 1

    return results


def run(user: str = GITHUB_USER, token: Optional[str] = GITHUB_TOKEN,
        dry_run: bool = False, no_individual: bool = False,
        prefer_gh: bool = True) -> dict:
    """메인 실행 함수. 외부에서 import하여 사용 가능."""
    print(f"[Cataloger] GitHub 레포 카탈로그 시작 — user={user}", flush=True)

    repos_raw = fetch_repos(user, token, prefer_gh=prefer_gh)
    if not repos_raw:
        print("[Cataloger] 레포 없음 또는 조회 실패.", flush=True)
        return {"error": "no repos fetched", "count": 0}

    repos = [analyze_repo(r) for r in repos_raw]

    # 통계 출력
    from collections import Counter
    act_counts = Counter(r["activity"] for r in repos)
    type_counts = Counter(r["repo_type"] for r in repos)
    print(f"[Cataloger] 활동 분류: {dict(act_counts)}", flush=True)
    print(f"[Cataloger] 유형 분류: {dict(type_counts)}", flush=True)

    result = write_catalog(repos, user, dry_run=dry_run, no_individual=no_individual)
    result["count"] = len(repos)
    result["activity"] = dict(act_counts)
    result["types"] = dict(type_counts)

    print(f"[Cataloger] 완료 — {len(repos)}개 레포 처리", flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="GitHub Repo Cataloger")
    parser.add_argument("--user", default=GITHUB_USER, help="GitHub 사용자명")
    parser.add_argument("--dry-run", action="store_true", help="파일 기록 없이 목록만 출력")
    parser.add_argument("--no-individual", action="store_true", help="개별 레포 노드 생성 안함")
    parser.add_argument("--api-only", action="store_true", help="gh CLI 없이 API만 사용")
    args = parser.parse_args()

    result = run(
        user=args.user,
        dry_run=args.dry_run,
        no_individual=args.no_individual,
        prefer_gh=not args.api_only,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
