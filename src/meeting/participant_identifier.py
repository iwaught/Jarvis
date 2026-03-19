"""Participant identifier module.

Attempts to extract speaker names from a meeting transcript using simple
heuristics and pattern matching.  The module is intentionally kept free of
heavyweight ML dependencies so it works out of the box; it can be extended
with a diarisation service (e.g. pyannote-audio) or an LLM for better
accuracy.

Detection strategy
------------------
1. **Self-introduction patterns** – phrases like "I'm John", "my name is Jane",
   "this is Carlos speaking", "hi, I'm …".
2. **Addressing patterns** – phrases like "John, can you …", "thanks, Sarah".
3. **Speaker labels in transcripts** – lines starting with "Speaker 1:" or
   "John:" are parsed directly.

Unknown participants result in a :class:`~models.MeetingParticipant` with an
empty *name* and ``identified=False``.
"""

from __future__ import annotations

import logging
import re
from typing import List, Set

from .models import MeetingParticipant

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

# "I'm John", "I am Sarah", "I'm Sarah Connors"
_INTRO_IM = re.compile(
    r"\b(?:I'?m|I am)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b"
)

# "my name is John", "my name's Jane"
_INTRO_NAME = re.compile(
    r"\bmy name(?:'s| is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
    re.IGNORECASE,
)

# "this is John speaking", "this is Jane here"
_INTRO_THIS_IS = re.compile(
    r"\bthis is\s+"
    r"([A-Z][a-z]+"
    r"(?:\s+(?!(?:speaking|here|calling)\b)[A-Z][a-z]+)?)"
    r"\s*(?:speaking|here|calling)?\b",
    re.IGNORECASE,
)

# "Speaker N:" or "Name:" at line start (diarised / formatted transcripts)
_SPEAKER_LABEL = re.compile(
    r"^\s*([A-Z][a-zA-Z\s]{1,30}):\s",
    re.MULTILINE,
)

# Addressing: "John, could you …"  – capitalised first word before a comma
_ADDRESSING = re.compile(
    r"(?:^|[\.\?\!]\s+)([A-Z][a-z]+),\s",
    re.MULTILINE,
)

_STOPWORDS: Set[str] = {
    "Ok", "Okay", "Yes", "No", "Sure", "Well", "So", "Now",
    "Hi", "Hello", "Hey", "Thanks", "Thank", "Right", "Great",
    "Good", "Sorry", "Please", "Actually", "Also", "Today",
    "Tomorrow", "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday", "January", "February", "March",
    "April", "May", "June", "July", "August", "September", "October",
    "November", "December", "Speaker",
}

# Words that may not appear as the *last* word of a detected name
_TRAILING_STOPWORDS: Set[str] = {
    "And", "But", "Or", "If", "Is", "Was", "Are", "The", "A", "An",
    "In", "On", "At", "To", "Of", "For", "With", "By", "From",
    "Who", "Which", "That", "This", "These", "Those",
}


class ParticipantIdentifier:
    """Extract participant names from a meeting transcript.

    Parameters
    ----------
    known_participants:
        Optional pre-seeded list of names that are already known.
        These are added with ``identified=True`` without needing to appear
        in the transcript.
    """

    def __init__(self, known_participants: List[str] | None = None) -> None:
        self._known: List[str] = list(known_participants or [])

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def identify(self, transcript: str) -> List[MeetingParticipant]:
        """Parse *transcript* and return a deduplicated list of participants.

        Any pre-seeded known participants are always included.  Automatically
        detected names are added with ``identified=True``.  If *no* names
        are detected at all, a single placeholder participant with an empty
        name is added.

        Parameters
        ----------
        transcript:
            Full meeting transcript as a plain string.

        Returns
        -------
        List[MeetingParticipant]
            Deduplicated participant list, sorted alphabetically by name.
        """
        detected = self._extract_names(transcript)
        all_names: Set[str] = set(self._known) | detected

        participants: List[MeetingParticipant] = []
        for name in sorted(all_names):
            if name:
                participants.append(MeetingParticipant(name=name, identified=True))

        if not participants:
            logger.warning(
                "No participants identified.  Adding a blank placeholder."
            )
            participants.append(MeetingParticipant(name="", identified=False))

        return participants

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _extract_names(self, transcript: str) -> Set[str]:
        """Return all candidate names found in *transcript*."""
        names: Set[str] = set()

        for pattern in (_INTRO_IM, _INTRO_NAME, _INTRO_THIS_IS, _SPEAKER_LABEL, _ADDRESSING):
            for match in pattern.finditer(transcript):
                raw = match.group(1).strip()
                cleaned = self._clean_name(raw)
                if cleaned:
                    names.add(cleaned)

        return names

    @staticmethod
    def _clean_name(raw: str) -> str:
        """Normalise and validate a candidate name string."""
        # Title-case each word
        words = [w.capitalize() for w in raw.split()]
        # Strip trailing conjunctions / stopwords
        while words and words[-1] in _TRAILING_STOPWORDS:
            words.pop()
        if not words:
            return ""
        candidate = " ".join(words)
        # Reject obvious false-positives based on first word
        first_word = words[0]
        if first_word in _STOPWORDS:
            return ""
        # Must be between 1 and 5 words, each at least 2 chars
        if not (1 <= len(words) <= 5):
            return ""
        if any(len(w) < 2 for w in words):
            return ""
        return candidate
