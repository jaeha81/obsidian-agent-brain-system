#!/usr/bin/env python3
"""
sync_vault_to_gbrain.py — Vault .md 파일을 G브레인에 전체 동기화

사용법:
  python -X utf8 scripts/sync_vault_to_gbrain.py [--tier 1|2|3|all]
  python -X utf8 scripts/sync_vault_to_gbrain.py --resume  # 이전 실패분 재시도
  python -X utf8 scripts/sync_vault_to_gbrain.py --dry-run  # 파일 목록만 출력

Tier 정의:
  Tier 1: 06_Context_Packs + 00_System (핵심 운영 지침)
  Tier 2: 03_Knowledge + 03_Projects + 10_AgentBus + graphify-out
  Tier 3: 01_RAW + 02_Processed + 04_Wiki + 05_Frameworks + 07_Reports + 08_Templates + 09_Archive + 나머지
  all:    전체 (기본값)
"""

import os
import sys
import json
import subprocess
import time
import argparse
import re
from pathlib import Path
from datetime import datetime

VAULT_ROOT = Path("D:/ai프로젝트/obsidian-agent-brain-system/ObsidianVault")
LOG_PATH = Path("D:/ai프로젝트/obsidian-agent-brain-system/logs/gbrain_sync.jsonl")
GBRAIN_TOKEN = os.environ.get("GBRAIN_TOKEN", "")

TIER_PREFIXES = {
    1: ["06_Context_Packs", "00_System"],
    2: ["03_Knowledge", "03_Projects", "10_AgentBus", "graphify-out"],
    3: None,  # 나머지 전체
}

# 절대 투입 금지 폴더 (보안 / 노이즈)
SKIP_DIRS = {
    "node_modules", ".git", ".obsidian", "__pycache__",
    "09_Archive/legacy-import",  # 레거시 원문 — 노이즈
}


def slug_for(path: Path) -> str:
    """파일 경로 → G브레인 슬러그 (소문자, 알파뉴메릭+하이픈)"""
    rel = path.relative_to(VAULT_ROOT)
    raw = str(rel).replace("\\", "/").replace(".md", "")
    # 한글, 특수문자 → 하이픈으로 치환, 연속 하이픈 정리
    slug = re.sub(r"[^a-zA-Z0-9가-힣/_.-]", "-", raw)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug


def collect_files(tier: str) -> list[Path]:
    """tier에 따라 처리할 .md 파일 목록 반환"""
    all_files: list[Path] = []

    for md in VAULT_ROOT.rglob("*.md"):
        # 스킵 조건 검사
        rel = md.relative_to(VAULT_ROOT).as_posix()
        skip = False
        for sd in SKIP_DIRS:
            if rel.startswith(sd) or f"/{sd}" in rel:
                skip = True
                break
        if skip:
            continue

        all_files.append(md)

    if tier == "all":
        return sorted(all_files)

    tier_num = int(tier)
    if tier_num == 1:
        prefixes = TIER_PREFIXES[1]
        return sorted(f for f in all_files
                      if any(f.relative_to(VAULT_ROOT).parts[0] == p for p in prefixes))
    elif tier_num == 2:
        prefixes = TIER_PREFIXES[2]
        return sorted(f for f in all_files
                      if any(f.relative_to(VAULT_ROOT).parts[0] == p for p in prefixes))
    else:  # tier 3 = 나머지
        t1 = set(TIER_PREFIXES[1])
        t2 = set(TIER_PREFIXES[2])
        return sorted(f for f in all_files
                      if f.relative_to(VAULT_ROOT).parts[0] not in (t1 | t2))


def load_done_slugs() -> set[str]:
    """로그에서 이미 완료된 슬러그 목록 로드"""
    done = set()
    if not LOG_PATH.exists():
        return done
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
                if rec.get("status") == "ok":
                    done.add(rec["slug"])
            except Exception:
                pass
    return done


def write_log(rec: dict):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def capture_file(md_path: Path, slug: str) -> tuple[bool, str]:
    """G브레인 HTTP API(put_page)로 파일 업로드.
    서버가 PGLite를 점유 중이라 CLI 직접 접근이 불가하므로 HTTP API를 사용한다.
    Windows 파이프 버퍼 제한(~45KB) 우회를 위해 청크 없이 전체 전송.
    """
    import urllib.request
    import urllib.error

    try:
        content = md_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return False, f"read error: {e}"

    # put_page JSON-RPC 요청
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "put_page",
            "arguments": {
                "slug": slug,
                "content": content,
            },
        },
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:8787/mcp",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GBRAIN_TOKEN}",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            # SSE or plain JSON
            for line in raw.splitlines():
                if line.startswith("data: "):
                    try:
                        obj = json.loads(line[6:])
                        if "error" in obj:
                            return False, str(obj["error"])
                        return True, "ok"
                    except Exception:
                        pass
            # plain JSON
            try:
                obj = json.loads(raw)
                if "error" in obj:
                    return False, str(obj["error"])
                return True, "ok"
            except Exception:
                return True, "ok (no json)"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")[:200]
        return False, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", default="all", choices=["1", "2", "3", "all"])
    parser.add_argument("--resume", action="store_true", help="이전 완료분 스킵 (resume)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="최대 처리 파일 수 (0=무제한)")
    parser.add_argument("--workers", type=int, default=4, help="병렬 업로드 워커 수 (기본=4)")
    args = parser.parse_args()

    files = collect_files(args.tier)
    total = len(files)
    print(f"[sync] 대상 파일: {total}개  (tier={args.tier}, workers={args.workers})")

    if args.dry_run:
        for f in files[:20]:
            print(f"  {slug_for(f)}")
        if total > 20:
            print(f"  ... 외 {total - 20}개")
        return

    done_slugs = load_done_slugs() if args.resume else set()
    if done_slugs:
        print(f"[sync] resume 모드: {len(done_slugs)}개 이미 완료, 스킵")

    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    log_lock = threading.Lock()
    counters = {"ok": 0, "fail": 0, "skip": 0, "processed": 0}
    counter_lock = threading.Lock()
    start = time.time()

    # 로그 파일 thread-safe 쓰기
    def write_log_safe(rec: dict):
        with log_lock:
            write_log(rec)

    def process_file(args_tuple):
        idx, md = args_tuple
        slug = slug_for(md)
        if slug in done_slugs:
            with counter_lock:
                counters["skip"] += 1
                counters["processed"] += 1
            return idx, None, None, None  # skipped
        ok, msg = capture_file(md, slug)
        rec = {
            "ts": datetime.now().isoformat(),
            "slug": slug,
            "file": str(md.relative_to(VAULT_ROOT)),
            "status": "ok" if ok else "fail",
            "msg": msg[:200] if msg else "",
        }
        write_log_safe(rec)
        with counter_lock:
            if ok:
                counters["ok"] += 1
            else:
                counters["fail"] += 1
            counters["processed"] += 1
        return idx, slug, ok, msg

    file_list = [(i, md) for i, md in enumerate(files, 1)
                 if not args.limit or i <= args.limit]

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_file, item): item for item in file_list}
        for future in as_completed(futures):
            idx, slug, ok, msg = future.result()
            if slug is None:
                continue  # skipped
            elapsed = time.time() - start
            processed = counters["ok"] + counters["fail"]
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (total - counters["processed"]) / rate if rate > 0 else 0
            status_icon = "✅" if ok else "❌"
            print(
                f"[{idx:4d}/{total}] {status_icon} {slug[:55]:<55} "
                f"| ok={counters['ok']} fail={counters['fail']} "
                f"| {rate:.1f}/s ETA={eta/60:.1f}m",
                flush=True,
            )

    elapsed = time.time() - start
    print(f"\n[sync 완료] ok={counters['ok']} fail={counters['fail']} skip={counters['skip']} "
          f"| 총 {elapsed:.0f}초 ({elapsed/60:.1f}분)")
    print(f"[log] {LOG_PATH}")




if __name__ == "__main__":
    main()
