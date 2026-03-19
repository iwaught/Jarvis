"""Notes generator module.

Transforms a raw meeting transcript into a concise list of summary bullet
points.  The module ships with two backends:

* **simple** (default) – Heuristic sentence scoring: longer sentences that
  contain key topic signals are promoted.  No external dependencies.
* **openai** – Calls the OpenAI Chat Completions API to produce high-quality
  summaries.  Requires an API key in ``config.yaml`` or the environment
  variable ``OPENAI_API_KEY``.
"""

from __future__ import annotations

import logging
import os
import re
import textwrap
from typing import List

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Keyword signals that indicate an important sentence
# ---------------------------------------------------------------------------

_SIGNAL_WORDS = {
    "decide", "decided", "decision", "agree", "agreed", "agreement",
    "plan", "planned", "planning", "propose", "proposed", "proposal",
    "action", "task", "deadline", "milestone", "goal", "objective",
    "issue", "problem", "concern", "risk", "blocker",
    "next steps", "follow up", "follow-up", "must", "need", "should",
    "will", "would", "important", "critical", "priority",
    "review", "approve", "approved", "implement", "update", "report",
    "launch", "release", "schedule", "timeline",
}


class NotesGenerator:
    """Generate structured summary bullet points from a meeting transcript.

    Parameters
    ----------
    backend:
        ``'simple'`` or ``'openai'``.
    openai_api_key:
        OpenAI API key.  Overrides environment variable / config.
    max_points:
        Maximum number of summary bullet points to produce.
    min_sentence_length:
        Minimum character length for a sentence to be considered.
    """

    def __init__(
        self,
        backend: str = "simple",
        openai_api_key: str | None = None,
        max_points: int = 10,
        min_sentence_length: int = 30,
    ) -> None:
        self.backend = backend.lower()
        self.max_points = max_points
        self.min_sentence_length = min_sentence_length
        self._api_key = openai_api_key or os.environ.get("OPENAI_API_KEY", "")

        if self.backend == "openai" and not self._api_key:
            raise ValueError(
                "An OpenAI API key is required for the 'openai' backend.  "
                "Set the OPENAI_API_KEY environment variable or pass it "
                "as 'openai_api_key'."
            )

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def generate(self, transcript: str) -> List[str]:
        """Return a list of summary bullet points for *transcript*.

        Parameters
        ----------
        transcript:
            Full meeting transcript.

        Returns
        -------
        List[str]
            Bullet points (plain strings, no leading ``•`` character).
        """
        if not transcript or not transcript.strip():
            return []

        if self.backend == "openai":
            return self._generate_openai(transcript)
        return self._generate_simple(transcript)

    # ------------------------------------------------------------------ #
    # Simple heuristic backend                                             #
    # ------------------------------------------------------------------ #

    def _generate_simple(self, transcript: str) -> List[str]:
        sentences = self._split_sentences(transcript)
        scored = []
        for sentence in sentences:
            score = self._score_sentence(sentence)
            if score > 0:
                scored.append((score, sentence))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [s for _, s in scored[: self.max_points]]
        # Re-order by original appearance for readability
        order = {s: i for i, s in enumerate(sentences)}
        top.sort(key=lambda s: order.get(s, 0))
        return [textwrap.shorten(s, width=200, placeholder=" …") for s in top]

    def _split_sentences(self, text: str) -> List[str]:
        """Split *text* into individual sentences, stripping speaker labels."""
        # Remove speaker labels like "John:" or "Speaker 1:"
        text = re.sub(r"^\s*[A-Z][a-zA-Z\s]{1,30}:\s*", "", text, flags=re.MULTILINE)
        # Split on sentence-ending punctuation
        raw = re.split(r"(?<=[.!?])\s+", text.strip())
        cleaned = []
        for s in raw:
            s = s.strip()
            if len(s) >= self.min_sentence_length:
                cleaned.append(s)
        return cleaned

    def _score_sentence(self, sentence: str) -> int:
        """Return a relevance score for *sentence* (higher = more relevant)."""
        lower = sentence.lower()
        score = 0
        for word in _SIGNAL_WORDS:
            if word in lower:
                score += 1
        return score

    # ------------------------------------------------------------------ #
    # OpenAI backend                                                       #
    # ------------------------------------------------------------------ #

    def _generate_openai(self, transcript: str) -> List[str]:
        try:
            import openai  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required for the 'openai' backend. "
                "Install it with:  pip install openai"
            ) from exc

        client = openai.OpenAI(api_key=self._api_key)
        prompt = (
            "You are a meeting assistant.  Analyse the following meeting "
            "transcript and produce a concise list of up to "
            f"{self.max_points} bullet-point summary items.  "
            "Return ONLY the bullet points, one per line, without numbers "
            "or leading dashes.\n\nTranscript:\n" + transcript
        )
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content: str = response.choices[0].message.content or ""
        points = [line.strip().lstrip("-•* ") for line in content.splitlines()]
        return [p for p in points if p][: self.max_points]
