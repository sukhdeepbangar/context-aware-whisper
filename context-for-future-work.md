# HandFree Project - Session Context

## Project Overview
HandFree is a speech-to-text app for macOS that:
- Records audio via Fn key press/release
- Transcribes using Groq Whisper API
- Auto-types transcribed text at cursor position

## Current Status
- ✅ Basic app working (main.py, running in background)
- ✅ Fn key trigger working
- ✅ Groq Whisper integration working
- ⚠️ Issue: Silent audio causes Whisper hallucinations ("thank you", "bye", etc.)

## Key Decisions & Next Steps

### 1. Always-Listening Mode (Desired Feature)
**Goal:** No button press - just speak naturally, text appears when it makes sense

**Architecture:**
```
Continuous VAD monitoring
  ↓
Detect speech → Record
  ↓
Detect silence (1-2s) → Stop
  ↓
Transcribe with Groq Whisper
  ↓
Filter: Does it make sense?
  ├─ Yes → Clean text → Auto-type
  └─ No → Discard (hallucination/noise)
  ↓
Back to listening
```

**Technical Components Needed:**
- Voice Activity Detection (VAD): SileroVAD or WebRTC VAD
- Hallucination filter: Remove "thank you", "bye", etc.
- Minimum length check: At least 3 words, 10 chars
- Text cleanup/sanitization

### 2. Text Cleanup/Sanitization (Critical Feature)
**Problem:** Natural speech has disfluencies
- "Hey, um, can you... sorry, can you send this?"
- Should output: "Can you send this?"

**Solution - Local Privacy-First Approach:**
```
Speak → Groq Whisper (cloud) → Ollama Llama (LOCAL) → Type
         ↑ only audio sent      ↑ text stays private
```

**Implementation:**
- Use Ollama (local LLM on Mac)
- Model: `llama3.2:1b` (1.3GB, fast, good quality)
- Process: Remove fillers (um, uh, like), false starts, corrections
- Privacy: Text never leaves user's machine

**Ollama Setup:**
```bash
brew install ollama
ollama serve &
ollama pull llama3.2:1b
pip install ollama
```

### 3. Groq API Free Tier Limits
**Whisper Large v3 Turbo:**
- 2,000 requests per day
- 7,200 audio-seconds per minute
- More than enough for always-listening mode

**Llama models (for cleanup if using cloud):**
- 30,000 tokens/min
- But we'll use Ollama locally instead

## Technical Stack
- **Audio Recording:** sounddevice, numpy, scipy
- **Transcription:** Groq Whisper API (whisper-large-v3-turbo)
- **Text Cleanup:** Ollama + llama3.2:1b (local)
- **VAD:** SileroVAD or WebRTC VAD (to implement)
- **Output:** pyautogui (typing), pyperclip (clipboard)
- **Platform:** macOS 14+, Python 3.10+

## File Structure
```
handfree/
├── main.py                    # Main entry point
├── src/handfree/
│   ├── audio_recorder.py     # Audio capture
│   ├── transcriber.py        # Groq Whisper API
│   ├── output_handler.py     # Auto-typing
│   ├── hotkey_detector.py    # Fn key detection
│   └── mute_detector.py      # AirPods mute (not working)
├── handfree.sh               # Management script
├── handfree.log              # Runtime logs
└── .env                      # API keys
```

## Current Issues to Fix
1. **Silent audio hallucinations** - Need VAD to detect if speech present before sending to API
2. **No text cleanup** - Need Ollama integration for disfluency removal
3. **Button-based** - Want always-listening mode

## Implementation Plan (Next Session)

### Phase 1: Add Text Cleanup with Ollama
1. Install and test Ollama locally
2. Add `cleanup_text()` method using Ollama
3. Integrate into transcription pipeline
4. Test with disfluent speech samples

### Phase 2: Add Voice Activity Detection
1. Choose VAD library (SileroVAD recommended)
2. Implement `detect_speech()` and `detect_silence()`
3. Add audio quality checks (RMS, amplitude)
4. Test to avoid hallucinations

### Phase 3: Always-Listening Mode
1. Replace hotkey detector with continuous VAD monitoring
2. Implement automatic recording on speech detection
3. Add hallucination filtering
4. Add visual status indicator (menu bar)
5. Add pause/resume hotkey

### Phase 4: Polish & Testing
1. Optimize performance and latency
2. Add configuration options
3. Handle edge cases
4. Battery optimization for laptop use

## Questions to Decide
- VAD sensitivity: How quiet before we stop recording?
- Cleanup aggressiveness: How much to sanitize?
- Visual feedback: Menu bar icon states?
- Pause mechanism: Which hotkey to pause/resume listening?

## Future Feature: whisper.cpp Local Transcription

### Benefits Over Groq API
| Aspect | Groq API (Current) | whisper.cpp (Future) |
|--------|-------------------|---------------------|
| Privacy | Audio sent to cloud | Audio stays local |
| Offline | Requires internet | Works offline |
| Latency | Network dependent | Local processing |
| Cost | Free tier limits | Completely free |
| Rate Limits | 2K req/day, 7.2K sec/min | Unlimited |

### Technical Approach
**Python Bindings:**
- `pywhispercpp` - Actively maintained, simple API
- `whispercpp` - Alternative binding

**Integration Points:**
1. `src/handfree/transcriber.py` - Add `WhisperCppTranscriber` class
2. Configuration option to choose backend (groq vs local)
3. Model download/management utility

### Model Options
- `tiny.en` (75MB) - Fastest, basic accuracy
- `base.en` (142MB) - Good balance (recommended)
- `small.en` (466MB) - Better accuracy
- `medium.en` (1.5GB) - High accuracy
- `large` (3GB) - Best accuracy, multilingual

### Implementation Notes
- Apple Silicon Macs get Metal acceleration (fast!)
- Models downloaded to `~/.cache/whisper/` or custom location
- Can run alongside Groq as fallback option

See `future_plans.md` for detailed implementation plan.

## Resources & References
- Groq API Docs: https://console.groq.com/docs
- Ollama: https://ollama.ai
- SileroVAD: https://github.com/snakers4/silero-vad
- Wispr Flow approach: Whisper → Llama cleanup → Output
- whisper.cpp: https://github.com/ggerganov/whisper.cpp
- pywhispercpp: https://github.com/abdeladim-s/pywhispercpp

## Current Environment
- Mac: Darwin 24.5.0
- Python: 3.14
- Running in: /Users/sukhdeepsingh/projects/ClaudeProjects/handfree
- App running in background: PID 33289
