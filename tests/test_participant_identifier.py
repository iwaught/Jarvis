"""Tests for the ParticipantIdentifier module."""

from __future__ import annotations

import pytest

from src.meeting.participant_identifier import ParticipantIdentifier


class TestParticipantIdentifier:
    def _identifier(self, known=None):
        return ParticipantIdentifier(known_participants=known)

    # ------------------------------------------------------------------ #
    # Introduction patterns                                                #
    # ------------------------------------------------------------------ #

    def test_intro_im(self):
        transcript = "Hi everyone, I'm Alice and I'll be leading today's meeting."
        participants = self._identifier().identify(transcript)
        names = [p.name for p in participants]
        assert "Alice" in names

    def test_intro_my_name_is(self):
        transcript = "Good morning. My name is Bob Johnson and I work in finance."
        participants = self._identifier().identify(transcript)
        names = [p.name for p in participants]
        assert "Bob Johnson" in names

    def test_intro_this_is(self):
        transcript = "Hello, this is Carol speaking from the engineering team."
        participants = self._identifier().identify(transcript)
        names = [p.name for p in participants]
        assert "Carol" in names

    # ------------------------------------------------------------------ #
    # Speaker-label patterns                                               #
    # ------------------------------------------------------------------ #

    def test_speaker_label(self):
        transcript = (
            "David: Good morning everyone.\n"
            "Eva: Thanks for joining, David.\n"
            "David: Let's begin with the agenda."
        )
        participants = self._identifier().identify(transcript)
        names = [p.name for p in participants]
        assert "David" in names
        assert "Eva" in names

    # ------------------------------------------------------------------ #
    # Addressing patterns                                                  #
    # ------------------------------------------------------------------ #

    def test_addressing_pattern(self):
        transcript = "Frank, could you share the latest numbers with the team?"
        participants = self._identifier().identify(transcript)
        names = [p.name for p in participants]
        assert "Frank" in names

    # ------------------------------------------------------------------ #
    # Pre-seeded known participants                                        #
    # ------------------------------------------------------------------ #

    def test_known_participants_always_included(self):
        participants = self._identifier(known=["Grace"]).identify(
            "No names mentioned here."
        )
        names = [p.name for p in participants]
        assert "Grace" in names

    def test_all_known_participants_identified_true(self):
        participants = self._identifier(known=["Henry"]).identify("")
        assert all(p.identified for p in participants if p.name == "Henry")

    # ------------------------------------------------------------------ #
    # Unknown participants                                                 #
    # ------------------------------------------------------------------ #

    def test_no_names_produces_blank_participant(self):
        participants = self._identifier().identify("The meeting was productive.")
        assert len(participants) == 1
        assert participants[0].name == ""
        assert participants[0].identified is False

    # ------------------------------------------------------------------ #
    # Deduplication                                                        #
    # ------------------------------------------------------------------ #

    def test_deduplication(self):
        transcript = (
            "I'm Alice, and I'm Alice again. Alice: Let's go."
        )
        participants = self._identifier().identify(transcript)
        names = [p.name for p in participants]
        # "Alice" should appear exactly once
        assert names.count("Alice") == 1

    # ------------------------------------------------------------------ #
    # False-positive prevention                                            #
    # ------------------------------------------------------------------ #

    def test_stopword_not_included(self):
        transcript = "Okay, let's start. Thanks, everyone."
        participants = self._identifier().identify(transcript)
        names = [p.name for p in participants]
        assert "Okay" not in names
        assert "Thanks" not in names

    def test_mixed_known_and_detected(self):
        transcript = "I'm Dave and I'll be presenting."
        participants = self._identifier(known=["Alice"]).identify(transcript)
        names = [p.name for p in participants]
        assert "Alice" in names
        assert "Dave" in names
