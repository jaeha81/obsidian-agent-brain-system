#!/usr/bin/env python3
"""Create functional knowledge bridge notes from raw and operational vault notes."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


SOURCE_DIRS = (
    "01_RAW",
    "10_AgentBus",
    "09_Archive",
    "Inbox",
)
EXCLUDED_SOURCE_PARTS = {
    "claude-sessions",
    "codex-sessions",
}

BRIDGE_DIR = Path("03_Knowledge") / "bridges"
BRIDGE_INDEX_DIR = Path("03_Knowledge") / "bridge-indexes"
HUB_DIR = Path("03_Knowledge") / "hubs"
WIKILINK_RE = re.compile(r"\[\[([^\]|#\n]+)")

HUB_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Bucky", ("bucky", "버키", "orchestrator", "오케스트레이터")),
    ("Graphify", ("graphify", "graph", "그래프", "knowledge graph", "지식 그래프")),
    ("Codex", ("codex", "review", "검수", "리뷰")),
    ("Claude Code", ("claude code", "claude", "implementation", "구현")),
    ("AgentBus", ("agentbus", "agent bus", "inbox", "outbox")),
    ("JH System", ("jh system", "jh", "system", "시스템")),
    ("Obsidian", ("obsidian", "vault", "옵시디언")),
)

HUB_LINKS: dict[str, tuple[str, ...]] = {
    "Bucky": ("JH System", "AgentBus", "Obsidian"),
    "Graphify": ("Bucky", "JH System", "Obsidian"),
    "Codex": ("Bucky", "AgentBus", "Claude Code"),
    "Claude Code": ("Bucky", "AgentBus", "Codex"),
    "AgentBus": ("Bucky", "Codex", "Claude Code"),
    "JH System": ("Bucky", "Graphify", "Obsidian"),
    "Obsidian": ("Bucky", "Graphify", "JH System"),
}


@dataclass(frozen=True)
class BridgeCandidate:
    source_path: Path
    title: str
    hubs: tuple[str, ...]
    excerpt: str


@dataclass(frozen=True)
class BridgeResult:
    candidates: int
    created: int
    skipped_existing: int
    output_dir: Path


def _normalise_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _slug(text: str) -> str:
    slug = re.sub(r"[^\w가-힣-]+", "-", text.lower(), flags=re.UNICODE)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:80] or "bridge"


def _has_wikilink(text: str) -> bool:
    return bool(WIKILINK_RE.search(text))


def _relative_source(path: Path, vault: Path) -> str:
    try:
        return path.relative_to(vault).as_posix()
    except ValueError:
        return path.as_posix()


def _wikilink_path(path: Path, vault: Path) -> str:
    rel = _relative_source(path, vault)
    if rel.lower().endswith(".md"):
        rel = rel[:-3]
    return rel


def classify_hubs(text: str, source_path: Path) -> tuple[str, ...]:
    haystack = f"{source_path.as_posix()} {text}".lower()
    hubs: list[str] = []
    for hub, keywords in HUB_KEYWORDS:
        if any(keyword.lower() in haystack for keyword in keywords):
            hubs.append(hub)

    if "JH System" not in hubs:
        hubs.append("JH System")
    if len(hubs) == 1:
        hubs.append("Obsidian")
    return tuple(dict.fromkeys(hubs))


def iter_source_notes(vault: Path) -> list[Path]:
    notes: list[Path] = []
    for source_dir in SOURCE_DIRS:
        root = vault / source_dir
        if not root.exists():
            continue
        notes.extend(
            p for p in root.rglob("*.md")
            if p.is_file() and not any(part in EXCLUDED_SOURCE_PARTS for part in p.parts)
        )
    return sorted(notes, key=lambda p: p.as_posix().lower())


def build_candidate(path: Path, vault: Path) -> BridgeCandidate | None:
    content = path.read_text(encoding="utf-8", errors="ignore")
    if not _normalise_text(content):
        return None

    # Notes that already participate in the graph can remain in their source layer.
    if _has_wikilink(content):
        return None

    title = path.stem
    hubs = classify_hubs(content, path)
    excerpt = _normalise_text(re.sub(r"---[\s\S]*?---", "", content))[:320]
    return BridgeCandidate(source_path=path, title=title, hubs=hubs, excerpt=excerpt)


def render_bridge(candidate: BridgeCandidate, vault: Path) -> str:
    source_rel = _relative_source(candidate.source_path, vault)
    hub_links = " ".join(f"[[{hub}]]" for hub in candidate.hubs)
    hub_yaml = "\n".join(f"  - \"{hub}\"" for hub in candidate.hubs)
    created = datetime.now().strftime("%Y-%m-%d")
    return f"""---
type: knowledge-bridge
source_path: "{source_rel}"
created: {created}
hubs:
{hub_yaml}
tags:
  - knowledge-bridge
---

# Bridge: {candidate.title}

## Connects

{hub_links}

## Source

`{source_rel}`

## Extract

{candidate.excerpt}

## Function

This bridge keeps raw, operational, or archived material out of the main graph while connecting its reusable knowledge to active system hubs.
"""


def bridge_path(candidate: BridgeCandidate, vault: Path) -> Path:
    source_rel = _relative_source(candidate.source_path, vault)
    return vault / BRIDGE_DIR / f"{_slug(source_rel)}.md"


def _existing_note_stems(vault: Path) -> set[str]:
    return {p.stem.lower() for p in vault.rglob("*.md") if "graphify-out" not in p.parts}


def _all_graph_notes(vault: Path) -> list[Path]:
    excluded = {".obsidian", "graphify-out"}
    return sorted(
        (
            p for p in vault.rglob("*.md")
            if p.is_file() and not any(part in excluded for part in p.parts)
        ),
        key=lambda p: p.as_posix().lower(),
    )


def _resolve_wikilink(link: str, vault: Path, by_stem: dict[str, Path], by_rel: dict[str, Path]) -> Path | None:
    clean = link.strip()
    rel_key = clean.replace("\\", "/").removesuffix(".md").lower()
    if rel_key in by_rel:
        return by_rel[rel_key]
    return by_stem.get(Path(clean).stem.lower())


def find_isolated_notes(vault: Path) -> list[Path]:
    notes = _all_graph_notes(vault)
    by_stem = {p.stem.lower(): p for p in notes}
    by_rel = {_wikilink_path(p, vault).lower(): p for p in notes}
    inbound: dict[Path, int] = {p: 0 for p in notes}
    outbound: dict[Path, int] = {p: 0 for p in notes}

    for note in notes:
        content = note.read_text(encoding="utf-8", errors="ignore")
        for raw_link in WIKILINK_RE.findall(content):
            target = _resolve_wikilink(raw_link, vault, by_stem, by_rel)
            if target is None or target == note:
                continue
            outbound[note] += 1
            inbound[target] += 1

    return [
        p for p in notes
        if inbound[p] == 0
        and outbound[p] == 0
        and BRIDGE_INDEX_DIR.as_posix() not in _relative_source(p, vault)
    ]


def render_hub_note(hub: str) -> str:
    links = " ".join(f"[[{target}]]" for target in HUB_LINKS[hub])
    created = datetime.now().strftime("%Y-%m-%d")
    return f"""---
type: knowledge-hub
created: {created}
tags:
  - knowledge-hub
---

# {hub}

## Connects

{links}

## Function

This hub gives bridge notes a stable, functional graph target for system knowledge.
"""


def ensure_hub_notes(vault: Path, dry_run: bool = False) -> list[Path]:
    vault = vault.resolve()
    existing = _existing_note_stems(vault)
    hub_root = vault / HUB_DIR
    created: list[Path] = []

    for hub in HUB_LINKS:
        if hub.lower() in existing:
            continue
        out = hub_root / f"{hub}.md"
        created.append(out)
        if not dry_run:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(render_hub_note(hub), encoding="utf-8")
    return created


def render_isolated_index(vault: Path, batch: list[Path], batch_no: int) -> str:
    created = datetime.now().strftime("%Y-%m-%d")
    items = []
    for note in batch:
        link_path = _wikilink_path(note, vault)
        items.append(f"- [[{link_path}|{note.stem}]]")
    links = "\n".join(items)
    return f"""---
type: knowledge-bridge-index
created: {created}
tags:
  - knowledge-bridge-index
---

# Knowledge Bridge Index {batch_no:03d}

## Functional Hubs

[[JH System]] [[Obsidian]] [[Bucky]] [[Graphify]]

## Connected Source Notes

{links}

## Function

This index connects previously isolated source notes into the knowledge base without modifying the source files.
"""


def connect_isolated_notes(vault: Path, batch_size: int = 80, dry_run: bool = False) -> dict[str, int]:
    vault = vault.resolve()
    ensure_hub_notes(vault, dry_run=dry_run)
    isolated = find_isolated_notes(vault)
    index_root = vault / BRIDGE_INDEX_DIR
    created = 0
    if not dry_run and isolated:
        index_root.mkdir(parents=True, exist_ok=True)
        for index, start in enumerate(range(0, len(isolated), batch_size), start=1):
            batch = isolated[start:start + batch_size]
            out = index_root / f"knowledge-bridge-index-{index:03d}.md"
            out.write_text(render_isolated_index(vault, batch, index), encoding="utf-8")
            created += 1
    return {"isolated": len(isolated), "created": created}


def build_knowledge_bridges(vault: Path, limit: int = 100, dry_run: bool = False) -> BridgeResult:
    vault = vault.resolve()
    ensure_hub_notes(vault, dry_run=dry_run)
    candidates: list[BridgeCandidate] = []
    for note in iter_source_notes(vault):
        candidate = build_candidate(note, vault)
        if candidate is not None:
            candidates.append(candidate)
        if len(candidates) >= limit:
            break

    output_dir = vault / BRIDGE_DIR
    created = 0
    skipped_existing = 0
    if not dry_run and candidates:
        output_dir.mkdir(parents=True, exist_ok=True)
        for candidate in candidates:
            out = bridge_path(candidate, vault)
            if out.exists():
                skipped_existing += 1
                continue
            out.write_text(render_bridge(candidate, vault), encoding="utf-8")
            created += 1

    return BridgeResult(
        candidates=len(candidates),
        created=created,
        skipped_existing=skipped_existing,
        output_dir=output_dir,
    )


def verify_bridge_notes(vault: Path) -> list[Path]:
    bridge_root = vault / BRIDGE_DIR
    if not bridge_root.exists():
        return []
    failures: list[Path] = []
    for note in sorted(bridge_root.glob("*.md")):
        content = note.read_text(encoding="utf-8", errors="ignore")
        links = WIKILINK_RE.findall(content)
        if len(set(links)) < 2:
            failures.append(note)
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", default="ObsidianVault", help="Path to ObsidianVault")
    parser.add_argument("--limit", type=int, default=100, help="Maximum bridge notes to create")
    parser.add_argument("--batch-size", type=int, default=80, help="Notes per bridge index")
    parser.add_argument("--dry-run", action="store_true", help="Report candidates without writing files")
    parser.add_argument("--connect-isolated", action="store_true", help="Create bridge indexes for all isolated notes")
    parser.add_argument("--verify", action="store_true", help="Verify existing bridge notes")
    args = parser.parse_args()

    vault = Path(args.vault)
    if args.connect_isolated:
        result = connect_isolated_notes(vault, batch_size=args.batch_size, dry_run=args.dry_run)
        mode = "DRY-RUN" if args.dry_run else "WRITE"
        print(f"{mode}: isolated={result['isolated']}, index_notes_created={result['created']}")
        return 0

    if args.verify:
        failures = verify_bridge_notes(vault)
        if failures:
            print("FAIL: bridge notes without at least two wikilinks")
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("PASS: all bridge notes have at least two wikilinks")
        return 0

    result = build_knowledge_bridges(vault=vault, limit=args.limit, dry_run=args.dry_run)
    mode = "DRY-RUN" if args.dry_run else "WRITE"
    print(
        f"{mode}: candidates={result.candidates}, created={result.created}, "
        f"skipped_existing={result.skipped_existing}, output={result.output_dir}"
    )
    if not args.dry_run:
        failures = verify_bridge_notes(vault)
        if failures:
            print("FAIL: generated bridge verification failed")
            for failure in failures:
                print(f"- {failure}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
