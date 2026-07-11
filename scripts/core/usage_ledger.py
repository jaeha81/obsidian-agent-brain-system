#!/usr/bin/env python3
"""Bucky OS V3 — 사용량 원장 (Stage 10, V3 Stage 10 축소판).

data/usage/YYYY-MM.jsonl에 실행 1건당 1줄 append + 월 합계 집계.
플랜 근거: gap_analysis.md G1, implementation_backlog.md P0-7, target_architecture.md §3·§4.

원칙:
- record()는 어떤 실패도 예외로 전파하지 않는다 — 기록 실패가 실행을 막으면 안 됨 (§4-3).
- data/usage/는 .gitignore (오픈 퀘스천 2, 07-11 사용자 확정 A안) — 원장 jsonl은 커밋하지 않는다.
- 단가 정본: config/model_registry.yaml pricing (USD per 1M tokens). 예산 "추정" 전용 —
  구독(CLI) 실행은 토큰 과금이 아니므로 실청구와 다르다.
- 토큰 미보고 경로(Claude CLI)는 문자수/4 추정으로 기록하고 token_source="estimated_chars" 표기.
- 이중 기록 방지: claude_code 실행은 bucky_client(layer="cli")가 기록하고, adapter 래퍼는
  layer="adapter"로 기록한다. claude_code 어댑터는 bucky_client를 경유하므로 두 층에 모두
  남는다 → month_summary(dedup=True)는 layer="cli" 전체 + layer="adapter" 중
  provider != "claude_code"만 합산한다.

Usage (Python):
    from core.usage_ledger import record, month_summary
    record(provider="claude_code", model="sonnet", layer="cli", output_chars=1200)
    month_summary()  # 이번 달 합계

Usage (CLI 셀프테스트):
    python -X utf8 scripts/core/usage_ledger.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# 직접 실행 시에도 core.* import 가능하게 (provider_adapter.py와 동일 패턴)
_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from core.config import DATA, load_model_registry  # noqa: E402

USAGE_DIR: Path = DATA / "usage"
CHARS_PER_TOKEN = 4  # 보수적 근사 — 한글 비중이 높으면 실제 토큰은 이보다 많을 수 있음


def _pricing(model: str) -> dict | None:
    """model_registry.yaml pricing.<model> 항목. 없으면 None (cost 미산정)."""
    pricing = load_model_registry().get("pricing")
    if isinstance(pricing, dict):
        entry = pricing.get(model)
        if isinstance(entry, dict):
            return entry
    return None


def record(
    provider: str,
    model: str,
    *,
    layer: str = "cli",  # "cli" (bucky_client) | "adapter" (provider_adapter)
    task_id: str = "",
    task_type: str = "",
    source: str = "",
    input_chars: int = 0,
    output_chars: int = 0,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    duration_ms: int | None = None,
    success: bool | None = None,
    usage_dir: Path | str | None = None,
) -> Path | None:
    """원장에 1건 append. 성공 시 기록된 파일 경로, 실패 시 None (예외 전파 금지)."""
    try:
        if tokens_in is not None:
            t_in, token_source = int(tokens_in), "reported"
        else:
            t_in, token_source = max(0, int(input_chars)) // CHARS_PER_TOKEN, "estimated_chars"
        t_out = int(tokens_out) if tokens_out is not None else max(0, int(output_chars)) // CHARS_PER_TOKEN

        price = _pricing(str(model))
        cost_usd = None
        if price is not None:
            try:
                cost_usd = round(
                    t_in / 1_000_000 * float(price.get("input", 0))
                    + t_out / 1_000_000 * float(price.get("output", 0)),
                    6,
                )
            except (TypeError, ValueError):
                cost_usd = None

        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "provider": str(provider),
            "model": str(model),
            "layer": str(layer),
            "task_id": str(task_id),
            "task_type": str(task_type),
            "source": str(source),
            "tokens_in": t_in,
            "tokens_out": t_out,
            "token_source": token_source,
            "cost_usd": cost_usd,
            "duration_ms": duration_ms,
            "success": success,
        }

        directory = Path(usage_dir) if usage_dir else USAGE_DIR
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{time.strftime('%Y-%m')}.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return path
    except Exception:
        return None


def month_summary(
    month: str | None = None,
    usage_dir: Path | str | None = None,
    dedup: bool = True,
) -> dict:
    """월 합계. month="YYYY-MM" (기본: 이번 달). 반환:
    {"month", "records", "tokens_in", "tokens_out", "cost_usd", "by_model": {(provider/model): {...}}}

    dedup=True: claude_code는 cli 층만 집계 (adapter 층과 이중 기록되므로 — 모듈 docstring 참조).
    """
    month = month or time.strftime("%Y-%m")
    path = (Path(usage_dir) if usage_dir else USAGE_DIR) / f"{month}.jsonl"
    totals = {"month": month, "records": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "by_model": {}}
    if not path.is_file():
        return totals
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if dedup and e.get("layer") == "adapter" and e.get("provider") == "claude_code":
                continue
            key = f"{e.get('provider', '?')}/{e.get('model', '?')}"
            bucket = totals["by_model"].setdefault(key, {"records": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0})
            for agg in (totals, bucket):
                agg["records"] += 1
                agg["tokens_in"] += int(e.get("tokens_in") or 0)
                agg["tokens_out"] += int(e.get("tokens_out") or 0)
                agg["cost_usd"] = round(agg["cost_usd"] + (e.get("cost_usd") or 0.0), 6)
    return totals


# ─────────────────────────────────────────────────────────────
# 셀프테스트
# ─────────────────────────────────────────────────────────────


def self_test() -> int:
    """임시 디렉터리에 기록/집계 왕복 검증. 실원장(data/usage/)은 건드리지 않는다."""
    import tempfile

    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        month = time.strftime("%Y-%m")

        # 1. 보고 토큰 + 단가 계산 (sonnet: $3/$15 per 1M → 1M/1M 토큰 = $18)
        p = record("claude_code", "sonnet", layer="cli", tokens_in=1_000_000, tokens_out=1_000_000, usage_dir=tmp)
        if p is None or not p.is_file():
            failures.append("기록 실패 (보고 토큰)")
        else:
            e = json.loads(p.read_text(encoding="utf-8").splitlines()[0])
            if e["token_source"] != "reported":
                failures.append(f"token_source: {e['token_source']!r} != 'reported'")
            if _pricing("sonnet") and e["cost_usd"] != 18.0:
                failures.append(f"sonnet 1M/1M cost_usd: {e['cost_usd']} != 18.0")

        # 2. 문자수 추정 경로
        record("claude_code", "sonnet", layer="cli", input_chars=400, output_chars=800, usage_dir=tmp)
        lines = (Path(tmp) / f"{month}.jsonl").read_text(encoding="utf-8").splitlines()
        e = json.loads(lines[-1])
        if (e["tokens_in"], e["tokens_out"], e["token_source"]) != (100, 200, "estimated_chars"):
            failures.append(f"문자수 추정 오류: {e['tokens_in']}/{e['tokens_out']}/{e['token_source']}")

        # 3. 미등록 모델 → cost_usd None (crash 금지)
        record("codex_pro", "gpt-x", layer="adapter", tokens_in=10, tokens_out=10, usage_dir=tmp)
        e = json.loads((Path(tmp) / f"{month}.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        if e["cost_usd"] is not None:
            failures.append(f"미등록 모델 cost_usd: {e['cost_usd']} != None")

        # 4. dedup: adapter 층 claude_code는 집계 제외, 타 provider adapter 층은 포함
        record("claude_code", "sonnet", layer="adapter", tokens_in=999, tokens_out=999, usage_dir=tmp)
        s = month_summary(month, usage_dir=tmp)
        if s["records"] != 3:  # 1+2+3번만 (4번 제외)
            failures.append(f"dedup 집계: records={s['records']} != 3")
        s_all = month_summary(month, usage_dir=tmp, dedup=False)
        if s_all["records"] != 4:
            failures.append(f"dedup=False 집계: records={s_all['records']} != 4")

    # 5. 기록 실패 시 예외 없이 None (usage_dir가 파일이면 mkdir 실패)
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        blocked = tf.name
    try:
        if record("x", "y", usage_dir=Path(blocked) / "sub") is not None:
            failures.append("실패 경로에서 None이 아님")
    finally:
        import os

        os.unlink(blocked)

    # 6. 단가표 로드 확인
    if _pricing("sonnet") is None:
        failures.append("model_registry.yaml pricing.sonnet 누락")

    if failures:
        print(f"셀프테스트 FAIL ({len(failures)}건)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("셀프테스트 PASS (6항목)")
    return 0


if __name__ == "__main__":
    sys.exit(self_test())
