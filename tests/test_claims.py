"""Tests for claim extraction and promotion."""

from wisewiki.claims import extract_candidate_claims
from wisewiki.models import CacheEntry, SessionEvent


def test_extract_candidate_claims_from_session_events():
    entry = CacheEntry(
        title="Html Writer",
        summary="",
        source_files=["src/wisewiki/html_writer.py"],
        session_id="session-events",
    )
    events = [
        SessionEvent(
            id="ev1",
            session_id="session-events",
            event_type="error_observed",
            created_at=1.0,
            payload={"message": "overview sidebar links broken"},
        ),
        SessionEvent(
            id="ev2",
            session_id="session-events",
            event_type="code_edit",
            created_at=2.0,
            payload={"path": "src/wisewiki/html_writer.py", "summary": "split relative link logic by page type"},
        ),
        SessionEvent(
            id="ev3",
            session_id="session-events",
            event_type="test_result",
            created_at=3.0,
            payload={"command": "uv run pytest tests/test_html_writer.py -v", "summary": "1 passed", "exit_code": 0},
        ),
        SessionEvent(
            id="ev4",
            session_id="session-events",
            event_type="assistant_message",
            created_at=4.0,
            payload={"text": "HtmlWriter depends on page location because overview and module pages live in different directories."},
        ),
    ]

    claims = extract_candidate_claims("wisewiki", "html_writer", "Quick freeform note", entry, session_events=events)
    summaries = [claim.summary for claim in claims]
    kinds = {claim.kind for claim in claims}

    assert "debug_outcome" in kinds
    assert "architecture" in kinds
    assert any("overview sidebar links broken" in summary for summary in summaries)
    assert any("different directories" in summary for summary in summaries)
