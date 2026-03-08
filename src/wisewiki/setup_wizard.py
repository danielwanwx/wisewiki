# src/wisewiki/setup_wizard.py

import json
import shutil
from pathlib import Path


WIKI_SAVE_SKILL_CONTENT = """\
# /wiki-save

Save code insights from this conversation to your local wiki.

## Steps

1. Review what code modules were discussed in this conversation
2. For each meaningful module (skip trivial config files, boilerplate):
   - Call `wiki_capture` with:
     - `repo`: infer from file paths (use directory name, kebab-case, e.g. "my-project")
     - `module`: component name in snake_case (e.g. "auth_service", "data_pipeline")
     - `content`: structured markdown with your understanding
     - `source_files`: optional list of concrete files discussed for provenance
3. Report saved pages with their file:// links

## Content Format

Use this structure for each module page:

```markdown
## Purpose
What this module does and why it exists (1-2 paragraphs).
Focus on WHY, not just what — the code already shows what it does.

## Key Functions
- `function_name(param: type) -> return_type`: brief description of contract
- `other_function(a: str, b: int) -> dict`: when to use and what it returns

## Design Decisions
- **Decision title**: Rationale. What alternatives were considered and why they were rejected.
- **Another decision**: More context on the tradeoff made.

## Architecture (if applicable)
How this module connects to other modules. Data flow.

## Gotchas (if applicable)
- Hidden behavior, non-obvious constraints, or pitfalls future sessions should remember.

## Open Questions (if applicable)
- Important unresolved questions worth carrying into a future coding session.

## Metrics (if mentioned)
- Any performance figures, latency numbers, or scale characteristics discussed
```

## Repo Name Convention
- Use the top-level directory name of the project being discussed
- Convert to kebab-case: `my_project` → `my-project`, `MyCPLProject` → `my-cpl-project`
- If unclear, use the name shown in `import` statements or file paths

## Module Name Convention
- Use snake_case matching the Python module name or filename stem
- For services/components without a direct file mapping, use descriptive snake_case
- Examples: `executor`, `auth_service`, `pipeline_runner`, `data_loader`

## What to Capture
- WHY decisions were made (not just what the code does)
- HOW components interact and depend on each other
- WHAT the public contract is (inputs, outputs, side effects)
- GOTCHAS and non-obvious behaviors discovered during debugging
- CONTEXT that the code itself doesn't make obvious
- SOURCE FILES when you can point to the concrete evidence

## What to Skip
- Trivial files: `__init__.py` with no logic, `conftest.py`, pure config
- Auto-generated code (migrations, protobuf output, etc.)
- Files you only briefly mentioned without gaining understanding
- Test files (unless the test reveals important behavior about the module under test)
- Standard library wrappers with no domain logic

## After Saving
Report a summary like:

Saved 3 wiki pages for help-cpl:
- executor → file:///Users/alice/.wisewiki/repos/help-cpl/modules/executor.html
- config → file:///Users/alice/.wisewiki/repos/help-cpl/modules/config.html
- pipeline_runner → file:///Users/alice/.wisewiki/repos/help-cpl/modules/pipeline_runner.html

Run `wiki view help-cpl` to browse all pages.
"""


def _mcp_server_config(wiki_dir: str) -> dict:
    """Build mcpServers entry. Use uvx for auto-update if available."""
    if shutil.which("uvx"):
        return {
            "command": "uvx",
            "args": ["--from", "wisewiki", "wiki", "serve"],
            "env": {"WIKI_DIR": wiki_dir},
        }
    return {
        "command": "wiki",
        "args": ["serve"],
        "env": {"WIKI_DIR": wiki_dir},
    }


def run_setup(platform: str | None) -> None:
    resolved = _detect_platform(platform)
    if resolved is None:
        _print_manual_instructions()
        return
    wiki_dir = str(Path.home() / ".wisewiki")
    if resolved == "claude":
        _setup_claude(wiki_dir)
    else:
        _setup_cursor(wiki_dir)


def _detect_platform(requested: str | None) -> str | None:
    if requested:
        return requested
    has_claude = (Path.home() / ".claude.json").exists()
    has_cursor = (Path.home() / ".cursor" / "mcp.json").exists()
    if has_claude and not has_cursor:
        return "claude"
    if has_cursor and not has_claude:
        return "cursor"
    if has_claude and has_cursor:
        import click
        choice = click.prompt("Configure for", type=click.Choice(["claude", "cursor"]))
        return choice
    return None


def _setup_claude(wiki_dir: str) -> None:
    import click
    config_path = Path.home() / ".claude.json"
    config = {}
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    config.setdefault("mcpServers", {})
    server_cfg = _mcp_server_config(wiki_dir)
    config["mcpServers"]["wisewiki"] = server_cfg
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    skills_dir = Path.home() / ".claude" / "skills"
    skill_path = _install_skill(skills_dir)

    using_uvx = server_cfg["command"] == "uvx"
    click.echo("Configured Claude Code:")
    click.echo("  MCP server: ~/.claude.json → mcpServers.wisewiki")
    if using_uvx:
        click.echo("  Auto-update: enabled (via uvx)")
    click.echo(f"  Skill file: {skill_path}")
    click.echo()
    click.echo("Restart Claude Code to activate.")
    click.echo("Use /wiki-save in any conversation to save code insights.")


def _setup_cursor(wiki_dir: str) -> None:
    import click
    config_path = Path.home() / ".cursor" / "mcp.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = {}
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    config.setdefault("mcpServers", {})
    server_cfg = _mcp_server_config(wiki_dir)
    config["mcpServers"]["wisewiki"] = server_cfg
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    using_uvx = server_cfg["command"] == "uvx"
    click.echo("Configured Cursor:")
    click.echo("  MCP server: ~/.cursor/mcp.json → mcpServers.wisewiki")
    if using_uvx:
        click.echo("  Auto-update: enabled (via uvx)")
    click.echo()
    click.echo("Restart Cursor to activate.")
    click.echo('Ask the AI: "Use wiki_capture to save what we just discussed."')


def _install_skill(skills_dir: Path) -> Path:
    skills_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skills_dir / "wiki-save.md"
    skill_path.write_text(WIKI_SAVE_SKILL_CONTENT, encoding="utf-8")
    return skill_path


def _print_manual_instructions() -> None:
    import click
    click.echo("No IDE config found. Add wisewiki manually:\n")
    cfg = _mcp_server_config(str(Path.home() / ".wisewiki"))
    click.echo("Claude Code (~/.claude.json) or Cursor (~/.cursor/mcp.json):")
    click.echo(json.dumps({"mcpServers": {"wisewiki": cfg}}, indent=2))
