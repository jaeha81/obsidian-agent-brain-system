#!/usr/bin/env python3
"""
Collection Pipeline — Phase 1 자동화 파이프라인
GPT + Claude 세션 수집 → 지식 정제 → 갭 분석 → Discord 알림

Usage:
    python collection_pipeline.py           # 증분 수집 + 정제 + 갭 분석
    python collection_pipeline.py --dry-run # 테스트 (저장 없음)
    python collection_pipeline.py --skip-distill  # 수집만
    python collection_pipeline.py --skip-collect  # 정제+갭만
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
VAULT_BASE = Path("D:/ai프로젝트/obsidian-agent-brain-system/ObsidianVault")
AGENTBUS_DIR = VAULT_BASE / "10_AgentBus"
LOG_FILE = SCRIPTS_DIR / "pipeline.log"


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_script(script: str, args: list[str], dry_run: bool = False) -> tuple[int, str]:
    cmd = [sys.executable, str(SCRIPTS_DIR / script)] + args
    if dry_run and "--dry-run" not in args:
        cmd.append("--dry-run")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", timeout=600
        )
        return result.returncode, (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return -1, "타임아웃 (600s)"
    except Exception as e:
        return -1, str(e)


def notify_agentbus(summary: dict) -> None:
    inbox = AGENTBUS_DIR / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    msg = {
        "type": "pipeline_complete",
        "timestamp": datetime.now().isoformat(),
        "summary": summary,
    }
    out = inbox / f"pipeline_{ts}.json"
    out.write_text(json.dumps(msg, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"AgentBus 알림 저장: {out.name}")


def main():
    parser = argparse.ArgumentParser(description="Brain Evolution Collection Pipeline")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-collect", action="store_true", help="수집 건너뜀")
    parser.add_argument("--skip-distill", action="store_true", help="정제 건너뜀")
    parser.add_argument("--skip-gaps", action="store_true", help="갭 분석 건너뜀")
    parser.add_argument("--distill-limit", type=int, default=20, help="정제 최대 파일 수")
    args = parser.parse_args()

    started_at = datetime.now()
    log(f"=== Collection Pipeline 시작 {'[DRY-RUN]' if args.dry_run else ''} ===")

    results: dict[str, str] = {}

    # ── Phase 1: 수집 ──────────────────────────────────────────────────────────
    if not args.skip_collect:
        log("▶ GPT 세션 수집 중...")
        rc, out = run_script("gpt_session_collector.py", ["--collect"], args.dry_run)
        status = "✅" if rc == 0 else f"❌ (rc={rc})"
        log(f"  GPT 수집 {status}\n  {out[:200]}")
        results["gpt_collect"] = status

        log("▶ Claude 세션 수집 중...")
        rc, out = run_script("claude_session_collector.py", ["--collect"], args.dry_run)
        status = "✅" if rc == 0 else f"❌ (rc={rc})"
        log(f"  Claude 수집 {status}\n  {out[:200]}")
        results["claude_collect"] = status
    else:
        log("⏭ 수집 건너뜀 (--skip-collect)")

    # ── Phase 2: 지식 정제 ────────────────────────────────────────────────────
    if not args.skip_distill:
        log(f"▶ 지식 정제 중 (최대 {args.distill_limit}개)...")
        extra_args = ["--limit", str(args.distill_limit)]
        rc, out = run_script("knowledge_distiller.py", extra_args, args.dry_run)
        status = "✅" if rc == 0 else f"❌ (rc={rc})"
        log(f"  정제 {status}\n  {out[:300]}")
        results["distill"] = status
    else:
        log("⏭ 정제 건너뜀 (--skip-distill)")

    # ── Phase 3: 갭 분석 ──────────────────────────────────────────────────────
    if not args.skip_gaps:
        log("▶ 지식 갭 분석 중...")
        rc, out = run_script("knowledge_gap_analyzer.py", [], dry_run=False)
        status = "✅" if rc == 0 else f"❌ (rc={rc})"
        log(f"  갭 분석 {status}\n  {out[:300]}")
        results["gap_analysis"] = status
    else:
        log("⏭ 갭 분석 건너뜀 (--skip-gaps)")

    # ── 결과 요약 ──────────────────────────────────────────────────────────────
    elapsed = (datetime.now() - started_at).seconds
    summary = {
        "elapsed_sec": elapsed,
        "dry_run": args.dry_run,
        "results": results,
    }
    log(f"=== 파이프라인 완료 ({elapsed}s) ===")
    for k, v in results.items():
        log(f"  {k}: {v}")

    if not args.dry_run:
        notify_agentbus(summary)

    failed = [k for k, v in results.items() if "❌" in v]
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
