#!/usr/bin/env python3
"""Bucky OS V3 — Claude CLI 어댑터 (Stage 6).

기존 scripts/bucky_client.py를 내부 호출하는 호환 래퍼 — 기존 경로 무파손.
모델 티어 라우팅(task_type → haiku/sonnet/opus)도 bucky_client.resolve_model에 위임.
"""

from __future__ import annotations

from core.agent_result import AgentResult
from core.provider_adapter import HEALTH_FAILED, HEALTH_OK, Health, ProviderAdapter
from core.task_spec import TaskSpec


class ClaudeCliAdapter(ProviderAdapter):
    name = "claude_code"

    def _probe(self) -> Health:
        import bucky_client

        if not bucky_client.is_bucky_available():
            return Health(self.name, HEALTH_FAILED, f"CLI 없음: {bucky_client.bucky_command()!r}")
        return Health(self.name, HEALTH_OK, f"CLI: {bucky_client.bucky_command()}")

    def _select_model(self, task_spec: TaskSpec) -> str:
        import bucky_client

        return bucky_client.resolve_model(task_spec.task_type or None)

    def _execute(self, task_spec: TaskSpec, instruction: str) -> AgentResult:
        import bucky_client

        output = bucky_client.run_bucky(instruction, task_type=task_spec.task_type or None)
        return AgentResult(
            agent=self.name,
            status="completed",
            summary=output,
            commands_run=[f"{bucky_client.bucky_command()} --print --model {self._select_model(task_spec)}"],
        )
