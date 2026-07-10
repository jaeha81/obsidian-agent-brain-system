#!/usr/bin/env python3
"""Obsidian Indexer — B2 (집PC 인덱서)

ObsidianVault/**/*.md 를 파싱해 **경량 인덱스**(메타데이터 + 짧은 스니펫)를 산출한다.
Oracle obsidian-index API(B3)가 이 산출물을 실어 키워드/메타 검색(발견·라우팅)을 제공한다.

설계 제약(왜 stdlib 전용인가):
    Oracle #2(aarch64)는 pip 없이 stdlib만 기동 → 인덱스는 plain JSON, 임베딩 없음.
    의미검색은 집PC gbrain(vault_rag)이 담당(공존). 스키마 정본: scripts/obsidian_index_schema.md.

재사용 근거:
    - 슬러그/제외폴더/tier/resume 패턴 → scripts/sync_vault_to_gbrain.py
    - 헤더 분할·frontmatter 파싱 아이디어 → scripts/vault_rag.py, knowledge_distiller.py

산출물(OBSIDIAN_INDEX_DIR, 기본 data/obsidian-index/):
    records.jsonl   노트 1개 = 1줄 JSON
    manifest.json   스키마 버전·생성시각·집계·증분 해시맵

사용법:
    python obsidian_indexer.py index              # 증분 인덱싱(변경분만)
    python obsidian_indexer.py index --force       # 전체 재인덱싱
    python obsidian_indexer.py index --tier 2      # 특정 tier만(sync 규약)
    python obsidian_indexer.py search "쿼리" -k 5   # 로컬 top-k 검증
    python obsidian_indexer.py stats               # 인덱스 요약
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
VAULT_ROOT = Path(os.environ.get("OBSIDIAN_VAULT", ROOT / "ObsidianVault"))
INDEX_DIR = Path(os.environ.get("OBSIDIAN_INDEX_DIR", ROOT / "data" / "obsidian-index"))
RECORDS_FILE = INDEX_DIR / "records.jsonl"
MANIFEST_FILE = INDEX_DIR / "manifest.json"

SCHEMA_VERSION = 1
SNIPPET_MAX_CHARS = 500

# 제외 폴더 = vault_rag.EXCLUDE_DIRS ∪ sync_vault_to_gbrain.SKIP_DIRS (09_Archive=보존 선반)
EXCLUDE_DIRS = {
    ".obsidian", ".trash", ".claude", ".rag", ".git",
    "node_modules", "__pycache__", "09_Archive",
}

# Taxonomy Standard "Required Catalog Fields" 중 스칼라 카탈로그 필드
SCALAR_FIELDS = ("type", "status", "domain", "asset_type", "growth_stage", "source", "confidence")
# 리스트 카탈로그 필드
LIST_FIELDS = ("keywords", "tags")

# tier 정의(sync_vault_to_gbrain와 동일 규약)
TIER_PREFIXES = {
    1: ["06_Context_Packs", "00_System"],
    2: ["03_Knowledge", "03_Projects", "10_AgentBus", "graphify-out"],
}

# 검색 스코어링 가중치(scripts/obsidian_index_schema.md 계약)
SEARCH_WEIGHTS = {"keywords": 5, "title": 4, "headings": 3, "meta": 2, "snippet": 1}


# ── 파싱 헬퍼 ──────────────────────────────────────────────────────────────────

_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)
_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def slug_for(path: Path) -> str:
    """파일 경로 → 안정 슬러그(소문자 불필요, 경로 유지). sync_vault_to_gbrain 규약."""
    rel = path.relative_to(VAULT_ROOT)
    raw = str(rel).replace("\\", "/")
    if raw.endswith(".md"):
        raw = raw[:-3]
    slug = re.sub(r"[^a-zA-Z0-9가-힣/_.-]", "-", raw)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug


def read_text_safe(path: Path) -> str:
    # utf-8-sig 우선 — Windows/Obsidian 생성 md의 선두 BOM을 제거해야 frontmatter가 파싱된다.
    for enc in ("utf-8-sig", "utf-8", "cp949", "latin-1"):
        try:
            return path.read_text(encoding=enc, errors="replace").lstrip("﻿")
        except OSError:
            continue
    return ""


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """선두 YAML frontmatter를 stdlib만으로 파싱한다(스칼라·인라인리스트·블록리스트).
    반환: (frontmatter dict, frontmatter 제거된 본문)."""
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    fm_text = m.group(1)
    body = text[m.end():]

    data: dict = {}
    key = None
    for raw_line in fm_text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        # 블록 리스트 항목: "  - value"
        block = re.match(r"^\s+-\s+(.*)$", line)
        if block and key is not None:
            data.setdefault(key, [])
            if isinstance(data[key], list):
                data[key].append(_clean_scalar(block.group(1)))
            continue
        # "key: value" 또는 "key:"
        kv = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not kv:
            continue
        key = kv.group(1).strip()
        val = kv.group(2).strip()
        if val == "":
            data[key] = []  # 다음 줄이 블록 리스트일 수 있음(아니면 빈 리스트로 남음)
        elif val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            data[key] = [_clean_scalar(x) for x in inner.split(",") if x.strip()] if inner else []
        else:
            data[key] = _clean_scalar(val)
    return data, body


def _clean_scalar(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        v = v[1:-1]
    return v.strip()


def extract_title(body: str, fallback: str) -> str:
    for line in body.splitlines():
        h = re.match(r"^#\s+(.+?)\s*$", line)
        if h:
            return h.group(1).strip()
    return fallback


def extract_headings(body: str) -> list[str]:
    return [g[1].strip() for g in _HEADING_RE.findall(body)]


def extract_wikilinks(text: str) -> list[str]:
    """파일 전체에서 [[대상]] 추출(별칭·앵커 제거, 중복 제거·순서 유지)."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in _WIKILINK_RE.findall(text):
        name = raw.split("|")[0].split("#")[0].strip()
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def build_snippet(title: str, body: str) -> str:
    """제목 + 본문 첫 줄들(헤딩 마커 제거) → SNIPPET_MAX_CHARS 이내."""
    lines: list[str] = []
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        s = re.sub(r"^#{1,6}\s+", "", s)  # 헤딩 마커 제거
        s = re.sub(r"^>\s?", "", s)        # 인용 마커 제거
        if s:
            lines.append(s)
        if sum(len(x) for x in lines) > SNIPPET_MAX_CHARS:
            break
    joined = " ".join(lines)
    snippet = f"{title} — {joined}" if joined else title
    return snippet[:SNIPPET_MAX_CHARS].strip()


def _as_list(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    return [str(v)] if str(v).strip() else []


# ── 레코드 빌드 ────────────────────────────────────────────────────────────────

def build_record(path: Path) -> dict:
    text = read_text_safe(path)
    fm, body = parse_frontmatter(text)
    rel = path.relative_to(VAULT_ROOT)
    title = extract_title(body, path.stem)

    rec: dict = {
        "slug": slug_for(path),
        "path": rel.as_posix(),
        "folder": rel.parts[0] if len(rel.parts) > 1 else "",
        "title": title,
    }
    for f in SCALAR_FIELDS:
        v = fm.get(f)
        rec[f] = _clean_scalar(str(v)) if isinstance(v, str) else (v if v not in ("", []) else None)
    for f in LIST_FIELDS:
        rec[f] = _as_list(fm.get(f))
    rec["wikilinks"] = extract_wikilinks(text)
    rec["headings"] = extract_headings(body)
    rec["snippet"] = build_snippet(title, body)
    try:
        st = path.stat()
        rec["mtime"] = int(st.st_mtime)
        rec["size"] = st.st_size
    except OSError:
        rec["mtime"] = 0
        rec["size"] = 0
    rec["hash"] = hashlib.md5(text.encode("utf-8", errors="replace")).hexdigest()
    return rec


# ── 파일 스캔 ──────────────────────────────────────────────────────────────────

def scan_vault(tier: str | None = None) -> list[Path]:
    files: list[Path] = []
    for md in VAULT_ROOT.rglob("*.md"):
        parts = set(md.relative_to(VAULT_ROOT).parts)
        if parts & EXCLUDE_DIRS:
            continue
        files.append(md)
    files.sort()
    if not tier or tier == "all":
        return files

    tier_num = int(tier)
    if tier_num in (1, 2):
        prefixes = TIER_PREFIXES[tier_num]
        return [f for f in files if f.relative_to(VAULT_ROOT).parts[0] in prefixes]
    # tier 3 = 나머지
    known = set(TIER_PREFIXES[1]) | set(TIER_PREFIXES[2])
    return [f for f in files if f.relative_to(VAULT_ROOT).parts[0] not in known]


# ── 인덱스 저장/로드 ───────────────────────────────────────────────────────────

def load_records() -> dict[str, dict]:
    """slug → record. 없으면 빈 dict."""
    out: dict[str, dict] = {}
    if RECORDS_FILE.exists():
        for line in RECORDS_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                out[r["slug"]] = r
            except (json.JSONDecodeError, KeyError):
                continue
    return out


def load_manifest() -> dict:
    if MANIFEST_FILE.exists():
        try:
            return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_index(records: dict[str, dict]) -> dict:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    ordered = sorted(records.values(), key=lambda r: r["path"])

    # records.jsonl 원자적 저장
    tmp = str(RECORDS_FILE) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in ordered:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, str(RECORDS_FILE))

    folders: dict[str, int] = {}
    types: dict[str, int] = {}
    for r in ordered:
        folders[r["folder"]] = folders.get(r["folder"], 0) + 1
        if r.get("type"):
            types[r["type"]] = types.get(r["type"], 0) + 1

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "vault": str(VAULT_ROOT),
        "count": len(ordered),
        "folders": dict(sorted(folders.items())),
        "types": dict(sorted(types.items(), key=lambda x: -x[1])),
        "hashes": {r["slug"]: r["hash"] for r in ordered},
    }
    tmp_m = str(MANIFEST_FILE) + ".tmp"
    Path(tmp_m).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_m, str(MANIFEST_FILE))
    return manifest


# ── index 명령 ─────────────────────────────────────────────────────────────────

def cmd_index(tier: str | None, force: bool) -> None:
    prev = {} if force else load_records()
    prev_hashes = load_manifest().get("hashes", {}) if not force else {}

    files = scan_vault(tier)
    print(f"[스캔] {VAULT_ROOT} → {len(files)}개 .md (tier={tier or 'all'}, force={force})")

    records: dict[str, dict] = {}
    new_cnt = upd_cnt = skip_cnt = 0
    for md in files:
        slug = slug_for(md)
        text = read_text_safe(md)
        cur_hash = hashlib.md5(text.encode("utf-8", errors="replace")).hexdigest()
        if not force and prev_hashes.get(slug) == cur_hash and slug in prev:
            records[slug] = prev[slug]  # 변경 없음 → 기존 레코드 재사용
            skip_cnt += 1
            continue
        records[slug] = build_record(md)
        if slug in prev:
            upd_cnt += 1
        else:
            new_cnt += 1

    # tier 부분 인덱싱 시, 이번 스캔 대상 밖의 기존 레코드는 보존(전체 인덱스 유지)
    if tier and tier != "all" and not force:
        scanned_slugs = {slug_for(md) for md in files}
        for slug, rec in prev.items():
            if slug not in scanned_slugs:
                records[slug] = rec

    manifest = save_index(records)
    print(f"[완료] 신규 {new_cnt} · 갱신 {upd_cnt} · 무변경 {skip_cnt} → 총 {manifest['count']}건")
    print(f"[산출] {RECORDS_FILE}")
    print(f"[산출] {MANIFEST_FILE}")


# ── search 명령 ────────────────────────────────────────────────────────────────

def score_record(rec: dict, tokens: list[str]) -> int:
    tiers = {
        "keywords": " ".join(rec.get("keywords", [])).lower(),
        "title": (rec.get("title") or "").lower(),
        "headings": " ".join(rec.get("headings", [])).lower(),
        "meta": " ".join(
            rec.get("tags", [])
            + [str(rec.get("type") or ""), str(rec.get("domain") or "")]
        ).lower(),
        "snippet": (rec.get("snippet") or "").lower(),
    }
    score = 0
    for tok in tokens:
        for tier, text in tiers.items():
            if tok in text:
                score += SEARCH_WEIGHTS[tier]
    return score


def cmd_search(query: str, top_k: int) -> None:
    records = load_records()
    if not records:
        print("[오류] 인덱스가 비어 있음 — 먼저 `index`를 실행하세요.", file=sys.stderr)
        sys.exit(1)
    tokens = [t for t in re.split(r"\s+", query.lower()) if t]
    scored = [(score_record(r, tokens), r) for r in records.values()]
    scored = [(s, r) for s, r in scored if s > 0]
    scored.sort(key=lambda x: (-x[0], x[1]["path"]))

    hits = scored[:top_k]
    print(f"[검색] \"{query}\" → {len(scored)}건 매칭, 상위 {len(hits)}건\n")
    for rank, (s, r) in enumerate(hits, 1):
        print(f"{rank}. [{s:>2}] {r['title']}  ({r['folder']})")
        print(f"     {r['path']}")
        if r.get("keywords"):
            print(f"     keywords: {', '.join(r['keywords'][:8])}")
        print(f"     {r['snippet'][:120]}")
        print()


def cmd_stats() -> None:
    m = load_manifest()
    if not m:
        print("[오류] manifest 없음 — 먼저 `index`를 실행하세요.", file=sys.stderr)
        sys.exit(1)
    print(f"스키마 v{m['schema_version']} · 생성 {m['generated_at']} · 총 {m['count']}건")
    print(f"Vault: {m['vault']}")
    print("\n[폴더별]")
    for folder, n in m.get("folders", {}).items():
        print(f"  {folder:<24} {n}")
    print("\n[타입별 top]")
    for t, n in list(m.get("types", {}).items())[:12]:
        print(f"  {t:<28} {n}")


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Obsidian 경량 인덱서 (obsidian-index B2)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_idx = sub.add_parser("index", help="증분 인덱싱")
    p_idx.add_argument("--force", action="store_true", help="전체 재인덱싱")
    p_idx.add_argument("--tier", default=None, help="1|2|3|all (sync 규약)")

    p_srch = sub.add_parser("search", help="로컬 top-k 검증")
    p_srch.add_argument("query")
    p_srch.add_argument("-k", "--top-k", type=int, default=5)

    sub.add_parser("stats", help="인덱스 요약")

    args = ap.parse_args()
    if args.cmd == "index":
        cmd_index(args.tier, args.force)
    elif args.cmd == "search":
        cmd_search(args.query, args.top_k)
    elif args.cmd == "stats":
        cmd_stats()


if __name__ == "__main__":
    main()
