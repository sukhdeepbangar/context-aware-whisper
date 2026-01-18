# HandFree

Fast speech-to-text for macOS. Hold the **Fn/Globe key** to record, release to transcribe and type.

## Features

- **Simple hotkey**: Hold Fn key to record, release to transcribe
- **Fast transcription**: Uses Groq Whisper API for near-instant results (~200ms)
- **Auto-typing**: Transcribed text is typed at your cursor position
- **Clipboard backup**: Text is also copied to clipboard as fallback
- **Language support**: Auto-detects language or specify manually

## Requirements

- **macOS 14 (Sonoma) or later**
- **Python 3.10 or later**
- **Groq API key** - Free tier available at [console.groq.com](https://console.groq.com)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/sukhdeepsingh/handfree.git
cd handfree
```

### 2. Create and activate virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -e .
```

Or install from requirements:

```bash
pip install -r requirements.txt
```

### 4. Configure API key

Create a `.env` file with your Groq API key:

```bash
cp .env.example .env
```

Edit `.env` and add your API key:

```
GROQ_API_KEY=your_api_key_here
```

Get your free API key at [console.groq.com/keys](https://console.groq.com/keys)

## Usage

1. Run the application:

```bash
python main.py
```

2. Click where you want text to appear (any text field or editor)
3. **Hold Fn/Globe key** - Recording starts
4. Speak while holding
5. **Release Fn key** - Recording stops, text is transcribed and typed

### State Flow

```
IDLE --[press Fn]--> RECORDING --[release Fn]--> TRANSCRIBING --> IDLE
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | - | Your Groq API key |
| `HANDFREE_LANGUAGE` | No | auto | Language code (e.g., "en", "es", "fr") |
| `HANDFREE_TYPE_DELAY` | No | 0 | Delay between keystrokes in seconds |
| `HANDFREE_SAMPLE_RATE` | No | 16000 | Audio sample rate in Hz |
| `HANDFREE_USE_PASTE` | No | false | Use clipboard paste instead of keystrokes |
| `HANDFREE_UI_ENABLED` | No | true | Enable visual recording indicator |
| `HANDFREE_HISTORY_ENABLED` | No | true | Enable transcription history storage |
| `HANDFREE_DEBUG` | No | false | Enable debug logging (verbose output) |

Example `.env` file:

```bash
GROQ_API_KEY=gsk_your_key_here
HANDFREE_LANGUAGE=en
HANDFREE_TYPE_DELAY=0
```

## Permissions Setup

HandFree requires two system permissions to function:

### 1. Microphone Access

On first run, macOS will prompt for microphone access. Click **Allow** to grant permission.

If you missed the prompt or need to re-enable:
1. Open **System Settings**
2. Go to **Privacy & Security** > **Microphone**
3. Find and enable access for **Terminal** (or your Python executable)

### 2. Accessibility Access

Required for typing text into applications and detecting the Fn key.

To grant accessibility access:
1. Open **System Settings**
2. Go to **Privacy & Security** > **Accessibility**
3. Click the **+** button
4. Add **Terminal** (or your terminal application)
5. Toggle it **ON**

If using an IDE terminal (VS Code, PyCharm), add that application instead.

### Verifying Permissions

After granting permissions, restart the terminal and run HandFree again. You should see:

```
=======================================================
  HandFree - Speech-to-Text
=======================================================

  Mode: HOTKEY (Fn/Globe key)

  Usage:
    1. HOLD Fn key            -> Recording starts
    2. Speak while holding
    3. RELEASE Fn key         -> Transcribes & types

  Press Ctrl+C to exit
=======================================================
```

## Troubleshooting

### "GROQ_API_KEY environment variable is not set"

**Solution**: Create a `.env` file with your API key:

```bash
echo "GROQ_API_KEY=your_key_here" > .env
```

Or export it directly:

```bash
export GROQ_API_KEY=your_key_here
```

### Text not typing into application

**Possible causes:**
- Missing Accessibility permission
- Application doesn't accept keystrokes
- Special characters causing issues

**Solutions:**
1. Check Accessibility permissions (see [Permissions Setup](#permissions-setup))
2. Try pasting from clipboard manually (Cmd+V) - text is always copied there
3. Set `HANDFREE_USE_PASTE=true` in `.env` to use clipboard paste instead of keystrokes

### Transcription is empty or incorrect

**Possible causes:**
- Audio too quiet or too noisy
- Speaking too fast or unclear
- Invalid API key
- Network issues

**Solutions:**
1. Speak clearly at a normal pace
2. Check that your Groq API key is valid
3. Verify internet connection
4. Try setting a specific language: `HANDFREE_LANGUAGE=en`

### "Rate limited" errors

**Cause**: Groq API rate limits exceeded.

**Solution**: Wait a moment before trying again. The app includes automatic retry with exponential backoff.

### Application crashes on startup

**Possible causes:**
- Missing dependencies
- Python version too old
- macOS version incompatible

**Solutions:**
1. Reinstall dependencies: `pip install -e .`
2. Ensure Python 3.10+ is installed: `python3 --version`
3. Verify macOS 14+: Apple menu > About This Mac

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_transcriber.py
```

### Project Structure

```
handfree/
├── main.py                     # Application entry point
├── src/handfree/
│   ├── __init__.py
│   ├── hotkey_detector.py      # Fn key detection via CGEvent
│   ├── audio_recorder.py       # Microphone audio capture
│   ├── transcriber.py          # Groq Whisper API client
│   ├── output_handler.py       # Clipboard + auto-typing
│   ├── config.py               # Configuration loading
│   └── exceptions.py           # Custom exceptions
├── tests/                      # Test suite
├── spec/                       # Specifications
├── plan/                       # Implementation plans
├── requirements.txt
├── pyproject.toml
└── .env.example
```

## How It Works

1. **Hotkey Detection** (`hotkey_detector.py`): Uses macOS CGEventTap API to detect Fn/Globe key press and release events

2. **Audio Recording** (`audio_recorder.py`): Captures audio from the microphone using `sounddevice` library, storing in memory as 16-bit mono WAV at 16kHz

3. **Transcription** (`transcriber.py`): Sends audio to Groq's Whisper API (`whisper-large-v3-turbo` model) for fast, accurate transcription

4. **Output** (`output_handler.py`): Types the transcribed text at the cursor position using AppleScript and copies to clipboard as backup

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [Groq](https://groq.com) for lightning-fast Whisper API
- [OpenAI Whisper](https://github.com/openai/whisper) for the speech recognition model
