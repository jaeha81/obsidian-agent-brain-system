"""체크리스트 단일 저장소 — 읽기 실패가 데이터 삭제로 번지는 것을 막는다.

정본: data/user_checklist.json          (git 미추적 — 봇이 수시로 갱신)
미러: docs/data/user_checklist.json     (git 추적 — 대시보드가 읽고, 정본 복구원 역할)

2026-07-11 사고: discord_bot._cl_load()가 파일을 못 읽으면 조용히 빈 목록을 반환했고,
이어진 저장이 그 빈 목록을 정본·미러 양쪽에 덮어써 태스크 75개가 1개로 소실됐다.
그래서 이 모듈은 "읽지 못했다"와 "읽었더니 비어 있다"를 절대 섞지 않는다.
읽기에 실패하면 ChecklistUnavailable을 던진다 — 호출자는 저장하면 안 된다.
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "user_checklist.json"
MIRROR = ROOT / "docs" / "data" / "user_checklist.json"


class ChecklistUnavailable(RuntimeError):
    """정본·미러 어느 쪽도 신뢰할 수 있게 읽지 못했다. 이 상태에서 저장은 금지."""


def _read(path: Path) -> dict:
    # 볼트 계열 파일은 선두 BOM이 붙는 경우가 있어 utf-8-sig로 읽는다.
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
        raise ValueError(f"{path}: 'tasks' 배열이 없다")
    return data


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)  # 기존 파일 교체가 목적이므로 replace가 맞다(원자적)


def load() -> dict:
    """체크리스트를 읽는다.

    정본이 깨졌거나 없으면 미러에서 복구한다.
    빈 목록은 정본·미러가 **둘 다 없는** 진짜 최초 실행일 때만 반환한다.
    그 밖의 읽기 실패는 ChecklistUnavailable로 알린다 — 조용히 빈 목록을 내주지 않는다.
    """
    master_error: Exception | None = None
    if MASTER.exists():
        try:
            return _read(MASTER)
        except Exception as exc:
            master_error = exc  # 정본 손상 — 미러 복구를 시도한다

    if MIRROR.exists():
        try:
            data = _read(MIRROR)
        except Exception as exc:
            raise ChecklistUnavailable(
                f"정본({MASTER})과 미러({MIRROR}) 모두 읽을 수 없다: {exc}"
            ) from exc
        save(data)  # 정본을 미러 내용으로 되살린다
        return data

    if master_error is not None:
        raise ChecklistUnavailable(
            f"정본({MASTER})이 손상됐고 복구할 미러가 없다: {master_error}"
        ) from master_error

    return {"meta": {"version": "2.0", "last_updated": ""}, "tasks": []}


def save(data: dict) -> None:
    """정본과 미러를 함께 갱신한다. 둘 중 하나만 쓰이는 일은 없다."""
    if not isinstance(data.get("tasks"), list):
        raise ValueError("'tasks' 배열이 없는 데이터는 저장하지 않는다")

    data.setdefault("meta", {})["last_updated"] = str(date.today())
    text = json.dumps(data, ensure_ascii=False, indent=2)
    _write(MASTER, text)
    _write(MIRROR, text)
