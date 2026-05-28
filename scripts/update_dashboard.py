"""
docs/index.html 대시보드 자동 업데이트 스크립트

- GitHub API: 신규 레포 감지
- Anthropic API: 신규 레포 분석 자동 생성
- 날짜 업데이트
- docs/index.html repos 배열에 신규 항목 삽입
"""

import re
import json
import os
import sys
from datetime import datetime, timezone, timedelta
import urllib.request
import urllib.error


GITHUB_USER = "jaeha81"
DOCS_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "index.html")


def github_get(url: str) -> list:
    token = os.environ.get("GITHUB_TOKEN", "")
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("User-Agent", "dashboard-updater/1.0")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"[WARN] GitHub API 실패: {e}", file=sys.stderr)
        return []


def fetch_all_repos() -> list[dict]:
    all_repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{GITHUB_USER}/repos?per_page=100&page={page}&sort=updated"
        data = github_get(url)
        if not data:
            break
        all_repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    return all_repos


def extract_existing_ids(html: str) -> set[str]:
    """repos 배열에서 id 값 추출"""
    return set(re.findall(r"id:\s*'([^']+)'", html))


def call_claude_analyze(repo: dict) -> dict | None:
    """Anthropic API로 레포 분석 생성"""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    name = repo.get("name", "")
    desc = repo.get("description") or ""
    lang = repo.get("language") or "Unknown"
    topics = repo.get("topics", [])
    stars = repo.get("stargazers_count", 0)

    prompt = f"""GitHub 레포 분석 (JSON 형식으로만 응답):

레포: {name}
설명: {desc}
언어: {lang}
토픽: {", ".join(topics) if topics else "없음"}
스타: {stars}

다음 JSON만 반환 (설명 없이):
{{
  "desc": "한 줄 설명 (최대 60자, 한국어)",
  "cat": "interior|commerce|saas|finance|ai-agent",
  "tier": 1|2|3,
  "completion": 0~100,
  "market": 0~100,
  "reason": "시장성 이유 (30자 이내)",
  "action": "즉시 해야 할 액션 (40자 이내)"
}}

tier 기준: 1=즉시출시가능(completion≥75), 2=개발필요(completion≥40), 3=인프라/보류"""

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        method="POST"
    )
    req.add_header("x-api-key", api_key)
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("content-type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            resp = json.loads(r.read().decode())
            text = resp["content"][0]["text"].strip()
            # JSON 블록 추출
            m = re.search(r"\{[\s\S]+\}", text)
            if m:
                return json.loads(m.group())
    except Exception as e:
        print(f"[WARN] Claude API 실패 ({name}): {e}", file=sys.stderr)
    return None


def make_js_entry(repo: dict, analysis: dict) -> str:
    name = repo["name"]
    url = repo["html_url"]
    lang = repo.get("language") or "—"

    desc = analysis.get("desc") or repo.get("description") or "설명 없음"
    cat = analysis.get("cat", "saas")
    tier = int(analysis.get("tier", 2))
    completion = int(analysis.get("completion", 30))
    market = int(analysis.get("market", 50))
    reason = analysis.get("reason", "분석 자동 생성")
    action = analysis.get("action", "Bucky 상세 분석 요청")

    # JS 특수문자 이스케이프
    def esc(s):
        return s.replace("\\", "\\\\").replace("'", "\\'")

    return (
        f"  {{\n"
        f"    id: '{esc(name)}',\n"
        f"    name: '{esc(name)}',\n"
        f"    url: '{esc(url)}',\n"
        f"    desc: '{esc(desc)}',\n"
        f"    lang: '{esc(lang)}', status: 'active', tier: {tier}, cat: '{esc(cat)}',\n"
        f"    completion: {completion}, market: {market},\n"
        f"    reason: '{esc(reason)}',\n"
        f"    action: '{esc(action)}'\n"
        f"  }}"
    )


def update_date(html: str, today: str) -> str:
    # "· 2026-05-26 ·" 패턴 교체
    updated = re.sub(r"· \d{4}-\d{2}-\d{2} ·", f"· {today} ·", html)
    if updated == html:
        # 날짜가 다른 형식일 경우 헤더 p 태그 안의 날짜 교체 시도
        updated = re.sub(
            r"(jaeha81[^·]*· )\d{4}-\d{2}-\d{2}",
            rf"\g<1>{today}",
            html
        )
    return updated


def main():
    # KST 기준 오늘 날짜
    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst).strftime("%Y-%m-%d")

    html_path = os.path.abspath(DOCS_PATH)
    if not os.path.exists(html_path):
        print(f"[ERROR] {html_path} 없음", file=sys.stderr)
        sys.exit(1)

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. 날짜 업데이트
    html = update_date(html, today)
    print(f"[INFO] 날짜 → {today}")

    # 2. 기존 ID 목록 추출
    existing_ids = extract_existing_ids(html)
    print(f"[INFO] 기존 레포 수: {len(existing_ids)}")

    # 3. GitHub API에서 전체 레포 가져오기
    gh_repos = fetch_all_repos()
    print(f"[INFO] GitHub 레포 수: {len(gh_repos)}")

    # 4. 신규 레포 필터링 (fork 제외)
    new_repos = [
        r for r in gh_repos
        if r["name"] not in existing_ids and not r.get("fork", False)
    ]
    print(f"[INFO] 신규 레포 수: {len(new_repos)}")

    if new_repos:
        new_entries = []
        for repo in new_repos:
            print(f"[INFO] 분석 중: {repo['name']}")
            analysis = call_claude_analyze(repo)
            if not analysis:
                # API 없으면 기본값
                analysis = {
                    "desc": repo.get("description") or "설명 없음 — Bucky 분석 필요",
                    "cat": "saas",
                    "tier": 2,
                    "completion": 30,
                    "market": 50,
                    "reason": "자동 감지 — 분석 대기",
                    "action": "🤖 Bucky 상세 분석 요청"
                }
            entry = make_js_entry(repo, analysis)
            new_entries.append(entry)

        # repos 배열 닫는 ]; 직전에 삽입
        insert_block = "\n  // ─── 자동 추가 (" + today + ") ───\n" + ",\n".join(new_entries) + ","
        html = re.sub(r"(\n\];\s*\n// ── GitHub)", insert_block + r"\n];\n// ── GitHub", html, count=1)
        if insert_block not in html:
            # fallback: const repos 배열의 마지막 }  앞에 삽입
            html = re.sub(r"(\];\s*\n\s*// ── GitHub)", insert_block + r"\n];\n// ── GitHub", html, count=1)

        print(f"[INFO] {len(new_repos)}개 레포 추가 완료")

    # 5. 저장
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[INFO] {html_path} 저장 완료")


if __name__ == "__main__":
    main()
