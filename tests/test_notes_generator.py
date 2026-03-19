"""Tests for the NotesGenerator module."""

from __future__ import annotations

import pytest

from src.meeting.notes_generator import NotesGenerator


class TestNotesGeneratorSimple:
    def _gen(self, **kwargs):
        return NotesGenerator(backend="simple", **kwargs)

    def test_empty_transcript_returns_empty(self):
        gen = self._gen()
        assert gen.generate("") == []

    def test_whitespace_only_returns_empty(self):
        gen = self._gen()
        assert gen.generate("   \n  ") == []

    def test_returns_list_of_strings(self):
        gen = self._gen()
        transcript = (
            "We decided to move the deadline to next Friday. "
            "John will prepare the report and submit it by Monday. "
            "The team agreed to review the design documents before the launch."
        )
        result = gen.generate(transcript)
        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)

    def test_signal_words_increase_inclusion(self):
        gen = self._gen(max_points=5)
        transcript = (
            "The weather was fine today. "
            "We agreed to deploy the new feature by next Wednesday. "
            "Everyone had coffee. "
            "The team decided to schedule a follow-up review."
        )
        result = gen.generate(transcript)
        combined = " ".join(result).lower()
        assert "deploy" in combined or "review" in combined or "agreed" in combined

    def test_respects_max_points(self):
        gen = self._gen(max_points=2)
        transcript = " ".join(
            [
                f"We will complete task {i} before the deadline."
                for i in range(20)
            ]
        )
        result = gen.generate(transcript)
        assert len(result) <= 2

    def test_strips_speaker_labels(self):
        gen = self._gen()
        transcript = (
            "Alice: We need to decide on the project plan.\n"
            "Bob: Agreed. We must submit the report by Friday."
        )
        result = gen.generate(transcript)
        # No result should start with "Alice:" or "Bob:"
        for point in result:
            assert not point.startswith("Alice:")
            assert not point.startswith("Bob:")

    def test_short_sentences_excluded(self):
        gen = self._gen(min_sentence_length=50)
        transcript = "Ok. Yes. No. We decided to change the whole project plan next month."
        result = gen.generate(transcript)
        # Short interjections should not appear
        for point in result:
            assert len(point) >= 10  # at least somewhat substantive

    def test_openai_backend_requires_key(self):
        with pytest.raises(ValueError, match="API key"):
            NotesGenerator(backend="openai", openai_api_key=None)
