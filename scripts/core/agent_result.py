#!/usr/bin/env python3
"""Bucky OS V3 — AgentResult 계약 (Stage 4).

에이전트가 일을 보고하는 표준 서식. status 값은 oracle 큐
(oracle/core/api_server.py)의 상태 체계와 호환된다 — 충돌 시 oracle이 정본.
스키마: ObsidianVault/10_AgentBus/contracts/agent_result.schema.json

Usage:
    from core.agent_result import AgentResult
    res = AgentResult(agent="claude", status="completed", summary="...")
    errors = res.validate()           # [] 이면 유효
    d = res.to_dict()                 # oracle 큐 result에 실을 dict
    same = AgentResult.from_dict(d)   # 왕복 복원
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields

# oracle/core/api_server.py의 상태 전이표가 다루는 전체 상태 = TRANSITIONS.keys() ∪ STATUS_TARGETS.
# 정본은 oracle (tests/test_agent_result.py가 크로스체크).
VALID_STATUSES = (
    "pending",
    "assigned",
    "running",
    "waiting",
    "completed",
    "failed",
    "cancelled",
)


@dataclass
class AgentResult:
    """V3 §Phase 4 AgentResult 필드. agent·status만 필수, 나머지는 기본값."""

    agent: str
    status: str
    summary: str = ""
    files_changed: list[str] = field(default_factory=list)
    commands_run: list[str] = field(default_factory=list)
    test_result: str = ""
    risks: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    def validate(self) -> list[str]:
        """계약 위반 목록 반환. 빈 리스트면 유효."""
        errors: list[str] = []
        if not (self.agent or "").strip():
            errors.append("agent 필수")
        if self.status not in VALID_STATUSES:
            errors.append(f"status must be one of {VALID_STATUSES}: {self.status!r}")
        for name in ("files_changed", "commands_run", "risks", "next_actions"):
            if not isinstance(getattr(self, name), list):
                errors.append(f"{name} must be a list")
        return errors

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AgentResult":
        """알 수 없는 키는 무시하고 복원."""
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})
