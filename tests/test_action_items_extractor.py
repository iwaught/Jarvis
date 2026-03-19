"""Tests for the ActionItemsExtractor module."""

from __future__ import annotations

import pytest

from src.meeting.action_items_extractor import ActionItemsExtractor
from src.meeting.models import MeetingParticipant


class TestActionItemsExtractorSimple:
    def _extractor(self, participants=None):
        return ActionItemsExtractor(
            backend="simple",
            known_participants=participants,
        )

    def test_empty_transcript_returns_empty(self):
        assert self._extractor().extract("") == []

    def test_modal_will_detected(self):
        transcript = "Alice will send the report to the team by Friday."
        items = self._extractor().extract(transcript)
        assert len(items) >= 1
        descriptions = [i.description.lower() for i in items]
        assert any("report" in d or "send" in d for d in descriptions)

    def test_assignee_extracted_from_modal(self):
        transcript = "Bob will prepare the presentation slides for Monday."
        items = self._extractor().extract(transcript)
        assert len(items) >= 1
        assert items[0].assignee == "Bob"

    def test_need_to_detected(self):
        transcript = "We need to review the contract before the deadline."
        items = self._extractor().extract(transcript)
        assert len(items) >= 1

    def test_must_detected(self):
        transcript = "The team must complete the testing phase by next week."
        items = self._extractor().extract(transcript)
        assert len(items) >= 1

    def test_explicit_action_item_phrase(self):
        transcript = "Action item: Schedule a follow-up meeting with the client."
        items = self._extractor().extract(transcript)
        assert len(items) >= 1

    def test_due_date_extracted(self):
        transcript = "Sarah will submit the budget report by Friday."
        items = self._extractor().extract(transcript)
        assert len(items) >= 1
        due_dates = [i.due_date for i in items]
        assert any("Friday" in d for d in due_dates)

    def test_urgency_sets_high_priority(self):
        transcript = "We urgently need to fix the production bug immediately."
        items = self._extractor().extract(transcript)
        assert len(items) >= 1
        assert items[0].priority == "high"

    def test_known_participant_matched_as_assignee(self):
        participants = [MeetingParticipant(name="Eve", identified=True)]
        extractor = self._extractor(participants=participants)
        transcript = "We need to send Eve the updated contract documents."
        items = extractor.extract(transcript)
        assignees = [i.assignee for i in items]
        assert "Eve" in assignees

    def test_deduplication(self):
        transcript = (
            "John will send the report. John will send the report."
        )
        items = self._extractor().extract(transcript)
        descriptions = [i.description.lower() for i in items]
        # Should not contain duplicates
        assert len(descriptions) == len(set(descriptions))

    def test_no_false_positives_for_plain_text(self):
        transcript = "The weather is nice. I enjoy coffee every morning."
        items = self._extractor().extract(transcript)
        assert items == []

    def test_openai_backend_requires_key(self):
        with pytest.raises(ValueError, match="API key"):
            ActionItemsExtractor(backend="openai", openai_api_key=None)
