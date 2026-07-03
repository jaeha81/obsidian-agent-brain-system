#!/usr/bin/env python3
"""
infranodus_sync.py — 03_Knowledge → InfraNodus 그래프 동기화

03_Knowledge 전체 노트를 텍스트로 조합하여 InfraNodus에 업로드하고,
분석 결과(topical clusters, content gaps, modality score)를
graphify-out/INFRANODUS_REPORT.md 에 저장.

InfraNodus는 Claude Code 세션에서 MCP 도구로 연결되어 있으나,
이 스크립트는 MCP 없이 REST API로도 동작 가능 (INFRANODUS_API_KEY 환경변수 필요).

사용법:
  python scripts/infranodus_sync.py              # 전체 동기화
  python scripts/infranodus_sync.py --delta      # 마지막 실행 이후 변경 파일만
  python scripts/infranodus_sync.py --dry-run    # 업로드 없이 텍스트만 준비
  python scripts/infranodus_sync.py --cluster <name>  # 특정 graph_cluster만
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).parent.parent
VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))
KNOWLEDGE_DIR = VAULT / "03_Knowledge"
GRAPHIFY_DIR = VAULT / "graphify-out"
STATE_FILE = _ROOT / "data" / "infranodus_sync_state.json"

INFRANODUS_API_KEY = os.getenv("INFRANODUS_API_KEY", "")
INFRANODUS_GRAPH_NAME = os.getenv("INFRANODUS_GRAPH_NAME", "oabs-knowledge")


# ──────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────

def _parse_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    try:
        import yaml
        return yaml.safe_load(text[3:end]) or {}
    except Exception:
        return {}


def _load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


# ──────────────────────────────────────────
# 텍스트 준비
# ──────────────────────────────────────────

def collect_notes(cluster_filter: Optional[str] = None, delta_since: float = 0.0) -> list[dict]:
    """03_Knowledge 노트 수집. cluster_filter 또는 delta(수정 시각) 적용."""
    notes = []
    for path in KNOWLEDGE_DIR.rglob("*.md"):
        if delta_since and path.stat().st_mtime <= delta_since:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        fm = _parse_frontmatter(text)
        cluster = str(fm.get("graph_cluster", "unclassified")).strip()
        if cluster_filter and cluster != cluster_filter:
            continue
        # frontmatter 제거 후 본문만
        body = re.sub(r"^---[\s\S]*?---\n?", "", text, count=1).strip()
        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        notes.append({
            "path": str(path.relative_to(KNOWLEDGE_DIR)),
            "title": fm.get("title", path.stem),
            "cluster": cluster,
            "tags": tags,
            "body": body,
        })
    return notes


def build_corpus(notes: list[dict]) -> str:
    """노트 목록을 InfraNodus 입력 텍스트로 변환."""
    parts = []
    for note in notes:
        # 제목 + 태그 + 본문 (최대 500자)
        tag_str = " ".join(note["tags"][:5])
        snippet = note["body"][:500].replace("\n", " ")
        parts.append(f"{note['title']} {tag_str} {snippet}")
    return "\n\n".join(parts)


# ──────────────────────────────────────────
# InfraNodus REST API 연동 (MCP 없이 독립 실행 시)
# ──────────────────────────────────────────

def push_to_infranodus_api(text: str, graph_name: str) -> dict:
    """InfraNodus REST API로 그래프 업데이트."""
    if not INFRANODUS_API_KEY:
        raise ValueError("INFRANODUS_API_KEY 환경변수 없음")

    import urllib.request
    import urllib.parse

    url = "https://infranodus.com/api/v1/graphs"
    payload = json.dumps({
        "graphName": graph_name,
        "text": text,
        "language": "ko",
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INFRANODUS_API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"InfraNodus API 오류: {e}")


def get_analysis_from_api(graph_name: str) -> dict:
    """InfraNodus REST API에서 분석 결과 수신."""
    if not INFRANODUS_API_KEY:
        return {"error": "API 키 없음 — MCP 도구로 실행 권장"}

    import urllib.request
    url = f"https://infranodus.com/api/v1/graphs/{urllib.parse.quote(graph_name)}/analysis"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {INFRANODUS_API_KEY}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────
# 리포트 작성
# ──────────────────────────────────────────

def write_report(notes: list[dict], analysis: dict, corpus_len: int):
    GRAPHIFY_DIR.mkdir(parents=True, exist_ok=True)
    report_path = GRAPHIFY_DIR / "INFRANODUS_REPORT.md"
    today = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 클러스터별 통계
    clusters: dict[str, int] = {}
    for note in notes:
        clusters[note["cluster"]] = clusters.get(note["cluster"], 0) + 1

    modality = analysis.get("modality", analysis.get("modularity", "N/A"))
    topics = analysis.get("topics", analysis.get("topicalClusters", []))
    gaps = analysis.get("gaps", analysis.get("contentGaps", []))

    lines = [
        "# InfraNodus Knowledge Graph Report",
        f"> 마지막 동기화: {today}",
        f"> 분석 노트: {len(notes)}개 | 텍스트: {corpus_len:,}자",
        "",
        "## 클러스터별 노트 분포",
        "",
    ]
    for cluster, count in sorted(clusters.items(), key=lambda x: -x[1]):
        bar = "█" * min(count // 2, 30)
        lines.append(f"- **{cluster}**: {count}개 {bar}")
    lines.append("")

    lines += [
        "## Modality Score",
        "",
        f"**{modality}**",
        "",
        "| 점수 | 상태 |",
        "|---|---|",
        "| < 0.3 | 과집중 — 새 도메인 노트 필요 |",
        "| 0.3 ~ 0.6 | 정상 다양성 ✅ |",
        "| > 0.6 | 파편화 — 연결 노트 작성 필요 |",
        "",
    ]

    if topics:
        lines += ["## 주요 토픽 클러스터", ""]
        for i, t in enumerate(topics[:10], 1):
            if isinstance(t, dict):
                lines.append(f"{i}. **{t.get('name', t)}** — {t.get('terms', '')}")
            else:
                lines.append(f"{i}. {t}")
        lines.append("")

    if gaps:
        lines += ["## 컨텐츠 갭 (지식 공백)", ""]
        for g in gaps[:5]:
            if isinstance(g, dict):
                lines.append(f"- {g.get('description', g)}")
            else:
                lines.append(f"- {g}")
        lines.append("")

    if analysis.get("error"):
        lines += [
            "## 분석 오류",
            "",
            f"> {analysis['error']}",
            ">",
            "> **MCP 사용 권장**: Claude Code 세션에서 `mcp__infranodus__generate_knowledge_graph` 직접 호출",
            "",
        ]

    lines += [
        "---",
        "",
        f"*생성: {today} by infranodus_sync.py*",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[infranodus_sync] 리포트 저장: {report_path}")
    return report_path


# ──────────────────────────────────────────
# 메인
# ──────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="03_Knowledge → InfraNodus 그래프 동기화")
    parser.add_argument("--delta", action="store_true", help="마지막 실행 이후 변경 파일만")
    parser.add_argument("--dry-run", action="store_true", help="업로드 없이 텍스트만 준비")
    parser.add_argument("--cluster", type=str, help="특정 graph_cluster만 동기화")
    args = parser.parse_args()

    state = _load_state()
    delta_since = float(state.get("last_run", 0)) if args.delta else 0.0

    print(f"[infranodus_sync] {'delta' if args.delta else '전체'} 동기화 시작...")
    notes = collect_notes(cluster_filter=args.cluster, delta_since=delta_since)
    print(f"[infranodus_sync] {len(notes)}개 노트 수집")

    if not notes:
        print("[infranodus_sync] 동기화할 노트 없음")
        return

    corpus = build_corpus(notes)
    print(f"[infranodus_sync] 텍스트 {len(corpus):,}자 준비")

    analysis = {}

    if args.dry_run:
        print(f"[infranodus_sync] --dry-run: 업로드 생략")
        print(f"[infranodus_sync] 샘플 텍스트 (첫 200자):\n  {corpus[:200]}...")
        analysis = {"error": "dry-run — 실제 분석 없음"}
    elif INFRANODUS_API_KEY:
        print(f"[infranodus_sync] InfraNodus API 업로드 중...")
        try:
            push_to_infranodus_api(corpus, INFRANODUS_GRAPH_NAME)
            print(f"[infranodus_sync] 업로드 완료. 분석 수신 중...")
            time.sleep(3)
            analysis = get_analysis_from_api(INFRANODUS_GRAPH_NAME)
        except Exception as e:
            print(f"[infranodus_sync] API 오류: {e}", file=sys.stderr)
            analysis = {"error": str(e)}
    else:
        print("[infranodus_sync] INFRANODUS_API_KEY 없음 — MCP 도구 사용 권장")
        print("  Claude Code 세션에서: mcp__infranodus__generate_knowledge_graph 직접 호출")
        analysis = {
            "error": "INFRANODUS_API_KEY 없음",
            "note": "Claude Code 세션에서 InfraNodus MCP 도구를 직접 사용하거나, INFRANODUS_API_KEY를 .env에 설정하세요",
        }

    report_path = write_report(notes, analysis, len(corpus))

    # 상태 저장
    _save_state({
        "last_run": time.time(),
        "last_run_date": datetime.now().isoformat(),
        "notes_synced": len(notes),
        "graph_name": INFRANODUS_GRAPH_NAME,
        "report": str(report_path),
    })

    print(f"[infranodus_sync] 완료")


if __name__ == "__main__":
    main()
