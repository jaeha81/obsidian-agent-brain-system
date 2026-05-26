#!/usr/bin/env python3
"""
Bucky Worker Pool — 비동기 멀티태스크 실행기.
Discord 명령 수신 즉시 백그라운드 실행. 사용자는 대기 없이 다음 명령 가능.

P0 (2026-05-26): 현황판 debounce+Lock, SQLite hydrate, thread_id, mention 무력화
P1 (2026-05-26): auto-retry, escalation, codex feedback loop, AllowedMentions.none()
"""

import asyncio
import discord
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

_NO_MENTIONS = discord.AllowedMentions.none()

from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8", override=True)

if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

import task_queue as tq
from bucky_client import run_bucky, BuckyError

POOL_SIZE: int     = int(os.getenv("WORKER_POOL_SIZE", "5"))
TASK_TIMEOUT: int  = int(os.getenv("BUCKY_TIMEOUT", "900"))
MAX_RETRIES: int   = int(os.getenv("TASK_MAX_RETRIES", "2"))
RETRY_DELAY: int   = int(os.getenv("TASK_RETRY_DELAY", "5"))
CODEX_AUTO_REVIEW: bool = os.getenv("CODEX_REVIEW_ENABLED", "1") == "1"
VAULT        = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
CODEX_OUTBOX = VAULT / "10_AgentBus" / "outbox" / os.getenv("AGENTBUS_WORKER_NAME", "Bucky")

_BOARD_MIN_INTERVAL = 3.0   # edit 최소 간격(초) — rate-limit 방지
_REGISTRY_TTL       = 1800  # 완료 태스크 30분 후 registry 정리
_REVIEW_ISSUE_KEYWORDS = ("오류", "버그", "문제", "수정", "실패", "잘못", "누락", "이슈", "error", "fix")


# ── 유틸 ───────────────────────────────────────────────────────────────────────

def _sanitize(text: str, max_len: int = 50) -> str:
    """Discord mention 무력화 + 길이 제한."""
    text = re.sub(r"@(everyone|here)", "@ \\1", text)
    return text[:max_len]


def _dispatch_codex_file(task_id: str, title: str, body: str) -> str:
    CODEX_OUTBOX.mkdir(parents=True, exist_ok=True)
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = CODEX_OUTBOX / f"P2_{ts}_Codex_{task_id}.md"
    out.write_text(
        f"---\ntype: implementation_request\ntask_id: {task_id}\n"
        f"from: Bucky\nto: Codex\npriority: P2\nstatus: pending\n"
        f"created: {datetime.now().isoformat(timespec='seconds')}\n---\n\n"
        f"# {title}\n\n{body}\n",
        encoding="utf-8",
    )
    return str(out)


# ── WorkerPool ─────────────────────────────────────────────────────────────────

class WorkerPool:
    def __init__(self, pool_size: int = POOL_SIZE):
        self._semaphore        = asyncio.Semaphore(pool_size)
        self._discord_client   = None
        self._status_channel_id: str  = os.getenv("BUCKY_STATUS_CHANNEL_ID", "").strip()
        self._results_channel_id: str = ""
        self._active: dict[str, asyncio.Task] = {}

        # 현황판
        self._task_registry: dict[str, dict] = {}
        self._board_msg_id:  Optional[int]   = None
        self._last_board_edit: float         = 0.0
        self._board_lock     = asyncio.Lock()
        self._board_pending  = False  # 대기 중인 update가 있으면 중복 skip
        self._reviewed_tasks: set[str] = set()  # feedback loop 무한반복 방지

    # ── 초기화 ────────────────────────────────────────────────────────────────

    def set_discord(self, client) -> None:
        self._discord_client = client

    def set_board_message(self, msg_id: int) -> None:
        self._board_msg_id = msg_id

    def set_results_channel(self, channel_id: str) -> None:
        self._results_channel_id = channel_id.strip()

    def hydrate_from_db(self) -> None:
        """봇 재시작 시 SQLite 미완료 태스크를 registry에 로드 (Codex P2 반영)."""
        try:
            for task in tq.get_active():
                tid = task["id"]
                if tid not in self._task_registry:
                    self._task_registry[tid] = {
                        "agent":             task.get("agent", "bucky"),
                        "title":             _sanitize(task.get("title", "?"), 50),
                        "status":            task.get("status", "pending"),
                        "started_at":        None,
                        "ended_at":          None,
                        "thread_id":         None,
                        "origin_channel_id": None,
                    }
            print(f"[WorkerPool] hydrate 완료: {len(self._task_registry)}개 로드", flush=True)
        except Exception as e:
            print(f"[WorkerPool] hydrate 실패: {e}", flush=True)

    def register_task(self, task: dict, thread_id: int | None = None,
                      origin_channel_id: int | None = None,
                      requester_id: int | None = None) -> None:
        self._task_registry[task["id"]] = {
            "agent":             task.get("agent", "bucky"),
            "title":             _sanitize(task.get("title", task.get("body", "?")), 50),
            "status":            "pending",
            "started_at":        None,
            "ended_at":          None,
            "thread_id":         thread_id,
            "origin_channel_id": origin_channel_id,
            "requester_id":      requester_id,
        }

    # ── 채널 resolve ─────────────────────────────────────────────────────────

    async def _resolve_reply_channel(self, tid: str):
        """thread_id 또는 origin_channel_id로 Discord 채널/스레드 resolve."""
        if not self._discord_client:
            return None
        info = self._task_registry.get(tid, {})
        for ch_id in (info.get("thread_id"), info.get("origin_channel_id")):
            if not ch_id:
                continue
            try:
                ch = self._discord_client.get_channel(int(ch_id))
                if ch:
                    return ch
            except Exception:
                pass
        return None

    # ── 현황판 ────────────────────────────────────────────────────────────────

    def _build_board(self) -> str:
        now = datetime.now()
        aicon  = {"claude": "🧠", "codex": "⚡", "bucky": "🤖"}
        sicon  = {"pending": "⏳", "in_progress": "🔄", "submitted": "📤",
                  "done": "✅", "failed": "❌"}
        sorder = {"in_progress": 0, "pending": 1, "submitted": 2, "done": 3, "failed": 4}

        tasks = sorted(self._task_registry.items(),
                       key=lambda x: sorder.get(x[1]["status"], 9))

        lines = [
            f"📋 **Bucky 작업 현황판** | {now.strftime('%H:%M:%S')}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]

        done_shown = 0
        for tid, info in tasks:
            st = info["status"]
            if st in ("done", "failed"):
                if done_shown >= 5:
                    continue
                done_shown += 1

            icon  = sicon.get(st, "❓")
            ai    = aicon.get(info["agent"], "🤖")
            title = info["title"]
            short = tid[-6:] if len(tid) >= 6 else tid

            if st == "in_progress" and info["started_at"]:
                delta = (now - info["started_at"]).total_seconds()
                ts = f" | {int(delta//60)}분 {int(delta%60)}초"
            elif st in ("done", "failed") and info["ended_at"]:
                ts = f" | {info['ended_at'].strftime('%H:%M')} 완료"
            else:
                ts = ""

            lines.append(f"{icon} `{short}` {ai} {title}{ts}")

        if not tasks:
            lines.append("─ 대기 중인 작업 없음")

        active = sum(1 for _, i in tasks if i["status"] == "in_progress")
        lines += [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"워커 {active}/{POOL_SIZE} 사용 중  |  `!task <내용>` 으로 추가  |  `!현황` 상세",
        ]
        return "\n".join(lines)[:2000]

    async def _update_board(self) -> None:
        if not self._discord_client or not self._status_channel_id or not self._board_msg_id:
            return
        # 이미 대기 중인 update가 있으면 중복 edit 방지 (trailing 방식으로 최신 상태 보장)
        if self._board_pending:
            return
        self._board_pending = True
        async with self._board_lock:
            self._board_pending = False
            wait = _BOARD_MIN_INTERVAL - (time.monotonic() - self._last_board_edit)
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                ch = self._discord_client.get_channel(int(self._status_channel_id))
                if not ch:
                    return
                msg = await ch.fetch_message(self._board_msg_id)
                await msg.edit(content=self._build_board(), allowed_mentions=_NO_MENTIONS)
                self._last_board_edit = time.monotonic()
            except Exception as e:
                print(f"[WorkerPool] 현황판 edit 실패: {e}", flush=True)

    # ── 상태 이벤트 메시지 ────────────────────────────────────────────────────

    async def _send_status(self, content: str) -> None:
        if not self._discord_client or not self._status_channel_id:
            return
        try:
            ch = self._discord_client.get_channel(int(self._status_channel_id))
            if ch:
                await ch.send(content[:2000], allowed_mentions=_NO_MENTIONS)
        except Exception as e:
            print(f"[WorkerPool] status 전송 실패: {e}", flush=True)

    # ── 실행 ─────────────────────────────────────────────────────────────────

    async def _execute(self, task: dict) -> None:
        tid   = task["id"]
        agent = task["agent"]
        body  = task["body"]
        title = _sanitize(task.get("title", body), 50)

        AGENT_LABEL = {
            "claude": "🧠 CLAUDE", "codex": "⚡ CODEX", "bucky": "🤖 BUCKY",
        }.get(agent, agent.upper())

        async with self._semaphore:
            # ── 시작 ──────────────────────────────────────────────────────────
            tq.update(tid, "in_progress")
            if tid in self._task_registry:
                self._task_registry[tid].update(status="in_progress", started_at=datetime.now())
            asyncio.ensure_future(self._update_board())

            reply_ch = await self._resolve_reply_channel(tid)
            await self._send_status(f"🔄 `{tid}` {AGENT_LABEL} **{title}** 시작")
            if reply_ch:
                try:
                    await reply_ch.send(
                        f"🔄 `{tid[-6:]}` {AGENT_LABEL} **{title}**\n"
                        "작업 시작 — 완료 시 이 스레드에 결과를 전달합니다."
                    )
                except Exception:
                    pass

            try:
                # ── Codex 경로 ────────────────────────────────────────────────
                if agent == "codex":
                    file_path = await asyncio.to_thread(_dispatch_codex_file, tid, title, body)
                    tq.update(tid, "submitted", f"AgentBus: {Path(file_path).name}")
                    if tid in self._task_registry:
                        self._task_registry[tid].update(status="submitted", ended_at=datetime.now())
                    asyncio.ensure_future(self._update_board())

                    await self._send_status(
                        f"📤 `{tid}` ⚡ CODEX **{title}** → AgentBus 전달 완료"
                    )
                    if reply_ch:
                        try:
                            await reply_ch.send(
                                f"📤 `{tid[-6:]}` **{title}**\n"
                                "Codex AgentBus 전달 완료. Codex가 독립 처리 후 저장합니다."
                            )
                        except Exception:
                            pass

                # ── Claude / Bucky 경로 (retry + escalation) ─────────────────
                else:
                    system_prompt = None
                    if agent == "bucky":
                        system_prompt = os.getenv("BUCKY_SYSTEM_PROMPT")

                    result = None
                    last_err = None
                    for attempt in range(MAX_RETRIES + 1):
                        try:
                            result = await asyncio.to_thread(
                                run_bucky, body,
                                system_prompt=system_prompt,
                                timeout=TASK_TIMEOUT,
                            )
                            break  # 성공
                        except (BuckyError, Exception) as e:
                            last_err = e
                            if attempt < MAX_RETRIES:
                                wait_sec = RETRY_DELAY * (attempt + 1)
                                await self._send_status(
                                    f"⚠️ `{tid}` {AGENT_LABEL} **{title}** "
                                    f"실패({attempt+1}/{MAX_RETRIES}) — {wait_sec}초 후 재시도"
                                )
                                await asyncio.sleep(wait_sec)
                            else:
                                await self._escalate(tid, AGENT_LABEL, title, last_err, reply_ch)
                                return

                    if result is None:
                        return  # escalate에서 처리됨

                    tq.update(tid, "done", result)
                    if tid in self._task_registry:
                        self._task_registry[tid].update(status="done", ended_at=datetime.now())
                    asyncio.ensure_future(self._update_board())
                    try:
                        import goal_tracker as gt
                        gt.mark_task(tid, "done")
                    except Exception:
                        pass

                    summary = result[:150] + ("..." if len(result) > 150 else "")
                    await self._send_status(f"✅ `{tid}` {AGENT_LABEL} **{title}** 완료\n> {summary}")
                    if reply_ch:
                        try:
                            reg = self._task_registry.get(tid, {})
                            requester_id = reg.get("requester_id")
                            mention = f"<@{requester_id}> " if requester_id else ""
                            full = f"{mention}✅ `{tid[-6:]}` **{title}** 완료\n\n{result}"
                            _user_mentions = discord.AllowedMentions(users=True)
                            for i in range(0, len(full), 1900):
                                await reply_ch.send(full[i:i+1900], allowed_mentions=_user_mentions)
                        except Exception:
                            pass

                    # ── Codex 자동 검수 피드백 루프 ──────────────────────────────
                    if CODEX_AUTO_REVIEW and agent == "claude" and tid not in self._reviewed_tasks:
                        asyncio.ensure_future(self._auto_review(tid, title, body, result, reply_ch))

            except Exception as e:
                await self._on_fail(tid, AGENT_LABEL, title, f"오류: {e}", reply_ch)
            finally:
                self._active.pop(tid, None)
                asyncio.ensure_future(self._cleanup_task(tid, _REGISTRY_TTL))

    async def _on_fail(self, tid, label, title, msg, reply_ch) -> None:
        tq.update(tid, "failed", msg)
        if tid in self._task_registry:
            self._task_registry[tid].update(status="failed", ended_at=datetime.now())
        asyncio.ensure_future(self._update_board())
        await self._send_status(f"❌ `{tid}` {label} **{title}** {msg}")
        if reply_ch:
            try:
                await reply_ch.send(f"❌ `{tid[-6:]}` **{title}** {msg}")
            except Exception:
                pass

    async def _escalate(self, tid, label, title, err, reply_ch) -> None:
        """MAX_RETRIES 소진 후 에스컬레이션 — 사용자에게 직접 알림."""
        msg = f"CLI 실패: {err}"
        tq.update(tid, "failed", f"[에스컬레이션] {msg}")
        if tid in self._task_registry:
            self._task_registry[tid].update(status="failed", ended_at=datetime.now())
        asyncio.ensure_future(self._update_board())
        escalation_text = (
            f"🚨 **에스컬레이션** `{tid}` {label} **{title}**\n"
            f"{MAX_RETRIES}회 재시도 모두 실패 — 수동 개입 필요\n"
            f"> {msg}"
        )
        await self._send_status(escalation_text)
        if reply_ch:
            try:
                await reply_ch.send(escalation_text[:2000])
            except Exception:
                pass
        print(f"[WorkerPool] 에스컬레이션: {tid} — {msg}", flush=True)

    async def _auto_review(self, parent_tid: str, title: str,
                           original_body: str, result: str, reply_ch) -> None:
        """claude 완료 후 자동 Codex 검수 → 이슈 발견 시 claude 재지시."""
        self._reviewed_tasks.add(parent_tid)
        review_prompt = (
            f"다음 작업 결과를 검수해줘. 오류·누락·개선점이 있으면 구체적으로 지적해.\n\n"
            f"## 원래 요청\n{original_body}\n\n"
            f"## 결과\n{result}"
        )
        try:
            review_result = await asyncio.to_thread(
                run_bucky, review_prompt, timeout=min(TASK_TIMEOUT, 300)
            )
        except Exception as e:
            print(f"[WorkerPool] 자동 검수 실패 ({parent_tid}): {e}", flush=True)
            return

        has_issues = any(kw in review_result.lower() for kw in _REVIEW_ISSUE_KEYWORDS)
        await self._send_status(
            f"🔍 `{parent_tid}` 자동 검수 완료 — "
            f"{'⚠️ 이슈 발견, 재지시 중' if has_issues else '✅ 이상 없음'}"
        )

        if has_issues:
            # 검수 결과를 포함해 claude에 재지시
            followup_body = (
                f"이전 결과에 검수 피드백이 있어. 반영해서 다시 수행해줘.\n\n"
                f"## 원래 요청\n{original_body}\n\n"
                f"## 검수 피드백\n{review_result}"
            )
            followup_task = tq.add(f"[재지시] {title}", followup_body, "claude", "auto_review")
            followup_task["parent_task_id"] = parent_tid
            origin_ch_id = self._task_registry.get(parent_tid, {}).get("origin_channel_id")
            self.register_task(followup_task, origin_channel_id=origin_ch_id)
            self._reviewed_tasks.add(followup_task["id"])  # 재지시 태스크는 검수 안 함
            asyncio.ensure_future(self._execute(followup_task))
            self._active[followup_task["id"]] = asyncio.current_task()

            if reply_ch:
                try:
                    await reply_ch.send(
                        f"🔁 `{parent_tid[-6:]}` 검수 피드백 반영 — 재지시 실행 중\n"
                        f"```{review_result[:300]}```"
                    )
                except Exception:
                    pass

    async def _cleanup_task(self, tid: str, delay: int) -> None:
        await asyncio.sleep(delay)
        self._task_registry.pop(tid, None)
        self._reviewed_tasks.discard(tid)

    # ── 공개 API ─────────────────────────────────────────────────────────────

    def submit(self, task: dict, reply_channel=None,
               thread_id: int | None = None) -> str:
        """태스크 백그라운드 제출. 즉시 반환.

        Args:
            thread_id: 결과를 보낼 Discord 스레드 ID (객체 아님, Codex P2 반영)
            reply_channel: 폴백용 채널 객체 (thread_id 없을 때 사용)
        """
        if task["id"] not in self._task_registry:
            origin_id = getattr(reply_channel, "id", None) if reply_channel else None
            self.register_task(task, thread_id=thread_id, origin_channel_id=origin_id)
        else:
            if thread_id:
                self._task_registry[task["id"]]["thread_id"] = thread_id
            if reply_channel and not self._task_registry[task["id"]].get("origin_channel_id"):
                self._task_registry[task["id"]]["origin_channel_id"] = getattr(reply_channel, "id", None)

        coro = self._execute(task)
        t = asyncio.ensure_future(coro)
        self._active[task["id"]] = t
        return task["id"]

    def active_count(self) -> int:
        return len(self._active)

    def get_board_text(self) -> str:
        return self._build_board()


# ── 싱글턴 ────────────────────────────────────────────────────────────────────

_pool: Optional[WorkerPool] = None


def get_pool() -> WorkerPool:
    global _pool
    if _pool is None:
        _pool = WorkerPool()
    return _pool
