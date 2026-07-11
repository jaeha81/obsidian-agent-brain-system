#!/usr/bin/env python3
"""Bucky OS V3 — Anthropic API 어댑터 (Stage 6).

키 확인(ANTHROPIC_API_KEY)은 베이스가 처리. run은 안전 stub — 실호출 경로는
Vercel 함수(api/) 등 별도이며(레지스트리 notes), 어댑터 실연동은 후속 Stage.
"""

from __future__ import annotations

from core.agent_result import AgentResult
from core.provider_adapter import HEALTH_OK, Health, ProviderAdapter
from core.task_spec import TaskSpec


class AnthropicApiAdapter(ProviderAdapter):
    name = "anthropic_api"

    def _probe(self) -> Health:
        return Health(self.name, HEALTH_OK, "env 키 존재 확인만 (실호출 없음)")

    def _execute(self, task_spec: TaskSpec, instruction: str) -> AgentResult:
        return self._failed("Stage 6 stub — Anthropic API 실연동 미구현")
