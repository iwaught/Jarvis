"""Meeting assistant orchestrator.

:class:`MeetingAssistant` is the top-level class that ties together all
the sub-modules:

* :class:`~audio_processor.AudioProcessor` – audio capture / transcription
* :class:`~participant_identifier.ParticipantIdentifier` – name detection
* :class:`~notes_generator.NotesGenerator` – summary bullet points
* :class:`~action_items_extractor.ActionItemsExtractor` – task extraction

Typical usage
-------------
.. code-block:: python

    from src.meeting import MeetingAssistant

    assistant = MeetingAssistant()

    # Record live meeting (blocks until Ctrl-C or max_duration reached)
    notes = assistant.run_live(max_duration=3600)

    # … or process a pre-recorded file
    notes = assistant.run_from_file("path/to/meeting.wav")

    # Save the results
    notes.save_json("output/meeting_notes.json")
    notes.save_text("output/meeting_notes.txt")
    print(notes.to_text())
"""

from __future__ import annotations

import logging
from typing import List, Optional

from .action_items_extractor import ActionItemsExtractor
from .audio_processor import AudioProcessor
from .models import ActionItem, MeetingNotes, MeetingParticipant
from .notes_generator import NotesGenerator
from .participant_identifier import ParticipantIdentifier

logger = logging.getLogger(__name__)


class MeetingAssistant:
    """Orchestrates the full meeting-capture pipeline.

    Parameters
    ----------
    audio_backend:
        Speech-to-text backend (``'google'``, ``'whisper'``, ``'file'``).
    notes_backend:
        Notes / summary backend (``'simple'`` or ``'openai'``).
    action_items_backend:
        Action-items backend (``'simple'`` or ``'openai'``).
    language:
        BCP-47 language tag passed to the audio processor.
    known_participants:
        Pre-seeded list of participant names.
    openai_api_key:
        OpenAI API key used by the ``'openai'`` backends.
    whisper_model:
        Whisper model size.  Ignored unless *audio_backend* is ``'whisper'``.
    """

    def __init__(
        self,
        audio_backend: str = "google",
        notes_backend: str = "simple",
        action_items_backend: str = "simple",
        language: str = "en-US",
        known_participants: Optional[List[str]] = None,
        openai_api_key: Optional[str] = None,
        whisper_model: str = "base",
    ) -> None:
        # Store audio parameters for lazy initialisation (audio is only needed
        # for run_live / run_from_file, not for run_from_transcript).
        self._audio_backend = audio_backend
        self._audio_language = language
        self._whisper_model = whisper_model
        self._audio: Optional[AudioProcessor] = None

        self._identifier = ParticipantIdentifier(
            known_participants=known_participants
        )
        self._notes = NotesGenerator(
            backend=notes_backend,
            openai_api_key=openai_api_key,
        )
        self._actions = ActionItemsExtractor(
            backend=action_items_backend,
            openai_api_key=openai_api_key,
        )

    def _get_audio(self) -> AudioProcessor:
        """Return the :class:`AudioProcessor`, creating it on first access."""
        if self._audio is None:
            self._audio = AudioProcessor(
                backend=self._audio_backend,
                language=self._audio_language,
                whisper_model=self._whisper_model,
            )
        return self._audio

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def run_live(self, max_duration: int = 3600) -> MeetingNotes:
        """Record from the microphone and process the meeting.

        Parameters
        ----------
        max_duration:
            Maximum recording time in seconds.

        Returns
        -------
        MeetingNotes
            Fully populated meeting notes object.
        """
        logger.info("Starting live meeting capture (max %ds) …", max_duration)
        transcript, duration = self._get_audio().listen_continuous(max_duration=max_duration)
        return self._process(transcript, duration)

    def run_from_file(self, path: str) -> MeetingNotes:
        """Load a pre-recorded audio file and process the meeting.

        Parameters
        ----------
        path:
            Filesystem path to the audio file (WAV or MP3).

        Returns
        -------
        MeetingNotes
            Fully populated meeting notes object.
        """
        logger.info("Processing audio file: %s", path)
        transcript = self._get_audio().transcribe_file(path)
        return self._process(transcript, duration=0.0)

    def run_from_transcript(self, transcript: str) -> MeetingNotes:
        """Process an already-transcribed text (no audio required).

        Useful for testing or when the transcript is produced by a
        third-party service.

        Parameters
        ----------
        transcript:
            Plain-text meeting transcript.

        Returns
        -------
        MeetingNotes
            Fully populated meeting notes object.
        """
        return self._process(transcript, duration=0.0)

    # ------------------------------------------------------------------ #
    # Internal pipeline                                                    #
    # ------------------------------------------------------------------ #

    def _process(self, transcript: str, duration: float) -> MeetingNotes:
        """Run the full analysis pipeline on *transcript*."""
        logger.info("Identifying participants …")
        participants = self._identifier.identify(transcript)

        # Update the action-items extractor with the discovered participants
        self._actions.set_participants(participants)

        logger.info("Generating summary notes …")
        summary_points = self._notes.generate(transcript)

        logger.info("Extracting action items …")
        action_items = self._actions.extract(transcript)

        # If any participant was NOT identified, prepend a high-priority
        # action item to complete the participant list.
        unknown_count = sum(1 for p in participants if not p.identified)
        if unknown_count > 0:
            complete_participants = ActionItem(
                description=(
                    "Complete the list of meeting participants "
                    f"({unknown_count} unknown participant(s) detected)."
                ),
                assignee="",
                priority="high",
                due_date="",
            )
            action_items.insert(0, complete_participants)

        notes = MeetingNotes(
            duration_seconds=duration,
            participants=participants,
            transcript=transcript,
            summary_points=summary_points,
            action_items=action_items,
        )
        logger.info("Meeting processing complete.")
        return notes
