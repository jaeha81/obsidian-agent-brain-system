#!/usr/bin/env python3
"""Oracle obsidian-index — 경량 인덱스 로드 + 키워드/메타 검색 (B3).

집PC 인덱서(scripts/obsidian_indexer.py)가 밀어넣은 records.jsonl/manifest.json을
읽어 키워드·메타데이터 검색(발견/라우팅)을 제공한다. stdlib 전용 — Oracle #2(aarch64)에서
pip 없이 동작. 의미검색은 집PC gbrain 담당(공존). 스키마 계약: scripts/obsidian_index_schema.md.

파일 mtime 기반 캐시라 집PC가 인덱스를 갱신하면 재기동 없이 자동 반영된다.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX_DIR = Path(os.environ.get("OBSIDIAN_INDEX_DIR", ROOT / "memory" / "obsidian-index"))
RECORDS_FILE = INDEX_DIR / "records.jsonl"
MANIFEST_FILE = INDEX_DIR / "manifest.json"

# 검색 스코어링 가중치 — scripts/obsidian_index_schema.md 계약과 동일.
SEARCH_WEIGHTS = {"keywords": 5, "title": 4, "headings": 3, "meta": 2, "snippet": 1}

# 무필터 기본 검색 시 운영/원본 선반 감점(지식 선반을 상위로). 명시 folder 필터 시엔 미적용.
FOLDER_DEMOTION = {
    "10_AgentBus": 0.2,
    "01_RAW": 0.35,
    "00_Inbox": 0.4,
    "05_Logs": 0.25,
    "02_Processed": 0.5,
    "04_DAILY_REPORTS": 0.5,
}

MAX_TOP_K = 50

# ── mtime 기반 캐시 ────────────────────────────────────────────────────────────
_cache: dict = {"mtime": None, "records": []}


def load_records() -> list[dict]:
    """records.jsonl을 로드(파일 mtime 변하면 재로드). 없으면 빈 리스트."""
    if not RECORDS_FILE.exists():
        _cache["mtime"] = None
        _cache["records"] = []
        return []
    mtime = RECORDS_FILE.stat().st_mtime
    if _cache["mtime"] == mtime:
        return _cache["records"]
    records: list[dict] = []
    with RECORDS_FILE.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    _cache["mtime"] = mtime
    _cache["records"] = records
    return records


def index_available() -> bool:
    return RECORDS_FILE.exists()


def _score(rec: dict, tokens: list[str]) -> int:
    tiers = {
        "keywords": " ".join(rec.get("keywords", [])).lower(),
        "title": (rec.get("title") or "").lower(),
        "headings": " ".join(rec.get("headings", [])).lower(),
        "meta": " ".join(
            rec.get("tags", []) + [str(rec.get("type") or ""), str(rec.get("domain") or "")]
        ).lower(),
        "snippet": (rec.get("snippet") or "").lower(),
    }
    score = 0
    for tok in tokens:
        for tier, text in tiers.items():
            if tok in text:
                score += SEARCH_WEIGHTS[tier]
    return score


def search(
    query: str,
    top_k: int = 5,
    folder: str | None = None,
    ntype: str | None = None,
) -> list[dict]:
    """키워드 top-k 검색. folder/type 필터 지원, 무필터 시 운영/원본 선반 감점."""
    tokens = [t for t in re.split(r"\s+", (query or "").lower()) if t]
    if not tokens:
        return []
    top_k = max(1, min(int(top_k or 5), MAX_TOP_K))
    records = load_records()

    scored: list[tuple[float, dict]] = []
    for rec in records:
        if folder and rec.get("folder") != folder:
            continue
        if ntype and rec.get("type") != ntype:
            continue
        base = _score(rec, tokens)
        if base <= 0:
            continue
        # 명시 folder 필터가 없을 때만 선반 감점 적용
        weight = 1.0 if folder else FOLDER_DEMOTION.get(rec.get("folder", ""), 1.0)
        scored.append((base * weight, rec))

    scored.sort(key=lambda x: (-x[0], x[1].get("path", "")))
    out: list[dict] = []
    for s, rec in scored[:top_k]:
        out.append(
            {
                "slug": rec.get("slug"),
                "path": rec.get("path"),
                "title": rec.get("title"),
                "folder": rec.get("folder"),
                "type": rec.get("type"),
                "keywords": rec.get("keywords", []),
                "snippet": rec.get("snippet"),
                "score": round(s, 2),
            }
        )
    return out


def stats() -> dict:
    """manifest 요약 + 로드된 레코드 수."""
    manifest = {}
    if MANIFEST_FILE.exists():
        try:
            manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            manifest = {}
    return {
        "available": index_available(),
        "index_dir": str(INDEX_DIR),
        "count": manifest.get("count", len(load_records())),
        "schema_version": manifest.get("schema_version"),
        "generated_at": manifest.get("generated_at"),
        "folders": manifest.get("folders", {}),
    }
