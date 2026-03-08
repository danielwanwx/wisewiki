from __future__ import annotations

import re
from typing import Iterable

from wisewiki.models import CacheEntry, CandidateClaim, PromotedClaim, SessionEvent


def _section_bullets(content: str, *section_names: str) -> list[str]:
    names = set(section_names)
    in_section = False
    bullets: list[str] = []
    for line in content.splitlines():
        if line.startswith("## "):
            in_section = line[3:].strip() in names
            continue
        if in_section and line.startswith("- "):
            bullets.append(line[2:].strip())
    return bullets


def _section_text(content: str, *section_names: str) -> str:
    names = set(section_names)
    in_section = False
    lines: list[str] = []
    for line in content.splitlines():
        if line.startswith("## "):
            in_section = line[3:].strip() in names
            continue
        if in_section:
            if line.startswith("## "):
                break
            if line.strip():
                lines.append(line.strip())
    return " ".join(lines).strip()


def _strip_markdown(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    return text.strip()


def _first_sentence(text: str, fallback: str) -> str:
    cleaned = _strip_markdown(text)
    if not cleaned:
        return fallback
    sentence = re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)[0].strip()
    return sentence or fallback


def _coerce_events(session_events: Iterable[SessionEvent | dict] | None) -> list[SessionEvent]:
    if not session_events:
        return []
    coerced: list[SessionEvent] = []
    for index, event in enumerate(session_events):
        if isinstance(event, SessionEvent):
            coerced.append(event)
            continue
        coerced.append(
            SessionEvent(
                id=str(event.get("id", f"event-{index}")),
                session_id=str(event.get("session_id", "")),
                event_type=str(event.get("event_type", "")),
                created_at=float(event.get("created_at", index)),
                payload=dict(event.get("payload", {})),
            )
        )
    return coerced


def _event_paths(events: list[SessionEvent]) -> list[str]:
    paths: list[str] = []
    for event in events:
        path = event.payload.get("path")
        if isinstance(path, str) and path and path not in paths:
            paths.append(path)
    return paths


def _event_claims(module: str, events: list[SessionEvent], evidence_refs: list[str]) -> list[CandidateClaim]:
    claims: list[CandidateClaim] = []
    error_events = [event for event in events if event.event_type == "error_observed"]
    edit_events = [event for event in events if event.event_type == "code_edit"]
    passing_tests = [
        event for event in events
        if event.event_type in {"test_result", "command_result"} and event.payload.get("exit_code", 0) == 0
    ]
    assistant_messages = [
        str(event.payload.get("text", ""))
        for event in events
        if event.event_type in {"assistant_message", "user_highlight"} and event.payload.get("text")
    ]

    if error_events and edit_events and passing_tests:
        summary = str(error_events[-1].payload.get("message", "observed issue")).strip()
        fix_summary = str(edit_events[-1].payload.get("summary", edit_events[-1].payload.get("path", "the implementation"))).strip()
        verification = str(passing_tests[-1].payload.get("summary", passing_tests[-1].payload.get("command", "verification command"))).strip()
        claims.append(
            CandidateClaim(
                kind="debug_outcome",
                module=module,
                summary=f"{summary} was addressed by {fix_summary} and verified by {verification}.",
                why_it_matters="Verified bug fixes save future debugging time.",
                confidence=0.9,
                reusability=0.88,
                specificity=0.9,
                evidence_refs=evidence_refs,
                candidate_reason="Error + code edit + passing verification is strong debug evidence.",
            )
        )

    for text in assistant_messages:
        cleaned = _strip_markdown(text)
        lowered = cleaned.lower()
        if "human-visible" in lowered or "session-centric" in lowered:
            claims.append(
                CandidateClaim(
                    kind="decision",
                    module=module,
                    summary=cleaned,
                    why_it_matters="Product-level presentation decisions shape how future users review session knowledge.",
                    confidence=0.76,
                    reusability=0.86,
                    specificity=0.78,
                    evidence_refs=evidence_refs,
                    candidate_reason="Presentation strategy is a reusable design decision for session memory UX.",
                )
            )
        if "because" in lowered and (
            "directory" in lowered
            or "directories" in lowered
            or "depends on" in lowered
            or "page location" in lowered
            or "relative link logic" in lowered
        ):
            claims.append(
                CandidateClaim(
                    kind="architecture",
                    module=module,
                    summary=cleaned,
                    why_it_matters="Module relationship explanations help future sessions recover context quickly.",
                    confidence=0.82,
                    reusability=0.85,
                    specificity=0.85,
                    evidence_refs=evidence_refs,
                    candidate_reason="Assistant explanation ties module behavior to a concrete structural reason.",
                )
            )
        if "should" in lowered and "?" in cleaned:
            claims.append(
                CandidateClaim(
                    kind="open_question",
                    module=module,
                    summary=cleaned,
                    why_it_matters="Open questions help resume unresolved design work.",
                    confidence=0.55,
                    reusability=0.7,
                    specificity=0.72,
                    evidence_refs=evidence_refs,
                    candidate_reason="Question-like guidance should remain visible for the next session.",
                )
            )

    return claims


def extract_candidate_claims(
    repo: str,
    module: str,
    content: str,
    entry: CacheEntry,
    *,
    session_events: Iterable[SessionEvent | dict] | None = None,
) -> list[CandidateClaim]:
    claims: list[CandidateClaim] = []
    events = _coerce_events(session_events)
    evidence_refs = list(dict.fromkeys([*entry.source_files, *_event_paths(events)]))
    source_boost = 0.15 if entry.source_files else 0.0

    if entry.summary:
        claims.append(
            CandidateClaim(
                kind="architecture",
                module=module,
                summary=entry.summary,
                why_it_matters=f"Helps future sessions quickly recall what `{module}` is responsible for.",
                confidence=min(0.65 + source_boost, 0.9),
                reusability=0.85,
                specificity=0.65 if entry.sections else 0.55,
                evidence_refs=evidence_refs,
                candidate_reason="Module summary is high-signal and reusable.",
            )
        )

    for bullet in _section_bullets(content, "Design Decisions"):
        cleaned = _strip_markdown(bullet)
        claims.append(
            CandidateClaim(
                kind="decision",
                module=module,
                summary=cleaned,
                why_it_matters=f"Captures why `{module}` was designed this way.",
                confidence=min(0.72 + source_boost, 0.95),
                reusability=0.9,
                specificity=0.8,
                evidence_refs=evidence_refs,
                candidate_reason="Design decisions are highly reusable across future sessions.",
            )
        )

    for sig in entry.code_sigs:
        claims.append(
            CandidateClaim(
                kind="contract",
                module=module,
                summary=f"`{sig}` is part of the important public contract for `{module}`.",
                why_it_matters="Public interfaces are frequently revisited in later coding sessions.",
                confidence=min(0.75 + source_boost, 0.95),
                reusability=0.88,
                specificity=0.82,
                evidence_refs=evidence_refs,
                candidate_reason="Function signatures make durable contract knowledge.",
            )
        )

    gotcha_bullets = _section_bullets(content, "Gotchas", "Known Issues", "Pitfalls")
    for bullet in gotcha_bullets:
        cleaned = _strip_markdown(bullet)
        claims.append(
            CandidateClaim(
                kind="gotcha",
                module=module,
                summary=cleaned,
                why_it_matters="Hidden behavior and pitfalls are high-value future reminders.",
                confidence=min(0.78 + source_boost, 0.96),
                reusability=0.94,
                specificity=0.86,
                evidence_refs=evidence_refs,
                candidate_reason="Gotchas are one of the highest-value claim types.",
            )
        )

    debug_bullets = _section_bullets(content, "Debug Outcomes", "Validation", "Fixes")
    for bullet in debug_bullets:
        cleaned = _strip_markdown(bullet)
        claims.append(
            CandidateClaim(
                kind="debug_outcome",
                module=module,
                summary=cleaned,
                why_it_matters="Verified root causes and fixes save re-debugging later.",
                confidence=min(0.8 + source_boost, 0.98),
                reusability=0.82,
                specificity=0.84,
                evidence_refs=evidence_refs,
                candidate_reason="Debug outcomes are valuable when they describe verified behavior.",
            )
        )

    for bullet in _section_bullets(content, "Open Questions", "Questions"):
        cleaned = _strip_markdown(bullet)
        claims.append(
            CandidateClaim(
                kind="open_question",
                module=module,
                summary=cleaned,
                why_it_matters="Open questions help future sessions resume unresolved design work.",
                confidence=0.55,
                reusability=0.7,
                specificity=0.7,
                evidence_refs=evidence_refs,
                candidate_reason="Open questions help maintain session continuity.",
            )
        )

    architecture_text = _section_text(content, "Architecture")
    if architecture_text:
        claims.append(
            CandidateClaim(
                kind="architecture",
                module=module,
                summary=_first_sentence(architecture_text, entry.summary or module),
                why_it_matters="Cross-module relationships are reusable future context.",
                confidence=min(0.7 + source_boost, 0.92),
                reusability=0.88,
                specificity=0.78,
                evidence_refs=evidence_refs,
                candidate_reason="Architecture notes describe how the module fits into the system.",
            )
        )

    claims.extend(_event_claims(module, events, evidence_refs))
    return claims


def promote_candidate_claims(
    claims: Iterable[CandidateClaim],
    *,
    existing_summaries: Iterable[str] = (),
    staleness_state: str = "unknown",
) -> list[PromotedClaim]:
    existing = {_strip_markdown(summary).lower() for summary in existing_summaries}
    promoted: list[PromotedClaim] = []
    for claim in claims:
        evidence_score = score_evidence(claim.evidence_refs)
        novelty_score = 0.25 if _strip_markdown(claim.summary).lower() in existing else 0.85
        final_score = round(
            (claim.confidence * 0.25)
            + (claim.reusability * 0.25)
            + (novelty_score * 0.20)
            + (claim.specificity * 0.15)
            + (evidence_score * 0.15),
            3,
        )
        if final_score < 0.55:
            continue
        promoted.append(
            PromotedClaim(
                kind=claim.kind,
                module=claim.module,
                summary=claim.summary,
                why_it_matters=claim.why_it_matters,
                confidence=claim.confidence,
                reusability=claim.reusability,
                specificity=claim.specificity,
                novelty_score=novelty_score,
                evidence_score=evidence_score,
                final_score=final_score,
                evidence_refs=list(claim.evidence_refs),
                staleness_state=staleness_state,
            )
        )
    return promoted


def score_evidence(evidence_refs: Iterable[str]) -> float:
    refs = [ref for ref in evidence_refs if ref]
    if not refs:
        return 0.2
    if len(refs) == 1:
        return 0.6
    return 0.85
