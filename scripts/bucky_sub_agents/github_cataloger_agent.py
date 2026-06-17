#!/usr/bin/env python3
"""
GitHub Cataloger Agent — bucky_sub_agent_manager 패턴을 따르는 서브에이전트 래퍼

AgentBus inbox/github-cataloger-*.json 파일을 감시하여 명령을 처리한다.
github_repo_cataloger.py 를 내부에서 호출하는 얇은 래퍼 역할을 한다.

지원 명령:
  catalog          — 전체 레포 카탈로그 업데이트 (overview + 개별 노트)
  status [repo]    — 특정 레포 상태 조회 (노드 파일 또는 실시간 API)
  report           — 개발 현황 요약 출력 (Discord 전송 지원)
  refresh          — catalog 별칭 (외부에서 편의상 사용)

AgentBus 메시지 형식 (JSON):
  {
    "command": "catalog" | "status" | "report" | "refresh",
    "repo": "repo-name",         // status 명령 시
    "user": "github-username",   // 기본값: jaeha81
    "dry_run": false,            // catalog 명령 시
    "no_individual": false,      // catalog 명령 시
    "webhook_url": "...",        // Discord Webhook URL (선택)
    "ts": "ISO8601"
  }

실행:
    python bucky_sub_agents/github_cataloger_agent.py
    python bucky_sub_agents/github_cataloger_agent.py --once
    python bucky_sub_agents/github_cataloger_agent.py --command catalog
    python bucky_sub_agents/github_cataloger_agent.py --command status --repo obsidian-agent-brain-system
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Optional

# scripts/ 디렉토리를 sys.path에 추가
_SCRIPTS = Path(__file__).parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

try:
    from dotenv import load_dotenv
    _ROOT = _SCRIPTS.parent
    load_dotenv(_ROOT / ".env", encoding="utf-8-sig", override=True)
except ImportError:
    _ROOT = _SCRIPTS.parent

VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
INBOX = VAULT / "10_AgentBus" / "inbox"
AGENT_PREFIX = "github-cataloger-"
POLL_INTERVAL = int(os.getenv("GITHUB_CATALOGER_POLL_SECS", "15"))

GITHUB_USER: str = os.getenv("GITHUB_USER", "jaeha81")
GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN") or None
DISCORD_WEBHOOK: Optional[str] = os.getenv("DISCORD_WEBHOOK_URL") or None

# 대시보드 경로
OVERVIEW_PATH = VAULT / "03_PROJECTS" / "github-overview.md"
REPOS_DIR = VAULT / "03_PROJECTS" / "github-repos"


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------

def _iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _send_discord(text: str, webhook_url: Optional[str] = None) -> bool:
    """Discord Webhook으로 메시지 전송. 실패 시 False 반환."""
    url = webhook_url or DISCORD_WEBHOOK
    if not url:
        return False
    chunks = [text[i : i + 1900] for i in range(0, len(text), 1900)]
    ok = True
    for chunk in chunks:
        payload = json.dumps({"content": chunk}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10):
                pass
        except Exception as e:
            print(f"[CatalogerAgent] Discord 전송 실패: {e}", flush=True)
            ok = False
    return ok


def _write_result(command: str, result: dict) -> Path:
    """결과를 AgentBus outbox에 기록."""
    outbox = VAULT / "10_AgentBus" / "outbox"
    outbox.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = outbox / f"{ts}_github-cataloger-result.json"
    out_path.write_text(
        json.dumps({"command": command, "ts": _iso(), **result}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path


# ---------------------------------------------------------------------------
# 명령 핸들러
# ---------------------------------------------------------------------------

def cmd_catalog(args: dict) -> str:
    """전체 레포 카탈로그 업데이트 (overview + 개별 노트)."""
    try:
        from github_repo_cataloger import run as cataloger_run

        result = cataloger_run(
            user=args.get("user", GITHUB_USER),
            dry_run=bool(args.get("dry_run", False)),
            no_individual=bool(args.get("no_individual", False)),
        )

        if "error" in result:
            return f"카탈로그 업데이트 실패: {result['error']}"

        count = result.get("count", 0)
        types = result.get("types", {})
        status = result.get("status", {})

        msg = (
            f"**GitHub 카탈로그 업데이트 완료**\n"
            f"전체: {count}개\n"
            f"🟢 active: {status.get('active', 0)}  "
            f"🟡 stale: {status.get('stale', 0)}  "
            f"🔴 inactive: {status.get('inactive', 0)}\n"
            f"📦 project: {types.get('project', 0)}  "
            f"⚙️ system: {types.get('system', 0)}  "
            f"🗃️ archive: {types.get('archive', 0)}  "
            f"🍴 fork: {types.get('fork', 0)}\n"
            f"대시보드: `ObsidianVault/03_PROJECTS/github-overview.md`\n"
            f"레포 노트: `ObsidianVault/03_PROJECTS/github-repos/`"
        )
        _write_result("catalog", result)
        return msg

    except Exception as e:
        err = f"[CatalogerAgent] catalog 실패: {e}"
        print(err, flush=True)
        return f"카탈로그 업데이트 실패: {e}"


def cmd_status(args: dict) -> str:
    """특정 레포 상태 조회."""
    repo_name = args.get("repo", "").strip()
    if not repo_name:
        return '`repo` 인자 필요: {"command": "status", "repo": "repo-name"}'

    user = args.get("user", GITHUB_USER)

    # 1) 로컬 노트 파일 확인
    repo_file = REPOS_DIR / f"{repo_name}.md"
    if repo_file.exists():
        content = repo_file.read_text(encoding="utf-8")
        status_m = re.search(r'^status: "?(\w+)"?', content, re.MULTILINE)
        repo_type_m = re.search(r'^repo_type: "?(\w+)"?', content, re.MULTILINE)
        stars_m = re.search(r'^stars: (\d+)', content, re.MULTILINE)
        lang_m = re.search(r'^language: "?([^"\n]*)"?$', content, re.MULTILINE)
        url_m = re.search(r'^repo: "?([^"\n]*)"?$', content, re.MULTILINE)
        last_commit_m = re.search(r'^last_commit: "?([^"\n]*)"?$', content, re.MULTILINE)

        status_icons = {
            "active": "🟢", "stale": "🟡", "inactive": "🔴", "unknown": "⚪"
        }
        type_icons = {
            "project": "📦", "system": "⚙️", "archive": "🗃️", "fork": "🍴"
        }

        lines = [f"**레포 상태: `{repo_name}`** (캐시)"]
        if url_m:
            lines.append(f"URL: {url_m.group(1)}")
        if last_commit_m:
            lines.append(f"마지막 커밋: {last_commit_m.group(1)}")
        if status_m:
            s = status_m.group(1)
            lines.append(f"활동: {status_icons.get(s, '⚪')} `{s}`")
        if repo_type_m:
            rt = repo_type_m.group(1)
            lines.append(f"유형: {type_icons.get(rt, '📁')} `{rt}`")
        if lang_m:
            lines.append(f"언어: {lang_m.group(1)}")
        if stars_m:
            lines.append(f"Stars: {stars_m.group(1)}")
        lines.append(f"노트: `ObsidianVault/03_PROJECTS/github-repos/{repo_name}.md`")
        return "\n".join(lines)

    # 2) 로컬 없으면 API 실시간 조회
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    api_url = f"https://api.github.com/repos/{user}/{repo_name}"
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        from github_repo_cataloger import _normalize_repo, analyze_repo

        normalized = _normalize_repo(data, "api")
        analyzed = analyze_repo(normalized)

        status_icons = {
            "active": "🟢", "stale": "🟡", "inactive": "🔴", "unknown": "⚪"
        }
        type_icons = {
            "project": "📦", "system": "⚙️", "archive": "🗃️", "fork": "🍴"
        }

        days_str = (
            f"{analyzed['days_since_push']}일 전"
            if analyzed["days_since_push"] is not None
            else "알 수 없음"
        )

        lines = [
            f"**레포 상태: `{repo_name}`** (실시간 조회)",
            f"URL: https://github.com/{user}/{repo_name}",
            f"마지막 커밋: {analyzed['last_commit']} ({days_str})",
            f"활동: {status_icons.get(analyzed['status'], '⚪')} `{analyzed['status']}`",
            f"유형: {type_icons.get(analyzed['repo_type'], '📁')} `{analyzed['repo_type']}`",
            f"언어: {analyzed['language'] or '미지정'}",
            f"Stars: {analyzed['stargazers_count']}",
        ]
        if analyzed["description"]:
            lines.insert(1, f"설명: {analyzed['description'][:100]}")
        lines.append("힌트: `catalog` 명령으로 노트를 생성하면 다음부터 빠르게 조회됩니다.")
        return "\n".join(lines)

    except urllib.error.HTTPError as e:
        if e.code == 404:
            return (
                f"레포 `{repo_name}` 없음 (또는 비공개). "
                f"먼저 `catalog` 명령으로 카탈로그를 생성하세요."
            )
        return f"API 오류 {e.code}: {e.reason}"
    except Exception as e:
        return f"상태 조회 실패: {e}"


def cmd_report(args: dict) -> str:
    """개발 현황 요약 생성 및 Discord 전송."""
    if not OVERVIEW_PATH.exists():
        return (
            "대시보드 없음. 먼저 `catalog` 명령으로 카탈로그를 생성하세요.\n"
            f"경로: {OVERVIEW_PATH}"
        )

    content = OVERVIEW_PATH.read_text(encoding="utf-8")

    total_m = re.search(r'^total_repos: (\d+)', content, re.MULTILINE)
    active_m = re.search(r'^active: (\d+)', content, re.MULTILINE)
    stale_m = re.search(r'^stale: (\d+)', content, re.MULTILINE)
    inactive_m = re.search(r'^inactive: (\d+)', content, re.MULTILINE)
    forks_m = re.search(r'^forks: (\d+)', content, re.MULTILINE)
    generated_m = re.search(r'^generated: "?([^"\n]+)"?', content, re.MULTILINE)

    gen_str = generated_m.group(1) if generated_m else "알 수 없음"

    report = (
        f"**GitHub 개발 현황 리포트** — {GITHUB_USER}\n"
        f"기준: {gen_str}\n\n"
        f"전체 레포: {total_m.group(1) if total_m else '?'}개\n"
        f"🟢 활성 (90일 이내): {active_m.group(1) if active_m else '?'}개\n"
        f"🟡 지연 (90~365일): {stale_m.group(1) if stale_m else '?'}개\n"
        f"🔴 비활성 (1년+): {inactive_m.group(1) if inactive_m else '?'}개\n"
        f"🍴 포크: {forks_m.group(1) if forks_m else '?'}개\n\n"
        f"대시보드: `ObsidianVault/03_PROJECTS/github-overview.md`"
    )

    webhook = args.get("webhook_url") or DISCORD_WEBHOOK
    if webhook:
        sent = _send_discord(report, webhook)
        suffix = "\n(Discord 전송 완료)" if sent else "\n(Discord 전송 실패)"
    else:
        suffix = "\n(Discord 미설정 — 콘솔에만 출력)"

    return report + suffix


# ---------------------------------------------------------------------------
# AgentBus 처리
# ---------------------------------------------------------------------------

DISPATCH = {
    "catalog": cmd_catalog,
    "refresh": cmd_catalog,  # 별칭
    "status": cmd_status,
    "report": cmd_report,
}


def process_message(msg_path: Path) -> None:
    """inbox JSON 파일 하나를 읽어 명령 처리."""
    try:
        data = json.loads(msg_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[CatalogerAgent] JSON 파싱 실패 ({msg_path.name}): {e}", flush=True)
        msg_path.rename(msg_path.with_suffix(".error"))
        return

    command = data.get("command", "").strip().lower()
    print(f"[CatalogerAgent] 처리: {command} ({msg_path.name})", flush=True)

    if command not in DISPATCH:
        reply = (
            f"알 수 없는 명령: `{command}`. "
            f"지원: {' / '.join(DISPATCH.keys())}"
        )
    else:
        reply = DISPATCH[command](data)

    print(f"[CatalogerAgent] 결과:\n{reply}", flush=True)

    # Discord 전송
    webhook = data.get("webhook_url") or DISCORD_WEBHOOK
    if webhook and reply:
        _send_discord(reply, webhook)

    # 처리 완료 파일 이동
    done_dir = INBOX / "done"
    done_dir.mkdir(parents=True, exist_ok=True)
    msg_path.rename(done_dir / msg_path.name)


def watch(once: bool = False) -> None:
    """INBOX 폴더에서 github-cataloger-*.json 파일 감시 및 처리."""
    INBOX.mkdir(parents=True, exist_ok=True)
    print(f"[CatalogerAgent] 감시 시작 — {INBOX}", flush=True)
    print(f"[CatalogerAgent] 폴링 간격: {POLL_INTERVAL}초", flush=True)

    while True:
        msgs = sorted(INBOX.glob(f"{AGENT_PREFIX}*.json"))
        for msg_path in msgs:
            process_message(msg_path)

        if once:
            break
        time.sleep(POLL_INTERVAL)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="GitHub Cataloger Agent — AgentBus 서브에이전트"
    )
    parser.add_argument("--once", action="store_true", help="한 번만 처리 후 종료")
    parser.add_argument("--watch", action="store_true", help="폴링 감시 모드 (기본)")
    parser.add_argument(
        "--command",
        choices=list(DISPATCH.keys()),
        help="직접 명령 실행: catalog / status / report / refresh",
    )
    parser.add_argument("--repo", help="--command status 시 레포명")
    parser.add_argument("--user", default=GITHUB_USER, help="GitHub 사용자명")
    parser.add_argument("--dry-run", action="store_true", help="catalog 시 파일 기록 없이 출력만")
    args = parser.parse_args()

    if args.command:
        # CLI 직접 실행 모드
        payload = {
            "repo": args.repo or "",
            "user": args.user,
            "dry_run": args.dry_run,
        }
        result_str = DISPATCH[args.command](payload)
        print(result_str)
        return

    watch(once=args.once)


if __name__ == "__main__":
    main()
