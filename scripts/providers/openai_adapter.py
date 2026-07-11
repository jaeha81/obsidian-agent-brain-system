#!/usr/bin/env python3
"""Bucky OS V3 — OpenAI 어댑터 (Stage 6, stub·disabled).

레지스트리 enabled:false — healthcheck가 항상 disabled를 반환한다 (AUDIT §3.5).
활성화 전 사용자 승인 필요. run은 안전 stub.
"""

from __future__ import annotations

from core.agent_result import AgentResult
from core.provider_adapter import ProviderAdapter
from core.task_spec import TaskSpec


class OpenAIAdapter(ProviderAdapter):
    name = "openai_gpt"

    def _execute(self, task_spec: TaskSpec, instruction: str) -> AgentResult:
        return self._failed("Stage 6 stub — openai_gpt는 disabled (활성화 전 사용자 승인 필요)")
