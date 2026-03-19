"""Tests for the MeetingAssistant orchestrator."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.meeting.meeting_assistant import MeetingAssistant
from src.meeting.models import MeetingNotes


SAMPLE_TRANSCRIPT = (
    "David: Good morning everyone. My name is David and I'll chair today's meeting.\n"
    "Eva: Hi, I'm Eva from the product team.\n"
    "David: Great. We need to review the Q1 roadmap and decide on priorities.\n"
    "Eva: I will prepare the roadmap document and share it with the team by Wednesday.\n"
    "David: Action item: schedule a follow-up meeting next week.\n"
    "Eva: Agreed. We must also update the stakeholder report before Friday.\n"
    "David: Perfect. Let's wrap up."
)


class TestMeetingAssistant:
    def _assistant(self, **kwargs):
        """Create a MeetingAssistant with a mocked AudioProcessor."""
        with patch("src.meeting.meeting_assistant.AudioProcessor"):
            return MeetingAssistant(**kwargs)

    def test_run_from_transcript_returns_meeting_notes(self):
        assistant = self._assistant()
        notes = assistant.run_from_transcript(SAMPLE_TRANSCRIPT)
        assert isinstance(notes, MeetingNotes)

    def test_participants_detected(self):
        assistant = self._assistant()
        notes = assistant.run_from_transcript(SAMPLE_TRANSCRIPT)
        names = [p.name for p in notes.participants]
        assert "David" in names
        assert "Eva" in names

    def test_action_items_extracted(self):
        assistant = self._assistant()
        notes = assistant.run_from_transcript(SAMPLE_TRANSCRIPT)
        assert len(notes.action_items) >= 1

    def test_summary_points_generated(self):
        assistant = self._assistant()
        notes = assistant.run_from_transcript(SAMPLE_TRANSCRIPT)
        assert isinstance(notes.summary_points, list)

    def test_transcript_preserved(self):
        assistant = self._assistant()
        notes = assistant.run_from_transcript(SAMPLE_TRANSCRIPT)
        assert notes.transcript == SAMPLE_TRANSCRIPT

    def test_unknown_participant_triggers_action_item(self):
        """When not all participants can be identified, the first action item
        should be to complete the participant list."""
        # Use a transcript with NO names so at least one participant is unknown
        assistant = self._assistant()
        notes = assistant.run_from_transcript(
            "We need to decide on the budget allocation for this quarter."
        )
        # There should be no identified participants, so the complete-list
        # action item should be prepended.
        assert len(notes.action_items) >= 1
        first_desc = notes.action_items[0].description.lower()
        assert "participant" in first_desc

    def test_known_participants_pre_seeded(self):
        assistant = self._assistant(known_participants=["Zara"])
        notes = assistant.run_from_transcript("We will review the project plan.")
        names = [p.name for p in notes.participants]
        assert "Zara" in names

    def test_run_from_file_calls_transcribe(self, tmp_path):
        """run_from_file should delegate to AudioProcessor.transcribe_file."""
        audio_file = tmp_path / "meeting.wav"
        audio_file.write_bytes(b"RIFF")  # dummy file

        with patch("src.meeting.meeting_assistant.AudioProcessor") as MockAudio:
            instance = MockAudio.return_value
            instance.transcribe_file.return_value = SAMPLE_TRANSCRIPT
            assistant = MeetingAssistant()
            notes = assistant.run_from_file(str(audio_file))

        instance.transcribe_file.assert_called_once_with(str(audio_file))
        assert isinstance(notes, MeetingNotes)

    def test_empty_transcript_produces_valid_notes(self):
        assistant = self._assistant()
        notes = assistant.run_from_transcript("")
        assert isinstance(notes, MeetingNotes)
        assert notes.summary_points == []
