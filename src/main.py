"""Jarvis entry point.

Run  ``python -m src.main --help``  for usage information.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# Add the repo root to the path so that ``src`` is importable both when
# running directly and when installed as a package.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.meeting import MeetingAssistant  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jarvis-meeting",
        description="Jarvis Meeting Assistant – capture, transcribe, and summarise meetings.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ---- live sub-command ---- #
    live = subparsers.add_parser("live", help="Record live from the microphone.")
    live.add_argument(
        "--duration",
        type=int,
        default=3600,
        metavar="SECONDS",
        help="Maximum recording duration in seconds (default: 3600).",
    )
    _add_common_args(live)

    # ---- file sub-command ---- #
    file_cmd = subparsers.add_parser("file", help="Process a pre-recorded audio file.")
    file_cmd.add_argument("path", help="Path to the audio file (WAV or MP3).")
    _add_common_args(file_cmd)

    # ---- transcript sub-command ---- #
    txt = subparsers.add_parser(
        "transcript",
        help="Process a plain-text transcript (no audio required).",
    )
    txt.add_argument("path", help="Path to the transcript text file.")
    _add_common_args(txt)

    return parser


def _add_common_args(sub: argparse.ArgumentParser) -> None:
    sub.add_argument(
        "--output",
        default="output/meeting_notes",
        help="Output file prefix (default: output/meeting_notes).",
    )
    sub.add_argument(
        "--audio-backend",
        default="google",
        choices=["google", "whisper"],
        help="Speech-to-text backend (default: google).",
    )
    sub.add_argument(
        "--notes-backend",
        default="simple",
        choices=["simple", "openai"],
        help="Notes/summary backend (default: simple).",
    )
    sub.add_argument(
        "--actions-backend",
        default="simple",
        choices=["simple", "openai"],
        help="Action-items backend (default: simple).",
    )
    sub.add_argument(
        "--language",
        default="en-US",
        help="BCP-47 language code (default: en-US).",
    )
    sub.add_argument(
        "--participants",
        nargs="*",
        metavar="NAME",
        help="Known participant names to pre-seed.",
    )
    sub.add_argument(
        "--openai-key",
        default=None,
        metavar="KEY",
        help="OpenAI API key (also read from OPENAI_API_KEY env var).",
    )


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    assistant = MeetingAssistant(
        audio_backend=args.audio_backend,
        notes_backend=args.notes_backend,
        action_items_backend=args.actions_backend,
        language=args.language,
        known_participants=args.participants or [],
        openai_api_key=args.openai_key,
    )

    if args.command == "live":
        notes = assistant.run_live(max_duration=args.duration)
    elif args.command == "file":
        notes = assistant.run_from_file(args.path)
    elif args.command == "transcript":
        with open(args.path, encoding="utf-8") as fh:
            text = fh.read()
        notes = assistant.run_from_transcript(text)
    else:
        parser.error(f"Unknown command: {args.command}")
        return  # unreachable – satisfies type checker

    # Save outputs
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    json_path = args.output + ".json"
    txt_path = args.output + ".txt"
    notes.save_json(json_path)
    notes.save_text(txt_path)
    print(notes.to_text())
    print(f"\nNotes saved to:  {json_path}")
    print(f"               {txt_path}")


if __name__ == "__main__":
    main()
