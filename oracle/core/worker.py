#!/usr/bin/env python3
"""Bucky Core 폴링 워커 — 집PC 실행 측 (Phase 3-⑤).

오라클 #2의 API를 폴링(pull)해 이 노드용 태스크를 선점하고, 실행 후 상태를 보고한다.
집PC는 아웃바운드 HTTP만 있으면 되고 인바운드 포트를 열 필요가 없다(pull 아키텍처).
client.py의 claim_task/update_status만 사용 — stdlib(urllib)만 의존한다.

상태 흐름 (서버 api_server.py §20.2 전이표):
    pending --claim--> assigned --> running --> completed | failed

Env:
    ORACLE_API_URL      API 베이스 URL (기본 http://127.0.0.1:8700)
    BUCKY_API_TOKEN     Bearer 인증 토큰 (필수)
    BUCKY_AGENT_ID      이 워커가 선점할 에이전트 ID (기본 home-pc-agent)
    BUCKY_POLL_INTERVAL 빈 큐일 때 대기 초 (기본 5.0)

Usage:
    BUCKY_API_TOKEN=<token> python3 oracle/core/worker.py
    BUCKY_API_TOKEN=<token> python3 oracle/core/worker.py --agent-id home-pc-agent --once
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from client import OracleClientError, claim_task, update_status

# TaskSpec/AgentResult 계약(Stage 4)은 scripts/core 패키지에 있다. ProviderAdapter와
# 같은 core.task_spec 경로로 import해야 isinstance 판정이 통한다(클래스 정체성 단일화).
# 뒤에 덧붙여(append) client 등 기존 oracle/core 모듈을 가리지 않게 한다.
sys.path.append(str(Path(__file__).resolve().parents[2] / "scripts"))
from core.agent_result import AgentResult  # noqa: E402
from core.task_spec import TaskSpec  # noqa: E402

DEFAULT_AGENT_ID = "home-pc-agent"
DEFAULT_POLL_INTERVAL = 5.0
# 서버 연결 실패 시 백오프 상한(초). 큐 폴링 간격과 무관하게 재연결 시도를 완만히 벌린다.
ERROR_BACKOFF_MAX = 60.0


def handle_task(task: dict) -> dict:
    """태스크를 실행하고 AgentResult 형식의 result(dict)를 반환한다 (Stage 8 규약).

    payload에 실린 TaskSpec 필드를 큐 레코드 상단 필드와 합쳐 TaskSpec으로 복원한다.
    큐 레코드가 정본이므로 레코드 필드를 마지막에 병합한다 — payload가 task_id·priority
    등 정본 필드를 덮어쓸 수 없다. 복원 후 validate() 위반은 AgentResult(failed)로 보고한다.
    payload에 TaskSpec이 없어도 동작한다(from_dict가 결손 키를 허용 — 생산자 무수정 호환).

    Stage 17: config/bucky.yaml `features.worker_adapter_dispatch: true`면 provider
    어댑터로 디스패치한다(_dispatch). 기본 false = echo 스텁 유지 — 회귀 보증이자
    즉시 롤백 스위치. 어댑터 지시문은 payload["instruction"]에서 온다 (Stage 8 규약).

    Stage 19: 실행 경로 선택(echo/디스패치) 직전에 정책을 상담한다(_policy_consult).
    shadow 규약(ADR-0004) — 판정은 이벤트로만, 입출력·차단에 어떤 영향도 없다.
    """
    agent = task.get("target_agent") or DEFAULT_AGENT_ID
    payload = task.get("payload")
    if not isinstance(payload, dict):
        payload = {}
    spec = TaskSpec.from_dict({**payload, **task})
    errors = spec.validate()
    if errors:
        return AgentResult(
            agent=agent,
            status="failed",
            summary="TaskSpec 위반: " + "; ".join(errors),
        ).to_dict()
    _policy_consult(spec, agent)
    if _dispatch_enabled():
        return _dispatch(spec, payload, agent)
    return AgentResult(
        agent=agent,
        status="completed",
        summary=f"echo({spec.task_type}): {json.dumps(payload, ensure_ascii=False)}",
    ).to_dict()


def _dispatch_enabled() -> bool:
    """config/bucky.yaml features.worker_adapter_dispatch (Stage 17). 로드 실패·부재 → False(echo)."""
    try:
        from core.config import load_bucky

        features = load_bucky().get("features")
        return bool(features.get("worker_adapter_dispatch")) if isinstance(features, dict) else False
    except Exception:
        return False


def _policy_mode() -> str:
    """config/bucky.yaml features.policy_enforcement (Stage 19). 로드 실패·부재·off → ""(상담 안 함).

    off/false/none/빈값 외의 모든 값(shadow, 조기 설정된 enforce 포함)에서 상담한다 —
    단 어떤 모드에서도 차단은 없다(enforce 전환은 플랜 범위 밖, ADR-0004 §3).
    조기 enforce 설정은 이벤트 payload의 mode로 관측된다.
    """
    try:
        from core.config import load_bucky

        features = load_bucky().get("features")
        mode = features.get("policy_enforcement") if isinstance(features, dict) else ""
        mode = str(mode or "").strip().lower()
        return "" if mode in ("off", "false", "none") else mode
    except Exception:
        return ""


def _policy_consult(spec: TaskSpec, agent: str) -> None:
    """디스패치 전 정책 상담 — 판정을 policy_decision 이벤트로만 방출한다 (Stage 19, ADR-0004).

    shadow 규약: 이 함수는 handle_task의 입출력에 어떤 영향도 주지 않는다 — 기존 동작
    바이트 동일 회귀(W17)가 이를 고정한다. require_approval 판정도 이벤트로만 남는다.
    enforce 시의 승인은 기존 pending_approval 파일큐+approve_task.py+Discord !approve
    재사용이 확정(신설 금지)이나 이번 범위 밖. 예산: usage 월 합계 추정 비용이
    budget.monthly_warn_usd 초과면 budget_warning(0·결손 = 비활성). 관측의 어떤 실패도
    예외를 전파하지 않는다 — 관측이 실행을 막지 않는다(ADR-0003).
    """
    try:
        mode = _policy_mode()
        if not mode:
            return
        from core.event_log import emit
        from core.policy_engine import evaluate

        verdict = evaluate(spec)
        emit("policy_decision", task_id=spec.task_id, agent=agent,
             payload={**verdict, "mode": mode, "task_type": spec.task_type})

        from core.config import load_bucky

        budget = load_bucky().get("budget")
        threshold = float(budget.get("monthly_warn_usd") or 0) if isinstance(budget, dict) else 0.0
        if threshold > 0:
            from core.usage_ledger import month_summary

            s = month_summary()
            cost = float(s.get("cost_usd") or 0.0)
            if cost > threshold:
                emit("budget_warning", task_id=spec.task_id, agent=agent,
                     payload={"month": s.get("month", ""), "cost_usd": cost,
                              "threshold_usd": threshold, "records": s.get("records", 0)})
    except Exception:
        return


def _dispatch(spec: TaskSpec, payload: dict, agent: str) -> dict:
    """provider_candidates 순서로 첫 실행 가능(estimate ok) 어댑터에 위임한다 (Stage 17).

    - model_decision 이벤트는 실행 provider 확정 직후·run() 직전에 남긴다 — 폴백으로
      2순위가 실행돼도 selected_provider가 실제 실행 provider와 일치한다 (G4 필수수정).
      전 provider 실행 불가면 결정이 없으므로 model_decision 없이 worker_dispatch_failed만
      남는다. emit 계열은 실패해도 예외를 전파하지 않으므로(ADR-0003) 관측이 실행을 막지 않는다.
    - usage 기록은 adapter.run() 내부(Stage 10 단일 관문)가 담당 — 여기서 중복 기록 금지.
    - 전 provider 실행 불가면 명시적 AgentResult(failed) + worker_dispatch_failed 이벤트.
      실동작 provider는 현재 claude_code뿐(나머지는 스텁) — 인터페이스 완성이지
      멀티 provider 실전이 아니다 (플랜 리스크 2).
    """
    from core.event_log import emit, emit_model_decision
    from model_router import explain, provider_candidates
    from providers import get_adapter

    chain = provider_candidates(spec.task_type)
    skipped: list[str] = []
    for name in chain:
        adapter = get_adapter(name)
        if adapter is None:
            skipped.append(f"{name}: 미등록 어댑터")
            continue
        estimate = adapter.estimate(spec)
        if not estimate.ok:
            skipped.append(f"{name}: {estimate.detail or 'estimate 불가'}")
            continue
        emit_model_decision(explain(spec.task_type), task_id=spec.task_id,
                            agent=agent, provider_chain=chain, selected_provider=name)
        return adapter.run(spec, instruction=str(payload.get("instruction") or "")).to_dict()
    summary = "디스패치 실패 — 실행 가능 provider 없음: " + "; ".join(skipped)
    emit("worker_dispatch_failed", task_id=spec.task_id, agent=agent,
         payload={"provider_chain": chain, "skipped": skipped})
    return AgentResult(agent=agent, status="failed", summary=summary).to_dict()


def run_once(agent_id, *, base_url=None, token=None):
    """태스크 1개를 선점·실행·보고한다. 처리한 task_id, 큐가 비었으면 None을 반환한다.

    handle_task 실행 중 예외는 서버에 failed로 보고하고 task_id를 반환한다(루프는 계속).
    claim/status의 서버 통신 오류(OracleClientError)는 호출자로 전파해 run_forever가
    백오프하도록 둔다 — 태스크 로직 실패와 서버 도달 실패를 구분한다.
    """
    task = claim_task(agent_id, base_url=base_url, token=token)
    if task is None:
        return None
    task_id = task["task_id"]
    update_status(task_id, "running", base_url=base_url, token=token)
    try:
        result = handle_task(task)
    except Exception as exc:
        # 태스크 실패는 워커를 죽이지 않는다 — 서버에 보고하고 다음 태스크로 넘어간다.
        failure = AgentResult(agent=agent_id, status="failed", summary=repr(exc))
        update_status(task_id, "failed", result=failure.to_dict(),
                      base_url=base_url, token=token)
        return task_id
    # handle_task가 검증 실패 등을 AgentResult(failed)로 반환하면 서버 상태도 failed로 맞춘다.
    status = "failed" if result.get("status") == "failed" else "completed"
    update_status(task_id, status, result=result, base_url=base_url, token=token)
    return task_id


def run_forever(agent_id, *, poll_interval=DEFAULT_POLL_INTERVAL, base_url=None, token=None):
    """큐를 계속 폴링한다. 빈 큐는 poll_interval, 서버 오류는 지수 백오프로 대기한다."""
    print(f"Bucky 워커 시작: agent_id={agent_id}, interval={poll_interval}s")
    backoff = poll_interval
    while True:
        try:
            task_id = run_once(agent_id, base_url=base_url, token=token)
            backoff = poll_interval  # 정상 왕복 후 백오프 리셋
            if task_id is None:
                time.sleep(poll_interval)  # 큐 비어 있음
        except OracleClientError as exc:
            # 서버 다운/일시 오류 — 크래시 대신 백오프하며 재시도한다.
            print(f"[warn] API 오류, {backoff:.0f}s 후 재시도: {exc}")
            time.sleep(backoff)
            backoff = min(backoff * 2, ERROR_BACKOFF_MAX)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bucky Core 폴링 워커 (집PC 실행 측)")
    parser.add_argument("--agent-id", default=os.environ.get("BUCKY_AGENT_ID", DEFAULT_AGENT_ID))
    parser.add_argument(
        "--interval", type=float,
        default=float(os.environ.get("BUCKY_POLL_INTERVAL", DEFAULT_POLL_INTERVAL)),
    )
    parser.add_argument("--once", action="store_true", help="태스크 1개만 처리하고 종료")
    args = parser.parse_args()
    if args.once:
        task_id = run_once(args.agent_id)
        print(f"처리: {task_id}" if task_id else "큐가 비어 있습니다.")
        return
    try:
        run_forever(args.agent_id, poll_interval=args.interval)
    except KeyboardInterrupt:
        print("\n워커 종료.")


if __name__ == "__main__":
    main()
