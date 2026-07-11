#!/usr/bin/env python3
"""Bucky OS V3 — config 단일화 스캐폴드 (Stage 3).

ROOT/Vault/AgentBus/data/docs 경로의 단일 정의 + config/*.yaml 로더.
env가 없어도, yaml이 깨져 있어도 crash하지 않는다 (빈 dict 폴백).
기존 파일들의 하드코딩 경로·모델명은 Stage 7 이후 점진 이관.

Usage (Python):
    from core.config import PATHS, load_bucky, load_model_registry, load_routing_policy

Usage (CLI 셀프테스트):
    python -X utf8 scripts/core/config.py
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        # 이미 utf-8이면 재래핑 금지 — reload 시 이전 래퍼 GC가 공유 버퍼를 닫는 사고 방지
        for _name in ("stdout", "stderr"):
            _stream = getattr(sys, _name)
            if (_stream.encoding or "").lower().replace("-", "") != "utf8":
                setattr(sys, _name, io.TextIOWrapper(_stream.buffer, encoding="utf-8", errors="replace"))
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────
# 경로 단일 정의
# ─────────────────────────────────────────────────────────────


def _detect_root() -> Path:
    """저장소 루트 탐지. env BUCKY_ROOT 우선, 없으면 이 파일 위치 기준."""
    env_root = os.getenv("BUCKY_ROOT", "").strip()
    if env_root:
        p = Path(env_root)
        if p.is_dir():
            return p.resolve()
    return Path(__file__).resolve().parents[2]


ROOT: Path = _detect_root()
CONFIG_DIR: Path = ROOT / "config"
VAULT: Path = ROOT / "ObsidianVault"
AGENT_BUS: Path = VAULT / "10_AgentBus"
DATA: Path = ROOT / "data"
DOCS: Path = ROOT / "docs"
SCRIPTS: Path = ROOT / "scripts"

PATHS: dict[str, Path] = {
    "root": ROOT,
    "config": CONFIG_DIR,
    "vault": VAULT,
    "agent_bus": AGENT_BUS,
    "data": DATA,
    "docs": DOCS,
    "scripts": SCRIPTS,
}

# 런타임에 생성되는 gitignore 경로 — 깨끗한 clone에는 없어도 정상 (존재 필수화 금지).
RUNTIME_KEYS: frozenset[str] = frozenset({"data"})

# ─────────────────────────────────────────────────────────────
# yaml 로더 (crash 금지 — 실패 시 빈 dict)
# ─────────────────────────────────────────────────────────────


def load_yaml(name: str, config_dir: Path | None = None) -> dict:
    """config/<name> yaml을 dict로 로드. 파일 없음·파싱 실패·PyYAML 부재 → {}."""
    path = (config_dir or CONFIG_DIR) / name
    if not path.is_file():
        return {}
    try:
        import yaml
    except ImportError:
        print(f"[config] PyYAML 없음 — {name} 건너뜀", file=sys.stderr)
        return {}
    try:
        with open(path, encoding="utf-8-sig") as f:  # BOM 방어
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"[config] {name} 파싱 실패: {e}", file=sys.stderr)
        return {}
    return data if isinstance(data, dict) else {}


def load_bucky() -> dict:
    return load_yaml("bucky.yaml")


def load_model_registry() -> dict:
    return load_yaml("model_registry.yaml")


def load_routing_policy() -> dict:
    return load_yaml("routing_policy.yaml")


# ─────────────────────────────────────────────────────────────
# 셀프테스트
# ─────────────────────────────────────────────────────────────


def self_test() -> int:
    """경로 해석 + yaml 3종 로드 확인. 실패 항목 있으면 1 반환."""
    failures: list[str] = []

    print("== 경로 ==")
    for key, path in PATHS.items():
        mark = "OK " if path.is_dir() else "MISS"
        print(f"  [{mark}] {key}: {path}")
        # 런타임 키는 "아예 없음"만 허용 — 일반 파일로 존재하면 실패 (Codex 재검수 LOW)
        if not path.is_dir() and (key not in RUNTIME_KEYS or path.exists()):
            failures.append(f"경로 없음: {key}={path}")

    print("== config yaml ==")
    checks = {
        "bucky.yaml": (load_bucky(), ["system", "paths", "oracle"]),
        "model_registry.yaml": (load_model_registry(), ["providers"]),
        "routing_policy.yaml": (load_routing_policy(), ["defaults"]),
    }
    for name, (data, required_keys) in checks.items():
        missing = [k for k in required_keys if k not in data]
        if missing:
            failures.append(f"{name}: 필수 키 누락 {missing}")
            print(f"  [FAIL] {name}: 필수 키 누락 {missing}")
        else:
            print(f"  [OK ] {name}: keys={sorted(data.keys())}")

    providers = load_model_registry().get("providers", {})
    if providers:
        enabled = [k for k, v in providers.items() if v.get("enabled")]
        print(f"  providers: {len(providers)}개 (enabled: {', '.join(enabled)})")

    if failures:
        print(f"셀프테스트 FAIL ({len(failures)}건)")
        return 1
    print("셀프테스트 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(self_test())
