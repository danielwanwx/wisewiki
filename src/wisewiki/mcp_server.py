# src/wisewiki/mcp_server.py

import asyncio
import hashlib
import logging
import re
import time
from pathlib import Path
from typing import Dict, Tuple

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from wisewiki.cache import WikiCache
from wisewiki.html_writer import HtmlWriter
from wisewiki.models import CacheEntry

logger = logging.getLogger(__name__)

# Session-scoped deduplication state (ephemeral)
_session_saves: Dict[Tuple[str, str], str] = {}


def _compute_content_hash(content: str) -> str:
    """Compute SHA256 hash for deduplication (first 16 chars)."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

NAME_RE = re.compile(r'^[a-zA-Z0-9_-]+$')

WIKI_CAPTURE_DESCRIPTION = """\
Save your understanding of a code module to the local wiki.

Use this tool after discussing a module to persist your insights for future sessions.
Call once per module. Safe to call multiple times — later calls overwrite earlier ones.

Returns a file:// link to the generated HTML page.
"""

WIKI_RESOLVE_DESCRIPTION = """\
ALWAYS use this tool FIRST when asked about a module, component, or codebase that
may have been previously documented in the wiki.

Retrieves wiki pages by keyword search, module name lookup, or repo listing.

Intent routing:
- "list", "repos", "repositories" → list all known repos
- Single word matching a module name → explain that module
- Multi-word query → keyword search across all pages

depth="auto" returns summary + section headings (L0+L1, ~150 tokens).
depth="full" returns the complete page content (L2, ~600 tokens).

Returns file:// links to HTML pages for browser viewing.

STOP RETRYING if response starts with [REPO_NOT_FOUND].
"""

WIKI_CAPTURE_SCHEMA = {
    "type": "object",
    "properties": {
        "repo": {"type": "string", "description": "Repository name (kebab-case)"},
        "module": {"type": "string", "description": "Module name (snake_case)"},
        "content": {"type": "string", "description": "Markdown content describing the module"},
    },
    "required": ["repo", "module", "content"],
}

WIKI_RESOLVE_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Module name, keywords, or 'list'"},
        "repo": {"type": "string", "description": "Optional: filter to a specific repo"},
        "depth": {
            "type": "string",
            "enum": ["auto", "full"],
            "default": "auto",
            "description": "'auto' = summary+sections. 'full' = complete page.",
        },
    },
    "required": ["query"],
}


def _entry_from_md(content: str, path: Path) -> dict:
    """Extract cache entry fields from markdown content. No LLM."""
    lines = content.splitlines()

    title = path.stem.replace("_", " ").replace("-", " ").title()
    for line in lines:
        if line.startswith("## "):
            title = line[3:].strip()
            break

    sections = [line[3:].strip() for line in lines if line.startswith("## ")]

    summary = ""
    in_code = False
    for line in lines:
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code or line.startswith("#"):
            continue
        stripped = line.strip()
        if stripped:
            summary = stripped[:500]
            break

    def _bullets(section_name: str) -> list[str]:
        in_s, out = False, []
        for line in lines:
            if line.startswith("## "):
                in_s = (line[3:].strip() == section_name)
            elif in_s and line.startswith("- "):
                out.append(line[2:].strip())
        return out

    def _table_headers() -> list[str]:
        headers = []
        for line in lines:
            s = line.strip()
            if s.startswith("|") and s.endswith("|") and not all(c in "-| :" for c in s[1:-1]):
                headers.append(s)
        return headers

    def _code_sigs() -> list[str]:
        in_s, sigs = False, []
        for line in lines:
            if line.startswith("## "):
                in_s = "Key Functions" in line
            elif in_s and line.startswith("- "):
                sigs.extend(re.findall(r'`([^`]+)`', line))
        return sigs

    tokens_est_l2 = max(len(content) // 4, 100)
    tokens_est_l1 = max(len(summary) // 4 + 80, 50)

    return {
        "title": title,
        "summary": summary,
        "sections": sections,
        "key_facts": _bullets("Key Facts"),
        "tables": _table_headers(),
        "decisions": _bullets("Design Decisions"),
        "code_sigs": _code_sigs(),
        "metrics": _bullets("Metrics") or _bullets("Performance"),
        "abs_path": str(path.resolve()),
        "generator": "wiki_capture",
        "wiki_generated": time.time(),
        "tokens_est_l1": tokens_est_l1,
        "tokens_est_l2": tokens_est_l2,
        "source_files": [],
    }


def _route_intent(query: str) -> str:
    q = query.strip().lower()
    if q in ("list", "repos", "repositories", "list repos", "show repos"):
        return "list_repos"
    if re.match(r'^[a-zA-Z0-9_-]+$', q):
        return "explain_module"
    return "search"


def _resolve(query: str, repo: str | None, depth: str, cache: WikiCache, wiki_dir: Path) -> str:
    intent = _route_intent(query)

    if intent == "list_repos":
        repos = cache.get_repos_in_cache()
        if not repos:
            return "[REPO_NOT_FOUND] No repos found in wiki. Use /wiki-save to capture your first page."
        lines = ["**Known repos:**"]
        for r in sorted(repos):
            count = sum(1 for k in cache._data if k.startswith(f"{r}/"))
            lines.append(f"- `{r}` ({count} pages)")
        return "\n".join(lines)

    results = cache.search(query, repo_filter=repo)
    if results:
        return cache.format_results(results[:5], depth=depth)

    if repo and intent == "explain_module":
        md_path = wiki_dir / "repos" / repo / "modules" / f"{query}.md"
        if md_path.exists():
            content = md_path.read_text(encoding="utf-8")
            if depth == "full":
                return content
            entry = _entry_from_md(content, md_path)
            from wisewiki.cache import _format_l1
            from wisewiki.models import SearchResult, CacheEntry
            sr = SearchResult(
                key=f"{repo}/{query}", repo=repo, module=query,
                entry=CacheEntry.from_dict(entry), score=0.0,
            )
            html_path = md_path.with_suffix(".html")
            return _format_l1(sr, f"file://{html_path}" if html_path.exists() else "")
        return f"[REPO_NOT_FOUND] No module '{query}' in repo '{repo}'."

    return f"[REPO_NOT_FOUND] No wiki page found for '{query}'. Use /wiki-save to capture it."


async def run_server(wiki_dir: Path) -> None:
    """Initialize and run the MCP stdio server."""
    cache = WikiCache(wiki_dir / ".index" / "cache.json")
    cache.load()
    html_writer = HtmlWriter(wiki_dir)
    server = Server("wisewiki")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(name="wiki_resolve", description=WIKI_RESOLVE_DESCRIPTION,
                       inputSchema=WIKI_RESOLVE_SCHEMA),
            types.Tool(name="wiki_capture", description=WIKI_CAPTURE_DESCRIPTION,
                       inputSchema=WIKI_CAPTURE_SCHEMA),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        if name == "wiki_resolve":
            query = arguments.get("query", "").strip()
            repo = arguments.get("repo", "").strip() or None
            depth = arguments.get("depth", "auto")
            result = _resolve(query, repo, depth, cache, wiki_dir)
            return [types.TextContent(type="text", text=result)]

        elif name == "wiki_capture":
            repo = arguments.get("repo", "").strip()
            module = arguments.get("module", "").strip()
            content = arguments.get("content", "").strip()

            if not NAME_RE.match(repo):
                return [types.TextContent(type="text", text=
                    f"Error: repo name '{repo}' invalid. Use alphanumeric, hyphens, underscores only.")]
            if not NAME_RE.match(module):
                return [types.TextContent(type="text", text=
                    f"Error: module name '{module}' invalid. Use alphanumeric, hyphens, underscores only.")]

            truncation_warning = ""
            content_bytes = content.encode("utf-8")
            if len(content_bytes) > 50 * 1024:
                content = content_bytes[:50 * 1024].decode("utf-8", errors="ignore")
                truncation_warning = "\n\n⚠ Content truncated to 50KB limit."

            # Phase 2: Session-level deduplication check
            key = (repo, module)
            content_hash = _compute_content_hash(content)

            module_dir = wiki_dir / "repos" / repo / "modules"
            module_dir.mkdir(parents=True, exist_ok=True)
            md_path = module_dir / f"{module}.md"

            if key in _session_saves and _session_saves[key] == content_hash:
                # Already saved in this session with identical content
                file_url = f"file://{md_path.with_suffix('.html')}"
                text = (
                    f"Already saved {repo}/{module} in this session. "
                    f"Use wiki_resolve to retrieve it.\n\n{file_url}"
                )
                return [types.TextContent(type="text", text=text)]

            # Phase 1: Disk-level content comparison
            operation_type = "created"
            if md_path.exists():
                existing_content = md_path.read_text(encoding="utf-8")
                if existing_content == content:
                    # Content unchanged - skip write operations
                    file_url = f"file://{md_path.with_suffix('.html')}"
                    text = (
                        f"No changes detected for {repo}/{module}. "
                        f"Wiki page is already up-to-date.\n\n{file_url}"
                    )
                    # Update session cache even though we skip write
                    _session_saves[key] = content_hash
                    return [types.TextContent(type="text", text=text)]
                operation_type = "updated"

            # Perform save operations
            tmp_md = md_path.with_suffix(".md.tmp")
            tmp_md.write_text(content, encoding="utf-8")
            tmp_md.replace(md_path)

            entry = _entry_from_md(content, md_path)
            cache.add_entry(f"{repo}/{module}", entry)
            cache.save()

            html_path = None
            try:
                html_path = html_writer.write_module_page(repo, module, content, md_path)
                html_writer.generate_index(repo)
            except Exception as e:
                logger.warning(f"HTML generation failed: {e}")

            # Record in session cache after successful save
            _session_saves[key] = content_hash

            file_url = f"file://{html_path}" if html_path else f"file://{md_path}"
            verb = "Created" if operation_type == "created" else "Updated"
            text = (
                f"{verb} wiki page for {repo}/{module}.\n\n"
                f"{file_url}{truncation_warning}"
            )
            return [types.TextContent(type="text", text=text)]

        raise ValueError(f"Unknown tool: {name}")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
