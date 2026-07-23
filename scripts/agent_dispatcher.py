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
from bucky_client import BuckyError, run_bucky
from harness_router import build_development_brief, is_harness_router_enabled

try:
    from agent_keyword_router import log_routing as _kw_log_routing
except ImportError:
    def _kw_log_routing(body: str, source: str = "") -> str:  # type: ignore[misc]
        return ""

# ── 환경 설정 ──────────────────────────────────────────────────────────────────

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8-sig", override=True)

VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
INBOX = VAULT / "10_AgentBus" / "inbox"
WORKER_NAME = os.getenv("AGENTBUS_WORKER_NAME", "Bucky")
OUTBOX_WORKER = VAULT / "10_AgentBus" / "outbox" / WORKER_NAME
OUTBOX_CODEX = VAULT / "10_AgentBus" / "outbox" / "Codex"
COMPLETED = VAULT / "10_AgentBus" / "completed"
FAILED = VAULT / "10_AgentBus" / "failed"
PENDING_APPROVAL = VAULT / "10_AgentBus" / "pending_approval"

OBSIDIAN_API_PORT: int = int(os.getenv("OBSIDIAN_API_PORT", "27123"))
OBSIDIAN_API_KEY: str = os.getenv("OBSIDIAN_API_KEY", "")
POLL_INTERVAL: int = int(os.getenv("DISPATCHER_POLL_INTERVAL", "5"))
AGENT_RUNTIME: str = os.getenv("AGENT_RUNTIME", "claude_cli")
HERMES_MODEL: str = os.getenv("HERMES_MODEL", "claude-sonnet-4-6")
DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_API = "https://discord.com/api/v10"

WIKI_DIR: Path = VAULT / "02_Wiki"
WIKI_AUTOWRITE_ENABLED: bool = os.getenv("WIKI_AUTOWRITE_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}
WIKI_TASK_TYPES = {"raw_text", "document_review", "voice_transcript", "video_transcript"}

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
    text = _FM_RE.sub("", text, count=1).strip()
    return text[:max_chars]


def load_jh_role_context() -> str:
    parts = []
    for vault_rel in (
        "03_Projects/agents/roles.md",
        "03_Projects/agents/onboarding.md",
        "00_System/ROUTING_RULES.md",
        "06_Context_Packs/bucky-agent-os-legacy-rules.md",
        "06_Context_Packs/bucky-context-efficiency-goal-mode.md",
    ):
        content = _read_optional(VAULT / vault_rel)
        if content:
            parts.append(f"## ObsidianVault/{vault_rel}\n{content}")

    legacy_enabled = os.getenv("BUCKY_ENABLE_LEGACY_CONTEXT", "0").strip().lower() in {"1", "true", "yes", "on"}
    legacy_shared = os.getenv("JH_SHARED_PATH", "").strip()
    if legacy_enabled and legacy_shared:
        shared = Path(legacy_shared)
        for rel in ("00_SYSTEM/roles.md", "00_SYSTEM/agent-onboarding.md"):
            content = _read_optional(shared / rel)
            if content:
                parts.append(
                    f"## Legacy reference only: JH-SHARED/{rel}\n"
                    f"{content}"
                )
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
- Bucky result: `{result_file}`

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
        "You are Bucky, the main Obsidian orchestrator agent. "
        "Analyze the request, route work to Claude Code or Codex when needed, "
        "and act through the AgentBus conventions."
    )
    return (
        "# Obsidian AgentBus task\n\n"
        "Use these system instructions, then answer or act on the task.\n\n"
        "## System instructions\n"
        f"{system}\n\n"
        "## Task\n"
        f"{body.strip()}"
    )


def handle_via_bucky(body: str, system_extra: str = "") -> str:
    """Bucky Agent (Claude CLI 구독)로 요청 처리."""
    # Hermes 비서 응답 → task_type='chat' (Sonnet 기본, 한도 시 폴백)
    return run_bucky(_build_hermes_prompt(body, system_extra), task_type="chat")


def handle_via_claude_code(task_prompt: str) -> tuple[str, bool]:
    """Compatibility wrapper: implementation tasks go through configured local agent."""
    print(f"  [Dispatcher] Spawning {WORKER_NAME} Agent ...")
    try:
        # 구현 작업 → task_type='implementation' (Sonnet 기본)
        return run_bucky(task_prompt, task_type="implementation"), True
    except Exception as exc:
        return f"FAILED: {type(exc).__name__}: {exc}", False


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


# ── LLM Wiki 자동 생성 ────────────────────────────────────────────────────────

_WIKI_PROMPT_TEMPLATE = """\
아래 원문을 분석해서 Obsidian 마크다운 위키 페이지를 한 개 작성해줘.

## 출력 규칙 (반드시 준수)
1. 첫 줄: `TITLE: <제목>` (파일명으로 사용, 특수문자 금지)
2. 둘째 줄: `CATEGORY: <카테고리>` (영문 소문자, 슬래시 허용 예: tech/ai)
3. 셋째 줄부터: 실제 마크다운 위키 본문
   - 요약 섹션 (`## 요약`)
   - 핵심 개념 섹션 (`## 핵심 개념`) — 엔티티를 [[wikilink]] 형태로 표기
   - 관련 주제 섹션 (`## 관련 주제`) — [[wikilink]] 목록
   - 출처 섹션 (`## 출처`) — source_file 명시

## 원문
source_file: {source_file}
task_type: {task_type}

{body}
"""


def generate_wiki_entry(body: str, source_file: str, task_type: str) -> tuple[str, str, str]:
    """LLM을 호출해 위키 제목·카테고리·본문을 반환한다."""
    prompt = _WIKI_PROMPT_TEMPLATE.format(
        source_file=source_file,
        task_type=task_type,
        body=body[:6000],
    )
    raw = handle_via_bucky(prompt)

    lines = raw.strip().splitlines()
    title = "untitled"
    category = "inbox"
    body_start = 0

    for i, line in enumerate(lines):
        if line.startswith("TITLE:"):
            title = re.sub(r"[^\w가-힣\- ]", "", line[6:].strip())[:60] or "untitled"
        elif line.startswith("CATEGORY:"):
            category = re.sub(r"[^\w/\-]", "", line[9:].strip().lower()) or "inbox"
        elif title != "untitled" and category != "inbox":
            body_start = i
            break

    wiki_body = "\n".join(lines[body_start:]).strip()
    return title, category, wiki_body


def write_wiki_file(title: str, category: str, wiki_body: str, source_file: str) -> Path:
    """ObsidianVault/02_Wiki/{category}/{title}.md 에 위키 파일을 저장한다."""
    dest_dir = WIKI_DIR / category
    dest_dir.mkdir(parents=True, exist_ok=True)

    safe_title = re.sub(r"[^\w가-힣\- ]", "_", title).strip()
    dest = dest_dir / f"{safe_title}.md"

    # 동명 파일 충돌 방지
    if dest.exists():
        dest = dest_dir / f"{safe_title}_{datetime.now().strftime('%H%M%S')}.md"

    frontmatter = (
        f"---\n"
        f"title: {title}\n"
        f"category: {category}\n"
        f"source_file: {source_file}\n"
        f"created: {iso()}\n"
        f"tags:\n  - llm-wiki\n  - auto-generated\n"
        f"---\n\n"
    )
    dest.write_text(frontmatter + wiki_body + "\n", encoding="utf-8")
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

    # 승인 게이트: requires_approval: true 이면 pending_approval/ 로 이동
    if fm.get("requires_approval", False):
        PENDING_APPROVAL.mkdir(parents=True, exist_ok=True)
        dest = PENDING_APPROVAL / filepath.name
        update_frontmatter(filepath, {
            "status": "awaiting_approval",
            "queued_at": iso(),
            "approval_note": "requires_approval=true — approve_task.py로 승인하거나 frontmatter에서 requires_approval을 false로 변경",
        })
        filepath.rename(dest)
        print(f"[Dispatcher] ⏸ awaiting approval: {filepath.name} → pending_approval/")
        return

    task_type = fm.get("type", "unknown")
    print(f"[Dispatcher] {filepath.name}  type={task_type}")

    # 키워드 라우팅 힌트 로그 (기존 라우팅 유지 — 참고용)
    kw_hint = _kw_log_routing(body, source=filepath.stem[:20])
    if kw_hint:
        print(f"  {kw_hint}")

    # 처리 시작 표시
    update_frontmatter(filepath, {"status": "processing", "processing_started": iso()})

    try:
        if task_type == "dispatcher_test":
            # dispatcher_test → 짧은 단발 응답 → chat (Sonnet 기본)
            output = run_bucky(body.strip(), task_type="chat")
            result_file = _write_result(filepath.name, output, _worker_suffix())
            update_frontmatter(filepath, {
                "status": "done",
                "processed_by": f"AgentDispatcher+{WORKER_NAME}",
                "processed_at": iso(),
                "output": str(result_file),
            })
            filepath.rename(COMPLETED / filepath.name)

        elif task_type == "claude_sync":
            # Repo CLAUDE.md and the user's real global ~/.claude/CLAUDE.md are
            # independently maintained (different content/purpose) — never
            # auto-overwrite the global file. Only run --check here; an actual
            # sync requires explicit manual approval and a manual script run.
            sync_script = Path(__file__).parent / "sync_claude_instructions.py"
            result = subprocess.run(
                ["python3", str(sync_script), "--check"],
                capture_output=True, text=True, encoding="utf-8"
            )
            output = (result.stdout + result.stderr).strip()
            if result.returncode == 0:
                status, folder = "done", COMPLETED
            elif result.returncode == 2:
                status, folder = "failed", FAILED
                output += "\n[Dispatcher] sync needed but auto-write is disabled — run scripts/sync_claude_instructions.py manually after user approval."
            else:
                status, folder = "failed", FAILED
            result_file = _write_result(filepath.name, output, "sync")
            update_frontmatter(filepath, {
                "status": status,
                "processed_by": "AgentDispatcher",
                "processed_at": iso(),
                "output": str(result_file),
            })
            filepath.rename(folder / filepath.name)
            print(f"  [Dispatcher] claude_sync {status.upper()}: {output[:80]}")

        elif task_type == "review_request":
            result_file = route_to_codex(filepath, fm, body)
            update_frontmatter(filepath, {
                "status": "done",
                "processed_by": "AgentDispatcher",
                "processed_at": iso(),
                "output": str(result_file),
            })
            filepath.rename(COMPLETED / filepath.name)

        elif task_type in WIKI_TASK_TYPES and WIKI_AUTOWRITE_ENABLED:
            source_file = fm.get("source_file", filepath.name)
            print(f"  [Dispatcher] Wiki auto-write: {source_file}")
            title, category, wiki_body = generate_wiki_entry(body, source_file, task_type)
            wiki_file = write_wiki_file(title, category, wiki_body, source_file)
            result_text = f"Wiki created: `{wiki_file.relative_to(VAULT)}`\nTitle: {title}\nCategory: {category}"
            result_file = _write_result(filepath.name, result_text, "wiki")
            print(f"  [Dispatcher] Wiki → {wiki_file}")
            update_frontmatter(filepath, {
                "status": "done",
                "processed_by": f"AgentDispatcher+{WORKER_NAME}",
                "processed_at": iso(),
                "output": str(wiki_file),
            })
            filepath.rename(COMPLETED / filepath.name)

        elif task_type == "discord_intake" and fm.get("source") == "realtime_bot":
            # bot이 이미 실시간으로 답변한 메시지 — 재처리 없이 아카이빙만
            update_frontmatter(filepath, {
                "status": "archived",
                "processed_by": "AgentDispatcher",
                "processed_at": iso(),
                "note": "realtime_bot이 이미 답변함. dispatcher 재처리 생략.",
            })
            filepath.rename(COMPLETED / filepath.name)
            print(f"  [Dispatcher] Archived (realtime_bot already replied)")

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
            # discord_intake 구현 요청이면 Discord에 완료 알림
            if task_type == "discord_intake" and success:
                channel_id = str(fm.get("channel_id", ""))
                if not channel_id or not channel_id.isdigit():
                    channel_id = os.getenv("DISCORD_CHANNEL_IDS", "").split(",")[0].strip()
                if channel_id:
                    author = fm.get("author", "사용자")
                    send_discord_reply(channel_id, f"✅ **{author}님의 구현 요청 완료**\n\n{output[:1800]}")
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
            # 기타 → Bucky Agent (Q&A 폴백)
            output = handle_via_bucky(body)
            result_file = _write_result(filepath.name, output, _worker_suffix())

            # discord_intake이면 Discord 채널에 답장 (channel_id 필드 우선)
            if task_type == "discord_intake":
                channel_id = str(fm.get("channel_id", ""))
                if not channel_id or not channel_id.isdigit():
                    channel_id = os.getenv("DISCORD_CHANNEL_IDS", "").split(",")[0].strip()
                if channel_id:
                    author = fm.get("author", "사용자")
                    sent = send_discord_reply(channel_id, f"**{author}** {output}")
                    print(f"  [Dispatcher] Discord reply {'sent' if sent else 'skipped'}")

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

def _run_launch_gate() -> None:
    """시작 전 bucky_os_gate.py --fast 실행. 실패해도 경고만 출력, 중단하지 않음."""
    gate_script = Path(__file__).parent / "bucky_os_gate.py"
    if not gate_script.exists():
        print("[Dispatcher] WARN: bucky_os_gate.py not found, skipping launch gate")
        return
    try:
        r = subprocess.run(
            ["python", "-X", "utf8", str(gate_script), "--fast"],
            capture_output=True, text=True, encoding="utf-8", timeout=15
        )
        first_line = (r.stdout or "").splitlines()[0] if r.stdout else "(no output)"
        if r.returncode == 0:
            print(f"[Dispatcher] launch gate: {first_line}")
        else:
            print(f"[Dispatcher] WARN launch gate failed: {first_line}")
    except Exception as e:
        print(f"[Dispatcher] WARN launch gate error: {e}")


QUEUE_AUDIT_INTERVAL: int = int(os.getenv("QUEUE_AUDIT_INTERVAL", "300"))   # 5분
SYNC_SENTINEL_INTERVAL: int = int(os.getenv("SYNC_SENTINEL_INTERVAL", "600"))  # 10분

_last_queue_audit: float = 0.0
_last_sync_sentinel: float = 0.0


def _run_periodic_tasks(now: float) -> None:
    global _last_queue_audit, _last_sync_sentinel
    scripts_dir = Path(__file__).parent

    if now - _last_queue_audit >= QUEUE_AUDIT_INTERVAL:
        audit_script = scripts_dir / "agentbus_queue_audit.py"
        if audit_script.exists():
            try:
                r = subprocess.run(
                    ["python", "-X", "utf8", str(audit_script), "--json"],
                    capture_output=True, text=True, encoding="utf-8", timeout=30, cwd=str(audit_script.parent.parent)
                )
                first = (r.stdout or "").splitlines()[0] if r.stdout else "(no output)"
                print(f"[Dispatcher] queue_audit: {first}")
            except Exception as e:
                print(f"[Dispatcher] WARN queue_audit: {e}")
        _last_queue_audit = now

    if now - _last_sync_sentinel >= SYNC_SENTINEL_INTERVAL:
        sentinel_script = scripts_dir / "sync_sentinel.py"
        if sentinel_script.exists():
            try:
                r = subprocess.run(
                    ["python", "-X", "utf8", str(sentinel_script), "--json"],
                    capture_output=True, text=True, encoding="utf-8", timeout=30, cwd=str(sentinel_script.parent.parent)
                )
                first = (r.stdout or "").splitlines()[0] if r.stdout else "(no output)"
                print(f"[Dispatcher] sync_sentinel: {first}")
            except Exception as e:
                print(f"[Dispatcher] WARN sync_sentinel: {e}")
        _last_sync_sentinel = now


def watch() -> None:
    _run_launch_gate()
    print(f"[Dispatcher] Started. Watching: {INBOX}")
    print(f"  poll_interval={POLL_INTERVAL}s  worker={WORKER_NAME}  runtime={AGENT_RUNTIME}  hermes_model={HERMES_MODEL}")
    print(f"  queue_audit_interval={QUEUE_AUDIT_INTERVAL}s  sync_sentinel_interval={SYNC_SENTINEL_INTERVAL}s")
    while True:
        now = time.time()
        _run_periodic_tasks(now)
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
