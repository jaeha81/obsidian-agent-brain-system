#!/usr/bin/env python3
"""Bucky OS V3 — TaskSpec 계약 (Stage 4).

에이전트가 일을 받는 표준 서식. task_id·priority 값은 oracle 큐
(oracle/core/api_server.py)와 호환된다 — 충돌 시 oracle 체계가 정본.
스키마: ObsidianVault/10_AgentBus/contracts/task_spec.schema.json

Usage:
    from core.task_spec import TaskSpec, new_task_id
    spec = TaskSpec(task_id=new_task_id(), task_type="code")
    errors = spec.validate()          # [] 이면 유효
    d = spec.to_dict()                # oracle 큐 payload에 실을 dict
    same = TaskSpec.from_dict(d)      # 왕복 복원
"""

from __future__ import annotations

import re
import secrets
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone

# oracle/core/api_server.py PRIORITIES와 동일 — 정본은 oracle (tests/test_task_spec.py가 크로스체크).
PRIORITIES = ("low", "normal", "high")

# oracle new_task_id 형식: task_{YYYYMMDD_HHMMSS}_{hex4}
TASK_ID_RE = re.compile(r"^task_\d{8}_\d{6}_[0-9a-f]{4}$")


def new_task_id(now: datetime | None = None) -> str:
    """oracle new_task_id와 동일 형식의 task_id 생성."""
    now = now or datetime.now(timezone.utc)
    return f"task_{now:%Y%m%d_%H%M%S}_{secrets.token_hex(2)}"


@dataclass
class TaskSpec:
    """V3 §Phase 4 TaskSpec 필드. task_id·task_type만 필수, 나머지는 기본값."""

    task_id: str
    task_type: str
    source: str = "api"
    channel: str = ""
    priority: str = "normal"
    required_capabilities: list[str] = field(default_factory=list)
    constraints: dict = field(default_factory=dict)
    expected_output: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def validate(self) -> list[str]:
        """계약 위반 목록 반환. 빈 리스트면 유효. 잘못된 타입도 예외 없이 목록으로 보고."""
        errors: list[str] = []
        if not isinstance(self.task_id, str) or not TASK_ID_RE.match(self.task_id):
            errors.append(f"task_id 형식 불일치(oracle 호환 필요): {self.task_id!r}")
        if not isinstance(self.task_type, str) or not self.task_type.strip():
            errors.append("task_type 필수")
        if self.priority not in PRIORITIES:
            errors.append(f"priority must be one of {PRIORITIES}: {self.priority!r}")
        if not isinstance(self.required_capabilities, list):
            errors.append("required_capabilities must be a list")
        if not isinstance(self.constraints, dict):
            errors.append("constraints must be an object")
        return errors

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: object) -> "TaskSpec":
        """알 수 없는 키는 무시하고 복원 (oracle 큐 record에 여분 필드가 있어도 안전).

        비-dict 입력도 예외 없이 복원 — validate()가 위반을 보고하는 invalid 인스턴스가 된다.
        """
        if not isinstance(data, dict):
            data = {}
        known = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in data.items() if k in known}
        kwargs.setdefault("task_id", "")
        kwargs.setdefault("task_type", "")
        return cls(**kwargs)
