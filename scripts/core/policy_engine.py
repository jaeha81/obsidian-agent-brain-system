#!/usr/bin/env python3
"""Bucky OS V3 — 승인 정책 엔진 (Stage 18, P0-6).

config/policy_rules.yaml의 T0~T3 위험 등급 데이터로 TaskSpec을 판정하는 순수 함수.
어디에도 배선되지 않았다 — worker 상담(shadow)은 Stage 19에서. 판정만 반환하며
실행·차단·이벤트 방출·승인 요청을 하지 않는다.

폴백 방향: 로드 실패·미분류·티어 정의 결손은 전부 보수 기본값(T3 require_approval).
다른 모듈의 crash-금지 폴백은 관대(echo 유지)지만, 정책 엔진이 관대로 폴백하면
결손이 조용히 auto로 새므로 보수가 맞다 — shadow에서는 이벤트만 남아 무해하고
오분류 관측 신호가 된다 (ADR-0004).

Usage:
    from core.policy_engine import evaluate
    verdict = evaluate(spec)  # {"tier": "T1", "decision": "auto_log", "reason": "..."}

CLI 셀프테스트:
    python -X utf8 scripts/core/policy_engine.py
"""

from __future__ import annotations

import io
import sys

if sys.platform == "win32":
    try:
        for _name in ("stdout", "stderr"):
            _stream = getattr(sys, _name)
            if (_stream.encoding or "").lower().replace("-", "") != "utf8":
                setattr(sys, _name, io.TextIOWrapper(_stream.buffer, encoding="utf-8", errors="replace"))
    except Exception:
        pass

RULES_FILE = "policy_rules.yaml"
REQUIRED_TIERS = ("T0", "T1", "T2", "T3")
# 보수 기본값 — 결손 시 자동 실행으로 새지 않게 하는 안전핀
CONSERVATIVE_TIER = "T3"
CONSERVATIVE_DECISION = "require_approval"


def load_rules() -> dict:
    """config/policy_rules.yaml 로드. 실패 시 {} (crash 금지 — 판정은 보수 폴백)."""
    from core.config import load_yaml

    return load_yaml(RULES_FILE)


def evaluate(spec: object, rules: dict | None = None) -> dict:
    """TaskSpec(또는 dict) → {"tier", "decision", "reason"} 판정. 순수 함수 — 부작용 없음.

    - task_type은 소문자 정규화 후 task_tiers에서 조회
    - 미분류 → default_tier (yaml 결손 시 T3)
    - tiers 섹션 자체가 없으면(로드 실패 포함) 보수 기본값
    """
    if rules is None:
        rules = load_rules()
    if isinstance(spec, dict):
        task_type = spec.get("task_type")
    else:
        task_type = getattr(spec, "task_type", "")
    key = task_type.lower().strip() if isinstance(task_type, str) else ""

    tiers = rules.get("tiers") if isinstance(rules, dict) else None
    if not isinstance(tiers, dict) or not tiers:
        return {"tier": CONSERVATIVE_TIER, "decision": CONSERVATIVE_DECISION,
                "reason": f"{RULES_FILE} 로드 실패 또는 tiers 없음 — 보수 기본값"}

    task_tiers = rules.get("task_tiers")
    tier = task_tiers.get(key) if isinstance(task_tiers, dict) else None
    if isinstance(tier, str) and tier:
        reason = f"task_tiers[{key!r}] → {tier}"
    else:
        tier = str(rules.get("default_tier") or CONSERVATIVE_TIER)
        reason = f"미분류 task_type={key!r} → 기본값 {tier}"

    tier_def = tiers.get(tier)
    decision = tier_def.get("decision") if isinstance(tier_def, dict) else None
    if not isinstance(decision, str) or not decision:
        return {"tier": tier, "decision": CONSERVATIVE_DECISION,
                "reason": reason + f" (tiers.{tier}.decision 결손 — 보수 기본값)"}
    return {"tier": tier, "decision": decision, "reason": reason}


def validate_rules(rules: dict, routing_policy: dict | None = None) -> list[str]:
    """policy_rules.yaml 구조 위반 목록 반환. 빈 리스트면 유효.

    routing_policy를 넘기면 top-level 키 중복도 검사한다 — 라우팅(provider 후보열)과
    정책(위험 티어)의 키 공간 분리 강제 (config 단일화 원칙, 플랜 Stage 18 요구).
    """
    errors: list[str] = []
    if not isinstance(rules, dict) or not rules:
        return [f"{RULES_FILE}이 비어 있거나 dict가 아님"]

    tiers = rules.get("tiers")
    if not isinstance(tiers, dict):
        errors.append("tiers 섹션 없음")
        tiers = {}
    for t in REQUIRED_TIERS:
        tier_def = tiers.get(t)
        if not isinstance(tier_def, dict) or not tier_def.get("decision"):
            errors.append(f"tiers.{t}.decision 누락")

    task_tiers = rules.get("task_tiers")
    if not isinstance(task_tiers, dict) or not task_tiers:
        errors.append("task_tiers 섹션 없음")
    else:
        for k, v in task_tiers.items():
            if v not in tiers:
                errors.append(f"task_tiers.{k}={v!r} — 미정의 tier 참조")

    if rules.get("default_tier") not in tiers:
        errors.append(f"default_tier={rules.get('default_tier')!r} — 미정의 tier 참조")

    dispatch = rules.get("dispatch")
    if not isinstance(dispatch, dict) or not isinstance(dispatch.get("fallback_on_run_failure"), bool):
        errors.append("dispatch.fallback_on_run_failure(bool) 누락 — G4 권고 1 확정 사항(07-12 A안)")

    if routing_policy is not None and isinstance(routing_policy, dict):
        dup = sorted(set(rules) & set(routing_policy))
        if dup:
            errors.append(f"routing_policy.yaml과 top-level 키 중복: {dup}")
    return errors


# ─────────────────────────────────────────────────────────────
# 셀프테스트
# ─────────────────────────────────────────────────────────────


def self_test() -> int:
    """repo yaml 유효성 + 대표 판정 3종 + 보수 폴백 확인. 실패 있으면 1 반환."""
    from core.config import load_routing_policy

    failures: list[str] = []
    rules = load_rules()

    errors = validate_rules(rules, routing_policy=load_routing_policy())
    if errors:
        failures.append(f"validate_rules: {errors}")
    print(f"  [{'FAIL' if errors else 'OK '}] policy_rules.yaml 유효성 (위반 {len(errors)}건)")

    cases = {  # task_type → 기대 (tier, decision)
        "classify": ("T0", "auto"),
        "code": ("T1", "auto_log"),
        "deploy": ("T3", "require_approval"),
        "없는유형": ("T3", "require_approval"),
    }
    for task_type, (want_tier, want_decision) in cases.items():
        v = evaluate({"task_type": task_type}, rules)
        ok = v["tier"] == want_tier and v["decision"] == want_decision
        if not ok:
            failures.append(f"{task_type}: {v}")
        print(f"  [{'OK ' if ok else 'FAIL'}] {task_type} → {v['tier']}/{v['decision']}")

    v = evaluate({"task_type": "chat"}, rules={})
    ok = v["decision"] == CONSERVATIVE_DECISION
    if not ok:
        failures.append(f"빈 rules 폴백: {v}")
    print(f"  [{'OK ' if ok else 'FAIL'}] 빈 rules → 보수 기본값 {v['decision']}")

    if failures:
        print(f"셀프테스트 FAIL ({len(failures)}건)")
        return 1
    print(f"셀프테스트 PASS ({1 + len(cases) + 1}항목)")
    return 0


if __name__ == "__main__":
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # scripts/ — core.* import용
    sys.exit(self_test())
