# Future Plans

## whisper.cpp - Local Transcription Support

### What
Local speech-to-text transcription using [whisper.cpp](https://github.com/ggerganov/whisper.cpp), a high-performance C/C++ port of OpenAI's Whisper model.

### Why
| Benefit | Description |
|---------|-------------|
| **Privacy** | Audio never leaves your machine - no cloud processing |
| **Offline Support** | Works without internet connection |
| **Lower Latency** | No network round-trip, faster transcription |
| **No API Costs** | Zero usage fees after initial setup |
| **No Rate Limits** | Unlimited transcriptions |
| **Data Control** | Full control over your audio data |

### How
Integrate whisper.cpp via Python bindings:

**Option 1: pywhispercpp**
```bash
pip install pywhispercpp
```
```python
from pywhispercpp.model import Model

model = Model('base.en')  # or tiny, small, medium, large
result = model.transcribe('audio.wav')
print(result)
```

**Option 2: whispercpp**
```bash
pip install whispercpp
```
```python
from whispercpp import Whisper

w = Whisper.from_pretrained("base.en")
result = w.transcribe("audio.wav")
```

### Model Options
| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| tiny | 75 MB | Fastest | Basic | Quick drafts, low-resource |
| base | 142 MB | Fast | Good | General use |
| small | 466 MB | Medium | Better | Balanced accuracy/speed |
| medium | 1.5 GB | Slow | Great | High accuracy needed |
| large | 3 GB | Slowest | Best | Maximum accuracy |

**Recommended:** `base.en` or `small.en` for English-only with best speed/accuracy tradeoff.

### Implementation Approach
1. Add whisper.cpp as optional backend alongside Groq API
2. Auto-detect if models are downloaded locally
3. Let users choose: cloud (Groq) vs local (whisper.cpp)
4. Fallback: Use Groq if local model unavailable

### Prerequisites
- Download whisper models (~75MB to 3GB depending on model)
- Sufficient RAM for model (tiny: 1GB, base: 2GB, small: 3GB)
- Apple Silicon recommended for best performance (uses Metal acceleration)

### Timeline
This is a planned future feature. Current implementation uses Groq Whisper API.
