# wisewiki

Lightweight, local-first wiki for AI-captured code understanding.

AI assistants forget everything after a conversation ends. wisewiki lets them save structured understanding to local wiki pages during a session, and instantly recall it in the next — at zero extra LLM cost.

## How it works

1. You discuss code with an AI assistant (Claude Code, Cursor)
2. At the end of the session, run `/wiki-save`
3. The AI calls `wiki_capture` to save structured markdown pages to disk
4. Next session, the AI calls `wiki_resolve` to recall previous understanding instantly

No API keys. No cloud. Everything stays on your machine.

## Quick Start

```bash
pip install wisewiki

# Auto-configure for Claude Code or Cursor
wiki setup

# Check status
wiki status
```

## Commands

| Command | Description |
|---------|-------------|
| `wiki serve` | Start MCP server on stdio (called by IDE) |
| `wiki setup [claude\|cursor]` | Configure MCP server for your IDE |
| `wiki status` | Show repos, page counts, last modified |
| `wiki view <repo>` | Open repo wiki in browser |

## MCP Tools

| Tool | Direction | Description |
|------|-----------|-------------|
| `wiki_capture` | Write | AI saves module understanding to disk |
| `wiki_resolve` | Read | AI retrieves previously saved understanding |

## Storage

All data lives under `~/.wisewiki/` (configurable via `WIKI_DIR` env var):

```
~/.wisewiki/
├── .index/cache.json    # search index
└── repos/
    └── my-project/
        ├── index.html
        └── modules/
            ├── executor.md
            └── executor.html
```

## Requirements

- Python 3.10+
- No LLM API keys required

## License

MIT
