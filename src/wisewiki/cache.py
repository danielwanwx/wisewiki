# src/wisewiki/cache.py

import json
import re
import time
from pathlib import Path

from wisewiki.models import CacheEntry, SearchResult


class WikiCache:
    def __init__(self, cache_path: Path) -> None:
        self._path = cache_path
        self._data: dict[str, dict] = {}

    def load(self) -> None:
        """Load cache.json from disk. Auto-repair if malformed."""
        if not self._path.exists():
            self._data = {}
            return
        try:
            with open(self._path, encoding="utf-8") as f:
                self._data = json.load(f)
        except (json.JSONDecodeError, OSError):
            import sys
            print(f"Cache corrupted at {self._path}. Rebuilding...", file=sys.stderr)
            self._data = {}

    def save(self) -> None:
        """Atomically write cache.json."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)
        tmp.replace(self._path)

    def add_entry(self, key: str, entry: dict) -> None:
        """Add or overwrite an entry. key = 'repo/module'."""
        self._data[key] = entry

    def get_repos_in_cache(self) -> list[str]:
        """Return list of unique repo names in cache."""
        repos = set()
        for key in self._data:
            if "/" in key:
                repos.add(key.split("/", 1)[0])
        return sorted(repos)

    def search(self, query: str, repo_filter: str | None = None) -> list[SearchResult]:
        """Keyword search over cache entries. Returns ranked results."""
        query_lower = query.lower()
        query_tokens = re.split(r'\W+', query_lower)
        query_tokens = [t for t in query_tokens if t]

        results = []
        for key, entry_dict in self._data.items():
            if repo_filter and not key.startswith(f"{repo_filter}/"):
                continue

            repo, _, module = key.partition("/")
            score = _score_entry(key, entry_dict, query_lower, query_tokens)
            if score > 0:
                try:
                    entry = CacheEntry.from_dict(entry_dict)
                except Exception:
                    continue
                results.append(SearchResult(
                    key=key,
                    repo=repo,
                    module=module,
                    entry=entry,
                    score=score,
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def format_results(self, results: list[SearchResult], depth: str = "auto") -> str:
        """Format search results for MCP response."""
        parts = []
        for r in results:
            entry = r.entry
            html_path = entry.abs_path.replace(".md", ".html") if entry.abs_path else ""
            file_url = f"file://{html_path}" if html_path else ""

            if depth == "full":
                # Read full markdown from disk
                md_path = Path(entry.abs_path)
                if md_path.exists():
                    content = md_path.read_text(encoding="utf-8")
                    parts.append(f"## {entry.title} ({r.key})\n\n{content}\n\n{file_url}")
                else:
                    parts.append(_format_l1(r, file_url))
            else:
                parts.append(_format_l1(r, file_url))

        return "\n\n---\n\n".join(parts)


def _format_l1(r: SearchResult, file_url: str) -> str:
    entry = r.entry
    sections_str = " · ".join(entry.sections) if entry.sections else "—"
    lines = [
        f"## {entry.title} ({r.key})",
        "",
        entry.summary or "(no summary)",
        "",
        f"**Sections:** {sections_str}",
    ]
    if file_url:
        lines += ["", file_url]
    return "\n".join(lines)


def _score_entry(key: str, entry: dict, query_lower: str, tokens: list[str]) -> float:
    """Score entry against query. Higher = better match."""
    score = 0.0
    searchable = " ".join([
        key,
        entry.get("title", ""),
        entry.get("summary", ""),
        " ".join(entry.get("sections", [])),
        " ".join(entry.get("key_facts", [])),
        " ".join(entry.get("code_sigs", [])),
    ]).lower()

    # Exact key match: highest priority
    if query_lower == key or query_lower == key.split("/", 1)[-1]:
        score += 100.0

    # Token matches
    for token in tokens:
        if token in key:
            score += 10.0
        count = searchable.count(token)
        score += min(count * 2.0, 20.0)

    # Title prefix bonus
    title_lower = entry.get("title", "").lower()
    if title_lower.startswith(query_lower):
        score += 15.0

    return score
