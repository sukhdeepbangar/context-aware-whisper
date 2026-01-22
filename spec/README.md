# Context-Aware Whisper Specifications

Design documentation for Context-Aware Whisper, a speech-to-text application for macOS with AirPods/hotkey triggers.

## Quick Links

| Document | Status | Description |
|----------|--------|-------------|
| [spec.md](./spec.md) | **Implemented** | Core architecture and module specifications |
| [spec.md#module-6](./spec.md#module-6-text_cleanuppy) | **Implemented** | Text cleanup/disfluency removal |
| [cross_platform_ui_spec.md](./cross_platform_ui_spec.md) | **Implemented** | Cross-platform support & UI framework |
| [ui_improvements_spec.md](./ui_improvements_spec.md) | Partial | UI/UX enhancements |
| [subprocess_indicator_spec.md](./subprocess_indicator_spec.md) | **Implemented** | Focus-preserving recording indicator |
| [vocabulary_spec.md](./vocabulary_spec.md) | **Implemented** | Custom vocabulary hints for transcription |

---

## Core Architecture

| Spec | Code | Purpose |
|------|------|---------|
| [spec.md](./spec.md) | [src/context_aware_whisper/](../src/context_aware_whisper/) | System architecture, state machine, module interfaces |

**Covers:**
- System architecture diagram
- State machine (IDLE → RECORDING → TRANSCRIBING)
- Module specifications:
  - `mute_detector.py` - AirPods mute/unmute detection
  - `audio_recorder.py` - Microphone audio capture
  - `transcriber.py` - Groq Whisper API client
  - `local_transcriber.py` - whisper.cpp local transcription
  - `text_cleanup.py` - Speech disfluency removal
  - `local_llm.py` - Local LLM for aggressive text cleanup
  - `model_manager.py` - Model management utilities
  - `output_handler.py` - Clipboard & auto-typing
  - `main.py` - Application entry point
- Dependencies and configuration
- Performance targets
- Security considerations

---

## Transcription

| Spec | Code | Purpose |
|------|------|---------|
| [spec.md#module-3](./spec.md) | [transcriber.py](../src/context_aware_whisper/transcriber.py) | Groq Whisper API (cloud) |
| [spec.md#module-3b](./spec.md) | [local_transcriber.py](../src/context_aware_whisper/local_transcriber.py) | whisper.cpp local transcription |

**Cloud (Groq):** Fast, accurate, requires internet and API key
**Local (whisper.cpp):** Private, offline, no API costs

See also: [whisper_cpp_plan.md](../plan/whisper_cpp_plan.md)

---

## User Interface

| Spec | Code | Purpose |
|------|------|---------|
| [cross_platform_ui_spec.md](./cross_platform_ui_spec.md) | [src/context_aware_whisper/ui/](../src/context_aware_whisper/ui/) | Recording indicator, history panel, tkinter UI |
| [ui_improvements_spec.md](./ui_improvements_spec.md) | [menubar.py](../src/context_aware_whisper/ui/menubar.py) | Menu bar icon integration |
| [subprocess_indicator_spec.md](./subprocess_indicator_spec.md) | [subprocess_indicator.py](../src/context_aware_whisper/ui/subprocess_indicator.py) | Focus-preserving indicator via subprocess |

**Key Features:**
- Recording indicator (top-center, always-on-top)
- Transcription history panel with SQLite storage
- Menu bar icon for app visibility
- Focus preservation during recording

**Additional UI Components:**
- `native_indicator.py` - Native platform indicator
- `history.py` - History panel UI
- `storage/history_store.py` - SQLite history persistence

---

## Cross-Platform Support

| Spec | Code | Purpose |
|------|------|---------|
| [cross_platform_ui_spec.md](./cross_platform_ui_spec.md) | [src/context_aware_whisper/platform/](../src/context_aware_whisper/platform/) | Platform abstraction layer |

**Platforms:**
| Platform | Hotkey | Status |
|----------|--------|--------|
| macOS | Fn/Globe key | **Implemented** |
| Windows | Ctrl+Shift+Space | **Implemented** |
| Linux | Ctrl+Shift+Space | **Implemented** |

**Platform Modules:**
- `platform/base.py` - Abstract base classes
- `platform/macos/` - macOS-specific (mute detector, hotkey, output handler)
- `platform/windows/` - Windows-specific (hotkey detector, output handler)
- `platform/linux/` - Linux-specific (hotkey detector, output handler)

---

## Implementation Plans

Related implementation plans in [../plan/](../plan/):

| Plan | Spec | Purpose |
|------|------|---------|
| [implementation_plan.md](../plan/implementation_plan.md) | [spec.md](./spec.md) | Core app implementation steps |
| [whisper_cpp_plan.md](../plan/whisper_cpp_plan.md) | [spec.md](./spec.md) | Local transcription integration |
| [text_cleanup_plan.md](../plan/text_cleanup_plan.md) | [spec.md](./spec.md) | Text cleanup/disfluency removal |
| [simplification_plan.md](../plan/simplification_plan.md) | — | Codebase simplification (40% reduction) |
| [cross_platform_ui_plan.md](../plan/cross_platform_ui_plan.md) | [cross_platform_ui_spec.md](./cross_platform_ui_spec.md) | Cross-platform & UI implementation |
| [ui_improvements_plan.md](../plan/ui_improvements_plan.md) | [ui_improvements_spec.md](./ui_improvements_spec.md) | UI enhancements implementation |
| [focus_preservation_fix_plan.md](../plan/focus_preservation_fix_plan.md) | [subprocess_indicator_spec.md](./subprocess_indicator_spec.md) | Focus stealing fix |
| [vocabulary_plan.md](../plan/vocabulary_plan.md) | [vocabulary_spec.md](./vocabulary_spec.md) | Custom vocabulary hints |

---

## Status Legend

| Status | Meaning |
|--------|---------|
| **Implemented** | Feature is complete and in production |
| Partial | Some components implemented |
| Planned | Specified but not yet implemented |
| Draft | Specification in progress |

---

## Contributing

When adding new specifications:

1. Create a new `.md` file in this directory
2. Follow the existing format (Requirements, Architecture, Interface sections)
3. Update this README.md with the new spec
4. Create a corresponding implementation plan in `../plan/`
