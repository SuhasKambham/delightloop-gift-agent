"""Unit tests for persistent feedback memory (no API keys required)."""

import json
import tempfile
from pathlib import Path

import app.services.feedback_memory as fm


CONTACT = {"name": "Aarav Mehta", "company": "Acme Corp"}


def test_feedback_persists_and_injects_into_context(monkeypatch, tmp_path):
    feedback_file = tmp_path / "feedback_memory.json"
    monkeypatch.setattr(fm, "FEEDBACK_FILE", feedback_file)
    monkeypatch.setattr(fm, "DATA_DIR", tmp_path)

    fm.save_feedback(
        CONTACT,
        run_id="run-1",
        action="reject",
        notes="Too generic — mention cricket and the discovery call",
        recommended_gifts=[{"gift_name": "Generic Hamper"}],
    )

    context, count = fm.build_feedback_context(CONTACT)
    assert count == 1
    assert "REJECTED" in context
    assert "cricket" in context.lower()
    assert "Generic Hamper" in context

    summary = fm.get_learning_summary(CONTACT)
    assert summary["historical_feedback_applied"] is True
    assert summary["last_action"] == "reject"


def test_approve_feedback_recorded(monkeypatch, tmp_path):
    feedback_file = tmp_path / "feedback_memory.json"
    monkeypatch.setattr(fm, "FEEDBACK_FILE", feedback_file)
    monkeypatch.setattr(fm, "DATA_DIR", tmp_path)

    fm.save_feedback(CONTACT, "run-2", "approve", notes="Cricket bat was perfect")
    context, _ = fm.build_feedback_context(CONTACT)
    assert "APPROVED" in context
    assert "Cricket bat was perfect" in context


def test_empty_contact_has_no_context(monkeypatch, tmp_path):
    feedback_file = tmp_path / "feedback_memory.json"
    monkeypatch.setattr(fm, "FEEDBACK_FILE", feedback_file)
    monkeypatch.setattr(fm, "DATA_DIR", tmp_path)

    context, count = fm.build_feedback_context({"name": "Nobody", "company": "Nowhere"})
    assert context == ""
    assert count == 0
