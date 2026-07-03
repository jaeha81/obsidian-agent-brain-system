#!/usr/bin/env python3
"""
MCP server exposing legalize-kr as Claude tools.

Tools:
  search_laws(query)          — grep legalize-kr/kr/**/*.md, top-10 matches
  read_law_article(law, art)  — read specific article file, max 1500 chars
  build_legal_context_pack(topic, laws, output) — run legalize_context_pack.py
  list_recent([limit])        — list recently modified law directories

Run:
  python scripts/legalize_mcp_server.py

Requires: pip install mcp
"""

import subprocess
import sys
from pathlib import Path

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool
except ImportError:
    print("ERROR: mcp package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).parent.parent
DATA_ROOT = ROOT / "external_data" / "legalize-kr" / "kr"
ALLOWED_OUTPUT_ROOT = ROOT / "ObsidianVault" / "06_Context_Packs"


def _safe_resolve(candidate: Path, allowed_root: Path) -> Path | None:
    """Return resolved path if within allowed_root, else None."""
    try:
        resolved = candidate.resolve()
        if resolved.is_relative_to(allowed_root.resolve()):
            return resolved
    except (OSError, ValueError):
        pass
    return None


server = Server("legalize-kr")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_laws",
            description="Search legalize-kr law files by keyword. Returns top-10 matching files with excerpts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword (Korean or English)"}
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="read_law_article",
            description="Read a specific law article file. Returns frontmatter + body (max 1500 chars).",
            inputSchema={
                "type": "object",
                "properties": {
                    "law_name": {"type": "string", "description": "Law directory name (e.g. '주택법')"},
                    "article_id": {"type": "string", "description": "Article filename stem (e.g. '제1조') or partial match"},
                },
                "required": ["law_name"],
            },
        ),
        Tool(
            name="build_legal_context_pack",
            description="Generate a Legal Context Pack markdown file using legalize_context_pack.py.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Topic name for the pack (used in filename)"},
                    "laws": {"type": "string", "description": "Comma-separated law names (e.g. '주택법,건축법')"},
                    "output": {"type": "string", "description": "Output .md file path relative to project root (must be within ObsidianVault/06_Context_Packs/)"},
                },
                "required": ["topic", "laws", "output"],
            },
        ),
        Tool(
            name="list_recent",
            description="List recently modified law directories in legalize-kr.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max number of results (default 10)"},
                },
                "required": [],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "search_laws":
        return _search_laws(arguments["query"])
    elif name == "read_law_article":
        return _read_law_article(arguments["law_name"], arguments.get("article_id", ""))
    elif name == "build_legal_context_pack":
        return _build_context_pack(
            arguments["topic"], arguments["laws"], arguments["output"]
        )
    elif name == "list_recent":
        return _list_recent(arguments.get("limit", 10))
    return [TextContent(type="text", text=f"Unknown tool: {name}")]


def _search_laws(query: str) -> list[TextContent]:
    if not DATA_ROOT.exists():
        return [TextContent(type="text", text=f"ERROR: {DATA_ROOT} not found. Run scripts/legalize_sync.sh first.")]

    results = []
    total_chars = 0
    cap = 2000

    for md_file in sorted(DATA_ROOT.rglob("*.md")):
        if total_chars >= cap:
            break
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
            if query in text:
                excerpt_start = text.find(query)
                start = max(0, excerpt_start - 40)
                excerpt = text[start : start + 120].replace("\n", " ")
                rel = md_file.relative_to(DATA_ROOT)
                line = f"[{rel}] ...{excerpt}..."
                results.append(line)
                total_chars += len(line)
        except OSError:
            continue

    if not results:
        return [TextContent(type="text", text=f"No results for: {query}")]

    output = f"Found {len(results)} matches for '{query}':\n\n" + "\n".join(results[:10])
    return [TextContent(type="text", text=output[:cap])]


def _read_law_article(law_name: str, article_id: str) -> list[TextContent]:
    safe = _safe_resolve(DATA_ROOT / law_name, DATA_ROOT)
    law_dir = Path(safe) if safe else None
    if law_dir is None or not law_dir.exists():
        # Partial match — only direct subdirectories of DATA_ROOT
        matches = [d for d in DATA_ROOT.iterdir() if d.is_dir() and law_name in d.name]
        if not matches:
            return [TextContent(type="text", text=f"Law directory not found: {law_name}")]
        law_dir = matches[0]

    if article_id:
        candidates = [f for f in law_dir.glob("*.md") if article_id in f.stem]
    else:
        candidates = sorted(law_dir.glob("*.md"))

    if not candidates:
        all_files = [f.stem for f in law_dir.glob("*.md")][:20]
        return [TextContent(type="text", text=f"No article '{article_id}' in {law_dir.name}. Available: {all_files}")]

    target = candidates[0]
    try:
        text = target.read_text(encoding="utf-8", errors="ignore")
        if len(text) > 1500:
            text = text[:1500] + "\n...(이하 생략)"
        return [TextContent(type="text", text=f"## {target.relative_to(DATA_ROOT)}\n\n{text}")]
    except OSError as e:
        return [TextContent(type="text", text=f"Read error: {e}")]


def _build_context_pack(topic: str, laws: str, output: str) -> list[TextContent]:
    output_candidate = ROOT / output if not Path(output).is_absolute() else Path(output)
    if _safe_resolve(output_candidate, ALLOWED_OUTPUT_ROOT) is None:
        return [TextContent(type="text", text="ERROR: output must be within ObsidianVault/06_Context_Packs/")]
    script = ROOT / "scripts" / "legalize_context_pack.py"
    cmd = [
        sys.executable, str(script),
        "--topic", topic,
        "--laws", laws,
        "--output", output,
    ]
    try:
        result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return [TextContent(type="text", text=result.stdout.strip() or f"Context pack written to: {output}")]
        return [TextContent(type="text", text=f"ERROR:\n{result.stderr}")]
    except subprocess.TimeoutExpired:
        return [TextContent(type="text", text="ERROR: Timed out after 60s")]
    except Exception as e:
        return [TextContent(type="text", text=f"ERROR: {e}")]


def _list_recent(limit: int = 10) -> list[TextContent]:
    if not DATA_ROOT.exists():
        return [TextContent(type="text", text="ERROR: DATA_ROOT not found.")]
    dirs = sorted(
        (d for d in DATA_ROOT.iterdir() if d.is_dir()),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )[:limit]
    if not dirs:
        return [TextContent(type="text", text="No law directories found.")]
    lines = [f"- {d.name}" for d in dirs]
    return [TextContent(type="text", text=f"Recent {len(dirs)} law directories:\n\n" + "\n".join(lines))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
