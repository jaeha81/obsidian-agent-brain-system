#!/usr/bin/env python3
"""
Model Router — Sonnet/Haiku/Opus 효율 라우팅.

작업 유형(task_type)을 받아 최적 모델을 반환.
Sonnet 한도 초과 시 자동 폴백 체인 지원.

정책 문서:
  ObsidianVault/05_Frameworks/guides/model-routing.md

Usage (Python):
    from model_router import select_model, fallback_chain, provider_candidates
    model = select_model("classify")          # → "haiku"
    chain = fallback_chain("sonnet")          # → ["sonnet", "haiku", "opus"]
    provs = provider_candidates("review")     # → ["codex_pro", "claude_code"] (V3 Stage 7)

Usage (CLI):
    python model_router.py classify           # prints: haiku
    python model_router.py --chain sonnet     # prints: sonnet,haiku,opus
    python model_router.py --providers review # prints: codex_pro,claude_code
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable

if sys.platform == "win32":
    try:
        # 이미 utf-8이면 손대지 않는다. wrapper 교체는 기존 wrapper GC가 공유 buffer를
        # 닫아 stdout이 죽을 수 있으므로 reconfigure로 인코딩만 바꾼다(내부 flush 포함).
        for _name in ("stdout", "stderr"):
            _stream = getattr(sys, _name)
            if (_stream.encoding or "").lower().replace("-", "") != "utf8":
                _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────
# 모델 라우팅 테이블
# ─────────────────────────────────────────────────────────────

# 모델별 특성:
# - haiku  : 빠름·저렴·별도 한도 / 단순 분류·추출·요약·태깅
# - sonnet : 기본·균형 / 일반 코딩·편집·대화·문서 작성
# - opus   : 강력·고비용 / 아키텍처·검수·디버깅·보안·복잡 추론

TASK_TO_MODEL: dict[str, str] = {
    # ── Haiku 영역 (단순·빈번·빠른 응답) ───────────────────
    "status": "haiku",          # 상태 확인, 헬스 체크
    "classify": "haiku",         # 메시지 분류, 라우팅 결정
    "extract": "haiku",          # 엔티티/태그/메타 추출
    "tag": "haiku",              # 태그 부여
    "format": "haiku",           # 텍스트 포맷 변환
    "short_summary": "haiku",    # 1~2문장 요약
    "nlp_preprocess": "haiku",   # NLP 전처리
    "intent": "haiku",           # 의도 분류
    "transcribe_postprocess": "haiku",  # STT 후처리

    # ── Sonnet 영역 (코딩·편집·대화 기본값) ────────────────
    "chat": "sonnet",            # 일반 대화
    "code": "sonnet",            # 코드 작성
    "edit": "sonnet",            # 파일 편집
    "doc": "sonnet",             # 문서 작성
    "research": "sonnet",        # 코드베이스 분석
    "implementation": "sonnet",  # 기능 구현
    "long_summary": "sonnet",    # 긴 요약
    "default": "sonnet",         # 알 수 없는 작업

    # ── Opus 영역 (복잡 추론·검수·고난도) ───────────────────
    "architecture": "opus",      # 아키텍처 설계
    "review": "opus",            # 코드 리뷰 (Codex 보완)
    "debug": "opus",             # 복잡한 디버깅
    "security": "opus",          # 보안 분석
    "reasoning": "opus",         # 멀티스텝 추론
    "self_reflection": "opus",   # 자기 반성·메타 분석
    "vision": "opus",            # 이미지 분석 (멀티모달 강점)
    "strategy": "opus",          # 전략 수립
    "knowledge_distill": "opus", # 지식 증류
}

# 모델별 폴백 체인 (한도 초과 시 다음 모델 시도)
FALLBACK_CHAINS: dict[str, list[str]] = {
    "sonnet": ["sonnet", "haiku", "opus"],  # Sonnet 빠르게 소진 → Haiku 폴백 (다른 한도)
    "haiku": ["haiku", "sonnet"],           # Haiku 한도 시 Sonnet
    "opus": ["opus", "sonnet", "haiku"],    # Opus 한도 시 Sonnet
}

# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────


def select_model(task_type: str, override: str | None = None) -> str:
    """작업 유형 기반 모델 선택. override 우선."""
    if override:
        return _normalize(override)
    # 환경변수 강제 override
    env_force = os.getenv("BUCKY_FORCE_MODEL", "").strip()
    if env_force:
        return _normalize(env_force)
    return TASK_TO_MODEL.get(task_type.lower().strip(), TASK_TO_MODEL["default"])


def fallback_chain(primary: str) -> list[str]:
    """1차 모델 → 폴백 체인 반환."""
    primary = _normalize(primary)
    return FALLBACK_CHAINS.get(primary, [primary])


def model_for_command(task_type: str) -> str:
    """Claude CLI에 그대로 넘길 수 있는 모델 별칭(sonnet/haiku/opus)."""
    return select_model(task_type)


# ─────────────────────────────────────────────────────────────
# Provider 라우팅 (V3 Stage 7) — task_type → provider 후보열
# ─────────────────────────────────────────────────────────────

# routing_policy.yaml 로드 실패 시 최소 안전 기본값 (실연동 어댑터 보유 provider만)
DEFAULT_PROVIDER_CHAIN: list[str] = ["claude_code"]


def provider_candidates(task_type: str, policy: dict | None = None) -> list[str]:
    """task_type → provider 후보열 (이름은 config/model_registry.yaml 키와 일치).

    정본은 config/routing_policy.yaml: overrides.<task_type> → defaults.provider_chain.
    로드 실패·형식 불량 시 DEFAULT_PROVIDER_CHAIN — crash 금지.
    claude 티어 선택(select_model)과는 독립: 후보열에 claude_code가 있으면
    그 내부 모델(haiku/sonnet/opus)은 기존 TASK_TO_MODEL이 정한다.
    """
    if policy is None:
        try:
            from core.config import load_routing_policy
            policy = load_routing_policy()
        except Exception:
            policy = {}
    if not isinstance(policy, dict):
        policy = {}
    key = (task_type or "").lower().strip()

    overrides = policy.get("overrides")
    if isinstance(overrides, dict):
        chain = overrides.get(key)
        if _valid_provider_chain(chain):
            return list(chain)

    defaults = policy.get("defaults")
    if isinstance(defaults, dict):
        chain = defaults.get("provider_chain")
        if _valid_provider_chain(chain):
            return list(chain)

    return list(DEFAULT_PROVIDER_CHAIN)


def _valid_provider_chain(chain: object) -> bool:
    return (
        isinstance(chain, list)
        and len(chain) > 0
        and all(isinstance(p, str) and p.strip() for p in chain)
    )


def explain(task_type: str) -> dict:
    """라우팅 의사결정 설명 (디버깅·로깅용)."""
    selected = select_model(task_type)
    return {
        "task_type": task_type,
        "selected_model": selected,
        "fallback_chain": fallback_chain(selected),
        "reason": _reason_for(task_type, selected),
        "env_override": bool(os.getenv("BUCKY_FORCE_MODEL", "").strip()),
    }


# ─────────────────────────────────────────────────────────────
# 내부 유틸
# ─────────────────────────────────────────────────────────────


def _normalize(model: str) -> str:
    """모델 별칭 정규화. claude-haiku-4-5-20251001 → haiku 등."""
    m = model.lower().strip()
    if "haiku" in m:
        return "haiku"
    if "opus" in m:
        return "opus"
    if "sonnet" in m:
        return "sonnet"
    return m  # 알 수 없으면 그대로


def _reason_for(task_type: str, model: str) -> str:
    reasons = {
        "haiku": "단순·빈번 작업 — 속도·비용 우선, Sonnet 한도 절약",
        "sonnet": "코딩·편집 기본값 — 균형 잡힌 성능",
        "opus": "복잡 추론·검수 — 정확성 우선, 한도 여유 활용",
    }
    in_table = task_type.lower().strip() in TASK_TO_MODEL
    base = reasons.get(model, "기본 라우팅")
    if not in_table:
        return f"{base} (작업 유형 미정의 → default 적용)"
    return base


def list_routing_table() -> str:
    """라우팅 테이블 마크다운 출력 (문서 생성·디버깅용)."""
    lines = ["| Task Type | Model |", "|-----------|-------|"]
    by_model: dict[str, list[str]] = {"haiku": [], "sonnet": [], "opus": []}
    for task, model in TASK_TO_MODEL.items():
        by_model.setdefault(model, []).append(task)
    for model in ("haiku", "sonnet", "opus"):
        tasks = sorted(by_model.get(model, []))
        for t in tasks:
            lines.append(f"| `{t}` | **{model}** |")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description="Model Router — task → sonnet/haiku/opus")
    ap.add_argument("task_type", nargs="?", default="default", help="작업 유형")
    ap.add_argument("--chain", metavar="MODEL", help="해당 모델의 폴백 체인 출력")
    ap.add_argument("--providers", action="store_true", help="task_type → provider 후보열 출력 (V3)")
    ap.add_argument("--explain", action="store_true", help="라우팅 의사결정 설명")
    ap.add_argument("--table", action="store_true", help="전체 라우팅 테이블 출력")
    args = ap.parse_args()

    if args.table:
        print(list_routing_table())
        return 0

    if args.chain:
        print(",".join(fallback_chain(args.chain)))
        return 0

    if args.providers:
        print(",".join(provider_candidates(args.task_type)))
        return 0

    if args.explain:
        import json
        print(json.dumps(explain(args.task_type), ensure_ascii=False, indent=2))
        return 0

    print(select_model(args.task_type))
    return 0


if __name__ == "__main__":
    sys.exit(main())
