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

# TaskSpec/AgentResult 계약(Stage 4)은 scripts/core에 있다 — 뒤에 덧붙여(append)
# client 등 기존 oracle/core 모듈을 가리지 않게 한다.
sys.path.append(str(Path(__file__).resolve().parents[2] / "scripts" / "core"))
from agent_result import AgentResult  # noqa: E402
from task_spec import TaskSpec  # noqa: E402

DEFAULT_AGENT_ID = "home-pc-agent"
DEFAULT_POLL_INTERVAL = 5.0
# 서버 연결 실패 시 백오프 상한(초). 큐 폴링 간격과 무관하게 재연결 시도를 완만히 벌린다.
ERROR_BACKOFF_MAX = 60.0


def handle_task(task: dict) -> dict:
    """태스크를 실행하고 AgentResult 형식의 result(dict)를 반환한다 (Stage 8 규약).

    payload에 실린 TaskSpec 필드를 큐 레코드 상단 필드와 합쳐 TaskSpec으로 복원한다.
    payload에 TaskSpec이 없어도 동작한다(from_dict가 결손 키를 허용 — 생산자 무수정 호환).

    TODO(후속 Phase): task["task_type"]별로 실제 로컬 에이전트/Claude Code를 호출한다.
    지금은 파이프라인을 종단까지 돌리기 위한 echo 스텁 — payload를 summary에 되돌려준다.
    """
    payload = task.get("payload")
    if not isinstance(payload, dict):
        payload = {}
    spec = TaskSpec.from_dict({**task, **payload})
    return AgentResult(
        agent=task.get("target_agent") or DEFAULT_AGENT_ID,
        status="completed",
        summary=f"echo({spec.task_type}): {json.dumps(payload, ensure_ascii=False)}",
    ).to_dict()


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
    update_status(task_id, "completed", result=result, base_url=base_url, token=token)
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
