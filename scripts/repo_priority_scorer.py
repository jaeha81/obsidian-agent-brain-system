#!/usr/bin/env python3
"""repo_priority_scorer.py — GitHub 레포 수익성 점수화 (Card 4 승인, 2026-06-20).

점수화 공식:
  score = 25*health + 25*traffic + 15*(1-dep_risk) + 20*(1-dev_effort) + 15*monet
  각 항목은 0.0~1.0 정규화 후 가중치 적용 → 최대 100점

선별 규칙:
  High  : score >= 75, repo_health >= 15/25
  Medium: 60 <= score < 75
  Low   : score < 60
  쇼트리스트: 상위 10 + monetization_signals >= 5

사용법:
  python -X utf8 scripts/repo_priority_scorer.py --owner jaeha81
  python -X utf8 scripts/repo_priority_scorer.py --repos sniper-buying-dashboard,obsidian-agent-brain-system
  python -X utf8 scripts/repo_priority_scorer.py --output-json out.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
DEFAULT_OWNER = "jaeha81"

# Repos with known monetization signals (수동 정의 — API로 감지 어려움)
MONETIZATION_REGISTRY: dict[str, dict] = {
    "sniper-buying-dashboard": {
        "active_revenue": True,
        "has_vercel_deploy": True,
        "has_stripe_or_payment": False,
        "has_b2b_potential": True,
        "targeting_paying_users": True,
    },
    "obsidian-agent-brain-system": {
        "active_revenue": False,
        "has_vercel_deploy": False,
        "has_stripe_or_payment": False,
        "has_b2b_potential": True,
        "targeting_paying_users": False,
    },
}


def _gh_request(path: str, token: str = GITHUB_TOKEN) -> Any:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"_error": str(e)}


def _collect_repo_health(repo: dict) -> float:
    """repo_health 0.0~1.0. 이슈, 포크, 스타, 업데이트 최신성."""
    score = 0.0
    # 오래된 레포 페널티 (updated_at)
    try:
        updated = repo.get("updated_at", "")
        if updated:
            age_days = (time.time() - time.mktime(time.strptime(updated[:19], "%Y-%m-%dT%H:%M:%S"))) / 86400
            if age_days < 30:
                score += 0.4
            elif age_days < 90:
                score += 0.2
    except Exception:
        pass
    # 오픈 이슈 수 (적을수록 좋음 — 유지보수 중)
    open_issues = repo.get("open_issues_count", 0)
    if open_issues == 0:
        score += 0.2
    elif open_issues < 5:
        score += 0.1
    # 기본 상태
    if not repo.get("archived", False):
        score += 0.2
    if not repo.get("disabled", False):
        score += 0.1
    # 설명 존재
    if repo.get("description"):
        score += 0.1
    return min(score, 1.0)


def _collect_traffic(owner: str, name: str) -> float:
    """traffic_usage 0.0~1.0. Traffic API (토큰 필요, 없으면 0.1 기본)."""
    if not GITHUB_TOKEN:
        return 0.1  # no token → minimal score
    views = _gh_request(f"/repos/{owner}/{name}/traffic/views")
    if "_error" in views:
        return 0.1
    total = views.get("count", 0)
    uniq = views.get("uniques", 0)
    # 100+ 조회수를 만점으로 정규화
    raw = min((total / 100) * 0.6 + (uniq / 30) * 0.4, 1.0)
    return round(raw, 3)


def _collect_dep_risk(owner: str, name: str) -> float:
    """dependency_risk 0.0~1.0. Dependabot 취약점 수 기반."""
    if not GITHUB_TOKEN:
        return 0.3  # no token → moderate risk assumed
    alerts = _gh_request(f"/repos/{owner}/{name}/vulnerability-alerts")
    if "_error" in alerts or not isinstance(alerts, list):
        return 0.3
    critical = sum(1 for a in alerts if a.get("security_vulnerability", {}).get("severity") == "critical")
    high = sum(1 for a in alerts if a.get("security_vulnerability", {}).get("severity") == "high")
    risk = min(critical * 0.3 + high * 0.1, 1.0)
    return round(risk, 3)


def _collect_dev_effort(repo: dict) -> float:
    """dev_effort 0.0~1.0. 레포 크기(LOC 추정) 기반."""
    size_kb = repo.get("size", 0)  # GitHub size is in KB
    # 10 MB 이상이면 effort 1.0
    effort = min(size_kb / 10000, 1.0)
    return round(effort, 3)


def _collect_monetization(name: str) -> tuple[float, int]:
    """monetization_signals — 0.0~1.0, signal count."""
    entry = MONETIZATION_REGISTRY.get(name, {})
    signals = [
        entry.get("active_revenue", False),
        entry.get("has_vercel_deploy", False),
        entry.get("has_stripe_or_payment", False),
        entry.get("has_b2b_potential", False),
        entry.get("targeting_paying_users", False),
    ]
    count = sum(1 for s in signals if s)
    score = count / len(signals)
    return round(score, 3), count


def score_repo(owner: str, name: str) -> dict:
    repo = _gh_request(f"/repos/{owner}/{name}")
    if "_error" in repo:
        return {"name": name, "error": repo["_error"], "score": 0, "tier": "Low"}

    health = _collect_repo_health(repo)
    traffic = _collect_traffic(owner, name)
    dep_risk = _collect_dep_risk(owner, name)
    dev_effort = _collect_dev_effort(repo)
    monet, monet_signals = _collect_monetization(name)

    score = round(
        25 * health
        + 25 * traffic
        + 15 * (1 - dep_risk)
        + 20 * (1 - dev_effort)
        + 15 * monet,
        1,
    )
    health_pts = round(25 * health, 1)

    if score >= 75 and health_pts >= 15:
        tier = "High"
    elif score >= 60:
        tier = "Medium"
    else:
        tier = "Low"

    return {
        "name": f"{owner}/{name}",
        "score": score,
        "tier": tier,
        "shortlist": score >= 75 and monet_signals >= 5,
        "details": {
            "repo_health": round(health_pts, 1),
            "traffic_score": round(25 * traffic, 1),
            "dep_risk_score": round(15 * (1 - dep_risk), 1),
            "dev_effort_score": round(20 * (1 - dev_effort), 1),
            "monetization_score": round(15 * monet, 1),
            "monetization_signals": monet_signals,
        },
        "repo_meta": {
            "description": repo.get("description", ""),
            "language": repo.get("language", ""),
            "stars": repo.get("stargazers_count", 0),
            "updated_at": repo.get("updated_at", ""),
            "archived": repo.get("archived", False),
        },
    }


def score_owner_repos(owner: str, max_repos: int = 50) -> list[dict]:
    page = 1
    results: list[dict] = []
    while len(results) < max_repos:
        repos = _gh_request(f"/users/{owner}/repos?per_page=30&page={page}&sort=updated")
        if "_error" in repos or not isinstance(repos, list) or not repos:
            break
        for r in repos:
            if len(results) >= max_repos:
                break
            entry = score_repo(owner, r["name"])
            results.append(entry)
            time.sleep(0.3)  # rate-limit courtesy
        page += 1
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results


def print_report(results: list[dict]) -> None:
    high = [r for r in results if r.get("tier") == "High"]
    medium = [r for r in results if r.get("tier") == "Medium"]
    low = [r for r in results if r.get("tier") == "Low"]
    shortlist = [r for r in results if r.get("shortlist")]

    print("\n=== 레포 수익성 점수화 보고서 ===\n")
    print(f"{'레포':<40} {'점수':>6}  {'등급':<8}  {'쇼트리스트'}")
    print("-" * 70)
    for r in results:
        star = "★" if r.get("shortlist") else ""
        err = r.get("error", "")
        if err:
            print(f"{r['name']:<40} {'ERR':>6}  {'Low':<8}  {err[:20]}")
        else:
            print(f"{r['name']:<40} {r['score']:>6.1f}  {r['tier']:<8}  {star}")

    print(f"\n요약: High={len(high)}, Medium={len(medium)}, Low={len(low)}, 쇼트리스트={len(shortlist)}")
    if shortlist:
        print("\n★ 쇼트리스트 (즉시 수익화 후보):")
        for r in shortlist:
            print(f"  - {r['name']} (점수: {r['score']})")


def main() -> None:
    parser = argparse.ArgumentParser(description="GitHub 레포 수익성 점수화")
    parser.add_argument("--owner", default=DEFAULT_OWNER, help="GitHub 사용자명")
    parser.add_argument("--repos", help="쉼표 구분 레포명 목록 (owner/name 또는 name)")
    parser.add_argument("--max", type=int, default=40, help="최대 레포 수 (기본 40)")
    parser.add_argument("--output-json", help="JSON 결과 저장 경로")
    args = parser.parse_args()

    if args.repos:
        names = [r.strip() for r in args.repos.split(",") if r.strip()]
        results: list[dict] = []
        for n in names:
            if "/" in n:
                owner, name = n.split("/", 1)
            else:
                owner, name = args.owner, n
            results.append(score_repo(owner, name))
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
    else:
        print(f"[repo_priority_scorer] {args.owner} 레포 스캔 중 (최대 {args.max}개)…")
        results = score_owner_repos(args.owner, args.max)

    print_report(results)

    out_path = args.output_json or str(DATA_DIR / "repo_priority_scores.json")
    Path(out_path).write_text(
        json.dumps({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[repo_priority_scorer] 결과 저장: {out_path}")


if __name__ == "__main__":
    main()
