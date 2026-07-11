#!/usr/bin/env python3
"""Bucky OS V3 — Task/Goal/Project 레지스트리 최소판 (Stage 16).

data/registry/projects.yaml (사람 편집: id/title/status/parent_goal) 로드·검증·조회.
플랜 근거: implementation_backlog.md P0-3, target_architecture.md §Stage 16.

원칙:
- **작업 정본은 오라클 큐 — 레지스트리는 분류 축만** (backlog P0-3).
- 로드는 crash 금지 — 파일 없음·파싱 실패 → 빈 레지스트리 (config.load_yaml 재사용, BOM 방어 포함).
- task_spec.project_id는 optional — 미등록 id도 태스크를 막지 않는다.
  validate_registry()는 등록부 자체 무결성만 검사한다.

Usage (Python):
    from core.registry import load_projects, get_project, validate_registry
    projects = load_projects()          # {id: {...}} — 실패 시 {}
    p = get_project("bucky-os-v3")      # dict | None
    errors = validate_registry()        # [] 이면 유효

Usage (CLI 셀프테스트):
    python -X utf8 scripts/core/registry.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# 직접 실행 시에도 core.* import 가능하게 (event_log.py와 동일 패턴)
_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from core.config import DATA, load_yaml  # noqa: E402

PROJECTS_PATH: Path = DATA / "registry" / "projects.yaml"

STATUSES: tuple[str, ...] = ("active", "paused", "done")


def _load_raw(path: Path | str | None = None) -> dict:
    p = Path(path) if path else PROJECTS_PATH
    return load_yaml(p.name, p.parent)


def load_projects(path: Path | str | None = None) -> dict[str, dict]:
    """id → project dict 맵. 중복 id는 첫 항목 유지. 실패·형식 불량 → {}."""
    items = _load_raw(path).get("projects")
    if not isinstance(items, list):
        return {}
    out: dict[str, dict] = {}
    for item in items:
        if isinstance(item, dict):
            pid = str(item.get("id") or "").strip()
            if pid and pid not in out:
                out[pid] = item
    return out


def get_project(project_id: str, path: Path | str | None = None) -> dict | None:
    """project_id로 항목 조회. 미등록·로드 실패 → None (예외 전파 금지)."""
    return load_projects(path).get(str(project_id or "").strip())


def validate_registry(path: Path | str | None = None) -> list[str]:
    """등록부 무결성 위반 목록 반환. 빈 리스트면 유효.

    미등록 project_id를 쓰는 태스크는 여기서 다루지 않는다 — 분류 축은 태스크를 막지 않는다.
    """
    raw = _load_raw(path)
    if not raw:
        return ["projects.yaml 로드 실패 또는 빈 파일"]
    items = raw.get("projects")
    if not isinstance(items, list):
        return ["projects는 리스트여야 함"]
    errors: list[str] = []
    seen: set[str] = set()
    for i, item in enumerate(items):
        where = f"projects[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: 객체가 아님")
            continue
        pid = str(item.get("id") or "").strip()
        if not pid:
            errors.append(f"{where}: id 필수")
        elif pid in seen:
            errors.append(f"{where}: id 중복 {pid!r}")
        else:
            seen.add(pid)
        if not str(item.get("title") or "").strip():
            errors.append(f"{where}: title 필수")
        if item.get("status") not in STATUSES:
            errors.append(f"{where}: status must be one of {STATUSES}: {item.get('status')!r}")
        if not isinstance(item.get("parent_goal", ""), str):
            errors.append(f"{where}: parent_goal은 문자열이어야 함")
    return errors


# ─────────────────────────────────────────────────────────────
# 셀프테스트
# ─────────────────────────────────────────────────────────────


def self_test() -> int:
    """실파일 검증 + tmp 경계 사례. 실패 항목 있으면 1 반환."""
    import tempfile

    failures: list[str] = []

    # 1. 실등록부 로드 + 무결성 (배포 시드는 항상 유효해야 함)
    real = load_projects()
    if not real:
        failures.append(f"실등록부 로드 실패: {PROJECTS_PATH}")
    real_errors = validate_registry()
    if real_errors:
        failures.append(f"실등록부 무결성 위반: {real_errors}")

    with tempfile.TemporaryDirectory() as tmp:
        # 2. 파일 없음 → 빈 레지스트리, get_project None (crash 금지)
        missing = Path(tmp) / "projects.yaml"
        if load_projects(missing) != {} or get_project("x", missing) is not None:
            failures.append("파일 없음에서 빈 레지스트리가 아님")

        # 3. 중복 id → validate 검출 + load는 첫 항목 유지
        dup = Path(tmp) / "dup.yaml"
        dup.write_text(
            "projects:\n"
            "  - {id: a, title: T1, status: active, parent_goal: g}\n"
            "  - {id: a, title: T2, status: active, parent_goal: g}\n",
            encoding="utf-8",
        )
        if not any("중복" in e for e in validate_registry(dup)):
            failures.append("중복 id 미검출")
        if load_projects(dup).get("a", {}).get("title") != "T1":
            failures.append("중복 id에서 첫 항목 유지 실패")

        # 4. 잘못된 status → 검출
        bad = Path(tmp) / "bad.yaml"
        bad.write_text("projects:\n  - {id: b, title: T, status: nope}\n", encoding="utf-8")
        if not any("status" in e for e in validate_registry(bad)):
            failures.append("잘못된 status 미검출")

        # 5. BOM 방어 (utf-8-sig 로드 — 볼트 BOM 함정 대비)
        bom = Path(tmp) / "bom.yaml"
        bom.write_bytes("projects:\n  - {id: c, title: T, status: active}\n".encode("utf-8-sig"))
        if "c" not in load_projects(bom):
            failures.append("BOM 파일 로드 실패")

    if failures:
        print(f"셀프테스트 FAIL ({len(failures)}건)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"셀프테스트 PASS (5항목, 실등록부 {len(real)}건)")
    return 0


if __name__ == "__main__":
    sys.exit(self_test())
