#!/usr/bin/env python3
"""
Bucky Wishket Agent — 오케스트레이터

스크래핑 → 제안서 생성 → Discord 보고 → 수익 트래킹 파이프라인.
Discord 슬래시 명령어 `/wishket` 또는 단독 실행 모두 지원.
"""

import json
import os
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).parent.parent
TRACKER_FILE = _ROOT / "ObsidianVault" / "10_AgentBus" / "wishket_tracker.json"


def load_tracker() -> dict:
    if TRACKER_FILE.exists():
        try:
            return json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"bids": [], "stats": {"total_bids": 0, "won": 0, "revenue_wan": 0}}


def save_tracker(data: dict) -> None:
    TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def record_bid(project: dict, proposal_file: str) -> None:
    tracker = load_tracker()
    tracker["bids"].append(
        {
            "title": project.get("title", ""),
            "link": project.get("link", ""),
            "budget": project.get("budget", "미정"),
            "budget_wan": project.get("budget_wan", 0),
            "proposal_file": proposal_file,
            "status": "submitted",
            "bid_at": datetime.now().isoformat(),
            "won_at": None,
            "revenue_wan": 0,
        }
    )
    tracker["stats"]["total_bids"] += 1
    save_tracker(tracker)


def get_stats() -> dict:
    tracker = load_tracker()
    stats = tracker["stats"].copy()
    stats["total_bids"] = len(tracker["bids"])
    stats["won"] = sum(1 for b in tracker["bids"] if b.get("status") == "won")
    stats["revenue_wan"] = sum(b.get("revenue_wan", 0) for b in tracker["bids"])
    stats["pending"] = sum(1 for b in tracker["bids"] if b.get("status") == "submitted")
    return stats


def format_stats_message(stats: dict) -> str:
    win_rate = (stats["won"] / stats["total_bids"] * 100) if stats["total_bids"] else 0
    return (
        f"**Wishket 수익 현황**\n"
        f"총 응찰: {stats['total_bids']}건 | "
        f"낙찰: {stats['won']}건 ({win_rate:.0f}%) | "
        f"대기: {stats['pending']}건\n"
        f"누적 수익: **{stats['revenue_wan']:,}만원**"
    )


def run_full_pipeline(max_pages: int = 2) -> dict:
    """스크래핑 → 제안서 생성 → 트래커 기록."""
    from wishket_scraper import run as scrape
    from wishket_proposal_generator import run as generate

    print("[WishketAgent] 파이프라인 시작")

    # 1. 스크래핑
    projects, json_path = scrape()
    if not projects:
        return {"status": "no_projects", "count": 0, "proposals": []}

    # 2. 제안서 생성
    results = generate(projects)

    # 3. 트래커 기록
    for r in results:
        record_bid(r["project"], r["file"])

    stats = get_stats()
    summary = {
        "status": "ok",
        "count": len(results),
        "proposals": [
            {
                "title": r["project"]["title"],
                "budget": r["project"]["budget"],
                "file": r["file"],
                "preview": r["proposal"][:200] + "..." if len(r["proposal"]) > 200 else r["proposal"],
            }
            for r in results
        ],
        "stats": stats,
    }

    print(f"[WishketAgent] 완료 — {len(results)}개 제안서 생성")
    return summary


def mark_won(project_title: str, revenue_wan: int) -> bool:
    """낙찰 처리 — Discord /wishket_won 명령어에서 호출."""
    tracker = load_tracker()
    for bid in tracker["bids"]:
        if project_title.lower() in bid["title"].lower() and bid["status"] == "submitted":
            bid["status"] = "won"
            bid["won_at"] = datetime.now().isoformat()
            bid["revenue_wan"] = revenue_wan
            tracker["stats"]["revenue_wan"] = tracker["stats"].get("revenue_wan", 0) + revenue_wan
            save_tracker(tracker)
            print(f"[WishketAgent] 낙찰 기록: {bid['title']} — {revenue_wan}만원")
            return True
    return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        stats = get_stats()
        print(format_stats_message(stats))
    elif len(sys.argv) > 1 and sys.argv[1] == "won":
        title = sys.argv[2] if len(sys.argv) > 2 else ""
        revenue = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        ok = mark_won(title, revenue)
        print("낙찰 기록 완료" if ok else "해당 공고 없음")
    else:
        result = run_full_pipeline()
        print(f"\n결과: {result['count']}개 제안서 생성")
        print(format_stats_message(result.get("stats", {})))
