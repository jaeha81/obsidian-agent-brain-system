#!/usr/bin/env python3
"""
GitHub Agent — bucky_sub_agent_manager 패턴을 따르는 GitHub 전담 서브에이전트

AgentBus inbox/github-agent-*.json 파일을 감시하여 명령을 처리한다.

지원 명령:
  catalog          — 전체 레포 카탈로그 업데이트
  status [repo]    — 특정 레포 상태 조회
  report           — 개발 현황 요약 Discord 전송

AgentBus 메시지 형식 (JSON):
  {
    "command": "catalog" | "status" | "report",
    "repo": "repo-name",         // status 명령 시
    "reply_channel": "...",      // Discord 채널 ID (선택)
    "ts": "ISO8601"
  }

실행:
    python bucky_sub_agents/github_agent.py
    python bucky_sub_agents/github_agent.py --once   # 한 번만 처리 후 종료
    python bucky_sub_agents/github_agent.py --watch  # 폴링 감시 모드 (기본)
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Optional

# 부모 디렉토리를 sys.path에 추가 (scripts/ 기준)
_SCRIPTS = Path(__file__).parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from dotenv import load_dotenv

_ROOT = _SCRIPTS.parent
load_dotenv(_ROOT / ".env", encoding="utf-8", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
INBOX = VAULT / "10_AgentBus" / "inbox"
AGENT_PREFIX = "github-agent-"
POLL_INTERVAL = int(os.getenv("GITHUB_AGENT_POLL_SECS", "15"))  # 초

GITHUB_USER: str = os.getenv("GITHUB_USER", "jaeha81")
GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN") or None

# Discord Webhook (선택) — 없으면 파일에만 기록
DISCORD_WEBHOOK: Optional[str] = os.getenv("DISCORD_WEBHOOK_URL") or None


def _iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _send_discord(text: str, webhook_url: Optional[str] = None) -> bool:
    """Discord Webhook으로 메시지 전송. 실패 시 False 반환."""
    url = webhook_url or DISCORD_WEBHOOK
    if not url:
        return False
    # 2000자 제한 처리
    chunks = [text[i:i+1900] for i in range(0, len(text), 1900)]
    ok = True
    for chunk in chunks:
        payload = json.dumps({"content": chunk}).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10):
                pass
        except Exception as e:
            print(f"[GithubAgent] Discord 전송 실패: {e}", flush=True)
            ok = False
    return ok


def _write_result(command: str, result: dict) -> Path:
    """결과를 AgentBus outbox에 기록."""
    outbox = VAULT / "10_AgentBus" / "outbox"
    outbox.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = outbox / f"{ts}_github-agent-result.json"
    out_path.write_text(
        json.dumps({"command": command, "ts": _iso(), **result},
                   ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return out_path


def cmd_catalog(args: dict) -> str:
    """전체 레포 카탈로그 업데이트."""
    try:
        from github_repo_cataloger import run as cataloger_run
        result = cataloger_run(
            user=args.get("user", GITHUB_USER),
        )
        count = result.get("count", 0)
        activity = result.get("activity", {})
        types = result.get("types", {})
        msg = (
            f"**GitHub 카탈로그 업데이트 완료**\n"
            f"전체: {count}개\n"
            f"🟢 active: {activity.get('active', 0)}  "
            f"🟡 stale: {activity.get('stale', 0)}  "
            f"🔴 archived: {activity.get('archived', 0)}\n"
            f"📦 project: {types.get('project', 0)}  "
            f"⚙️ system: {types.get('system', 0)}  "
            f"📁 general: {types.get('general', 0)}\n"
            f"카탈로그: `ObsidianVault/03_Projects/github-catalog.md`"
        )
        _write_result("catalog", result)
        return msg
    except Exception as e:
        err = f"[GithubAgent] catalog 실패: {e}"
        print(err, flush=True)
        return f"카탈로그 업데이트 실패: {e}"


def cmd_status(args: dict) -> str:
    """특정 레포 상태 조회."""
    repo_name = args.get("repo", "").strip()
    if not repo_name:
        return "repo 인자 필요: `{\"command\": \"status\", \"repo\": \"repo-name\"}`"

    user = args.get("user", GITHUB_USER)
    token = GITHUB_TOKEN

    # 먼저 개별 노드 파일 확인
    repo_file = VAULT / "03_Projects" / "repos" / f"{repo_name}.md"
    if repo_file.exists():
        content = repo_file.read_text(encoding="utf-8")
        # frontmatter에서 핵심 정보 추출
        import re
        activity = re.search(r'^activity: "?(\w+)"?', content, re.MULTILINE)
        repo_type = re.search(r'^repo_type: "?(\w+)"?', content, re.MULTILINE)
        stars = re.search(r'^stars: (\d+)', content, re.MULTILINE)
        lang = re.search(r'^language: "?(.*?)"?$', content, re.MULTILINE)
        url = re.search(r'^url: "?(.*?)"?$', content, re.MULTILINE)

        lines = [f"**레포 상태: `{repo_name}`**"]
        if url:
            lines.append(f"URL: {url.group(1)}")
        if activity:
            from github_repo_cataloger import _emoji_for_activity
            act = activity.group(1)
            lines.append(f"활동: {_emoji_for_activity(act)} `{act}`")
        if repo_type:
            from github_repo_cataloger import _emoji_for_type
            rt = repo_type.group(1)
            lines.append(f"유형: {_emoji_for_type(rt)} `{rt}`")
        if lang:
            lines.append(f"언어: {lang.group(1)}")
        if stars:
            lines.append(f"Stars: {stars.group(1)}")
        lines.append(f"노드: `ObsidianVault/03_Projects/repos/{repo_name}.md`")
        return "\n".join(lines)

    # 파일 없으면 API로 직접 조회
    headers = {"Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{user}/{repo_name}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        from github_repo_cataloger import (
            _normalize_repo, analyze_repo, _emoji_for_activity, _emoji_for_type
        )
        normalized = _normalize_repo(data, "api")
        analyzed = analyze_repo(normalized)
        act_emoji = _emoji_for_activity(analyzed["activity"])
        type_emoji = _emoji_for_type(analyzed["repo_type"])
        days_str = f"{analyzed['days_since_push']}일 전" if analyzed["days_since_push"] is not None else "알 수 없음"

        lines = [
            f"**레포 상태: `{repo_name}`** (실시간 조회)",
            f"URL: {analyzed['html_url']}",
            f"활동: {act_emoji} `{analyzed['activity']}` ({days_str})",
            f"유형: {type_emoji} `{analyzed['repo_type']}`",
            f"언어: {analyzed['language'] or '미지정'}",
            f"Stars: {analyzed['stargazers_count']}",
        ]
        if analyzed["description"]:
            lines.insert(1, f"설명: {analyzed['description'][:100]}")
        return "\n".join(lines)

    except urllib.error.HTTPError as e:
        if e.code == 404:
            return f"레포 `{repo_name}` 없음 (또는 비공개). 카탈로그 먼저 업데이트: `!깃헙`"
        return f"API 오류 {e.code}: {e.reason}"
    except Exception as e:
        return f"상태 조회 실패: {e}"


def cmd_report(args: dict) -> str:
    """개발 현황 요약 생성 및 Discord 전송."""
    catalog_path = VAULT / "03_Projects" / "github-catalog.md"
    if not catalog_path.exists():
        return "카탈로그 없음. 먼저 `!깃헙` 실행하여 카탈로그를 생성하세요."

    content = catalog_path.read_text(encoding="utf-8")
    import re

    # frontmatter 파싱
    total = re.search(r'^total_repos: (\d+)', content, re.MULTILINE)
    active = re.search(r'^active: (\d+)', content, re.MULTILINE)
    stale = re.search(r'^stale: (\d+)', content, re.MULTILINE)
    archived = re.search(r'^archived: (\d+)', content, re.MULTILINE)
    generated = re.search(r'^generated: "?([^"\n]+)"?', content, re.MULTILINE)

    gen_str = generated.group(1) if generated else "알 수 없음"

    report = (
        f"**GitHub 개발 현황 리포트** — {GITHUB_USER}\n"
        f"기준: {gen_str}\n\n"
        f"전체 레포: {total.group(1) if total else '?'}개\n"
        f"🟢 활성 (90일 이내): {active.group(1) if active else '?'}개\n"
        f"🟡 지연 (90~365일): {stale.group(1) if stale else '?'}개\n"
        f"🔴 보관 (1년+): {archived.group(1) if archived else '?'}개\n\n"
        f"상세: `ObsidianVault/03_Projects/github-catalog.md`"
    )

    # Discord 전송 시도
    webhook = args.get("webhook_url") or DISCORD_WEBHOOK
    if webhook:
        sent = _send_discord(report, webhook)
        suffix = " (Discord 전송 완료)" if sent else " (Discord 전송 실패)"
    else:
        suffix = " (Discord 미설정)"

    return report + suffix


def process_message(msg_path: Path) -> None:
    """inbox JSON 파일 하나를 읽어 명령 처리."""
    try:
        data = json.loads(msg_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[GithubAgent] JSON 파싱 실패 ({msg_path.name}): {e}", flush=True)
        msg_path.rename(msg_path.with_suffix(".error"))
        return

    command = data.get("command", "").strip().lower()
    print(f"[GithubAgent] 처리: {command} ({msg_path.name})", flush=True)

    dispatch = {
        "catalog": cmd_catalog,
        "status": cmd_status,
        "report": cmd_report,
    }

    if command not in dispatch:
        reply = f"알 수 없는 명령: `{command}`. 지원: catalog / status / report"
    else:
        reply = dispatch[command](data)

    print(f"[GithubAgent] 결과:\n{reply}", flush=True)

    # Discord 전송 (reply_channel은 봇이 없으면 webhook으로 처리)
    webhook = data.get("webhook_url") or DISCORD_WEBHOOK
    if webhook and reply:
        _send_discord(reply, webhook)

    # 처리 완료 파일 이동 (done 디렉토리)
    done_dir = INBOX / "done"
    done_dir.mkdir(parents=True, exist_ok=True)
    msg_path.rename(done_dir / msg_path.name)


def watch(once: bool = False) -> None:
    """INBOX 폴더에서 github-agent-*.json 파일 감시 및 처리."""
    INBOX.mkdir(parents=True, exist_ok=True)
    print(f"[GithubAgent] 감시 시작 — {INBOX}", flush=True)
    print(f"[GithubAgent] 폴링 간격: {POLL_INTERVAL}초", flush=True)

    while True:
        msgs = sorted(INBOX.glob(f"{AGENT_PREFIX}*.json"))
        for msg_path in msgs:
            process_message(msg_path)

        if once:
            break
        time.sleep(POLL_INTERVAL)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="GitHub Agent — AgentBus 서브에이전트")
    parser.add_argument("--once", action="store_true", help="한 번만 처리 후 종료")
    parser.add_argument("--watch", action="store_true", help="폴링 감시 모드 (기본)")
    parser.add_argument("--command", help="직접 명령 실행: catalog / status / report")
    parser.add_argument("--repo", help="--command status 시 레포명")
    args = parser.parse_args()

    if args.command:
        # CLI 직접 실행 모드
        dispatch = {"catalog": cmd_catalog, "status": cmd_status, "report": cmd_report}
        if args.command not in dispatch:
            print(f"알 수 없는 명령: {args.command}. 지원: catalog / status / report")
            sys.exit(1)
        result = dispatch[args.command]({"repo": args.repo or ""})
        print(result)
        return

    watch(once=args.once)


if __name__ == "__main__":
    main()
