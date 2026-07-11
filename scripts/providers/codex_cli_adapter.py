#!/usr/bin/env python3
"""Bucky OS V3 — Codex CLI 어댑터 (Stage 6).

Codex는 독립 검수자(reviewer) — Claude 파이프라인이 어댑터 경유로 실행시키지 않는다
(레지스트리 notes 참조). healthcheck만 실동작, run은 안전 stub.
"""

from __future__ import annotations

from core.agent_result import AgentResult
from core.provider_adapter import HEALTH_FAILED, HEALTH_OK, Health, ProviderAdapter
from core.task_spec import TaskSpec


class CodexCliAdapter(ProviderAdapter):
    name = "codex_pro"

    def _probe(self) -> Health:
        import bucky_client

        if not bucky_client.is_codex_available():
            return Health(self.name, HEALTH_FAILED, f"CLI 없음: {bucky_client.codex_command()!r}")
        return Health(self.name, HEALTH_OK, f"CLI: {bucky_client.codex_command()}")

    def _execute(self, task_spec: TaskSpec, instruction: str) -> AgentResult:
        return self._failed("codex는 독립 검수 전용 — 어댑터 경유 실행 미지원 (Stage 6 stub)")
