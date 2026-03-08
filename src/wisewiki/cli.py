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


def _resolve_repo_dir(repo: str, wiki_dir: str) -> tuple[Path, Path]:
    wiki_path = Path(wiki_dir).expanduser().resolve()
    repo_dir = wiki_path / "repos" / repo
    if not repo_dir.exists():
        click.echo(f"Repo '{repo}' not found at {repo_dir}")
        raise SystemExit(1)
    return wiki_path, repo_dir


@cli.command()
@click.argument("repo")
@click.option("--wiki-dir", envvar="WIKI_DIR", default="~/.wisewiki")
def reindex(repo: str, wiki_dir: str) -> None:
    """Regenerate index.html for a repo (e.g. after manual edits)."""
    wiki_path, repo_dir = _resolve_repo_dir(repo, wiki_dir)

    from wisewiki.html_writer import HtmlWriter
    writer = HtmlWriter(wiki_path)
    writer.generate_index(repo)
    click.echo(f"Regenerated index for {repo}.")


@cli.command()
@click.argument("repo")
@click.option("--wiki-dir", envvar="WIKI_DIR", default="~/.wisewiki")
def view(repo: str, wiki_dir: str) -> None:
    """Open repo wiki in browser."""
    import webbrowser
    wiki_path, repo_dir = _resolve_repo_dir(repo, wiki_dir)

    index_html = repo_dir / "index.html"
    if not index_html.exists():
        click.echo(f"No index.html found for '{repo}'. Run: wiki reindex {repo}")
        raise SystemExit(1)

    url = f"file://{index_html}"
    click.echo(f"Opening {url}")
    webbrowser.open(url)


@cli.command()
@click.argument("repo")
@click.option("--wiki-dir", envvar="WIKI_DIR", default="~/.wisewiki")
def sessions(repo: str, wiki_dir: str) -> None:
    """List recent sessions for a repo."""
    from wisewiki.session_store import SessionStore

    wiki_path, _ = _resolve_repo_dir(repo, wiki_dir)
    store = SessionStore(wiki_path)
    rows = store.get_recent_sessions(repo, limit=10)
    if not rows:
        click.echo(f"No sessions found for '{repo}'.")
        return

    click.echo(f"Recent sessions for {repo}:\n")
    for row in rows:
        updated = datetime.fromtimestamp(float(row["updated_at"])).strftime("%Y-%m-%d %H:%M")
        click.echo(f"  {row['id']}  {row['capture_count']} captures  updated: {updated}")
        click.echo(f"    {row['summary']}")


@cli.command()
@click.argument("repo")
@click.argument("session_id")
@click.option("--wiki-dir", envvar="WIKI_DIR", default="~/.wisewiki")
def recap(repo: str, session_id: str, wiki_dir: str) -> None:
    """Show a session recap summary in the terminal."""
    from wisewiki.session_store import SessionStore

    wiki_path, _ = _resolve_repo_dir(repo, wiki_dir)
    store = SessionStore(wiki_path)
    recap = store.build_session_recap(repo, session_id)

    click.echo(f"Session recap: {recap.session_id}")
    click.echo(f"Title: {recap.title}")
    click.echo(f"Summary: {recap.summary}")
    click.echo("\nKey takeaways:")
    if recap.key_takeaways:
        for item in recap.key_takeaways:
            click.echo(f"- {item}")
    else:
        click.echo("- No takeaways captured.")


@cli.command()
@click.argument("repo")
@click.option("--wiki-dir", envvar="WIKI_DIR", default="~/.wisewiki")
def graph(repo: str, wiki_dir: str) -> None:
    """Show the location of the repo graph view."""
    wiki_path, repo_dir = _resolve_repo_dir(repo, wiki_dir)
    graph_html = repo_dir / "graph.html"
    graph_json = repo_dir / "graph.json"
    if not graph_html.exists() or not graph_json.exists():
        from wisewiki.html_writer import HtmlWriter
        from wisewiki.session_store import SessionStore

        store = SessionStore(wiki_path)
        writer = HtmlWriter(wiki_path)
        graph_data = store.get_graph_data(repo)
        graph_json = writer.write_graph_data(repo, graph_data)
        graph_html = writer.write_graph_page(repo, graph_data)
    click.echo(f"Graph HTML: file://{graph_html}")
    click.echo(f"Graph JSON: {graph_json}")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
