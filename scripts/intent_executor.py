#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from obsidian_voice_logger import logger

BUCKY_API_URL = os.environ.get("BUCKY_API_URL", "http://localhost:8765/message")
OBSIDIAN_API_URL = os.environ.get("OBSIDIAN_API_URL", "http://localhost:27123")
CLAUDE_MODEL = "claude-sonnet-4-6"

_CODEX_KEYWORDS = re.compile(
    r"개발|코드|api|만들어|수정|리팩토링", re.IGNORECASE
)
_CLAUDE_KEYWORDS = re.compile(
    r"분석|검토|리뷰|검증|설명", re.IGNORECASE
)
_OBSIDIAN_KEYWORDS = re.compile(
    r"옵시디언|저장|노트|정리|검색", re.IGNORECASE
)


class IntentExecutor:

    def classify_intent(self, text: str) -> str:
        # Claude keywords checked before Codex: analysis/review verbs win over
        # generic "code" noun when both appear (e.g. "코드 검토해줘").
        if _CLAUDE_KEYWORDS.search(text):
            return "claude"
        if _CODEX_KEYWORDS.search(text):
            return "codex"
        if _OBSIDIAN_KEYWORDS.search(text):
            return "obsidian"
        return "bucky"

    async def execute(self, event: dict) -> dict:
        if event.get("type") != "asr.final":
            return {"status": "ignored", "reason": "not asr.final"}

        text: str = event.get("text", "").strip()
        if not text:
            return {"status": "ignored", "reason": "empty text"}

        agent = self.classify_intent(text)

        try:
            if agent == "codex":
                result = await self._route_codex(text, event)
            elif agent == "claude":
                result = await self._route_claude(text)
            elif agent == "obsidian":
                result = await self._route_obsidian(text)
            else:
                result = await self._route_bucky(text)
        except Exception as exc:
            error_msg = str(exc)
            logger.log_error(event, agent, error_msg)
            return {"status": "error", "agent": agent, "reason": error_msg}

        logger.log_final(event, agent, result)
        return result

    async def _route_bucky(self, text: str) -> dict:
        payload = {"message": text}
        async with aiohttp.ClientSession() as session:
            async with session.post(BUCKY_API_URL, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
                data = await resp.json()
        return {"status": "ok", "agent": "bucky", "response": data}

    async def _route_codex(self, text: str, event: dict) -> dict:
        task_id = f"VOICE_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        codex_script = str(SCRIPTS / "codex_request.py")

        proc = await asyncio.create_subprocess_exec(
            sys.executable, codex_script,
            "--task-id", task_id,
            "--subject", text,
            "--priority", "P1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

        if proc.returncode != 0:
            raise RuntimeError(stderr.decode("utf-8", errors="replace").strip())

        output = stdout.decode("utf-8", errors="replace").strip()
        return {"status": "ok", "agent": "codex", "task_id": task_id, "detail": output}

    async def _route_claude(self, text: str) -> dict:
        import anthropic

        client = anthropic.AsyncAnthropic()
        message = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": text}],
        )
        reply = message.content[0].text if message.content else ""
        return {"status": "ok", "agent": "claude", "response": reply}

    async def _route_obsidian(self, text: str) -> dict:
        payload = {
            "content": text,
            "created": datetime.now().isoformat(timespec="seconds"),
        }
        obsidian_token = os.environ.get("OBSIDIAN_REST_API_KEY", "")
        headers = {}
        if obsidian_token:
            headers["Authorization"] = f"Bearer {obsidian_token}"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OBSIDIAN_API_URL}/vault/voice-inbox/",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                resp.raise_for_status()
                try:
                    data = await resp.json()
                except Exception:
                    data = {"raw": await resp.text()}

        return {"status": "ok", "agent": "obsidian", "response": data}


async def _main_demo() -> None:
    executor = IntentExecutor()
    test_events = [
        {"type": "asr.final", "text": "API 엔드포인트 만들어줘", "source": "local"},
        {"type": "asr.final", "text": "이 코드 검토해줘", "source": "local"},
        {"type": "asr.final", "text": "노트 저장해줘", "source": "local"},
        {"type": "asr.partial", "text": "부분 인식", "source": "remote"},
        {"type": "asr.final", "text": "오늘 할 일 뭐야", "source": "local"},
    ]
    for evt in test_events:
        result = await executor.execute(evt)
        print(f"[{evt['type']}] {evt['text']!r} → {result}")


if __name__ == "__main__":
    asyncio.run(_main_demo())
