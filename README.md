# Context-Aware Whisper

Cross-platform speech-to-text application. Hold a hotkey to record, release to transcribe and type.

## Features

- **Cross-platform**: Works on macOS, Windows, and Linux
- **Simple hotkey**: Hold to record, release to transcribe
  - **macOS**: Fn/Globe key
  - **Windows/Linux**: Ctrl+Shift+Space
- **Fast transcription**: Uses Groq Whisper API for near-instant results (~200ms)
- **Auto-typing**: Transcribed text is typed at your cursor position
- **Clipboard backup**: Text is also copied to clipboard as fallback
- **Visual indicator**: On-screen recording status indicator
- **History panel**: Browse and copy previous transcriptions (toggle with Cmd+H / Ctrl+H)
- **Language support**: Auto-detects language or specify manually

## Requirements

### All Platforms
- **Python 3.10 or later**
- **Groq API key** (for cloud transcription) - Free tier available at [console.groq.com](https://console.groq.com)
- **OR** whisper.cpp models (for local transcription) - No API key needed

### macOS
- **macOS 14 (Sonoma) or later**
- Accessibility permission for Terminal/IDE

### Windows
- **Windows 10 or later**
- May need to run as Administrator for hotkey detection

### Linux
- **Ubuntu 22.04+, Fedora 38+, or equivalent**
- **X11**: Works out of the box with pynput
- **Wayland**: Requires `wtype` for typing and `wl-copy` for clipboard

## Installation

### macOS

```bash
# Clone the repository
git clone https://github.com/sukhdeepsingh/context-aware-whisper.git
cd context-aware-whisper

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install with macOS-specific dependencies
pip install -e ".[macos]"

# Or install from requirements
pip install -r requirements.txt
```

### Windows

```bash
# Clone the repository
git clone https://github.com/sukhdeepsingh/context-aware-whisper.git
cd context-aware-whisper

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -e .

# Or install from requirements
pip install -r requirements.txt
```

### Linux

```bash
# Clone the repository
git clone https://github.com/sukhdeepsingh/context-aware-whisper.git
cd context-aware-whisper

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .

# For X11 (optional fallback tools)
sudo apt install xdotool  # Debian/Ubuntu
sudo dnf install xdotool  # Fedora

# For Wayland (required)
sudo apt install wtype wl-clipboard  # Debian/Ubuntu
sudo dnf install wtype wl-clipboard  # Fedora
```

### Configure API Key

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

3. **Hold the hotkey** - Recording starts (indicator shows red "REC")
   - **macOS**: Hold Fn/Globe key
   - **Windows/Linux**: Hold Ctrl+Shift+Space

4. Speak while holding

5. **Release the hotkey** - Recording stops, text is transcribed and typed

### Hotkey Reference

| Platform | Record | Toggle History |
|----------|--------|----------------|
| macOS | Fn/Globe key | Cmd+H |
| Windows | Ctrl+Shift+Space | Ctrl+H |
| Linux | Ctrl+Shift+Space | Ctrl+H |

### State Flow

```
IDLE --[press hotkey]--> RECORDING --[release hotkey]--> TRANSCRIBING --> IDLE
```

### Visual Indicator

A small indicator appears at the top-center of your screen:

| State | Color | Text |
|-------|-------|------|
| Recording | Red | REC |
| Transcribing | Orange | ... |
| Success | Green | OK |
| Error | Red | ERR |

### History Panel

Press **Cmd+H** (macOS) or **Ctrl+H** (Windows/Linux) to toggle the history panel:

- View recent transcriptions with timestamps
- Click "Copy" to copy any entry to clipboard
- Entries persist across application restarts
- Maximum 1000 entries stored (oldest are deleted automatically)

## Local Transcription (whisper.cpp)

For offline, private transcription, you can use whisper.cpp instead of the Groq cloud API.

### Benefits

| Feature | Cloud (Groq) | Local (whisper.cpp) |
|---------|--------------|---------------------|
| Privacy | Audio sent to cloud | Audio stays local |
| Offline | Requires internet | Works offline |
| Cost | Free tier (limited) | Completely free |
| Latency | ~200ms + network | ~200ms (base model) |
| Setup | API key only | Model download (~142MB) |

### Setup

1. **Install pywhispercpp** (included in requirements):
   ```bash
   pip install pywhispercpp
   ```

2. **Download a model**:
   ```bash
   python -m context_aware_whisper.model_manager download base.en
   ```

3. **Enable local transcription**:
   ```bash
   # Add to your .env file
   CAW_TRANSCRIBER=local
   ```

### Model Selection Guide

| Model | Size | Speed | Quality | Recommended For |
|-------|------|-------|---------|-----------------|
| `tiny.en` | 75 MB | Fastest | Basic | Quick testing |
| `base.en` | 142 MB | Fast | Good | **General use (recommended)** |
| `small.en` | 466 MB | Medium | Better | Higher accuracy needs |
| `medium.en` | 1.5 GB | Slow | Great | Best accuracy (high-end hardware) |
| `large-v3` | 3 GB | Slowest | Best | Maximum quality, multilingual |

**Note:** Models ending in `.en` are English-only but faster. Models without `.en` support multiple languages.

### Model Management Commands

```bash
# List all available models and download status
python -m context_aware_whisper.model_manager list

# Download a specific model
python -m context_aware_whisper.model_manager download base.en

# Show detailed model info
python -m context_aware_whisper.model_manager info base.en

# Force re-download a model
python -m context_aware_whisper.model_manager download base.en --force
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Conditional* | - | Groq API key (required when `CAW_TRANSCRIBER=groq`) |
| `CAW_TRANSCRIBER` | No | `groq` | Transcription backend: `groq` (cloud) or `local` (whisper.cpp) |
| `CAW_WHISPER_MODEL` | No | `base.en` | Whisper model for local transcription |
| `CAW_MODELS_DIR` | No | `~/.cache/whisper` | Directory for whisper model files |
| `CAW_LANGUAGE` | No | auto | Language code (e.g., "en", "es", "fr") |
| `CAW_TYPE_DELAY` | No | 0 | Delay between keystrokes in seconds |
| `CAW_SAMPLE_RATE` | No | 16000 | Audio sample rate in Hz |
| `CAW_USE_PASTE` | No | false | Use clipboard paste instead of keystrokes |
| `CAW_UI_ENABLED` | No | true | Enable visual recording indicator |
| `CAW_UI_POSITION` | No | top-center | Indicator position (top-center, top-right, top-left, bottom-center, bottom-right, bottom-left) |
| `CAW_HISTORY_ENABLED` | No | true | Enable transcription history storage |
| `CAW_HISTORY_MAX` | No | 1000 | Maximum number of history entries |
| `CAW_HOTKEY` | No | - | Custom hotkey (e.g., "ctrl+shift+r") |
| `CAW_DEBUG` | No | false | Enable debug logging (verbose output) |

Example `.env` file:

```bash
GROQ_API_KEY=gsk_your_key_here
CAW_LANGUAGE=en
CAW_TYPE_DELAY=0
CAW_UI_POSITION=top-right
```

## Permissions Setup

### macOS

Context-Aware Whisper requires two system permissions to function:

#### 1. Microphone Access

On first run, macOS will prompt for microphone access. Click **Allow** to grant permission.

If you missed the prompt or need to re-enable:
1. Open **System Settings**
2. Go to **Privacy & Security** > **Microphone**
3. Find and enable access for **Terminal** (or your Python executable)

#### 2. Accessibility Access

Required for typing text into applications and detecting the Fn key.

To grant accessibility access:
1. Open **System Settings**
2. Go to **Privacy & Security** > **Accessibility**
3. Click the **+** button
4. Add **Terminal** (or your terminal application)
5. Toggle it **ON**

If using an IDE terminal (VS Code, PyCharm), add that application instead.

### Windows

#### 1. Microphone Access

Windows will prompt for microphone access on first use. Click **Allow**.

To verify:
1. Open **Settings** > **Privacy & Security** > **Microphone**
2. Ensure microphone access is enabled for your terminal/Python

#### 2. Administrator Mode (if needed)

Some antivirus software may block keyboard monitoring. If hotkeys don't work:
1. Right-click on Command Prompt or PowerShell
2. Select **Run as administrator**
3. Navigate to context-aware-whisper directory and run `python main.py`

### Linux

#### 1. Microphone Access

Ensure your user has access to audio devices:
```bash
# Add user to audio group (may require logout/login)
sudo usermod -a -G audio $USER
```

#### 2. Input Device Access (for hotkey detection)

For pynput to work, you may need:
```bash
# Add user to input group
sudo usermod -a -G input $USER
```

#### 3. X11 vs Wayland

Check your display server:
```bash
echo $XDG_SESSION_TYPE
```

**For X11**: pynput works directly. Install xdotool as fallback:
```bash
sudo apt install xdotool  # Debian/Ubuntu
```

**For Wayland**: Install wtype and wl-clipboard:
```bash
sudo apt install wtype wl-clipboard  # Debian/Ubuntu
```

### Verifying Permissions

After granting permissions, restart the terminal and run Context-Aware Whisper again. You should see:

```
=======================================================
  Context-Aware Whisper - Speech-to-Text
=======================================================

  Mode: HOTKEY (Ctrl+Shift+Space)  # or Fn/Globe key on macOS

  Usage:
    1. HOLD hotkey            -> Recording starts
    2. Speak while holding
    3. RELEASE hotkey         -> Transcribes & types

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
- Missing Accessibility permission (macOS)
- Application doesn't accept keystrokes
- Special characters causing issues
- On Wayland: wtype not installed

**Solutions:**
1. Check platform-specific permissions (see [Permissions Setup](#permissions-setup))
2. Try pasting from clipboard manually - text is always copied there
3. Set `CAW_USE_PASTE=true` in `.env` to use clipboard paste instead of keystrokes
4. On Linux Wayland: Install wtype (`sudo apt install wtype`)

### Hotkey not working

**macOS:**
- Grant Accessibility permission to Terminal/IDE
- Restart the application after granting permission

**Windows:**
- Try running as Administrator
- Check if antivirus is blocking keyboard monitoring

**Linux:**
- Add user to `input` group: `sudo usermod -a -G input $USER`
- On Wayland: Some compositors may not support global hotkeys

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
4. Try setting a specific language: `CAW_LANGUAGE=en`

### "Rate limited" errors

**Cause**: Groq API rate limits exceeded.

**Solution**: Wait a moment before trying again. The app includes automatic retry with exponential backoff.

### Application crashes on startup

**Possible causes:**
- Missing dependencies
- Python version too old
- Platform-specific dependencies not installed

**Solutions:**
1. Reinstall dependencies: `pip install -e .` (or `pip install -e ".[macos]"` on macOS)
2. Ensure Python 3.10+ is installed: `python3 --version`
3. On macOS: Verify macOS 14+ (Apple menu > About This Mac)
4. On Linux: Install platform tools (xdotool for X11, wtype for Wayland)

### Visual indicator not appearing

**Possible causes:**
- UI disabled in configuration
- tkinter not available

**Solutions:**
1. Check `CAW_UI_ENABLED` is not set to `false`
2. Install tkinter if missing:
   - macOS: Included with Python from python.org
   - Ubuntu/Debian: `sudo apt install python3-tk`
   - Fedora: `sudo dnf install python3-tkinter`

### Local Transcription Troubleshooting

#### "Model not found" or "Failed to load whisper model" error

**Solution**: Download the model first:
```bash
python -m context_aware_whisper.model_manager download base.en
```

#### Slow local transcription

**Possible causes:**
- Using a large model on limited hardware
- Metal GPU acceleration not working (macOS)

**Solutions:**
1. Use a smaller model:
   ```bash
   export CAW_WHISPER_MODEL=tiny.en
   ```
2. Check that Metal acceleration is enabled (macOS Apple Silicon)
3. Ensure sufficient RAM is available (base model needs ~2GB)

#### High memory usage with local transcription

**Cause:** Larger models require more RAM.

**Solutions:**
1. Use smaller models: `tiny` (~1GB), `base` (~2GB), `small` (~3GB)
2. Restart the app to unload the model from memory
3. Set a smaller model: `CAW_WHISPER_MODEL=tiny.en`

#### Local transcription quality issues

**Possible causes:**
- Using a smaller model
- Audio quality issues
- Speaking non-English with English-only model

**Solutions:**
1. Try a larger model: `export CAW_WHISPER_MODEL=small.en`
2. Ensure clear audio input with minimal background noise
3. For non-English, use multilingual models (without `.en` suffix): `base`, `small`, `medium`, `large-v3`

#### "pywhispercpp not installed" error

**Solution**: Install the pywhispercpp package:
```bash
pip install pywhispercpp
```

## Development

### Prerequisites for Development

This repository uses **Git LFS** to manage audio test fixtures. Install it before cloning:

```bash
# macOS
brew install git-lfs

# Ubuntu/Debian
sudo apt install git-lfs

# Windows (with Chocolatey)
choco install git-lfs
```

After installing, initialize Git LFS:

```bash
git lfs install
```

When you clone the repository, Git LFS will automatically download the audio fixture files.

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

# Run with coverage
pytest --cov=context_aware_whisper

# Run integration tests (requires hardware/whisper model)
pytest tests/integration/ -v -m integration
```

### Project Structure

```
context-aware-whisper/
├── main.py                     # Application entry point
├── src/context_aware_whisper/
│   ├── __init__.py
│   ├── audio_recorder.py       # Microphone audio capture
│   ├── transcriber.py          # Groq Whisper API client (cloud)
│   ├── local_transcriber.py    # whisper.cpp transcription (local)
│   ├── model_manager.py        # Model download/management CLI
│   ├── config.py               # Configuration loading
│   ├── exceptions.py           # Custom exceptions
│   ├── platform/               # Platform abstraction layer
│   │   ├── __init__.py         # Platform detection & factories
│   │   ├── base.py             # Abstract base classes
│   │   ├── macos/              # macOS implementations
│   │   │   ├── hotkey_detector.py   # Fn key via CGEvent
│   │   │   ├── output_handler.py    # AppleScript typing
│   │   │   └── mute_detector.py     # AirPods mute detection
│   │   ├── windows/            # Windows implementations
│   │   │   ├── hotkey_detector.py   # Ctrl+Shift+Space via pynput
│   │   │   └── output_handler.py    # pynput typing
│   │   └── linux/              # Linux implementations
│   │       ├── hotkey_detector.py   # Ctrl+Shift+Space via pynput
│   │       └── output_handler.py    # xdotool/wtype fallback
│   ├── ui/                     # Visual UI components
│   │   ├── __init__.py
│   │   ├── app.py              # UI controller
│   │   ├── indicator.py        # Recording state indicator
│   │   └── history.py          # Transcription history panel
│   └── storage/                # Data persistence
│       ├── __init__.py
│       └── history_store.py    # JSONL history storage
├── tests/                      # Test suite
├── spec/                       # Specifications
├── plan/                       # Implementation plans
├── requirements.txt
├── pyproject.toml
└── .env.example
```

## How It Works

1. **Hotkey Detection**: Platform-specific detection of hotkey press/release
   - macOS: CGEventTap for Fn/Globe key
   - Windows/Linux: pynput for Ctrl+Shift+Space

2. **Audio Recording** (`audio_recorder.py`): Captures audio from the microphone using `sounddevice` library, storing in memory as 16-bit mono WAV at 16kHz

3. **Transcription**: Converts audio to text using one of two backends:
   - **Cloud** (`transcriber.py`): Groq Whisper API (`whisper-large-v3-turbo`) - fast, accurate, requires internet
   - **Local** (`local_transcriber.py`): whisper.cpp - private, offline, no API costs

4. **Output**: Platform-specific text typing
   - macOS: AppleScript for reliable keystroke injection
   - Windows: pynput keyboard controller
   - Linux X11: pynput with xdotool fallback
   - Linux Wayland: wtype for keyboard simulation

5. **Visual Feedback** (`ui/`): tkinter-based recording indicator and history panel

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [Groq](https://groq.com) for lightning-fast Whisper API
- [OpenAI Whisper](https://github.com/openai/whisper) for the speech recognition model
- [whisper.cpp](https://github.com/ggerganov/whisper.cpp) for efficient local transcription
