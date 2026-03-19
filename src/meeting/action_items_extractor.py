"""Action-items extractor module.

Scans a meeting transcript for sentences that express a commitment, task,
or follow-up obligation and returns them as structured
:class:`~models.ActionItem` objects.

Detection strategy (simple backend)
-------------------------------------
* **Modal-verb patterns** – sentences containing modal verbs combined with
  task verbs (e.g. *"John will send the report"*, *"we need to review …"*).
* **Imperative patterns** – direct instructions (e.g. *"Send the email by
  Friday"*).
* **Explicit task phrases** – *"action item"*, *"to-do"*, *"follow up"*, etc.
* **Deadline signals** – *"by"* / *"before"* / *"until"* followed by a date
  or day name.

The extractor also attempts to identify the *assignee* (the person who owns
the task) and a *priority* (derived from urgency language).
"""

from __future__ import annotations

import logging
import os
import re
from typing import List, Optional, Tuple

from .models import ActionItem, MeetingParticipant

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

_TASK_VERBS = (
    "send|write|create|prepare|review|update|schedule|organise|organize|"
    "complete|finish|follow up|follow-up|implement|deploy|fix|resolve|"
    "contact|reach out|confirm|report|present|submit|add|remove|check|"
    "investigate|research|coordinate|discuss|share|provide|build|test|"
    "design|approve|merge|release|launch|document|notify|invite|define"
)

_MODAL_PATTERN = re.compile(
    rf"\b(?:will|shall|must|should|need(?:s)? to|has to|have to|is going to|"
    rf"are going to|going to)\b.{{0,80}}\b(?:{_TASK_VERBS})\b",
    re.IGNORECASE,
)

_IMPERATIVE_PATTERN = re.compile(
    rf"^(?:[A-Z][a-z]+,\s+)?(?:{_TASK_VERBS})\b",
    re.MULTILINE | re.IGNORECASE,
)

_EXPLICIT_TASK = re.compile(
    r"\b(?:action item|to-do|todo|follow[- ]up|next step|deliverable)\b",
    re.IGNORECASE,
)

_DEADLINE = re.compile(
    r"\bby\s+(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
    r"|(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?|\d{1,2}[/-]\d{1,2}"
    r"(?:[/-]\d{2,4})?)\b",
    re.IGNORECASE,
)

_URGENCY = re.compile(
    r"\b(?:urgent|urgently|immediately|asap|as soon as possible|"
    r"critical|high priority|right away)\b",
    re.IGNORECASE,
)

# Matches "John will …", "Sarah needs to …" to extract assignee
_ASSIGNEE_PATTERN = re.compile(
    r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:will|shall|must|should|needs? to|"
    r"has to|is going to)\b",
)


class ActionItemsExtractor:
    """Extract actionable items from a meeting transcript.

    Parameters
    ----------
    backend:
        ``'simple'`` (heuristic) or ``'openai'``.
    known_participants:
        List of participant names used to improve assignee detection.
    openai_api_key:
        OpenAI API key.  Only used when *backend* is ``'openai'``.
    """

    def __init__(
        self,
        backend: str = "simple",
        known_participants: Optional[List[MeetingParticipant]] = None,
        openai_api_key: Optional[str] = None,
    ) -> None:
        self.backend = backend.lower()
        self._participants: List[str] = [
            p.name for p in (known_participants or []) if p.name
        ]
        self._api_key = openai_api_key or os.environ.get("OPENAI_API_KEY", "")

        if self.backend == "openai" and not self._api_key:
            raise ValueError(
                "An OpenAI API key is required for the 'openai' backend.  "
                "Set the OPENAI_API_KEY environment variable."
            )

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def set_participants(self, participants: List[MeetingParticipant]) -> None:
        """Update the list of known participants used for assignee detection.

        Parameters
        ----------
        participants:
            New list of participants.  Only named (identified) participants
            are stored.
        """
        self._participants = [p.name for p in participants if p.name]

    def extract(self, transcript: str) -> List[ActionItem]:
        """Return a list of action items found in *transcript*.

        Parameters
        ----------
        transcript:
            Full meeting transcript.

        Returns
        -------
        List[ActionItem]
            Deduplicated list of action items in order of appearance.
        """
        if not transcript or not transcript.strip():
            return []
        if self.backend == "openai":
            return self._extract_openai(transcript)
        return self._extract_simple(transcript)

    # ------------------------------------------------------------------ #
    # Simple heuristic backend                                             #
    # ------------------------------------------------------------------ #

    def _extract_simple(self, transcript: str) -> List[ActionItem]:
        sentences = self._split_sentences(transcript)
        items: List[ActionItem] = []
        seen: set[str] = set()

        for sentence in sentences:
            if not self._is_action_sentence(sentence):
                continue
            key = sentence.lower().strip()
            if key in seen:
                continue
            seen.add(key)

            assignee = self._extract_assignee(sentence)
            priority = "high" if _URGENCY.search(sentence) else "medium"
            due_date = self._extract_due_date(sentence)
            description = self._clean_description(sentence)

            items.append(
                ActionItem(
                    description=description,
                    assignee=assignee,
                    priority=priority,
                    due_date=due_date,
                )
            )
        return items

    def _is_action_sentence(self, sentence: str) -> bool:
        return bool(
            _MODAL_PATTERN.search(sentence)
            or _EXPLICIT_TASK.search(sentence)
            or _IMPERATIVE_PATTERN.match(sentence)
        )

    def _extract_assignee(self, sentence: str) -> str:
        # Try the grammar pattern first ("John will …")
        m = _ASSIGNEE_PATTERN.match(sentence.strip())
        if m:
            candidate = m.group(1)
            if candidate.lower() not in {"we", "i", "they", "you", "it"}:
                return candidate

        # Fall back to matching a known participant name in the sentence
        lower = sentence.lower()
        for name in self._participants:
            if name and name.lower() in lower:
                return name
        return ""

    @staticmethod
    def _extract_due_date(sentence: str) -> str:
        m = _DEADLINE.search(sentence)
        return m.group(0).strip() if m else ""

    @staticmethod
    def _clean_description(sentence: str) -> str:
        """Remove speaker labels and normalise whitespace."""
        cleaned = re.sub(r"^\s*[A-Z][a-zA-Z\s]{1,30}:\s*", "", sentence)
        return cleaned.strip()

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        raw = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in raw if len(s.strip()) > 15]

    # ------------------------------------------------------------------ #
    # OpenAI backend                                                       #
    # ------------------------------------------------------------------ #

    def _extract_openai(self, transcript: str) -> List[ActionItem]:
        try:
            import openai  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required for the 'openai' backend. "
                "Install it with:  pip install openai"
            ) from exc

        import json

        client = openai.OpenAI(api_key=self._api_key)
        participants_hint = (
            f"Known participants: {', '.join(self._participants)}." if self._participants else ""
        )
        prompt = (
            "You are a meeting assistant.  Extract all action items from the "
            "following meeting transcript.  "
            f"{participants_hint}  "
            "Return ONLY a JSON array where each element has the keys: "
            "'description' (string), 'assignee' (string, empty if unknown), "
            "'priority' ('high', 'medium', or 'low'), 'due_date' (string, "
            "empty if not mentioned).\n\nTranscript:\n" + transcript
        )
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content: str = response.choices[0].message.content or "[]"
        # Strip markdown code fences if present
        content = re.sub(r"^```(?:json)?\s*", "", content.strip())
        content = re.sub(r"\s*```$", "", content)
        try:
            raw_items = json.loads(content)
        except json.JSONDecodeError:
            logger.error("Failed to parse OpenAI response as JSON: %s", content[:200])
            return []
        return [
            ActionItem(
                description=item.get("description", ""),
                assignee=item.get("assignee", ""),
                priority=item.get("priority", "medium"),
                due_date=item.get("due_date", ""),
            )
            for item in raw_items
            if item.get("description")
        ]
