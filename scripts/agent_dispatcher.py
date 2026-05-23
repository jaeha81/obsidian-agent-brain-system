#!/usr/bin/env python3
"""
Agent Dispatcher — ObsidianVault/10_AgentBus/inbox/ 감시 → 지침 로드 → 실행 → 결과 기록

Flow:
  inbox/*.md (status: pending)
    → frontmatter 파싱 → 태스크 타입 분류
    → Obsidian 에이전트 지침 로드 (REST API 우선, 직접 파일 폴백)
    → 처리기 라우팅:
        discord_intake  → configured local agent one-shot
        implementation_request → configured local agent one-shot
        review_request  → Codex outbox 라우팅
        * 기타 → configured local agent 폴백
    → 결과 outbox/{worker}/ 저장 + inbox 상태 갱신

Requirements: pip install python-dotenv pyyaml requests
"""

import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv
from harness_router import build_development_brief, is_harness_router_enabled
from hermes_client import HermesError, run_hermes

# ── 환경 설정 ──────────────────────────────────────────────────────────────────

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
INBOX = VAULT / "10_AgentBus" / "inbox"
WORKER_NAME = os.getenv("AGENTBUS_WORKER_NAME", "Hermes")
OUTBOX_WORKER = VAULT / "10_AgentBus" / "outbox" / WORKER_NAME
OUTBOX_CODEX = VAULT / "10_AgentBus" / "outbox" / "Codex"
COMPLETED = VAULT / "10_AgentBus" / "completed"
FAILED = VAULT / "10_AgentBus" / "failed"

OBSIDIAN_API_PORT: int = int(os.getenv("OBSIDIAN_API_PORT", "27123"))
OBSIDIAN_API_KEY: str = os.getenv("OBSIDIAN_API_KEY", "")
AGENT_RUNTIME: str = os.getenv("AGENT_RUNTIME", "hermes")
HERMES_MODEL: str = os.getenv("HERMES_MODEL", "default")
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

def _read_optional(path: Path, max_chars: int = 6000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    return text[:max_chars]


def load_jh_role_context() -> str:
    shared = Path(os.getenv("JH_SHARED_PATH", "G:/내 드라이브/JH-SHARED"))
    room = Path(os.getenv("JH_AGENT_ROOM_PATH", "G:/내 드라이브/JH-Agent-Room"))
    parts = []
    for rel in (
        "00_SYSTEM/roles.md",
        "00_SYSTEM/agent-onboarding.md",
        "05_TASK_LOCKS/README.md",
        "04_DAILY_REPORTS/README.md",
    ):
        content = _read_optional(shared / rel)
        if content:
            parts.append(f"## JH-SHARED/{rel}\n{content}")
    room_readme = _read_optional(room / "README.md")
    if room_readme:
        parts.append(f"## JH-Agent-Room/README.md\n{room_readme}")
    return "\n\n---\n\n".join(parts)


def _write_result(source_name: str, result_text: str, suffix: str = "result") -> Path:
    stem = re.sub(r"[^\w\-]", "_", source_name.replace(".md", ""))
    OUTBOX_WORKER.mkdir(parents=True, exist_ok=True)
    outfile = OUTBOX_WORKER / f"{ts()}_{stem}_{suffix}.md"
    outfile.write_text(
        f"---\ntype: result\nsource: {source_name}\ncreated: {iso()}\n---\n\n{result_text}\n",
        encoding="utf-8",
    )
    return outfile


def _worker_suffix() -> str:
    return re.sub(r"[^\w\-]", "_", WORKER_NAME.lower())


def _safe_task_id(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", value.replace(".md", ""))
    return safe[:32] or ts()


def _build_harness_context(body: str, source_name: str) -> str:
    if not is_harness_router_enabled():
        return ""
    try:
        return build_development_brief(body, source_name=source_name)
    except Exception as exc:
        return (
            "## Harness Framework Routing\n"
            f"Harness router failed: {exc}\n"
            "Proceed with the JH role boundary and report the router failure."
        )


def _write_codex_review_request(source_name: str, result_file: Path, context: str) -> Path | None:
    if os.getenv("CODEX_REVIEW_ENABLED", "1").strip().lower() in {"0", "false", "no", "off"}:
        return None
    task_id = _safe_task_id(source_name)
    out_path = OUTBOX_WORKER / f"P2_{ts()}_Codex_{task_id}.md"
    out_path.write_text(
        f"""---
type: review_request
task_id: {task_id}
from: {WORKER_NAME}
to: Codex
priority: P2
status: pending
created: {iso()}
source: {source_name}
target_output: {result_file}
---

# Codex Review Request: {task_id}

## Review Target

- Source request: `{source_name}`
- Hermes result: `{result_file}`

## Review Scope

Review the implementation result independently. Verify actual files when paths are mentioned. Check Harness Framework fit, JH role compliance, correctness, tests, and security.

## Harness Context

{context[:5000] if context else "No Harness context was generated."}
""",
        encoding="utf-8",
    )
    return out_path


def _build_hermes_prompt(body: str, system_extra: str = "") -> str:
    instructions = _loader.load_agent_instructions()
    jh_roles = load_jh_role_context()
    system = "\n\n".join(filter(None, [instructions, jh_roles, system_extra])).strip() or (
        "You are Hermes, the AI agent connected to the Obsidian knowledge system. "
        "Answer clearly and act through the AgentBus conventions."
    )
    return (
        "# Obsidian AgentBus task\n\n"
        "Use these system instructions, then answer or act on the task.\n\n"
        "## System instructions\n"
        f"{system}\n\n"
        "## Task\n"
        f"{body.strip()}"
    )


def handle_via_hermes(body: str, system_extra: str = "") -> str:
    """Generate a response through configured local agent."""
    return run_hermes(_build_hermes_prompt(body, system_extra))


def handle_via_api(body: str, system_extra: str = "") -> str:
    """Compatibility wrapper: direct Q&A goes through configured local agent."""
    return handle_via_hermes(body, system_extra)


def handle_via_claude_code(task_prompt: str) -> tuple[str, bool]:
    """Compatibility wrapper: implementation tasks go through configured local agent."""
    print(f"  [Dispatcher] Spawning {WORKER_NAME} Agent ...")
    try:
        return run_hermes(task_prompt), True
    except HermesError as exc:
        return f"FAILED: {exc}", False


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
        if task_type == "dispatcher_test":
            output = run_hermes(body.strip())
            result_file = _write_result(filepath.name, output, _worker_suffix())
            update_frontmatter(filepath, {
                "status": "done",
                "processed_by": f"AgentDispatcher+{WORKER_NAME}",
                "processed_at": iso(),
                "output": str(result_file),
            })
            filepath.rename(COMPLETED / filepath.name)

        elif task_type == "claude_sync":
            # Obsidian CLAUDE_MASTER.md → ~/.claude/CLAUDE.md 동기화
            sync_script = Path(__file__).parent / "sync_claude_instructions.py"
            result = subprocess.run(
                ["python3", str(sync_script)],
                capture_output=True, text=True, encoding="utf-8"
            )
            output = (result.stdout + result.stderr).strip()
            success = result.returncode == 0
            result_file = _write_result(filepath.name, output, "sync")
            update_frontmatter(filepath, {
                "status": "done" if success else "failed",
                "processed_by": "AgentDispatcher",
                "processed_at": iso(),
                "output": str(result_file),
            })
            filepath.rename((COMPLETED if success else FAILED) / filepath.name)
            print(f"  [Dispatcher] claude_sync {'OK' if success else 'FAILED'}: {output[:80]}")

        elif task_type == "review_request":
            result_file = route_to_codex(filepath, fm, body)
            update_frontmatter(filepath, {
                "status": "done",
                "processed_by": "AgentDispatcher",
                "processed_at": iso(),
                "output": str(result_file),
            })
            filepath.rename(COMPLETED / filepath.name)

        elif task_type in {"implementation_request", "harness_development_request"} or (
            task_type == "discord_intake" and _is_implementation_request(body)
        ):
            task_body = f"Source file: {filepath.name}\n\n{body.strip()}"
            harness_context = _build_harness_context(body, filepath.name)
            task_prompt = _build_hermes_prompt(task_body, harness_context)
            output, success = handle_via_claude_code(task_prompt)
            result_file = _write_result(filepath.name, output, _worker_suffix())
            review_file = _write_codex_review_request(filepath.name, result_file, harness_context) if success else None
            if review_file:
                print(f"  [Dispatcher] Codex review requested: {review_file.name}")
            status = "done" if success else "failed"
            update_frontmatter(filepath, {
                "status": status,
                "processed_by": f"AgentDispatcher+{WORKER_NAME}",
                "processed_at": iso(),
                "output": str(result_file),
                "codex_review_request": str(review_file) if review_file else "",
            })
            dest_dir = COMPLETED if success else FAILED
            filepath.rename(dest_dir / filepath.name)

        else:
            # discord_intake (단순 Q&A) 및 기타 → Hermes Agent
            output = handle_via_api(body)
            result_file = _write_result(filepath.name, output, _worker_suffix())

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
                "processed_by": f"AgentDispatcher+{WORKER_NAME}",
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
    print(f"  poll_interval={POLL_INTERVAL}s  worker={WORKER_NAME}  runtime={AGENT_RUNTIME}  hermes_model={HERMES_MODEL}")
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
