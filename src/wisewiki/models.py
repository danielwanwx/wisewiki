# src/wisewiki/models.py

from dataclasses import dataclass, field
from typing import Any
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
    capture_kind: str = "session"
    session_id: str = ""
    captured_at: float = field(default_factory=time.time)
    tokens_est_l1: int = 50
    tokens_est_l2: int = 100
    source_files: list[str] = field(default_factory=list)
    staleness_state: str = "unknown"
    quality_score: float = 0.0

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
            "capture_kind": self.capture_kind,
            "session_id": self.session_id,
            "captured_at": self.captured_at,
            "tokens_est_l1": self.tokens_est_l1,
            "tokens_est_l2": self.tokens_est_l2,
            "source_files": self.source_files,
            "staleness_state": self.staleness_state,
            "quality_score": self.quality_score,
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


@dataclass
class SessionEvent:
    id: str
    session_id: str
    event_type: str
    created_at: float
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidateClaim:
    kind: str
    module: str
    summary: str
    why_it_matters: str = ""
    confidence: float = 0.0
    reusability: float = 0.0
    specificity: float = 0.0
    evidence_refs: list[str] = field(default_factory=list)
    candidate_reason: str = ""


@dataclass
class PromotedClaim:
    kind: str
    module: str
    summary: str
    why_it_matters: str
    confidence: float
    reusability: float
    specificity: float
    novelty_score: float
    evidence_score: float
    final_score: float
    evidence_refs: list[str] = field(default_factory=list)
    staleness_state: str = "unknown"
    status: str = "promoted"


@dataclass
class SessionRecap:
    session_id: str
    repo: str
    title: str
    summary: str
    key_takeaways: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    gotchas: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    modules_touched: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)
    commands_run: list[str] = field(default_factory=list)
    tests_run: list[str] = field(default_factory=list)
    related_claims: list[PromotedClaim] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
