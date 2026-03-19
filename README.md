# Jarvis

**Jarvis** is a personal AI work assistant built in Python.  It connects existing free APIs and services so you don't have to build everything from scratch.

---

## Features

### 🎙️ Meeting Assistant *(v0.1)*

Jarvis can listen to a meeting (live microphone or pre-recorded audio), automatically identify participants, take intelligent notes, and generate a prioritised list of action items.

**Highlights:**
- Speech-to-text via Google Speech Recognition (free) or Whisper (offline)
- Automatic participant detection from transcript patterns
- Structured meeting notes (JSON + human-readable text)
- Intelligent action-item extraction with assignees and due dates
- Unknown participants produce a high-priority "complete the list" action item

→ See [docs/meeting-feature-setup.md](docs/meeting-feature-setup.md) for setup and usage instructions.

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/iwaught/Jarvis.git
cd Jarvis
pip install -r requirements.txt

# Analyse a transcript file
python -m src.main transcript path/to/transcript.txt

# Record a live meeting (press Ctrl-C to stop)
python -m src.main live --output output/my_meeting

# Process a WAV file
python -m src.main file recording.wav
```

---

## Project Structure

```
Jarvis/
├── src/
│   ├── main.py                 # CLI entry point
│   └── meeting/                # Meeting assistant modules
│       ├── models.py
│       ├── audio_processor.py
│       ├── participant_identifier.py
│       ├── notes_generator.py
│       ├── action_items_extractor.py
│       └── meeting_assistant.py
├── tests/                      # pytest test suite
├── docs/                       # Feature documentation
├── issues/                     # User stories / feature specs
├── config.yaml                 # Global configuration
└── requirements.txt
```

---

## Running Tests

```bash
pytest tests/ -v
```
