"""Tests for the MeetingParticipant, ActionItem, and MeetingNotes data models."""

from __future__ import annotations

import json

import pytest

from src.meeting.models import ActionItem, MeetingNotes, MeetingParticipant


class TestMeetingParticipant:
    def test_defaults(self):
        p = MeetingParticipant()
        assert p.name == ""
        assert p.identified is False

    def test_identified_participant(self):
        p = MeetingParticipant(name="Alice Smith", identified=True)
        assert p.name == "Alice Smith"
        assert p.identified is True

    def test_to_dict(self):
        p = MeetingParticipant(name="Bob", identified=True)
        d = p.to_dict()
        assert d == {"name": "Bob", "identified": True}


class TestActionItem:
    def test_defaults(self):
        item = ActionItem(description="Send the report")
        assert item.assignee == ""
        assert item.priority == "medium"
        assert item.due_date == ""

    def test_full_item(self):
        item = ActionItem(
            description="Review the design",
            assignee="Alice",
            priority="high",
            due_date="by Friday",
        )
        d = item.to_dict()
        assert d["description"] == "Review the design"
        assert d["assignee"] == "Alice"
        assert d["priority"] == "high"
        assert d["due_date"] == "by Friday"


class TestMeetingNotes:
    def _sample_notes(self) -> MeetingNotes:
        return MeetingNotes(
            date="2024-01-01T10:00:00",
            duration_seconds=600.0,
            participants=[
                MeetingParticipant(name="Alice", identified=True),
                MeetingParticipant(name="", identified=False),
            ],
            transcript="Alice: We need to send the report by Friday.",
            summary_points=["Discussed the Q1 report deadline."],
            action_items=[
                ActionItem(
                    description="Complete participant list",
                    priority="high",
                ),
                ActionItem(
                    description="Send the report",
                    assignee="Alice",
                    priority="medium",
                    due_date="by Friday",
                ),
            ],
        )

    def test_to_dict_structure(self):
        notes = self._sample_notes()
        d = notes.to_dict()
        assert "date" in d
        assert "participants" in d
        assert "action_items" in d
        assert len(d["participants"]) == 2
        assert len(d["action_items"]) == 2

    def test_to_json_valid(self):
        notes = self._sample_notes()
        raw = notes.to_json()
        parsed = json.loads(raw)
        assert parsed["duration_seconds"] == 600.0

    def test_save_json(self, tmp_path):
        notes = self._sample_notes()
        path = str(tmp_path / "meeting.json")
        notes.save_json(path)
        with open(path) as fh:
            parsed = json.load(fh)
        assert parsed["transcript"] == notes.transcript

    def test_save_text(self, tmp_path):
        notes = self._sample_notes()
        path = str(tmp_path / "meeting.txt")
        notes.save_text(path)
        with open(path) as fh:
            content = fh.read()
        assert "MEETING NOTES" in content
        assert "Alice" in content
        assert "Send the report" in content

    def test_to_text_unknown_participant(self):
        notes = self._sample_notes()
        text = notes.to_text()
        assert "(unknown)" in text

    def test_empty_notes(self):
        notes = MeetingNotes()
        text = notes.to_text()
        assert "(none identified)" in text
        assert "(no action items)" in text
