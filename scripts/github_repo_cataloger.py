#!/usr/bin/env python3
"""
GitHub Repo Cataloger — jaeha81 GitHub 레포 분석 및 ObsidianVault 카탈로그 생성

기능:
  - GitHub API 또는 gh CLI로 레포 목록 조회
  - 레포 분류: project / system / archive / fork
  - ObsidianVault/03_PROJECTS/github-repos/ 에 레포별 노트 생성
  - 전체 현황 대시보드: ObsidianVault/03_PROJECTS/github-overview.md

환경변수:
  GITHUB_TOKEN  — GitHub Personal Access Token (선택, 미설정 시 공개 API 사용)
  VAULT_PATH    — ObsidianVault 경로 (기본: 스크립트 루트의 ObsidianVault)
  GITHUB_USER   — GitHub 사용자명 (기본: jaeha81)

사용법:
    python github_repo_cataloger.py
    python github_repo_cataloger.py --user jaeha81 --dry-run
    python github_repo_cataloger.py --no-individual   # 개별 노트 생성 안함
    python github_repo_cataloger.py --api-only        # gh CLI 없이 API만 사용
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    _ROOT = Path(__file__).parent.parent
    load_dotenv(_ROOT / ".env", encoding="utf-8-sig", override=True)
except ImportError:
    _ROOT = Path(__file__).parent.parent

GITHUB_USER: str = os.getenv("GITHUB_USER", "jaeha81")
GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN") or None
VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))

# 출력 경로 (요구사항 기준)
OVERVIEW_PATH = VAULT / "03_PROJECTS" / "github-overview.md"
REPOS_DIR = VAULT / "03_PROJECTS" / "github-repos"

# 하위 호환: 구 경로도 병행 지원 (catalog는 overview로 대체)
CATALOG_PATH = OVERVIEW_PATH  # alias

# 활동 기준 (일 단위)
ACTIVE_DAYS = 90
STALE_DAYS = 365

# 레포 유형 분류 키워드
SYSTEM_KEYWORDS = {
    "brain", "agent", "infra", "infrastructure", "obsidian", "vault",
    "automation", "pipeline", "manager", "orchestrator", "workflow",
    "scheduler", "monitor", "deploy", "devops", "ci", "cd", "bus",
    "dispatcher", "cataloger", "bucky",
}
PROJECT_KEYWORDS = {
    "app", "system", "api", "bot", "tool", "web", "server", "service",
    "platform", "framework", "plugin", "extension", "client", "dashboard",
    "site", "page", "blog", "shop",
}


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------

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


def _date_str(iso_str: Optional[str]) -> str:
    """ISO8601 → YYYY-MM-DD 형식 문자열."""
    if not iso_str:
        return "unknown"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# 분류
# ---------------------------------------------------------------------------

def _classify_type(name: str, description: str, topics: list, is_fork: bool,
                   is_archived: bool, days: Optional[int]) -> str:
    """
    레포 분류:
      fork    — 포크된 레포
      archive — GitHub archived 플래그이거나 1년 이상 비활성
      system  — 에이전트/인프라/자동화 관련
      project — 일반 개발 프로젝트
    우선순위: fork > archive > system > project
    """
    if is_fork:
        return "fork"
    if is_archived or (days is not None and days > STALE_DAYS):
        return "archive"
    combined = " ".join([name, description or "", *topics]).lower()
    for kw in SYSTEM_KEYWORDS:
        if kw in combined:
            return "system"
    for kw in PROJECT_KEYWORDS:
        if kw in combined:
            return "project"
    return "project"  # 기본값을 project로 (general 제거)


def _status_from_days(days: Optional[int], is_archived: bool) -> str:
    """활동 상태 문자열."""
    if is_archived:
        return "inactive"
    if days is None:
        return "unknown"
    if days <= ACTIVE_DAYS:
        return "active"
    if days <= STALE_DAYS:
        return "stale"
    return "inactive"


# ---------------------------------------------------------------------------
# 데이터 수집
# ---------------------------------------------------------------------------

def _fetch_via_api(user: str, token: Optional[str]) -> list:
    """GitHub REST API로 레포 목록 조회. 페이지네이션 지원."""
    repos: list = []
    page = 1
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    while True:
        url = (
            f"https://api.github.com/users/{user}/repos"
            f"?per_page=100&page={page}&sort=pushed&type=all"
        )
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            print(f"[Cataloger] API 오류 {e.code}: {e.reason}", flush=True)
            if e.code == 403:
                print(
                    "[Cataloger] Rate limit 초과. GITHUB_TOKEN을 설정하거나 나중에 재시도하세요.",
                    flush=True,
                )
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


def _fetch_via_gh_cli(user: str) -> list:
    """gh CLI를 사용하여 레포 목록 조회."""
    try:
        result = subprocess.run(
            [
                "gh", "repo", "list", user,
                "--json",
                "name,description,pushedAt,updatedAt,isArchived,isFork,"
                "url,topics,primaryLanguage,stargazerCount,forkCount,isPrivate",
                "--limit", "300",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
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
        pushed_at = raw.get("pushedAt") or raw.get("updatedAt")
        topics = [
            t.get("name", t) if isinstance(t, dict) else t
            for t in (raw.get("topics") or [])
        ]
        lang_obj = raw.get("primaryLanguage") or {}
        lang_name = lang_obj.get("name", "") if isinstance(lang_obj, dict) else str(lang_obj or "")
        return {
            "name": raw.get("name", ""),
            "description": raw.get("description") or "",
            "html_url": raw.get("url", ""),
            "pushed_at": pushed_at,
            "archived": raw.get("isArchived", False),
            "fork": raw.get("isFork", False),
            "topics": topics,
            "language": lang_name,
            "stargazers_count": raw.get("stargazerCount", 0),
            "forks_count": raw.get("forkCount", 0),
            "private": raw.get("isPrivate", False),
        }
    else:
        # GitHub REST API 필드명
        topics = raw.get("topics") or []
        return {
            "name": raw.get("name", ""),
            "description": raw.get("description") or "",
            "html_url": raw.get("html_url", ""),
            "pushed_at": raw.get("pushed_at"),
            "archived": raw.get("archived", False),
            "fork": raw.get("fork", False),
            "topics": topics,
            "language": raw.get("language") or "",
            "stargazers_count": raw.get("stargazers_count", 0),
            "forks_count": raw.get("forks_count", 0),
            "private": raw.get("private", False),
        }


def fetch_repos(user: str, token: Optional[str] = None, prefer_gh: bool = True) -> list:
    """레포 목록 조회 — gh CLI 우선, 실패 시 API 폴백."""
    raw: list = []
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
    last_commit_date = _date_str(repo["pushed_at"])
    repo_type = _classify_type(
        repo["name"],
        repo["description"],
        repo["topics"],
        repo["fork"],
        repo["archived"],
        days,
    )
    status = _status_from_days(days, repo["archived"])

    return {
        **repo,
        "days_since_push": days,
        "last_commit": last_commit_date,
        "repo_type": repo_type,
        "status": status,
    }


# ---------------------------------------------------------------------------
# 이모지 헬퍼
# ---------------------------------------------------------------------------

def _emoji_for_type(repo_type: str) -> str:
    return {
        "project": "📦",
        "system": "⚙️",
        "archive": "🗃️",
        "fork": "🍴",
    }.get(repo_type, "📁")


def _emoji_for_status(status: str) -> str:
    return {
        "active": "🟢",
        "stale": "🟡",
        "inactive": "🔴",
        "unknown": "⚪",
    }.get(status, "⚪")


# ---------------------------------------------------------------------------
# 마크다운 생성
# ---------------------------------------------------------------------------

def generate_overview_md(repos: list, user: str) -> str:
    """github-overview.md (대시보드) 내용 생성."""
    now = _iso_now()
    total = len(repos)

    by_type: dict = {}
    by_status: dict = {}
    for r in repos:
        by_type.setdefault(r["repo_type"], []).append(r)
        by_status.setdefault(r["status"], []).append(r)

    active_count = len(by_status.get("active", []))
    stale_count = len(by_status.get("stale", []))
    inactive_count = len(by_status.get("inactive", []))
    fork_count = len(by_type.get("fork", []))

    lines = [
        "---",
        "tags:",
        "  - github",
        "  - overview",
        "  - dev-status",
        f'generated: "{now}"',
        f'github_user: "{user}"',
        f"total_repos: {total}",
        f"active: {active_count}",
        f"stale: {stale_count}",
        f"inactive: {inactive_count}",
        f"forks: {fork_count}",
        "---",
        "",
        f"# GitHub 레포 현황 대시보드 — {user}",
        "",
        f"> 생성: {now}  |  전체: **{total}개**  "
        f"|  🟢 활성: {active_count}  "
        f"|  🟡 지연: {stale_count}  "
        f"|  🔴 비활성: {inactive_count}  "
        f"|  🍴 포크: {fork_count}",
        "",
        "## 요약 통계",
        "",
        "| 분류 | 개수 |",
        "|------|------|",
        f"| 🟢 active (90일 이내) | {active_count} |",
        f"| 🟡 stale (90~365일) | {stale_count} |",
        f"| 🔴 inactive (1년 이상) | {inactive_count} |",
        f"| 📦 project 유형 | {len(by_type.get('project', []))} |",
        f"| ⚙️ system 유형 | {len(by_type.get('system', []))} |",
        f"| 🗃️ archive 유형 | {len(by_type.get('archive', []))} |",
        f"| 🍴 fork 유형 | {fork_count} |",
        "",
    ]

    # 유형별 섹션
    sections = [
        ("system", "## ⚙️ 시스템/에이전트 레포"),
        ("project", "## 📦 프로젝트 레포"),
        ("archive", "## 🗃️ 보관/비활성 레포"),
        ("fork", "## 🍴 포크 레포"),
    ]

    for type_key, header in sections:
        group = by_type.get(type_key, [])
        if not group:
            continue
        lines.append(header)
        lines.append("")
        # 활성 순으로 정렬 (최근 푸시 우선)
        sorted_group = sorted(group, key=lambda x: x.get("days_since_push") or 9999)
        for r in sorted_group:
            status_emoji = _emoji_for_status(r["status"])
            days_str = f"{r['days_since_push']}일 전" if r["days_since_push"] is not None else "날짜 불명"
            lang = f" · `{r['language']}`" if r["language"] else ""
            stars = f" · ⭐{r['stargazers_count']}" if r["stargazers_count"] else ""
            priv = " · 🔒" if r["private"] else ""
            desc = f" — {r['description'][:80]}" if r["description"] else ""
            lines.append(
                f"- {status_emoji} [[github-repos/{r['name']}|{r['name']}]]{desc}"
                f"{lang}{stars}{priv} ({days_str})"
            )
        lines.append("")

    lines += [
        "## 개별 레포 노트",
        "",
        "> 각 레포의 상세 정보: `ObsidianVault/03_PROJECTS/github-repos/` 폴더 참조",
        "",
        "---",
        f"*자동 생성 by github_repo_cataloger.py — {now}*",
    ]

    return "\n".join(lines) + "\n"


def generate_repo_md(repo: dict, user: str) -> str:
    """개별 레포 노트 MD 내용 생성 (요구사항 포맷)."""
    now = _iso_now()
    topics_str = ", ".join(repo["topics"]) if repo["topics"] else "없음"
    days_str = (
        f"{repo['days_since_push']}일 전"
        if repo["days_since_push"] is not None
        else "알 수 없음"
    )

    rname = repo["name"]
    rlang = repo["language"]
    rlast = repo["last_commit"]
    rstatus = repo["status"]
    rtype = repo["repo_type"]
    rpriv = str(repo["private"]).lower()

    lines = [
        "---",
        "tags:",
        "  - github",
        f"  - {rtype}",
        f'repo: "https://github.com/{user}/{rname}"',
        f'language: "{rlang}"',
        f'last_commit: "{rlast}"',
        f'status: "{rstatus}"',
        f'repo_type: "{rtype}"',
        f"stars: {repo['stargazers_count']}",
        f"forks: {repo['forks_count']}",
        f"private: {rpriv}",
        f'generated: "{now}"',
        "---",
        "",
        f"# {rname}",
        "",
    ]

    if repo["description"]:
        lines += [f"> {repo['description']}", ""]

    lines += [
        f"**GitHub:** [{repo['name']}](https://github.com/{user}/{repo['name']})",
        f"**마지막 커밋:** {repo['last_commit']} ({days_str})",
        f"**언어:** {repo['language'] or '미지정'}",
        f"**상태:** `{repo['status']}`  |  **유형:** `{repo['repo_type']}`",
        f"**토픽:** {topics_str}",
        f"**Stars:** {repo['stargazers_count']}  |  **Forks:** {repo['forks_count']}",
        f"**공개 여부:** {'비공개' if repo['private'] else '공개'}",
        "",
        "## 개요",
        "",
        repo["description"] if repo["description"] else "_(설명 없음)_",
        "",
        "## 현재 개발 현황",
        "",
        "_(직접 작성)_",
        "",
        "## 다음 작업",
        "",
        "_(직접 작성)_",
        "",
        "---",
        f"*자동 생성 by github_repo_cataloger.py — {now}*",
        f"*[[github-overview]] 로 돌아가기*",
    ]

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 파일 기록
# ---------------------------------------------------------------------------

def write_catalog(
    repos: list,
    user: str,
    dry_run: bool = False,
    no_individual: bool = False,
) -> dict:
    """대시보드 및 개별 노트 파일 기록. dry_run=True면 실제 기록 안 함."""
    results: dict = {
        "overview": str(OVERVIEW_PATH),
        "repos_written": 0,
        "repos_skipped": 0,
    }

    overview_content = generate_overview_md(repos, user)

    if dry_run:
        print(
            f"[DryRun] 대시보드 → {OVERVIEW_PATH} ({len(overview_content)} chars)",
            flush=True,
        )
    else:
        OVERVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
        OVERVIEW_PATH.write_text(overview_content, encoding="utf-8")
        print(f"[Cataloger] 대시보드 저장 → {OVERVIEW_PATH}", flush=True)

    if not no_individual:
        if not dry_run:
            REPOS_DIR.mkdir(parents=True, exist_ok=True)
        for repo in repos:
            repo_path = REPOS_DIR / f"{repo['name']}.md"
            repo_content = generate_repo_md(repo, user)
            if dry_run:
                print(f"[DryRun] 레포 노트 → {repo_path}", flush=True)
                results["repos_written"] += 1
            else:
                repo_path.write_text(repo_content, encoding="utf-8")
                results["repos_written"] += 1

    return results


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------

def run(
    user: str = GITHUB_USER,
    token: Optional[str] = GITHUB_TOKEN,
    dry_run: bool = False,
    no_individual: bool = False,
    prefer_gh: bool = True,
) -> dict:
    """메인 실행 함수. 외부에서 import하여 사용 가능."""
    print(f"[Cataloger] GitHub 레포 카탈로그 시작 — user={user}", flush=True)

    repos_raw = fetch_repos(user, token, prefer_gh=prefer_gh)
    if not repos_raw:
        print("[Cataloger] 레포 없음 또는 조회 실패.", flush=True)
        return {"error": "no repos fetched", "count": 0}

    repos = [analyze_repo(r) for r in repos_raw]

    # 통계 출력
    type_counts = Counter(r["repo_type"] for r in repos)
    status_counts = Counter(r["status"] for r in repos)
    print(f"[Cataloger] 유형 분류: {dict(type_counts)}", flush=True)
    print(f"[Cataloger] 활동 분류: {dict(status_counts)}", flush=True)

    result = write_catalog(repos, user, dry_run=dry_run, no_individual=no_individual)
    result["count"] = len(repos)
    result["types"] = dict(type_counts)
    result["status"] = dict(status_counts)

    print(f"[Cataloger] 완료 — {len(repos)}개 레포 처리", flush=True)
    return result


# ---------------------------------------------------------------------------
# 하위 호환 헬퍼 (github_agent.py 등에서 import)
# ---------------------------------------------------------------------------

def _emoji_for_activity(activity: str) -> str:
    """하위 호환: activity 문자열 → 이모지."""
    return _emoji_for_status(activity)


def _normalize_repo_public(raw: dict, source: str) -> dict:
    """하위 호환 export."""
    return _normalize_repo(raw, source)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="GitHub Repo Cataloger")
    parser.add_argument("--user", default=GITHUB_USER, help="GitHub 사용자명")
    parser.add_argument("--dry-run", action="store_true", help="파일 기록 없이 목록만 출력")
    parser.add_argument("--no-individual", action="store_true", help="개별 레포 노트 생성 안함")
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
