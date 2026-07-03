"""
JH 레포지토리 대시보드 GitHub 데이터 갱신 스크립트.

GitHub API로 jaeha81의 레포 목록을 가져와 docs/index.html의
repoCount 통계를 업데이트하고, 신규 레포를 감지해 콘솔에 보고한다.

사용:
  python scripts/generate_repo_dashboard.py
  python scripts/generate_repo_dashboard.py --token ghp_xxx
"""
import json
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime

try:
    import urllib.request as urlreq
except ImportError:
    urlreq = None

ROOT = Path(__file__).parent.parent
DASHBOARD_PATH = ROOT / "docs" / "index.html"
GITHUB_USER = "jaeha81"
API_URL = f"https://api.github.com/users/{GITHUB_USER}/repos?per_page=100&sort=updated"


def fetch_repos(token: str = "") -> list[dict]:
    req = urlreq.Request(API_URL)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "JH-Dashboard/1.0")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urlreq.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def extract_known_ids(html: str) -> set[str]:
    return set(re.findall(r"id:\s*'([^']+)'", html))


def main():
    parser = argparse.ArgumentParser(description="JH 레포 대시보드 갱신")
    parser.add_argument("--token", default="", help="GitHub Personal Access Token")
    parser.add_argument("--dry-run", action="store_true", help="변경 없이 보고만")
    args = parser.parse_args()

    if not DASHBOARD_PATH.exists():
        print(f"[ERROR] 대시보드 파일 없음: {DASHBOARD_PATH}")
        sys.exit(1)

    html = DASHBOARD_PATH.read_text(encoding="utf-8")
    known_ids = extract_known_ids(html)

    print(f"[INFO] GitHub API 조회 중 — {GITHUB_USER}")
    try:
        repos = fetch_repos(args.token)
    except Exception as e:
        print(f"[WARN] GitHub API 실패 (인증 필요할 수 있음): {e}")
        print("  → gh auth login 후 재시도하거나 --token 플래그 사용")
        sys.exit(0)

    total = len(repos)
    print(f"[INFO] 전체 레포: {total}개")

    # 신규 레포 감지
    new_repos = [r for r in repos if r["name"] not in known_ids]
    if new_repos:
        print(f"\n[NEW] 대시보드에 없는 레포 {len(new_repos)}개:")
        for r in sorted(new_repos, key=lambda x: x.get("updated_at", ""), reverse=True):
            lang = r.get("language") or "—"
            desc = (r.get("description") or "설명 없음")[:60]
            print(f"  · {r['name']} [{lang}] — {desc}")
        print("\n  → docs/index.html REPOS 배열에 수동 추가 후 cat/tier/completion/market 설정")
    else:
        print("[OK] 신규 레포 없음 — 대시보드 최신 상태")

    # 통계 업데이트
    if not args.dry_run:
        today = datetime.now().strftime("%Y-%m-%d")
        # repoCount span 업데이트
        new_html = re.sub(
            r'(<span id="repoCount">)\d+(</span>)',
            rf'\g<1>{total}\g<2>',
            html
        )
        # 날짜 업데이트
        new_html = re.sub(
            r'(\d{4}-\d{2}-\d{2}) · Bucky Agent',
            rf'{today} · Bucky Agent',
            new_html
        )
        if new_html != html:
            DASHBOARD_PATH.write_text(new_html, encoding="utf-8")
            print(f"[OK] 대시보드 업데이트 완료 → repoCount={total}, 날짜={today}")
        else:
            print("[OK] 변경 없음")
    else:
        print("[DRY-RUN] 파일 변경 없음")


if __name__ == "__main__":
    main()
