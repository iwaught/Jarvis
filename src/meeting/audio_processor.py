"""Audio processing module: captures audio and converts it to text.

Supported backends
------------------
* ``google``  – Uses the free Google Speech Recognition API via the
                *SpeechRecognition* library.  Requires internet access.
* ``whisper`` – Uses OpenAI's open-source Whisper model running locally.
                Requires ``openai-whisper`` and ``ffmpeg`` to be installed.
* ``file``    – Loads a pre-recorded WAV/MP3 file instead of the microphone.
                Useful for testing and batch processing.

The :class:`AudioProcessor` is intentionally kept thin so it can be
swapped or mocked easily in tests.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

_SPEECH_RECOGNITION_AVAILABLE = False
_WHISPER_AVAILABLE = False

try:
    import speech_recognition as sr  # type: ignore

    _SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    pass

try:
    import whisper  # type: ignore

    _WHISPER_AVAILABLE = True
except ImportError:
    pass


class AudioProcessor:
    """Captures audio from a microphone (or file) and converts it to text.

    Parameters
    ----------
    backend:
        Speech-to-text backend to use (``'google'``, ``'whisper'``, or
        ``'file'``).
    language:
        BCP-47 language code used by the selected backend (e.g.
        ``'en-US'``, ``'es-ES'``).
    audio_file:
        Path to an audio file.  Required when *backend* is ``'file'``.
    whisper_model:
        Whisper model size (``'tiny'``, ``'base'``, ``'small'``, …).
        Only used when *backend* is ``'whisper'``.
    timeout:
        Seconds to wait for audio input before giving up.
    phrase_time_limit:
        Maximum seconds of audio to capture per phrase.
    """

    def __init__(
        self,
        backend: str = "google",
        language: str = "en-US",
        audio_file: Optional[str] = None,
        whisper_model: str = "base",
        timeout: int = 10,
        phrase_time_limit: Optional[int] = None,
    ) -> None:
        self.backend = backend.lower()
        self.language = language
        self.audio_file = audio_file
        self.whisper_model = whisper_model
        self.timeout = timeout
        self.phrase_time_limit = phrase_time_limit

        self._recognizer = None
        self._whisper_model_instance = None

        if self.backend in ("google", "file"):
            if not _SPEECH_RECOGNITION_AVAILABLE:
                raise ImportError(
                    "The 'SpeechRecognition' package is required for this backend. "
                    "Install it with:  pip install SpeechRecognition"
                )
            self._recognizer = sr.Recognizer()  # type: ignore[attr-defined]

        elif self.backend == "whisper":
            if not _WHISPER_AVAILABLE:
                raise ImportError(
                    "The 'openai-whisper' package is required for this backend. "
                    "Install it with:  pip install openai-whisper"
                )
            logger.info("Loading Whisper model '%s' …", whisper_model)
            self._whisper_model_instance = whisper.load_model(whisper_model)  # type: ignore[attr-defined]

        else:
            raise ValueError(
                f"Unknown backend '{backend}'. Choose 'google', 'whisper', or 'file'."
            )

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def transcribe_file(self, path: str) -> str:
        """Return the full transcript of an audio *file* at *path*.

        Parameters
        ----------
        path:
            Filesystem path to a WAV or MP3 file.

        Returns
        -------
        str
            Transcribed text, or an empty string on failure.
        """
        if self.backend == "whisper":
            return self._transcribe_with_whisper(path)
        return self._transcribe_file_with_sr(path)

    def listen_and_transcribe(self) -> tuple[str, float]:
        """Listen from the microphone until silence and return ``(text, duration)``.

        Returns
        -------
        tuple[str, float]
            The transcribed text and the recording duration in seconds.
        """
        if self.backend == "whisper":
            return self._listen_whisper()
        return self._listen_sr()

    def listen_continuous(self, max_duration: int = 3600) -> tuple[str, float]:
        """Record continuously for up to *max_duration* seconds.

        Keeps appending recognised phrases until the time limit is reached or
        the user interrupts with Ctrl-C.

        Returns
        -------
        tuple[str, float]
            Full concatenated transcript and total duration in seconds.
        """
        parts: list[str] = []
        start = time.time()
        logger.info("Recording for up to %d seconds … (Ctrl-C to stop)", max_duration)
        try:
            while (time.time() - start) < max_duration:
                text, _ = self.listen_and_transcribe()
                if text:
                    parts.append(text)
        except KeyboardInterrupt:
            logger.info("Recording stopped by user.")
        duration = time.time() - start
        return " ".join(parts), duration

    # ------------------------------------------------------------------ #
    # Internal helpers – SpeechRecognition                                 #
    # ------------------------------------------------------------------ #

    def _listen_sr(self) -> tuple[str, float]:
        import speech_recognition as sr  # type: ignore

        start = time.time()
        with sr.Microphone() as source:  # type: ignore[attr-defined]
            logger.info("Adjusting for ambient noise …")
            self._recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.info("Listening …")
            audio = self._recognizer.listen(
                source,
                timeout=self.timeout,
                phrase_time_limit=self.phrase_time_limit,
            )
        duration = time.time() - start
        text = self._recognise_sr(audio)
        return text, duration

    def _transcribe_file_with_sr(self, path: str) -> str:
        import speech_recognition as sr  # type: ignore

        with sr.AudioFile(path) as source:  # type: ignore[attr-defined]
            audio = self._recognizer.record(source)
        return self._recognise_sr(audio)

    def _recognise_sr(self, audio) -> str:  # type: ignore[type-arg]
        import speech_recognition as sr  # type: ignore

        try:
            text: str = self._recognizer.recognize_google(audio, language=self.language)
            return text
        except sr.UnknownValueError:
            logger.warning("Speech not understood.")
            return ""
        except sr.RequestError as exc:
            logger.error("Google Speech API error: %s", exc)
            return ""

    # ------------------------------------------------------------------ #
    # Internal helpers – Whisper                                           #
    # ------------------------------------------------------------------ #

    def _transcribe_with_whisper(self, path: str) -> str:
        result = self._whisper_model_instance.transcribe(path)  # type: ignore[union-attr]
        return result.get("text", "").strip()

    def _listen_whisper(self) -> tuple[str, float]:
        """Capture one phrase from the microphone and transcribe with Whisper."""
        import speech_recognition as sr  # type: ignore

        if not _SPEECH_RECOGNITION_AVAILABLE:
            raise ImportError("SpeechRecognition is needed for microphone capture.")

        recognizer = sr.Recognizer()  # type: ignore[attr-defined]
        start = time.time()
        with sr.Microphone() as source:  # type: ignore[attr-defined]
            recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.info("Listening (Whisper backend) …")
            audio = recognizer.listen(
                source,
                timeout=self.timeout,
                phrase_time_limit=self.phrase_time_limit,
            )
        duration = time.time() - start
        wav_bytes = audio.get_wav_data()
        with open("/tmp/_jarvis_audio_tmp.wav", "wb") as fh:
            fh.write(wav_bytes)
        text = self._transcribe_with_whisper("/tmp/_jarvis_audio_tmp.wav")
        return text, duration
