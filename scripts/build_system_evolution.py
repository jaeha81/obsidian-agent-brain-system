#!/usr/bin/env python3
"""System Evolution 대시보드 데이터 생성기.

hand-authored seed(scripts/system_evolution_seed.json)를 읽어, growth_metrics의
now 값만 라이브로 계산(폴더 .md 카운트 / 스크립트 glob / git 커밋 수)한 뒤
docs/data/system_evolution.json 으로 병합 출력한다. 파일만 쓰고 git은 하지 않는다
(커밋/푸시는 run_daily_plus_pipeline.ps1 이 담당).

강건성 원칙: 안심용 페이지는 항상 렌더돼야 하므로, 폴더 부재/git 실패 시에도
raise 하지 않고 0 으로 degrade 한 뒤 계속 진행한다.
"""

from __future__ import annotations

import argparse
import glob
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "scripts" / "system_evolution_seed.json"
OUT = ROOT / "docs" / "data" / "system_evolution.json"
KST = timezone(timedelta(hours=9))


def _today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def _md_count(rel_path: str) -> int:
    try:
        return len(list((ROOT / rel_path).rglob("*.md")))
    except Exception:
        return 0


def _glob_count(pattern: str) -> int:
    try:
        return len(glob.glob(str(ROOT / pattern)))
    except Exception:
        return 0


def _git_commits() -> int:
    try:
        r = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=30,
        )
        return int(r.stdout.strip()) if r.returncode == 0 else 0
    except Exception:
        return 0


def _resolve_now(metric: dict, today: str) -> tuple[int, str]:
    """now_source.type 에 따라 (값, 기준일) 반환. static 은 seed의 now_date 보존."""
    src = metric.get("now_source", {})
    t = src.get("type")
    if t == "md_count":
        return _md_count(src.get("path", "")), today
    if t == "glob_count":
        return _glob_count(src.get("pattern", "")), today
    if t == "git_commits":
        return _git_commits(), today
    if t == "static":
        return int(src.get("value", 0)), src.get("now_date", today)
    return 0, today


def build(seed_path: Path = SEED, out_path: Path = OUT) -> Path:
    today = _today_kst()
    with seed_path.open(encoding="utf-8") as f:
        data = json.load(f)

    for metric in data.get("growth_metrics", []):
        now, now_date = _resolve_now(metric, today)
        metric["now"] = now
        metric["now_date"] = now_date
        metric.pop("now_source", None)  # 내부 계산 상세는 프런트에 노출하지 않음

    data["meta"] = {
        "last_updated": today,
        "version": "1.0",
        "next_update": "매일 오전 8시 자동",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="System Evolution 데이터 생성기")
    ap.add_argument("--seed", type=Path, default=SEED)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    out = build(args.seed, args.out)
    print(f"[system-evolution] wrote {out}")


if __name__ == "__main__":
    main()
