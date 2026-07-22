#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_dashboard_graph.py — 대시보드 "Vault" 탭용 지식 그래프 JSON 생성

큐레이트 지식 폴더의 노트 간 [[위키링크]]를 파싱해 폰에서 렌더 가능한
압축 그래프를 만든다. 산출물 스키마는 project-graph.html의 GRAPHS.vault와
동일: {title, color, groups, nodes:[{id,label,group,size,desc}], links:[{s,t}]}

출력: docs/data/knowledge_graph.json
데이터 원천 = 파일 기반 옵시디언 노트 (gbrain 라이브 MCP 미사용).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "ObsidianVault"
OUT = ROOT / "docs" / "data" / "knowledge_graph.json"

# 큐레이트 지식 범위 (사용자 승인: "큐레이트 지식 중심")
FOLDERS = {
    "03_Knowledge":         {"label": "정제 지식 (SoT)", "color": "#ffd93d"},
    "04_Wiki":              {"label": "Wiki",            "color": "#4ecdc4"},
    "05_Frameworks":        {"label": "Frameworks",      "color": "#43e97b"},
    "06_Context_Packs":     {"label": "Context Packs",   "color": "#6c63ff"},
    "09_Knowledge_Capture": {"label": "Knowledge Capture", "color": "#4facfe"},
    "00_System":            {"label": "System",          "color": "#ff8c42"},
}

WIKILINK = re.compile(r"!?\[\[([^\]]+)\]\]")
IMG_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf")


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:]
    return text


def first_desc(text: str) -> str:
    """프론트매터/헤딩을 걷어내고 첫 의미 있는 문장 한 줄을 desc로."""
    body = strip_frontmatter(text)
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(("#", ">", "-", "*", "|", "```", "!", "[")):
            continue
        line = re.sub(r"[*_`]", "", line)          # 마크다운 강조 제거
        line = re.sub(r"\[\[([^\]|]+)(\|[^\]]+)?\]\]", r"\1", line)  # 위키링크 텍스트화
        line = line.strip()
        if len(line) >= 4:
            return line[:140]
    return ""


def link_target_basename(raw: str) -> str:
    """[[folder/name|alias#heading]] → name"""
    t = raw.split("|", 1)[0].split("#", 1)[0].strip()
    t = t.replace("\\", "/").split("/")[-1]
    if t.lower().endswith(".md"):
        t = t[:-3]
    return t.strip()


def main() -> None:
    nodes = []
    id_by_path = {}          # posix rel path → node id (id == rel path, 유일 보장)
    id_by_basename = {}      # basename(소문자) → node id (위키링크 해석용, 첫 등장 우선)
    raw_texts = {}           # node id → 본문 (링크 파싱용)

    for folder, meta in FOLDERS.items():
        base = VAULT / folder
        if not base.exists():
            continue
        for md in sorted(base.rglob("*.md")):
            rel = md.relative_to(VAULT).as_posix()
            nid = rel                      # 경로 자체를 id로 (유일)
            label = md.stem
            try:
                text = md.read_text(encoding="utf-8", errors="replace")
            except Exception:
                text = ""
            nodes.append({
                "id": nid,
                "label": label,
                "group": folder,
                "size": 8,                 # 링크 계산 후 갱신
                "desc": first_desc(text) or label,
            })
            id_by_path[rel] = nid
            raw_texts[nid] = text
            key = label.lower()
            if key not in id_by_basename:  # 동명 노트는 첫 등장으로 해석
                id_by_basename[key] = nid

    # 링크 파싱 (양끝이 모두 범위 내 노드일 때만)
    links = []
    seen = set()
    degree = {n["id"]: 0 for n in nodes}
    for nid, text in raw_texts.items():
        for m in WIKILINK.finditer(text):
            tgt = link_target_basename(m.group(1))
            if not tgt or tgt.lower().endswith(IMG_EXT):
                continue
            tid = id_by_basename.get(tgt.lower())
            if not tid or tid == nid:
                continue
            pair = (nid, tid)
            if pair in seen:
                continue
            seen.add(pair)
            links.append({"s": nid, "t": tid})
            degree[nid] += 1
            degree[tid] += 1

    # 링크 차수로 노드 크기 조절 (허브가 크게, 6~22 범위)
    for n in nodes:
        n["size"] = max(6, min(22, 6 + degree[n["id"]] * 2))

    groups = {folder: {"label": meta["label"], "color": meta["color"]}
              for folder, meta in FOLDERS.items()}

    out = {
        "title": "Vault (실데이터)",
        "color": "#4facfe",
        "groups": groups,
        "nodes": nodes,
        "links": links,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    connected = sum(1 for n in nodes if degree[n["id"]] > 0)
    print(f"[OK] {OUT}")
    print(f"  nodes={len(nodes)}  links={len(links)}  연결된노드={connected} "
          f"(고립={len(nodes)-connected})")


if __name__ == "__main__":
    main()
