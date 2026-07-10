#!/usr/bin/env python3
"""Bucky Core API 클라이언트 — 오라클 #2 API 래퍼 (Phase 3-④).

submit 측(Discord 봇 등 명령 투입)은 태스크를 생성/조회(submit_task/get_task)하고,
폴링 측(집PC 워커)은 태스크를 선점하고 상태를 보고(claim_task/update_status)한다.
api_server.py와 동일하게 stdlib(urllib)만 사용 — pip 설치 없이 어느 노드에서나 임포트된다.
서버가 검증의 단일 원천이므로 필드 검증은 서버에 위임하고, 여기서는 요청 구성·인증
부착·HTTP 오류를 사람이 읽을 수 있는 예외로 번역하는 것만 담당한다.

Env:
    ORACLE_API_URL    API 베이스 URL (기본 http://127.0.0.1:8700)
    BUCKY_API_TOKEN   Bearer 인증 토큰 (없으면 호출 시 OracleClientError)

Usage:
    from client import submit_task, get_task, claim_task, update_status
    res = submit_task("chat", payload={"instruction": "..."}, target_agent="home-pc-agent")
    task = get_task(res["task_id"])
    # 폴링 측(집PC):
    task = claim_task("home-pc-agent")                       # None이면 큐가 비어 있음
    update_status(task["task_id"], "completed", result={"reply": "..."})
    # obsidian-index 검색(B4):
    hits = index_search("버키 코어", top_k=5, folder="03_Knowledge")
    info = index_stats()
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "http://127.0.0.1:8700"
DEFAULT_TIMEOUT = 10


class OracleClientError(RuntimeError):
    """오라클 API 호출 실패. status는 서버 응답 코드(연결 전 실패 시 None)."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def _resolve_base_url(base_url: str | None) -> str:
    return (base_url or os.environ.get("ORACLE_API_URL", DEFAULT_BASE_URL)).rstrip("/")


def _resolve_token(token: str | None) -> str:
    tok = (token or os.environ.get("BUCKY_API_TOKEN", "")).strip()
    if not tok:
        raise OracleClientError("BUCKY_API_TOKEN이 없어 오라클 API를 호출할 수 없습니다.")
    return tok


def _request(
    method: str,
    path: str,
    *,
    base_url: str | None,
    token: str | None,
    body: dict | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    url = _resolve_base_url(base_url) + path
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {_resolve_token(token)}")
    if data is not None:
        req.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("error", "")
        except Exception:
            detail = ""
        raise OracleClientError(
            f"오라클 API {method} {path} 실패 ({exc.code})" + (f": {detail}" if detail else ""),
            status=exc.code,
        ) from exc
    except urllib.error.URLError as exc:
        raise OracleClientError(f"오라클 API 연결 실패 ({url}): {exc.reason}") from exc


def submit_task(
    task_type: str,
    *,
    payload: dict | None = None,
    target_agent: str = "bucky-main",
    priority: str = "normal",
    source: str = "api",
    requested_by: str = "unknown",
    base_url: str | None = None,
    token: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """POST /api/v1/tasks — 태스크 생성. 성공 시 {"task_id", "status"} 반환."""
    body = {
        "task_type": task_type,
        "target_agent": target_agent,
        "priority": priority,
        "payload": payload or {},
        "source": source,
        "requested_by": requested_by,
    }
    return _request("POST", "/api/v1/tasks", base_url=base_url, token=token, body=body, timeout=timeout)


def get_task(
    task_id: str,
    *,
    base_url: str | None = None,
    token: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """GET /api/v1/tasks/{task_id} — 태스크 레코드 반환(미존재 시 404 → OracleClientError)."""
    return _request(
        "GET", f"/api/v1/tasks/{task_id}", base_url=base_url, token=token, timeout=timeout
    )


def claim_task(
    agent_id: str,
    *,
    base_url: str | None = None,
    token: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict | None:
    """POST /api/v1/tasks/claim — 이 에이전트용 pending 태스크 1개를 선점(→assigned).

    가져갈 태스크가 있으면 태스크 레코드(dict), 큐가 비어 있으면 None을 반환한다.
    미등록 agent_id는 서버가 400으로 거부(→ OracleClientError).
    """
    res = _request(
        "POST", "/api/v1/tasks/claim",
        base_url=base_url, token=token, body={"agent_id": agent_id}, timeout=timeout,
    )
    return res.get("task")


def update_status(
    task_id: str,
    status: str,
    *,
    result: dict | None = None,
    base_url: str | None = None,
    token: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """POST /api/v1/tasks/{task_id}/status — 상태 전이 보고. 성공 시 {"task_id", "status"}.

    result는 completed/failed 등 종료 보고 시 첨부하는 산출물(선택). 허용되지 않는 전이는
    서버가 409로 거부(→ OracleClientError)한다.
    """
    body: dict = {"status": status}
    if result is not None:
        body["result"] = result
    return _request(
        "POST", f"/api/v1/tasks/{task_id}/status",
        base_url=base_url, token=token, body=body, timeout=timeout,
    )


def index_search(
    query: str,
    *,
    top_k: int = 5,
    folder: str | None = None,
    ntype: str | None = None,
    base_url: str | None = None,
    token: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """GET /api/v1/index/search — obsidian-index 키워드 검색.

    성공 시 {"query", "count", "results"} 반환. folder/ntype은 서버 측 필터
    (쿼리스트링 folder=/type=). 인덱스 미구축이면 서버가 503, 빈 질의면 400으로
    거부한다(둘 다 OracleClientError로 전달).
    """
    params: dict = {"q": query, "k": top_k}
    if folder:
        params["folder"] = folder
    if ntype:
        params["type"] = ntype
    return _request(
        "GET", "/api/v1/index/search?" + urllib.parse.urlencode(params),
        base_url=base_url, token=token, timeout=timeout,
    )


def index_stats(
    *,
    base_url: str | None = None,
    token: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """GET /api/v1/index/stats — 인덱스 요약({"available", "count", "folders", ...}) 반환."""
    return _request(
        "GET", "/api/v1/index/stats", base_url=base_url, token=token, timeout=timeout
    )
