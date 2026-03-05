# src/wisewiki/html_writer.py

import re
from pathlib import Path

import markdown as md_lib


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — wisewiki</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           margin: 0; display: flex; min-height: 100vh; }}
    nav {{ width: 220px; background: #f5f5f5; padding: 1rem; border-right: 1px solid #ddd;
          flex-shrink: 0; overflow-y: auto; font-size: 0.85rem; }}
    nav h3 {{ margin: 0 0 0.5rem; font-size: 0.9rem; color: #666; text-transform: uppercase; }}
    nav a {{ display: block; padding: 0.2rem 0; color: #333; text-decoration: none; }}
    nav a:hover {{ color: #0066cc; }}
    main {{ flex: 1; padding: 2rem; max-width: 860px; }}
    h1, h2, h3 {{ color: #1a1a1a; }}
    h2 {{ border-bottom: 1px solid #eee; padding-bottom: 0.3rem; }}
    code {{ background: #f0f0f0; padding: 0.1em 0.3em; border-radius: 3px;
           font-size: 0.9em; }}
    pre code {{ background: none; padding: 0; }}
    pre {{ background: #f8f8f8; padding: 1rem; border-radius: 4px; overflow-x: auto;
          border: 1px solid #e0e0e0; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 0.5rem 0.8rem; text-align: left; }}
    th {{ background: #f5f5f5; }}
    .footer {{ margin-top: 3rem; font-size: 0.8rem; color: #999; }}
  </style>
</head>
<body>
  <nav>
    <h3>{repo}</h3>
    {sidebar}
  </nav>
  <main>
    {body}
    <div class="footer">wisewiki · {repo}/{module}</div>
  </main>
</body>
</html>
"""


class HtmlWriter:
    def __init__(self, wiki_dir: Path) -> None:
        self.wiki_dir = wiki_dir

    def write_module_page(
        self, repo: str, module: str, md_content: str, md_path: Path
    ) -> Path:
        html_content = self._md_to_html(md_content)
        sidebar = self._build_sidebar(repo, current=module)
        title = self._extract_title(md_content, module)
        page = HTML_TEMPLATE.format(
            title=title,
            repo=repo,
            module=module,
            sidebar=sidebar,
            body=html_content,
        )
        html_path = md_path.with_suffix(".html")
        self._atomic_write(html_path, page)
        return html_path

    def write_overview_page(self, repo: str, md_content: str) -> Path:
        html_content = self._md_to_html(md_content)
        sidebar = self._build_sidebar(repo, current="overview")
        title = self._extract_title(md_content, repo)
        page = HTML_TEMPLATE.format(
            title=title,
            repo=repo,
            module="overview",
            sidebar=sidebar,
            body=html_content,
        )
        html_path = self.wiki_dir / "repos" / repo / "overview.html"
        self._atomic_write(html_path, page)
        return html_path

    def generate_index(self, repo: str) -> Path:
        """Generate index.html: overview + module list with links."""
        repo_dir = self.wiki_dir / "repos" / repo
        overview_html = repo_dir / "overview.html"

        if overview_html.exists():
            # Redirect to overview
            content = (
                f'<!DOCTYPE html><html><head><meta charset="UTF-8">'
                f'<meta http-equiv="refresh" content="0;url=overview.html">'
                f'</head><body>Redirecting to <a href="overview.html">overview</a>'
                f'</body></html>'
            )
        else:
            # Generate a simple index listing modules
            modules = self._list_modules(repo)
            links = "\n".join(
                f'<li><a href="modules/{m}.html">{m}</a></li>'
                for m in modules
            )
            content = (
                f'<!DOCTYPE html><html><head><meta charset="UTF-8">'
                f'<title>{repo} — wisewiki</title></head>'
                f'<body><h1>{repo}</h1><ul>{links}</ul></body></html>'
            )

        index_path = repo_dir / "index.html"
        self._atomic_write(index_path, content)
        return index_path

    def _build_sidebar(self, repo: str, current: str = "") -> str:
        modules = self._list_modules(repo)
        items = []
        for m in modules:
            active = ' style="font-weight:bold;color:#0066cc"' if m == current else ""
            items.append(f'<a href="../modules/{m}.html"{active}>{m}</a>')
        # Also link overview
        overview_link = '<a href="../overview.html">overview</a>' if (
            self.wiki_dir / "repos" / repo / "overview.html"
        ).exists() else ""
        return (overview_link + "\n" if overview_link else "") + "\n".join(items)

    def _list_modules(self, repo: str) -> list[str]:
        module_dir = self.wiki_dir / "repos" / repo / "modules"
        if not module_dir.exists():
            return []
        return sorted(p.stem for p in module_dir.glob("*.md"))

    def _md_to_html(self, content: str) -> str:
        return md_lib.markdown(
            content,
            extensions=["tables", "fenced_code", "nl2br"],
        )

    def _extract_title(self, content: str, fallback: str) -> str:
        for line in content.splitlines():
            if line.startswith("## "):
                return line[3:].strip()
        return fallback.replace("_", " ").replace("-", " ").title()

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
