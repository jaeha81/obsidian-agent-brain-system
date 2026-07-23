#!/usr/bin/env python3
"""Bucky OS V3 — Gemini 어댑터 (Stage 8).

키 확인(GEMINI_API_KEY)은 베이스가 처리. _probe는 google-genai 패키지 존재만 추가 점검.
run()은 scripts/gemini_client.run_gemini()을 실제 호출한다 (도구 실행 불가 — 텍스트 응답 전용).
"""

from __future__ import annotations

from core.agent_result import AgentResult
from core.provider_adapter import HEALTH_FAILED, HEALTH_OK, Health, ProviderAdapter
from core.task_spec import TaskSpec

# task_type → gemini_client 역할(고정 5종). 매칭 없으면 "rag"(Vault 컨텍스트 기반 일반 응답).
_ROLE_BY_TASK_TYPE: dict[str, str] = {
    "content": "content",
    "doc": "content",
    "research": "research",
    "rag": "rag",
    "chat": "rag",
    "review": "validator",
    "validator": "validator",
}


class GeminiAdapter(ProviderAdapter):
    name = "gemini"
    execution_supported = True  # 실연동 — 단, 파일/도구 실행은 지원하지 않는 텍스트 전용 응답

    def _probe(self) -> Health:
        try:
            from google import genai  # noqa: F401
        except ImportError:
            return Health(self.name, HEALTH_FAILED, "google-genai 패키지 없음 (pip install google-genai)")
        return Health(self.name, HEALTH_OK, "키·패키지 존재 확인만 (실호출 없음)")

    def _select_role(self, task_spec: TaskSpec) -> str:
        return _ROLE_BY_TASK_TYPE.get((task_spec.task_type or "").lower().strip(), "rag")

    def _execute(self, task_spec: TaskSpec, instruction: str) -> AgentResult:
        import gemini_client

        role = self._select_role(task_spec)
        output = gemini_client.run_gemini(role, instruction)
        if output.startswith("❌"):
            return self._failed(output)
        return AgentResult(
            agent=self.name,
            status="completed",
            summary=output,
            commands_run=[f"gemini_client.run_gemini(role={role!r})"],
        )
