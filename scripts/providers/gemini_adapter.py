#!/usr/bin/env python3
"""Bucky OS V3 — Gemini 어댑터 (Stage 6).

키 확인(GEMINI_API_KEY)은 베이스가 처리. _probe는 google-genai 패키지 존재만 추가 점검.
run은 안전 stub — 실연동(scripts/gemini_client.py 경유)은 Stage 8 이후.
"""

from __future__ import annotations

from core.agent_result import AgentResult
from core.provider_adapter import HEALTH_FAILED, HEALTH_OK, Health, ProviderAdapter
from core.task_spec import TaskSpec


class GeminiAdapter(ProviderAdapter):
    name = "gemini"

    def _probe(self) -> Health:
        try:
            from google import genai  # noqa: F401
        except ImportError:
            return Health(self.name, HEALTH_FAILED, "google-genai 패키지 없음 (pip install google-genai)")
        return Health(self.name, HEALTH_OK, "키·패키지 존재 확인만 (실호출 없음)")

    def _execute(self, task_spec: TaskSpec, instruction: str) -> AgentResult:
        return self._failed("Stage 6 stub — gemini_client 실연동은 Stage 8 이후")
