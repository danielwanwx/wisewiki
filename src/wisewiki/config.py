# src/wisewiki/config.py

import os
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Python 3.10


DEFAULT_WIKI_DIR = Path.home() / ".wisewiki"
DEFAULTS = {
    "wiki_dir": str(DEFAULT_WIKI_DIR),
    "default_depth": "auto",
    "max_results": 5,
    "html_theme": "default",
    "highlight_code": True,
    "sidebar_max_items": 50,
}


def get_wiki_dir() -> Path:
    """Resolve wiki root directory from env > config.toml > default."""
    env_val = os.environ.get("WIKI_DIR")
    if env_val:
        return Path(env_val).expanduser().resolve()

    config_path = DEFAULT_WIKI_DIR / "config.toml"
    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        wiki_section = data.get("wisewiki", {})
        if "wiki_dir" in wiki_section:
            return Path(wiki_section["wiki_dir"]).expanduser().resolve()

    return DEFAULT_WIKI_DIR.resolve()


def load_config() -> dict[str, Any]:
    """Load full config with defaults."""
    config = dict(DEFAULTS)
    wiki_dir = get_wiki_dir()
    config_path = wiki_dir / "config.toml"

    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        wiki_section = data.get("wisewiki", {})
        config.update(wiki_section)
        html_section = data.get("wisewiki", {}).get("html", {})
        config.update(html_section)

    config["wiki_dir"] = str(wiki_dir)
    return config
