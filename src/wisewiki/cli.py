# src/wisewiki/cli.py

import click
from datetime import datetime
from pathlib import Path


@click.group()
@click.version_option(package_name="wisewiki")
def cli() -> None:
    """wisewiki — local wiki for AI-captured code understanding."""
    pass


@cli.command()
@click.option("--wiki-dir", envvar="WIKI_DIR", default="~/.wisewiki",
              help="Wiki root directory")
def serve(wiki_dir: str) -> None:
    """Start wisewiki MCP server on stdio."""
    import asyncio
    from wisewiki.mcp_server import run_server

    wiki_path = Path(wiki_dir).expanduser().resolve()
    try:
        wiki_path.mkdir(parents=True, exist_ok=True)
        (wiki_path / ".index").mkdir(parents=True, exist_ok=True)
    except OSError as e:
        click.echo(f"Error: cannot create wiki directory {wiki_path}: {e}", err=True)
        raise SystemExit(1)

    asyncio.run(run_server(wiki_path))


@cli.command()
@click.argument("platform", required=False, type=click.Choice(["claude", "cursor"]))
def setup(platform: str | None) -> None:
    """Configure MCP server for Claude Code or Cursor."""
    from wisewiki.setup_wizard import run_setup
    run_setup(platform)


@cli.command()
@click.option("--wiki-dir", envvar="WIKI_DIR", default="~/.wisewiki")
def status(wiki_dir: str) -> None:
    """Show wiki repos and page counts."""
    wiki_path = Path(wiki_dir).expanduser().resolve()

    if not wiki_path.exists():
        click.echo(f"Wiki directory not found at {wiki_dir}.\nRun: wiki setup")
        raise SystemExit(1)

    repos_dir = wiki_path / "repos"
    click.echo(f"wisewiki status — {wiki_dir}\n")

    if not repos_dir.exists() or not any(repos_dir.iterdir()):
        click.echo("  No repos found. Use /wiki-save in a conversation to get started.")
        return

    rows = []
    total = 0
    for repo_dir in sorted(repos_dir.iterdir()):
        if not repo_dir.is_dir():
            continue
        module_dir = repo_dir / "modules"
        pages = list(module_dir.glob("*.md")) if module_dir.exists() else []
        count = len(pages)
        total += count
        if pages:
            last_mtime = max(p.stat().st_mtime for p in pages)
            last_str = datetime.fromtimestamp(last_mtime).strftime("%Y-%m-%d %H:%M")
        else:
            last_str = "—"
        rows.append((repo_dir.name, count, last_str))

    max_name = max(len(r[0]) for r in rows) if rows else 10
    for name, count, last in rows:
        click.echo(f"  {name:<{max_name}}  {count:>3} pages   last: {last}")

    click.echo(f"\nTotal: {total} pages across {len(rows)} repos.")


# Register alias
cli.add_command(status, name="st")


@cli.command()
@click.argument("repo")
@click.option("--wiki-dir", envvar="WIKI_DIR", default="~/.wisewiki")
def view(repo: str, wiki_dir: str) -> None:
    """Open repo wiki in browser."""
    import webbrowser
    wiki_path = Path(wiki_dir).expanduser().resolve()
    repo_dir = wiki_path / "repos" / repo

    if not repo_dir.exists():
        click.echo(f"Repo '{repo}' not found at {repo_dir}")
        raise SystemExit(1)

    index_html = repo_dir / "index.html"
    if not index_html.exists():
        click.echo(f"No index.html found for '{repo}'. Run: wiki reindex {repo}")
        raise SystemExit(1)

    url = f"file://{index_html}"
    click.echo(f"Opening {url}")
    webbrowser.open(url)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
