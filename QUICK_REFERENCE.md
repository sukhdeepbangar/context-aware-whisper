# Context-Aware Whisper - Quick Reference

## Current Status
- ✅ Working: Fn key → Record → Transcribe → Type
- ⚠️ Issue: Silent audio → "thank you" hallucination
- 🎯 Goal: Always-listening + text cleanup

## Management Commands
```bash
./context-aware-whisper.sh status    # Check if running
./context-aware-whisper.sh start     # Start app
./context-aware-whisper.sh stop      # Stop app
./context-aware-whisper.sh logs      # View logs
./context-aware-whisper.sh restart   # Restart
```

## Next Features to Implement
1. **Ollama text cleanup** (remove um, uh, false starts)
2. **VAD** (Voice Activity Detection - detect speech vs silence)
3. **Always-listening mode** (no button needed)

## Key Files
- `main.py` - Main application
- `src/context-aware-whisper/transcriber.py` - Groq Whisper integration
- `src/context-aware-whisper/audio_recorder.py` - Audio capture
- `SESSION_CONTEXT.md` - Full project context
- `NEXT_SESSION_PROMPT.md` - Planning prompt

## API Limits (Groq Free Tier)
- Whisper: 2,000 requests/day ✅ Plenty
- Llama: 30,000 tokens/min ✅ Plenty

## Ollama Setup (For Next Session)
```bash
brew install ollama
ollama serve &
ollama pull llama3.2:1b
pip install ollama
```

## Architecture Vision
```
Always listening → VAD detects speech → Record → Whisper API
  → Ollama cleanup (local) → Filter hallucinations → Type
```
