# wisewiki

Local-first session memory for AI-assisted coding.

AI assistants forget most of the high-signal knowledge discovered during a coding session. wisewiki captures that knowledge, turns it into browsable HTML session recaps and module pages, and lets future sessions resolve it instantly at zero extra LLM cost.

## How it works

1. You discuss code with an AI assistant (Claude Code, Cursor)
2. At the end of the session, run `/wiki-save`
3. The AI calls `wiki_capture` to save structured session knowledge to disk
4. wisewiki publishes:
   - module pages
   - a session recap page
   - a lightweight graph view
5. Next session, the AI calls `wiki_resolve` to recall previous understanding instantly

No API keys. No cloud. Everything stays on your machine.

## Quick Start

```bash
# Recommended: install via uv (auto-update on each IDE restart)
uv tool install wisewiki

# Or: install via pip
pip install wisewiki

# Auto-configure for Claude Code or Cursor
wiki setup

# Check status
wiki status
```

`wiki setup` auto-detects your IDE and writes the MCP config. If `uvx` is available, MCP config will use it so wisewiki auto-updates each time the IDE starts the server. Otherwise it falls back to the `wiki` command directly.

## Commands

| Command | Description |
|---------|-------------|
| `wiki serve` | Start MCP server on stdio (called by IDE) |
| `wiki setup [claude\|cursor]` | Configure MCP server for your IDE |
| `wiki status` | Show repos, page counts, last modified |
| `wiki view <repo>` | Open the session-centric repo home in browser |
| `wiki reindex <repo>` | Regenerate index.html for a repo |

## MCP Configuration

`wiki setup` writes the following to your IDE config. You can also configure manually:

**With uvx (auto-update, recommended):**

```json
{
  "mcpServers": {
    "wisewiki": {
      "command": "uvx",
      "args": ["--from", "wisewiki", "wiki", "serve"],
      "env": { "WIKI_DIR": "~/.wisewiki" }
    }
  }
}
```

**Without uvx (direct pip install):**

```json
{
  "mcpServers": {
    "wisewiki": {
      "command": "wiki",
      "args": ["serve"],
      "env": { "WIKI_DIR": "~/.wisewiki" }
    }
  }
}
```

Config file locations:
- Claude Code: `~/.claude.json`
- Cursor: `~/.cursor/mcp.json`

## MCP Tools

| Tool | Direction | Description |
|------|-----------|-------------|
| `wiki_capture` | Write | AI saves session/module knowledge to disk and updates recap/graph views |
| `wiki_resolve` | Read | AI retrieves previously saved understanding |

## Storage

All data lives under `~/.wisewiki/` (configurable via `WIKI_DIR` env var):

```
~/.wisewiki/
├── .index/cache.json    # search index
├── .index/wisewiki.db   # session + claim metadata
└── repos/
    └── my-project/
        ├── index.html
        ├── graph.html
        ├── graph.json
        ├── sessions/
        │   └── session-20260308-120000.html
        └── modules/
            ├── executor.md
            └── executor.html
```

## Product Shape

wisewiki is optimized for four outcomes:

- `Visibility`: see what the AI actually learned in a session
- `Trust`: inspect source provenance, capture time, and freshness
- `Filtering`: hide low-signal or provenance-free captures
- `Reviewability`: revisit session recaps before jumping back into code

## Requirements

- Python 3.10+
- No LLM API keys required

## License

MIT
