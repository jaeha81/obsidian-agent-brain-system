#!/usr/bin/env python3
"""Bucky OS V3 — 통합 이벤트 로그 (Stage 15).

ObsidianVault/05_Logs/bucky-events.jsonl 단일 append-only 관측 로그.
플랜 근거: gap_analysis.md G3·G8, implementation_backlog.md P0-2·P0-8, ADR-0003.

원칙 (ADR-0003):
- 이벤트 버스가 아니다 — 구독·라우팅·재전송 없음. 소비는 읽기 전용 집계뿐.
- 큐가 아니다 — 10_AgentBus 무접촉. 기존 3개 jsonl(cli-tools 등)은 불변.
- emit()은 어떤 실패도 예외로 전파하지 않는다 — 관측이 실행을 죽이지 않는다
  (G:드라이브 동기화 위 append 경합 대비, assumptions.md A3).
- envelope 8필드 고정: event_id/ts/kind/task_id/conversation_id/agent/model/payload.

kind는 자유 문자열. 예정된 소비처의 관례:
- "model_decision"  — model_router.explain() 기반 라우팅 감사 (배선은 Stage 17)
- "policy_decision" / "budget_warning" — Stage 19 예정

model_decision payload는 10_AgentBus/contracts/model_decision.schema.json 정합이
필수(additionalProperties: false)라 explain() dict를 그대로 넣지 않고
build_model_decision()으로 변환한다 (env_override는 reason에 접힘).
task_id는 스키마 패턴(task_YYYYMMDD_HHMMSS_hex4) 검증을 호출자가 책임진다.

Usage (Python):
    from core.event_log import emit, emit_model_decision
    emit("task_dispatched", task_id="task_20260711_120000_ab12", agent="worker")
    emit_model_decision(explain("review"), task_id="task_20260711_120000_ab12")

Usage (CLI 셀프테스트):
    python -X utf8 scripts/core/event_log.py
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

# 직접 실행 시에도 core.* / model_router import 가능하게 (usage_ledger.py와 동일 패턴)
_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from core.config import VAULT  # noqa: E402

EVENTS_PATH: Path = VAULT / "05_Logs" / "bucky-events.jsonl"

ENVELOPE_KEYS: tuple[str, ...] = (
    "event_id",
    "ts",
    "kind",
    "task_id",
    "conversation_id",
    "agent",
    "model",
    "payload",
)


def emit(
    kind: str,
    *,
    task_id: str = "",
    conversation_id: str = "",
    agent: str = "",
    model: str = "",
    payload: dict | None = None,
    log_path: Path | str | None = None,
) -> Path | None:
    """이벤트 1건 append. 성공 시 기록된 파일 경로, 실패 시 None (예외 전파 금지)."""
    try:
        entry = {
            "event_id": uuid.uuid4().hex,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "kind": str(kind),
            "task_id": str(task_id),
            "conversation_id": str(conversation_id),
            "agent": str(agent),
            "model": str(model),
            "payload": payload if isinstance(payload, dict) else {},
        }
        path = Path(log_path) if log_path else EVENTS_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        # default=str: payload에 Path·datetime 등이 섞여도 기록을 유실하지 않는다
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        return path
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# model_decision 방출 준비 (배선은 Stage 17 — worker 디스패치 시)
# ─────────────────────────────────────────────────────────────


def build_model_decision(
    explain: dict,
    *,
    provider_chain: list[str] | None = None,
    task_id: str = "",
    selected_provider: str = "",
) -> dict:
    """model_router.explain() dict → model_decision.schema.json 정합 payload.

    - selected_provider = 인자로 받은 실제 실행 provider. 미지정 시 provider_chain
      1순위 폴백 — 폴백 실행 시 불일치 가능하므로 실행측(worker)은 반드시 넘긴다 (G4)
    - env_override는 스키마에 없는 키라 reason 끝에 접어넣는다
    - task_id는 비었으면 키 자체를 넣지 않는다 (스키마 패턴 위반 방지)
    """
    explain = explain if isinstance(explain, dict) else {}
    chain = [str(p) for p in provider_chain] if provider_chain else None
    if chain is None:
        try:
            from model_router import provider_candidates

            chain = provider_candidates(str(explain.get("task_type") or ""))
        except Exception:
            chain = ["claude_code"]

    reason = str(explain.get("reason") or "")
    if explain.get("env_override"):
        reason = f"{reason} [env_override: BUCKY_FORCE_MODEL]".strip()

    decision = {
        "task_type": str(explain.get("task_type") or "default"),
        "selected_provider": selected_provider or (chain[0] if chain else "claude_code"),
        "selected_model": str(explain.get("selected_model") or ""),
        "provider_chain": chain,
        "fallback_chain": [str(m) for m in explain.get("fallback_chain") or []],
        "reason": reason,
        "decided_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if task_id:
        decision["task_id"] = str(task_id)
    return decision


def emit_model_decision(
    explain: dict,
    *,
    task_id: str = "",
    conversation_id: str = "",
    agent: str = "",
    provider_chain: list[str] | None = None,
    selected_provider: str = "",
    log_path: Path | str | None = None,
) -> Path | None:
    """explain() dict를 model_decision 이벤트로 기록. 실패 시 None (예외 전파 금지)."""
    try:
        decision = build_model_decision(explain, provider_chain=provider_chain,
                                        task_id=task_id, selected_provider=selected_provider)
        return emit(
            "model_decision",
            task_id=task_id,
            conversation_id=conversation_id,
            agent=agent,
            model=decision["selected_model"],
            payload=decision,
            log_path=log_path,
        )
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# 셀프테스트
# ─────────────────────────────────────────────────────────────


def self_test() -> int:
    """임시 파일에 emit 왕복 검증. 실로그(05_Logs/bucky-events.jsonl)는 건드리지 않는다."""
    import tempfile

    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "events.jsonl"

        # 1. emit 왕복 — envelope 8필드 정확 일치
        p = emit("test_kind", task_id="t1", agent="tester", model="sonnet", payload={"k": "v"}, log_path=log)
        if p is None or not p.is_file():
            failures.append("emit 기록 실패")
        else:
            e = json.loads(p.read_text(encoding="utf-8").splitlines()[0])
            if tuple(e.keys()) != ENVELOPE_KEYS:
                failures.append(f"envelope 키 불일치: {tuple(e.keys())}")
            if (e["kind"], e["payload"]) != ("test_kind", {"k": "v"}):
                failures.append(f"본문 불일치: {e['kind']}/{e['payload']}")

        # 2. append-only + event_id 유일
        emit("test_kind", log_path=log)
        lines = log.read_text(encoding="utf-8").splitlines()
        if len(lines) != 2:
            failures.append(f"append 줄 수: {len(lines)} != 2")
        else:
            ids = [json.loads(ln)["event_id"] for ln in lines]
            if len(set(ids)) != 2:
                failures.append("event_id 중복")

        # 3. 직렬화 불가 값 → default=str로 기록 유실 방지
        p = emit("test_kind", payload={"path": Path(tmp)}, log_path=log)
        if p is None:
            failures.append("비직렬화 payload에서 기록 유실")

        # 4. build_model_decision — 스키마 정합 (required 충족·미허용 키 없음)
        schema_path = VAULT / "10_AgentBus" / "contracts" / "model_decision.schema.json"
        try:
            from model_router import explain

            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            d = build_model_decision(explain("review"), task_id="task_20260711_120000_ab12")
            missing = [k for k in schema["required"] if k not in d]
            extra = [k for k in d if k not in schema["properties"]]
            if missing or extra:
                failures.append(f"스키마 정합 실패: missing={missing} extra={extra}")
            if "env_override" in d:
                failures.append("env_override가 payload에 노출됨")
        except Exception as exc:  # noqa: BLE001 — 셀프테스트 보고용
            failures.append(f"스키마 정합 검증 불가: {exc}")

        # 5. emit_model_decision 왕복 — envelope.model == selected_model
        p = emit_model_decision({"task_type": "code", "selected_model": "sonnet"}, provider_chain=["claude_code"], log_path=log)
        if p is None:
            failures.append("emit_model_decision 기록 실패")
        else:
            e = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
            if e["kind"] != "model_decision" or e["model"] != "sonnet":
                failures.append(f"model_decision envelope 불일치: {e['kind']}/{e['model']}")
            if e["payload"].get("selected_provider") != "claude_code":
                failures.append(f"selected_provider: {e['payload'].get('selected_provider')}")

    # 6. 기록 실패 시 예외 없이 None (부모가 파일인 경로 → mkdir 실패)
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        blocked = tf.name
    try:
        if emit("x", log_path=Path(blocked) / "sub" / "e.jsonl") is not None:
            failures.append("실패 경로에서 None이 아님")
    finally:
        import os

        os.unlink(blocked)

    # 7. 기본 경로 = Vault 05_Logs (실기록 없이 경로만 확인)
    if EVENTS_PATH != VAULT / "05_Logs" / "bucky-events.jsonl":
        failures.append(f"기본 경로 이탈: {EVENTS_PATH}")

    if failures:
        print(f"셀프테스트 FAIL ({len(failures)}건)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("셀프테스트 PASS (7항목)")
    return 0


if __name__ == "__main__":
    sys.exit(self_test())
