#!/usr/bin/env python3
"""
Bucky Worker Pool — 비동기 멀티태스크 실행기.
Discord 명령 수신 즉시 백그라운드 실행. 사용자는 대기 없이 다음 명령 가능.

라우팅:
  codex  → AgentBus outbox 파일 생성 (Codex 비동기 처리)
  claude → Claude CLI (run_bucky) 직접 실행
  bucky  → Claude CLI (run_bucky) Bucky 시스템 프롬프트 포함
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8", override=True)

if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

import task_queue as tq
from bucky_client import run_bucky, BuckyError

POOL_SIZE: int = int(os.getenv("WORKER_POOL_SIZE", "5"))
TASK_TIMEOUT: int = int(os.getenv("BUCKY_TIMEOUT", "900"))
VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
CODEX_OUTBOX = VAULT / "10_AgentBus" / "outbox" / os.getenv("AGENTBUS_WORKER_NAME", "Bucky")


def _dispatch_codex_file(task_id: str, title: str, body: str) -> str:
    """Codex AgentBus outbox에 태스크 파일 생성."""
    CODEX_OUTBOX.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = CODEX_OUTBOX / f"P2_{ts}_Codex_{task_id}.md"
    now_iso = datetime.now().isoformat(timespec="seconds")
    out_path.write_text(
        f"---\ntype: implementation_request\ntask_id: {task_id}\nfrom: Bucky\nto: Codex\n"
        f"priority: P2\nstatus: pending\ncreated: {now_iso}\n---\n\n# {title}\n\n{body}\n",
        encoding="utf-8",
    )
    return str(out_path)


class WorkerPool:
    def __init__(self, pool_size: int = POOL_SIZE):
        self._semaphore = asyncio.Semaphore(pool_size)
        self._discord_client = None
        self._status_channel_id: str = os.getenv("BUCKY_STATUS_CHANNEL_ID", "").strip()
        self._active: dict[str, asyncio.Task] = {}

    def set_discord(self, client) -> None:
        self._discord_client = client

    async def _send_status(self, content: str) -> None:
        if not self._discord_client or not self._status_channel_id:
            return
        try:
            ch = self._discord_client.get_channel(int(self._status_channel_id))
            if ch:
                await ch.send(content[:2000])
        except Exception as e:
            print(f"[WorkerPool] status 채널 전송 실패: {e}", flush=True)

    async def _execute(self, task: dict, reply_channel=None) -> None:
        tid = task["id"]
        agent = task["agent"]
        body = task["body"]
        title = task["title"]

        async with self._semaphore:
            tq.update(tid, "in_progress")
            agent_label = {"claude": "🧠 CLAUDE", "codex": "⚡ CODEX", "bucky": "🤖 BUCKY"}.get(agent, agent.upper())
            await self._send_status(f"🔄 `{tid}` {agent_label} **{title}** 시작")
            if reply_channel:
                try:
                    await reply_channel.send(f"🔄 `{tid}` {agent_label} **{title}** 백그라운드 실행 중...")
                except Exception:
                    pass

            try:
                if agent == "codex":
                    file_path = await asyncio.to_thread(_dispatch_codex_file, tid, title, body)
                    tq.update(tid, "submitted", f"AgentBus 전달: {Path(file_path).name}")
                    await self._send_status(
                        f"📤 `{tid}` ⚡ CODEX **{title}** → AgentBus 전달 완료\n"
                        f"   Codex가 처리 후 outbox에 결과 저장"
                    )
                    if reply_channel:
                        try:
                            await reply_channel.send(
                                f"📤 `{tid}` **{title}** → Codex AgentBus 전달 완료\n"
                                f"Codex가 독립 처리 후 결과 저장합니다."
                            )
                        except Exception:
                            pass
                else:
                    # claude / bucky → Claude CLI 직접 실행
                    system_prompt = None
                    if agent == "bucky":
                        system_prompt = os.getenv(
                            "BUCKY_SYSTEM_PROMPT",
                            "당신은 Bucky입니다. Obsidian 지식 관리 시스템과 연결된 AI 에이전트.",
                        )
                    result = await asyncio.to_thread(
                        run_bucky, body, system_prompt=system_prompt, timeout=TASK_TIMEOUT
                    )
                    tq.update(tid, "done", result)
                    summary = result[:150] + ("..." if len(result) > 150 else "")
                    await self._send_status(
                        f"✅ `{tid}` {agent_label} **{title}** 완료\n> {summary}"
                    )
                    if reply_channel:
                        try:
                            full_reply = f"✅ `{tid}` **{title}** 완료\n\n{result}"
                            # 2000자 초과 시 분할
                            for i in range(0, len(full_reply), 1900):
                                await reply_channel.send(full_reply[i:i+1900])
                        except Exception:
                            pass

            except BuckyError as e:
                tq.update(tid, "failed", f"BuckyError: {e}")
                await self._send_status(f"❌ `{tid}` {agent_label} **{title}** CLI 실패: {e}")
            except Exception as e:
                tq.update(tid, "failed", str(e))
                await self._send_status(f"❌ `{tid}` {agent_label} **{title}** 오류: {e}")
            finally:
                self._active.pop(tid, None)

    def submit(self, task: dict, reply_channel=None) -> str:
        """태스크를 비동기 백그라운드로 제출. 즉시 반환."""
        coro = self._execute(task, reply_channel)
        t = asyncio.ensure_future(coro)
        self._active[task["id"]] = t
        return task["id"]

    def active_count(self) -> int:
        return len(self._active)


_pool: Optional[WorkerPool] = None


def get_pool() -> WorkerPool:
    global _pool
    if _pool is None:
        _pool = WorkerPool()
    return _pool
