#!/usr/bin/env python3
"""Bucky OS V3 — Provider Adapter 인터페이스 (Stage 6).

모든 provider(claude/codex/gemini/anthropic/openai)가 따르는 공통 계약:
    healthcheck()              → Health   (ok | disabled | failed)
    estimate(task_spec)        → Estimate (실행 가능 여부 + 모델)
    run(task_spec, instruction) → AgentResult (Stage 4 계약)

안전 규칙 (플랜 §Stage 6):
- 키 없음 → disabled 반환 (crash 금지)
- CLI 없음 → healthcheck failed 반환
- run()의 예외는 전부 failed AgentResult로 변환 — 호출측으로 예외 전파 금지

instruction은 oracle 큐 payload의 "instruction" 키에서 온다 (Stage 8에서 연결).
TaskSpec 자체에는 지시문 필드가 없으므로 run()이 별도 인자로 받는다.

구체 어댑터: scripts/providers/ (팩토리 get_adapter/all_adapters 포함).

Usage (CLI 셀프테스트):
    python -X utf8 scripts/core/provider_adapter.py
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

# 직접 실행(python scripts/core/provider_adapter.py) 시에도 core.* import 가능하게
_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from core.agent_result import AgentResult  # noqa: E402
from core.config import ROOT, load_model_registry  # noqa: E402
from core.task_spec import TaskSpec  # noqa: E402

# env_keys 판정 전에 .env 로드. override=False — 호출측/테스트가 명시한 env가 우선.
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", encoding="utf-8-sig", override=False)
except Exception:
    pass

HEALTH_OK = "ok"
HEALTH_DISABLED = "disabled"
HEALTH_FAILED = "failed"


@dataclass
class Health:
    """healthcheck() 결과."""

    provider: str
    status: str  # HEALTH_OK | HEALTH_DISABLED | HEALTH_FAILED
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status == HEALTH_OK


@dataclass
class Estimate:
    """estimate() 결과 — 이 provider가 task를 받을 수 있는지 + 예상 모델."""

    provider: str
    ok: bool
    model: str = ""
    detail: str = ""


class ProviderAdapter:
    """provider 공통 베이스. 구체 어댑터는 name 지정 + _probe/_select_model/_execute만 오버라이드."""

    name: str = ""

    def __init__(self, entry: dict | None = None):
        """entry: config/model_registry.yaml providers.<name> 항목. 미지정 시 레지스트리에서 로드."""
        if entry is None:
            entry = load_model_registry().get("providers", {}).get(self.name, {})
        self.entry: dict = entry if isinstance(entry, dict) else {}

    # ── 공통 판정 ────────────────────────────────────────────

    def enabled(self) -> bool:
        return bool(self.entry.get("enabled"))

    def missing_env_keys(self) -> list[str]:
        """레지스트리 env_keys 중 env에 없거나 빈 값인 키 목록."""
        keys = self.entry.get("env_keys") or []
        if not isinstance(keys, list):
            return []
        return [str(k) for k in keys if not os.getenv(str(k), "").strip()]

    def default_model(self) -> str:
        """레지스트리 default_model 별칭을 실제 모델명으로 해석. 없으면 ""."""
        alias = self.entry.get("default_model")
        if not alias:
            return ""
        models = self.entry.get("models")
        if isinstance(models, dict) and alias in models:
            return str(models[alias])
        return str(alias)

    # ── 공통 계약 메서드 ─────────────────────────────────────

    def healthcheck(self) -> Health:
        """enabled/env 키 공통 판정 후 provider별 _probe() 위임. 예외 → failed."""
        if not self.enabled():
            return Health(self.name, HEALTH_DISABLED, "registry enabled: false")
        missing = self.missing_env_keys()
        if missing:
            return Health(self.name, HEALTH_DISABLED, f"env 키 없음: {', '.join(missing)}")
        try:
            return self._probe()
        except Exception as e:
            return Health(self.name, HEALTH_FAILED, f"probe 예외: {e}")

    def estimate(self, task_spec: TaskSpec) -> Estimate:
        """실행 가능 여부 + 사용할 모델. 실호출 없음 — 판정만."""
        health = self.healthcheck()
        if not health.ok:
            return Estimate(self.name, False, "", health.detail or health.status)
        errors = self._spec_errors(task_spec)
        if errors:
            return Estimate(self.name, False, "", "; ".join(errors))
        try:
            return Estimate(self.name, True, self._select_model(task_spec))
        except Exception as e:
            return Estimate(self.name, False, "", f"모델 선택 예외: {e}")

    def run(self, task_spec: TaskSpec, instruction: str = "") -> AgentResult:
        """공통 가드(health/spec/instruction) 후 _execute() 위임. 예외 → failed AgentResult."""
        health = self.healthcheck()
        if not health.ok:
            return self._failed(f"실행 불가({health.status}): {health.detail}")
        errors = self._spec_errors(task_spec)
        if errors:
            return self._failed("TaskSpec 위반: " + "; ".join(errors))
        if not isinstance(instruction, str) or not instruction.strip():
            return self._failed("instruction 없음 — oracle payload의 instruction 키 필요")
        try:
            return self._execute(task_spec, instruction)
        except Exception as e:
            return self._failed(f"실행 예외: {type(e).__name__}: {e}")

    # ── provider별 오버라이드 지점 ───────────────────────────

    def _probe(self) -> Health:
        """enabled+키 통과 후의 provider별 추가 점검 (CLI 존재 등). 기본: ok."""
        return Health(self.name, HEALTH_OK)

    def _select_model(self, task_spec: TaskSpec) -> str:
        """estimate용 모델 선택. 기본: 레지스트리 default_model."""
        return self.default_model()

    def _execute(self, task_spec: TaskSpec, instruction: str) -> AgentResult:
        """실제 실행. Stage 6 기본은 안전 stub — 실연동은 어댑터별로 최소만."""
        return self._failed("Stage 6 stub — 실연동 미구현")

    # ── 헬퍼 ─────────────────────────────────────────────────

    def _spec_errors(self, task_spec: object) -> list[str]:
        if not isinstance(task_spec, TaskSpec):
            return [f"task_spec must be TaskSpec, got {type(task_spec).__name__}"]
        return task_spec.validate()

    def _failed(self, summary: str) -> AgentResult:
        # name 미지정 서브클래스여도 유효한 AgentResult 계약을 지킨다 (agent 필수)
        return AgentResult(agent=self.name or type(self).__name__, status="failed", summary=summary)


# ─────────────────────────────────────────────────────────────
# 셀프테스트 — 계약 준수 확인 (provider가 실제 사용 가능할 필요는 없음)
# ─────────────────────────────────────────────────────────────


def self_test() -> int:
    """5종 어댑터 전부: 예외 없이 Health/Estimate 반환 + run() 가드 동작 확인."""
    from core.task_spec import new_task_id
    from providers import all_adapters

    failures: list[str] = []
    spec = TaskSpec(task_id=new_task_id(), task_type="code")

    adapters = all_adapters()
    # flush 필수 — 첫 healthcheck의 lazy import(bucky_client→model_router)가 sys.stdout을
    # 재래핑하므로(model_router.py:31), 미flush 버퍼는 유실된다. (Stage 7에서 근본 수정 후보)
    print(f"== 어댑터 {len(adapters)}종 ==", flush=True)
    for name, adapter in adapters.items():
        try:
            h = adapter.healthcheck()
            if h.status not in (HEALTH_OK, HEALTH_DISABLED, HEALTH_FAILED):
                failures.append(f"{name}: 잘못된 health status {h.status!r}")
            est = adapter.estimate(spec)
            guard = adapter.run(spec, instruction="")  # instruction 없음 → failed여야 함
            if guard.status != "failed":
                failures.append(f"{name}: 빈 instruction인데 failed가 아님: {guard.status}")
            print(f"  [{h.status.upper():8}] {name}: {h.detail or '-'} | estimate ok={est.ok} model={est.model or '-'}")
        except Exception as e:
            failures.append(f"{name}: 예외 {type(e).__name__}: {e}")
            print(f"  [CRASH   ] {name}: {e}")

    disabled = adapters.get("openai_gpt")
    if disabled is not None and disabled.healthcheck().status != HEALTH_DISABLED:
        failures.append("openai_gpt: 레지스트리 enabled:false인데 disabled가 아님")

    if failures:
        print(f"셀프테스트 FAIL ({len(failures)}건)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("셀프테스트 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(self_test())
