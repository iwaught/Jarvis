# Jarvis – Meeting Assistant Feature

## Setup & Usage Guide

---

### Overview

The **Meeting Assistant** module lets Jarvis:

1. **Listen** to a live meeting (microphone) or process a pre-recorded audio file.
2. **Transcribe** the audio to text using Google Speech Recognition (free) or Whisper (offline).
3. **Identify participants** automatically from the transcript.  Unknown participants result in a blank placeholder, and an action item to complete the list is automatically added.
4. **Generate structured meeting notes** – a concise list of key discussion points.
5. **Extract action items** – tasks, commitments, and follow-ups with assignees and due-dates.
6. **Save the output** as both JSON and human-readable text.

---

### Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | |
| `portaudio` library | Only for **live microphone** capture. `sudo apt-get install portaudio19-dev` (Linux) or `brew install portaudio` (macOS) |
| Internet access | Only for the default **Google Speech** backend |

---

### Installation

```bash
# Clone the repository
git clone https://github.com/iwaught/Jarvis.git
cd Jarvis

# (Recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

> **Note:** `PyAudio` is only required for live microphone capture.  If you are only processing audio files or plain-text transcripts you can skip it:
> ```bash
> pip install SpeechRecognition pytest pytest-cov
> ```

---

### Usage

Run the CLI from the project root:

```bash
python -m src.main <command> [options]
```

#### Commands

| Command | Description |
|---|---|
| `live` | Record from the microphone in real-time |
| `file` | Process a pre-recorded WAV or MP3 file |
| `transcript` | Analyse a plain-text transcript |

#### Common Options

| Option | Default | Description |
|---|---|---|
| `--output PREFIX` | `output/meeting_notes` | Output file prefix (.json and .txt are appended) |
| `--audio-backend` | `google` | `google` or `whisper` |
| `--notes-backend` | `simple` | `simple` or `openai` |
| `--actions-backend` | `simple` | `simple` or `openai` |
| `--language` | `en-US` | BCP-47 language code |
| `--participants NAME …` | *(none)* | Pre-seed known participant names |
| `--openai-key KEY` | *(env var)* | OpenAI API key |

#### Examples

```bash
# Record a live meeting (up to 60 minutes)
python -m src.main live --duration 3600 --output output/my_meeting

# Process a WAV file
python -m src.main file recordings/standup.wav --output output/standup_notes

# Analyse a plain-text transcript
python -m src.main transcript docs/transcript.txt

# Use Whisper for offline transcription
python -m src.main file meeting.wav --audio-backend whisper

# Pre-seed known participants
python -m src.main live --participants "Alice Smith" "Bob Jones"

# Use OpenAI for higher-quality summaries (requires API key)
export OPENAI_API_KEY=sk-...
python -m src.main transcript transcript.txt --notes-backend openai --actions-backend openai
```

---

### Output Format

Two files are written for each run:

#### JSON (`meeting_notes.json`)

```json
{
  "date": "2024-01-15T10:30:00.123456",
  "duration_seconds": 1843.2,
  "participants": [
    { "name": "Alice Smith", "identified": true },
    { "name": "",            "identified": false }
  ],
  "transcript": "Full speech-to-text transcript …",
  "summary_points": [
    "The team agreed to move the deployment deadline to next Friday.",
    "Alice will prepare the Q1 report."
  ],
  "action_items": [
    {
      "description": "Complete the list of meeting participants (1 unknown participant(s) detected).",
      "assignee": "",
      "priority": "high",
      "due_date": ""
    },
    {
      "description": "Alice will prepare the Q1 report and send it to the team.",
      "assignee": "Alice Smith",
      "priority": "medium",
      "due_date": "by Friday"
    }
  ]
}
```

#### Text (`meeting_notes.txt`)

```
============================================================
MEETING NOTES – JARVIS
============================================================
Date       : 2024-01-15T10:30:00.123456
Duration   : 1843.2s

PARTICIPANTS
----------------------------------------
  1. Alice Smith
  2. (unknown)

SUMMARY
----------------------------------------
  • The team agreed to move the deployment deadline to next Friday.
  • Alice will prepare the Q1 report.

ACTION ITEMS
----------------------------------------
  1. [HIGH] Complete the list of meeting participants (1 unknown …) — TBD
  2. [MEDIUM] Alice will prepare the Q1 report … — Alice Smith (due: by Friday)

TRANSCRIPT
----------------------------------------
Full speech-to-text transcript …
============================================================
```

---

### Module Architecture

```
src/
├── __init__.py
├── main.py                        # CLI entry point
└── meeting/
    ├── __init__.py
    ├── models.py                  # Data models (MeetingParticipant, ActionItem, MeetingNotes)
    ├── audio_processor.py         # Audio capture & speech-to-text
    ├── participant_identifier.py  # Participant name detection
    ├── notes_generator.py         # Summary generation
    ├── action_items_extractor.py  # Action-item extraction
    └── meeting_assistant.py       # Orchestrator

tests/
├── __init__.py
├── test_models.py
├── test_participant_identifier.py
├── test_notes_generator.py
├── test_action_items_extractor.py
└── test_meeting_assistant.py
```

Each module is independently testable.  To run the full test suite:

```bash
pytest tests/ -v
```

---

### Extending the Feature

#### Adding a new Speech-to-Text backend

1. Open `src/meeting/audio_processor.py`.
2. Add a new branch in `__init__` and implement `transcribe_file` / `listen_and_transcribe` for the new backend.
3. Expose the new backend name via the `--audio-backend` CLI option in `src/main.py`.

#### Improving participant identification

The `ParticipantIdentifier` uses heuristic regex patterns.  For diarisation-quality results:

* Integrate **pyannote-audio** (speaker diarisation) and pass labelled speaker segments.
* Or pass the transcript through an LLM (e.g., using the `openai` backend) with a custom prompt.

#### Improving action-item extraction

Set `--actions-backend openai` to use GPT-3.5-turbo for much higher accuracy.  This requires an `OPENAI_API_KEY` environment variable.

---

### Configuration (`config.yaml`)

Global defaults can be overridden in `config.yaml` at the repository root:

```yaml
settings:
  debug: true
  language: en-US          # default BCP-47 language
  audio_backend: google    # google | whisper
  notes_backend: simple    # simple | openai
  actions_backend: simple  # simple | openai
  max_recording_duration: 3600
  output_dir: output/
```
