import asyncio
import base64
import os
import subprocess
import tempfile
import time
from collections import deque
from typing import Optional

import aiohttp
import numpy as np


REMOTE_ASR_URL = os.environ.get("REMOTE_ASR_URL", "")
WHISPER_CPP_PATH = os.environ.get("WHISPER_CPP_PATH", "whisper.cpp")

POLICY_FAST = "FAST"
POLICY_DEGRADE = "DEGRADE"
POLICY_FAILOVER = "FAILOVER"

FAST_P50 = 300
FAST_P95 = 600
FAST_P99 = 900

DEGRADE_P50 = 450
DEGRADE_P95 = 900
DEGRADE_P99 = 1500

FAILOVER_P99 = 1500
FAILOVER_TIMEOUT_COUNT = 2

ROLLING_WINDOW = 100
CIRCUIT_BREAKER_SECONDS = 60
REMOTE_TIMEOUT_SECONDS = 2


class RollingMetrics:
    def __init__(self, maxlen: int = ROLLING_WINDOW):
        self._window: deque[float] = deque(maxlen=maxlen)

    def record(self, ms: float) -> None:
        self._window.append(ms)

    def percentile(self, p: float) -> float:
        if not self._window:
            return 0.0
        arr = np.array(self._window)
        return float(np.percentile(arr, p))

    def p50(self) -> float:
        return self.percentile(50)

    def p95(self) -> float:
        return self.percentile(95)

    def p99(self) -> float:
        return self.percentile(99)

    def __len__(self) -> int:
        return len(self._window)


class ASRRouter:
    def __init__(self):
        self._metrics = RollingMetrics()
        self._timeout_count = 0
        self._circuit_open_at: Optional[float] = None
        self._session: Optional[aiohttp.ClientSession] = None

    def record_latency(self, ms: float) -> None:
        self._metrics.record(ms)

    def get_policy(self) -> str:
        if len(self._metrics) == 0:
            return POLICY_FAST

        p50 = self._metrics.p50()
        p95 = self._metrics.p95()
        p99 = self._metrics.p99()

        if (
            p99 > FAILOVER_P99
            or self._timeout_count >= FAILOVER_TIMEOUT_COUNT
        ):
            return POLICY_FAILOVER

        if (
            p50 <= FAST_P50
            and p95 <= FAST_P95
            and p99 <= FAST_P99
        ):
            return POLICY_FAST

        if (
            p50 <= DEGRADE_P50
            and p95 <= DEGRADE_P95
            and p99 <= DEGRADE_P99
        ):
            return POLICY_DEGRADE

        return POLICY_FAILOVER

    def is_degrade_mode(self) -> bool:
        return self.get_policy() == POLICY_DEGRADE

    def _is_circuit_open(self) -> bool:
        if self._circuit_open_at is None:
            return False
        elapsed = time.monotonic() - self._circuit_open_at
        if elapsed >= CIRCUIT_BREAKER_SECONDS:
            self._circuit_open_at = None
            self._timeout_count = 0
            return False
        return True

    def _open_circuit(self) -> None:
        self._circuit_open_at = time.monotonic()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _call_remote(self, audio_bytes: bytes, sample_rate: int) -> dict:
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        payload = {"audio_b64": audio_b64, "sample_rate": sample_rate}

        session = await self._get_session()
        timeout = aiohttp.ClientTimeout(total=REMOTE_TIMEOUT_SECONDS)

        t0 = time.monotonic()
        try:
            async with session.post(
                REMOTE_ASR_URL, json=payload, timeout=timeout
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except asyncio.TimeoutError:
            self._timeout_count += 1
            raise
        elapsed_ms = (time.monotonic() - t0) * 1000
        self.record_latency(elapsed_ms)

        return {
            "type": "asr.partial",
            "text": data.get("text", ""),
            "latency_ms": data.get("latency_ms", elapsed_ms),
            "source": "remote",
        }

    async def _call_local(self, audio_bytes: bytes, sample_rate: int) -> dict:
        with tempfile.NamedTemporaryFile(suffix=".pcm", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                WHISPER_CPP_PATH,
                "--model", "Q5_K_M",
                "--length", "0.5",
                "--no-timestamps",
                tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()
            text = stdout.decode("utf-8", errors="replace").strip()
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        return {
            "type": "asr.final",
            "text": text,
            "confidence": None,
            "source": "local",
        }

    async def route(self, audio_bytes: bytes, sample_rate: int) -> dict:
        policy = self.get_policy()

        if policy == POLICY_FAILOVER or self._is_circuit_open():
            if not self._is_circuit_open():
                self._open_circuit()
            return await self._call_local(audio_bytes, sample_rate)

        try:
            result = await self._call_remote(audio_bytes, sample_rate)
            self._timeout_count = 0
            return result
        except Exception:
            self._timeout_count += 1
            new_policy = self.get_policy()
            if new_policy == POLICY_FAILOVER:
                self._open_circuit()
            return await self._call_local(audio_bytes, sample_rate)

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
