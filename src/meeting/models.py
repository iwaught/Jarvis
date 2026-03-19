"""Data models used throughout the meeting assistant feature."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class MeetingParticipant:
    """Represents a single meeting participant.

    Attributes:
        name: Full name of the participant.  Empty string when unknown.
        identified: Whether the participant was automatically identified.
    """

    name: str = ""
    identified: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ActionItem:
    """Represents a single actionable item extracted from a meeting.

    Attributes:
        description: What needs to be done.
        assignee: Person responsible.  Empty string when unknown.
        priority: One of 'high', 'medium', 'low'.
        due_date: Optional ISO-formatted due date string.
    """

    description: str
    assignee: str = ""
    priority: str = "medium"
    due_date: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MeetingNotes:
    """Structured output produced by the meeting assistant.

    Attributes:
        date: ISO-formatted timestamp of when the meeting was recorded.
        duration_seconds: Total recording duration in seconds.
        participants: List of identified (or blank) participants.
        transcript: Full speech-to-text transcript of the meeting.
        summary_points: High-level summary bullet points.
        action_items: Ordered list of actionable items.
    """

    date: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_seconds: float = 0.0
    participants: List[MeetingParticipant] = field(default_factory=list)
    transcript: str = ""
    summary_points: List[str] = field(default_factory=list)
    action_items: List[ActionItem] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Serialisation helpers                                                #
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "duration_seconds": self.duration_seconds,
            "participants": [p.to_dict() for p in self.participants],
            "transcript": self.transcript,
            "summary_points": self.summary_points,
            "action_items": [a.to_dict() for a in self.action_items],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save_json(self, path: str) -> None:
        """Write notes as a JSON file to *path*."""
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_json())

    def save_text(self, path: str) -> None:
        """Write notes as a human-readable text file to *path*."""
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_text())

    def to_text(self) -> str:
        """Return a human-readable representation of the meeting notes."""
        lines: List[str] = []
        lines.append("=" * 60)
        lines.append("MEETING NOTES – JARVIS")
        lines.append("=" * 60)
        lines.append(f"Date       : {self.date}")
        lines.append(f"Duration   : {self.duration_seconds:.1f}s")
        lines.append("")

        lines.append("PARTICIPANTS")
        lines.append("-" * 40)
        if self.participants:
            for i, p in enumerate(self.participants, start=1):
                label = p.name if p.identified and p.name else "(unknown)"
                lines.append(f"  {i}. {label}")
        else:
            lines.append("  (none identified)")
        lines.append("")

        lines.append("SUMMARY")
        lines.append("-" * 40)
        if self.summary_points:
            for point in self.summary_points:
                lines.append(f"  • {point}")
        else:
            lines.append("  (no summary available)")
        lines.append("")

        lines.append("ACTION ITEMS")
        lines.append("-" * 40)
        if self.action_items:
            for i, item in enumerate(self.action_items, start=1):
                assignee = item.assignee if item.assignee else "TBD"
                due = f" (due: {item.due_date})" if item.due_date else ""
                lines.append(
                    f"  {i}. [{item.priority.upper()}] {item.description}"
                    f" — {assignee}{due}"
                )
        else:
            lines.append("  (no action items)")
        lines.append("")

        lines.append("TRANSCRIPT")
        lines.append("-" * 40)
        lines.append(self.transcript or "(no transcript)")
        lines.append("=" * 60)
        return "\n".join(lines)
