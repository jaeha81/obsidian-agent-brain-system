#!/usr/bin/env python3
"""Bucky OS V3 — Brain Status 대시보드 데이터 생성기 (Stage 21).

오라클 태스크 큐(data/bucky_tasks.db) 읽기전용 집계 + usage_ledger 월간 요약 +
policy shadow 판정 분포(bucky-events.jsonl) + agents.yaml 실행 인프라 목록을 읽어
docs/data/bucky_brain_status.json / docs/data/agents_org.json으로 출력한다.
파일만 쓰고 git은 하지 않는다(커밋/푸시는 run_daily_plus_pipeline.ps1이 담당) —
build_system_evolution.py와 동일 원칙.

플랜 근거: foamy-churning-swing.md Stage 21, ADR-0001 §"Stage 21 대시보드는 큐를
읽기 전용으로 참조하면 된다".

읽기전용 접근: SQLite는 `file:...?mode=ro` URI로 연다 — 기존 worker.py는 오라클과
HTTP client로만 통신하고 DB를 직접 열지 않으므로, 이 스크립트가 읽기전용 직접
접근 패턴을 최초로 확립한다.

강건성 원칙: 대시보드는 항상 렌더돼야 하므로, DB/원장/로그/yaml 부재·손상 시에도
raise 하지 않고 빈 값으로 degrade한 뒤 계속 진행한다.

Usage:
    python -X utf8 scripts/generate_brain_status.py
"""

from __future__ import annotations

import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        for _name in ("stdout", "stderr"):
            _stream = getattr(sys, _name)
            if (_stream.encoding or "").lower().replace("-", "") != "utf8":
                setattr(sys, _name, io.TextIOWrapper(_stream.buffer, encoding="utf-8", errors="replace"))
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from core.config import DATA, DOCS, VAULT  # noqa: E402
from core.usage_ledger import month_summary  # noqa: E402

DB_PATH: Path = DATA / "bucky_tasks.db"
EVENTS_PATH: Path = VAULT / "05_Logs" / "bucky-events.jsonl"
AGENTS_FILE: Path = ROOT / "oracle" / "core" / "agents.yaml"
OUT_STATUS: Path = DOCS / "data" / "bucky_brain_status.json"
OUT_AGENTS: Path = DOCS / "data" / "agents_org.json"

# §20.2 상태 전이표(oracle/core/api_server.py TRANSITIONS)의 전체 상태 7종
TASK_STATUSES: tuple[str, ...] = (
    "pending", "assigned", "running", "waiting", "completed", "failed", "cancelled",
)


def _now_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _aggregate_status_rows(rows) -> dict:
    """[(status, count), ...] → {"total", "by_status"}. 로컬·원격 집계 공용."""
    by_status = {s: 0 for s in TASK_STATUSES}
    total = 0
    for status, n in rows:
        total += int(n)
        if status in by_status:
            by_status[status] = int(n)
    return {"total": total, "by_status": by_status}


def task_queue_summary(db_path: Path | None = None) -> dict:
    """로컬 태스크 큐 상태별 집계. 읽기전용 연결(mode=ro). DB 부재/손상 → 전부 0."""
    path = db_path or DB_PATH
    if not path.is_file():
        return _aggregate_status_rows([])
    try:
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        try:
            rows = con.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status").fetchall()
        finally:
            con.close()
    except Exception:
        return _aggregate_status_rows([])
    return _aggregate_status_rows(rows)


def remote_task_summary() -> dict | None:
    """실배포(오라클 #2)에서 태스크 큐는 #2의 DB에 쌓인다(split-brain). BUCKY_ORACLE_SSH가
    설정되면 그 DB를 읽기전용 ssh로 원격 집계한다. 미설정/실패/타임아웃 → None(호출측이
    로컬 DB로 폴백). 대시보드는 항상 렌더돼야 하므로 여기서 raise 하지 않는다.

    Env:
        BUCKY_ORACLE_SSH      ssh 대상 (예: "ubuntu@161.33.204.158"). 없으면 비활성.
        BUCKY_ORACLE_SSH_KEY  ssh 개인키 경로 (선택).
        BUCKY_ORACLE_DB       #2의 태스크 DB 경로 (기본 /opt/ai-os/data/bucky_tasks.db).
    """
    target = os.environ.get("BUCKY_ORACLE_SSH", "").strip()
    if not target:
        return None
    key = os.environ.get("BUCKY_ORACLE_SSH_KEY", "").strip()
    remote_db = os.environ.get("BUCKY_ORACLE_DB", "/opt/ai-os/data/bucky_tasks.db").strip()
    remote_py = (
        "import sqlite3,json;"
        f"c=sqlite3.connect('file:{remote_db}?mode=ro',uri=True);"
        "print(json.dumps(c.execute('SELECT status,COUNT(*) FROM tasks GROUP BY status').fetchall()))"
    )
    cmd = ["ssh", "-o", "ConnectTimeout=8", "-o", "BatchMode=yes"]
    if key:
        cmd += ["-i", key]
    cmd += [target, f'python3 -c "{remote_py}"']
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if out.returncode != 0:
            return None
        rows = json.loads(out.stdout.strip())
    except Exception:
        return None
    summary = _aggregate_status_rows(rows)
    summary["source"] = "oracle"
    return summary


def usage_summary(usage_dir: Path | None = None, month: str | None = None) -> dict:
    """이번 달 usage_ledger 합계. 원장 부재 시 month_summary가 이미 0 집계 반환."""
    try:
        s = month_summary(month=month, usage_dir=usage_dir)
        return {
            "month": s["month"],
            "records": s["records"],
            "tokens_in": s["tokens_in"],
            "tokens_out": s["tokens_out"],
            "cost_usd": s["cost_usd"],
            "by_model": s["by_model"],
        }
    except Exception:
        return {"month": time.strftime("%Y-%m"), "records": 0, "tokens_in": 0,
                 "tokens_out": 0, "cost_usd": 0.0, "by_model": {}}


def policy_shadow_summary(events_path: Path | None = None) -> dict:
    """bucky-events.jsonl에서 policy_decision/budget_warning 집계. 로그 부재/파싱실패는 스킵."""
    path = events_path or EVENTS_PATH
    empty = {"total": 0, "by_tier": {}, "by_decision": {}, "budget_warnings": 0}
    if not path.is_file():
        return empty
    by_tier: dict[str, int] = {}
    by_decision: dict[str, int] = {}
    total = 0
    budget_warnings = 0
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                kind = e.get("kind")
                if kind == "policy_decision":
                    total += 1
                    payload = e.get("payload") or {}
                    tier = str(payload.get("tier") or "unknown")
                    decision = str(payload.get("decision") or "unknown")
                    by_tier[tier] = by_tier.get(tier, 0) + 1
                    by_decision[decision] = by_decision.get(decision, 0) + 1
                elif kind == "budget_warning":
                    budget_warnings += 1
    except Exception:
        return empty
    return {"total": total, "by_tier": by_tier, "by_decision": by_decision, "budget_warnings": budget_warnings}


def _parse_agents_flat_yaml(path: Path) -> list[dict]:
    """agents.yaml 평탄 포맷 stdlib 파서 — PyYAML 비의존.

    oracle/core/api_server.py의 load_agents()와 동일한 포맷 계약(agents.yaml:2 —
    `agents:` 헤더 + `- key: value` 블록)을 읽는다. 오라클 VM에 PyYAML이 없어 이
    포맷이 존재하며(api_server.py:82), 이 생성기를 스케줄 실행하는 환경도 PyYAML이
    없을 수 있어(Task Scheduler 기본 Python) core.config.load_yaml()에 의존하면 안
    된다 — 07-13 실제 스케줄 실행에서 PyYAML 부재로 agents_org.json이 빈 배열로
    커밋된 사고 재발 방지. api_server.py는 형식 오류에 fail-fast(sys.exit)하지만
    이쪽은 대시보드 조회용이라 형식 불량 라인은 건너뛰고 best-effort로 이어간다 —
    설정 무결성 검증은 api_server.py 기동 시 이미 수행된다.
    """
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8-sig")  # BOM 방어
    except Exception:
        return []
    agents: list[dict] = []
    current: dict | None = None
    in_agents = False
    for raw in text.splitlines():
        stripped = re.split(r"\s#", raw, maxsplit=1)[0].strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not in_agents:
            if stripped == "agents:":
                in_agents = True
            continue
        if stripped.startswith("- "):
            current = {}
            agents.append(current)
            stripped = stripped[2:].strip()
        key, sep, value = stripped.partition(":")
        key = key.strip()
        if current is None or not sep or not key:
            continue  # 형식 불량 라인 스킵 (best-effort)
        current[key] = value.strip().strip("'\"")
    return agents


def agents_org(agents_file: Path | None = None) -> list[dict]:
    """oracle/core/agents.yaml → 실행 인프라 노드 목록. 부재/파싱실패 → []."""
    path = agents_file or AGENTS_FILE
    items = _parse_agents_flat_yaml(path)
    out: list[dict] = []
    for item in items:
        if isinstance(item, dict) and str(item.get("id") or "").strip():
            out.append({
                "id": str(item.get("id")),
                "type": str(item.get("type") or ""),
                "location": str(item.get("location") or ""),
                "role": str(item.get("role") or ""),
                "status": str(item.get("status") or "unknown"),
            })
    return out


def build_status() -> dict:
    # 실배포에선 라이브 큐가 오라클 #2에 있다 — 원격 집계 우선, 실패 시 로컬 폴백.
    tq = remote_task_summary()
    if tq is None:
        tq = task_queue_summary()
        tq["source"] = "local"
    return {
        "meta": {"last_updated": _now_ts(), "generator": "generate_brain_status.py"},
        "task_queue": tq,
        "usage": usage_summary(),
        "policy_shadow": policy_shadow_summary(),
    }


def build_agents_org() -> dict:
    return {
        "meta": {"last_updated": _now_ts(), "source": "oracle/core/agents.yaml"},
        "agents": agents_org(),
    }


def main() -> int:
    OUT_STATUS.parent.mkdir(parents=True, exist_ok=True)
    status = build_status()
    OUT_STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")

    org = build_agents_org()
    OUT_AGENTS.write_text(json.dumps(org, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: {OUT_STATUS.name} (tasks={status['task_queue']['total']}, "
          f"policy_events={status['policy_shadow']['total']}) / "
          f"{OUT_AGENTS.name} (agents={len(org['agents'])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
