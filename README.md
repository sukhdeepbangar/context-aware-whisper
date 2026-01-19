# Context-Aware Whisper

Local-first speech-to-text for macOS, Windows, and Linux. Hold a hotkey to record, release to transcribe and type.

## Local-First Philosophy

Your voice stays on your device. No cloud required.

- **Local transcription** via whisper.cpp - audio never leaves your machine
- **Local text cleanup** via MLX on Apple Silicon - grammar correction without cloud APIs
- **Cloud option** available (Groq Whisper API) when you need maximum speed

## Models

| Purpose | Model | Backend |
|---------|-------|---------|
| Speech-to-text | OpenAI Whisper (base.en) | whisper.cpp |
| Text cleanup | Phi-3-mini-4k-instruct | MLX (Apple Silicon) |
| Cloud transcription | whisper-large-v3-turbo | Groq API (optional) |

## Quick Start

```bash
# Clone and install
git clone https://github.com/sukhdeepbangar/context-aware-whisper.git
cd context-aware-whisper
python3 -m venv venv && source venv/bin/activate
pip install -e ".[macos]"  # or just pip install -e . for Windows/Linux

# Download whisper model
python -m context_aware_whisper.model_manager download base.en

# Enable local transcription
echo "CAW_TRANSCRIBER=local" >> .env

# Run
python main.py
```

## Usage

1. **Hold** the hotkey (Fn on macOS, Ctrl+Shift+Space on Windows/Linux)
2. **Speak**
3. **Release** - text appears at your cursor

## Requirements

- Python 3.10+
- macOS 14+ / Windows 10+ / Linux (X11 or Wayland)
- ~150MB disk space for base whisper model

## License

MIT
