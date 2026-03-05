# src/wisewiki/models.py

from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class CacheEntry:
    title: str
    summary: str
    sections: list[str] = field(default_factory=list)
    key_facts: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    code_sigs: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    abs_path: str = ""
    generator: str = "wiki_capture"
    wiki_generated: float = field(default_factory=time.time)
    tokens_est_l1: int = 50
    tokens_est_l2: int = 100
    source_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "summary": self.summary,
            "sections": self.sections,
            "key_facts": self.key_facts,
            "tables": self.tables,
            "decisions": self.decisions,
            "code_sigs": self.code_sigs,
            "metrics": self.metrics,
            "abs_path": self.abs_path,
            "generator": self.generator,
            "wiki_generated": self.wiki_generated,
            "tokens_est_l1": self.tokens_est_l1,
            "tokens_est_l2": self.tokens_est_l2,
            "source_files": self.source_files,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CacheEntry":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class SearchResult:
    key: str           # "repo/module"
    repo: str
    module: str
    entry: CacheEntry
    score: float = 0.0


@dataclass
class WikiPage:
    repo: str
    module: str
    content: str       # raw markdown
    html_path: str     # abs path to .html
    md_path: str       # abs path to .md
