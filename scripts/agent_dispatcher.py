#!/usr/bin/env python3
"""
Agent Dispatcher — ObsidianVault/10_AgentBus/inbox/ 감시 → 지침 로드 → 실행 → 결과 기록

Flow:
  inbox/*.md (status: pending)
    → frontmatter 파싱 → 태스크 타입 분류
    → Obsidian 에이전트 지침 로드 (REST API 우선, 직접 파일 폴백)
    → 처리기 라우팅:
        discord_intake  → Anthropic API (단순 Q&A)
        implementation_request → Claude Code CLI 스폰
        review_request  → Codex outbox 라우팅
        * 기타 → Anthropic API 폴백
    → 결과 outbox/ClaudeCode/ 저장 + inbox 상태 갱신

Requirements: pip install anthropic python-dotenv pyyaml requests
"""

import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

import anthropic
import requests
import yaml
from dotenv import load_dotenv

# ── 환경 설정 ──────────────────────────────────────────────────────────────────

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
INBOX = VAULT / "10_AgentBus" / "inbox"
OUTBOX_CLAUDE = VAULT / "10_AgentBus" / "outbox" / "ClaudeCode"
OUTBOX_CODEX = VAULT / "10_AgentBus" / "outbox" / "Codex"
COMPLETED = VAULT / "10_AgentBus" / "completed"
FAILED = VAULT / "10_AgentBus" / "failed"

OBSIDIAN_API_PORT: int = int(os.getenv("OBSIDIAN_API_PORT", "27123"))
OBSIDIAN_API_KEY: str = os.getenv("OBSIDIAN_API_KEY", "")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
POLL_INTERVAL: int = int(os.getenv("DISPATCHER_POLL_INTERVAL", "5"))
DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_API = "https://discord.com/api/v10"

# ── 헬퍼 ───────────────────────────────────────────────────────────────────────

_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = _FM_RE.match(text)
    if m:
        try:
            return yaml.safe_load(m.group(1)) or {}, text[m.end():]
        except yaml.YAMLError:
            return {}, text
    return {}, text


def update_frontmatter(filepath: Path, updates: dict) -> None:
    content = filepath.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(content)
    fm.update(updates)
    new_content = f"---\n{yaml.dump(fm, allow_unicode=True, default_flow_style=False)}---\n{body}"
    filepath.write_text(new_content, encoding="utf-8")


def ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ── Obsidian 지침 로더 ─────────────────────────────────────────────────────────

class ObsidianLoader:
    """Obsidian Vault에서 에이전트 지침을 로드한다.
    obsidian-local-rest-api 우선, 실패 시 직접 파일 읽기 폴백.
    """

    BASE_URL = f"https://127.0.0.1:{OBSIDIAN_API_PORT}/vault"

    def _api_get(self, vault_rel_path: str) -> str | None:
        if not OBSIDIAN_API_KEY:
            return None
        try:
            r = requests.get(
                f"{self.BASE_URL}/{vault_rel_path}",
                headers={"Authorization": f"Bearer {OBSIDIAN_API_KEY}"},
                verify=False,
                timeout=3,
            )
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        return None

    def load(self, vault_rel_path: str) -> str:
        """vault_rel_path: 'ObsidianVault' 아래 상대 경로 (예: '03_Projects/agents/mneme.md')"""
        content = self._api_get(vault_rel_path)
        if content:
            return content
        local = VAULT / vault_rel_path
        if local.exists():
            return local.read_text(encoding="utf-8")
        return ""

    def load_agent_instructions(self) -> str:
        """dispatcher + common philosophy 지침 합산."""
        dispatcher = self.load("03_Projects/agents/agent-dispatcher.md")
        philosophy = self.load("03_Projects/agents/COMMON-PHILOSOPHY.md")
        parts = []
        if dispatcher:
            parts.append(dispatcher)
        if philosophy:
            parts.append(philosophy)
        return "\n\n---\n\n".join(parts) if parts else ""


_loader = ObsidianLoader()


# ── 처리기 ─────────────────────────────────────────────────────────────────────

def _write_result(source_name: str, result_text: str, suffix: str = "result") -> Path:
    stem = re.sub(r"[^\w\-]", "_", source_name.replace(".md", ""))
    outfile = OUTBOX_CLAUDE / f"{ts()}_{stem}_{suffix}.md"
    outfile.write_text(
        f"---\ntype: result\nsource: {source_name}\ncreated: {iso()}\n---\n\n{result_text}\n",
        encoding="utf-8",
    )
    return outfile


def handle_via_api(body: str, system_extra: str = "") -> str:
    """Anthropic API로 직접 응답 생성."""
    instructions = _loader.load_agent_instructions()
    system = "\n\n".join(filter(None, [instructions, system_extra])).strip() or (
        "당신은 Obsidian 지식 관리 시스템과 연결된 AI 에이전트입니다. "
        "사용자의 요청에 간결하고 정확하게 한국어로 답변하세요."
    )
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": body.strip()}],
    )
    return resp.content[0].text


def handle_via_claude_code(task_prompt: str) -> tuple[str, bool]:
    """Claude Code CLI 스폰. (claude -p '...' --output-format text)"""
    print(f"  [Dispatcher] Spawning Claude Code CLI ...")
    result = subprocess.run(
        ["claude", "-p", task_prompt, "--output-format", "text"],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
        timeout=600,
    )
    if result.returncode == 0:
        return result.stdout.strip(), True
    return f"FAILED (code {result.returncode}):\n{result.stderr.strip()}", False


def send_discord_reply(channel_id: str, message: str) -> bool:
    """Discord 채널에 메시지 전송 (봇 토큰 사용)."""
    if not DISCORD_BOT_TOKEN or not channel_id:
        return False
    try:
        # Discord 2000자 제한
        chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
        for chunk in chunks:
            r = requests.post(
                f"{DISCORD_API}/channels/{channel_id}/messages",
                headers={
                    "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={"content": chunk},
                timeout=10,
            )
            if r.status_code not in (200, 201):
                print(f"  [Dispatcher] Discord reply failed: {r.status_code} {r.text[:100]}")
                return False
        return True
    except Exception as exc:
        print(f"  [Dispatcher] Discord reply error: {exc}")
        return False


def route_to_codex(filepath: Path, fm: dict, body: str) -> Path:
    """review_request → Codex outbox로 복사 후 상태 갱신."""
    task_id = fm.get("task_id", ts())
    dest = OUTBOX_CODEX / f"P1_{ts()}_{task_id}_routed.md"
    dest.write_text(filepath.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [Dispatcher] Routed to Codex: {dest.name}")
    return dest


# ── 태스크 처리 ────────────────────────────────────────────────────────────────

_IMPL_KEYWORDS = (
    "구현", "만들어", "작성해", "코드", "스크립트", "파일 생성",
    "implement", "create", "write code", "build",
)


def _is_implementation_request(body: str) -> bool:
    return any(kw in body for kw in _IMPL_KEYWORDS)


def process_file(filepath: Path) -> None:
    content = filepath.read_text(encoding="utf-8-sig")
    fm, body = parse_frontmatter(content)

    if fm.get("status") != "pending":
        return

    task_type = fm.get("type", "unknown")
    print(f"[Dispatcher] {filepath.name}  type={task_type}")

    # 처리 시작 표시
    update_frontmatter(filepath, {"status": "processing", "processing_started": iso()})

    try:
        if task_type == "review_request":
            result_file = route_to_codex(filepath, fm, body)
            update_frontmatter(filepath, {
                "status": "done",
                "processed_by": "AgentDispatcher",
                "processed_at": iso(),
                "output": str(result_file),
            })
            filepath.rename(COMPLETED / filepath.name)

        elif task_type == "implementation_request" or (
            task_type == "discord_intake" and _is_implementation_request(body)
        ):
            task_prompt = (
                f"# AgentBus 태스크\n\n"
                f"소스: {filepath.name}\n\n"
                f"{body.strip()}"
            )
            output, success = handle_via_claude_code(task_prompt)
            result_file = _write_result(filepath.name, output, "claude_code")
            status = "done" if success else "failed"
            update_frontmatter(filepath, {
                "status": status,
                "processed_by": "AgentDispatcher+ClaudeCode",
                "processed_at": iso(),
                "output": str(result_file),
            })
            dest_dir = COMPLETED if success else FAILED
            filepath.rename(dest_dir / filepath.name)

        else:
            # discord_intake (단순 Q&A) 및 기타 → Anthropic API
            output = handle_via_api(body)
            result_file = _write_result(filepath.name, output, "api")

            # discord_intake면 Discord 채널에도 답장
            if task_type == "discord_intake":
                channel_id = str(fm.get("channel_id", fm.get("author_id", "")))
                # channel_id가 없으면 DISCORD_CHANNEL_IDS 첫번째 사용
                if not channel_id or not channel_id.isdigit():
                    raw = os.getenv("DISCORD_CHANNEL_IDS", "")
                    channel_id = raw.split(",")[0].strip() if raw else ""
                if channel_id:
                    author = fm.get("author", "사용자")
                    reply_msg = f"**{author}님의 요청 처리 완료**\n\n{output}"
                    sent = send_discord_reply(channel_id, reply_msg)
                    print(f"  [Dispatcher] Discord reply {'sent' if sent else 'skipped (no token/channel)'}")

            update_frontmatter(filepath, {
                "status": "done",
                "processed_by": "AgentDispatcher+API",
                "processed_at": iso(),
                "output": str(result_file),
            })
            filepath.rename(COMPLETED / filepath.name)

        print(f"  [Dispatcher] Done → {result_file.name if 'result_file' in dir() else 'routed'}")

    except Exception as exc:
        print(f"  [Dispatcher] ERROR: {exc}")
        try:
            update_frontmatter(filepath, {
                "status": "failed",
                "error": str(exc)[:500],
                "processed_at": iso(),
            })
            filepath.rename(FAILED / filepath.name)
        except Exception:
            pass


# ── 메인 루프 ──────────────────────────────────────────────────────────────────

def watch() -> None:
    print(f"[Dispatcher] Started. Watching: {INBOX}")
    print(f"  poll_interval={POLL_INTERVAL}s  model={CLAUDE_MODEL}")
    while True:
        for fp in sorted(INBOX.glob("*.md")):
            if fp.name == ".gitkeep":
                continue
            content = fp.read_text(encoding="utf-8-sig", errors="ignore")
            fm, _ = parse_frontmatter(content)
            if fm.get("status") == "pending":
                process_file(fp)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    watch()
