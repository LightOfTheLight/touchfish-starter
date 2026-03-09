# Project Requirements

## 1. Overview

**Project Name:** Speech-to-Text Terminal Plugin
**Project Type:** CLI Application / Terminal Plugin
**Target Users:** Developers and power users who want hands-free, voice-driven terminal interaction — including voice-controlled Claude Code sessions

### 1.1 Vision

A terminal plugin that captures microphone input and transcribes speech locally using open-source NLP models — no cloud dependencies. In agent mode, transcribed speech is piped directly into `claude -p`, enabling hands-free voice control of AI-assisted coding tasks.

### 1.2 Core Principles

- **Local-first:** All STT processing runs on-device; no data is sent to external services
- **Non-blocking:** Audio capture and Claude processing are independent threads; one never stalls the other
- **Transparent output:** Every interaction is clearly labeled (`> You:` / `Claude:`) so the user always knows what was heard and what was answered

---

## 2. Functional Requirements

### 2.1 Real-Time Speech Transcription

**Description:** Capture microphone audio and transcribe it locally using an open-source STT model (Whisper / faster-whisper recommended). Transcribed text is printed to the terminal as utterances are completed.

**Acceptance Criteria:**
- [ ] Microphone audio is captured continuously in real-time
- [ ] Energy-based VAD detects speech start and end
- [ ] After silence is detected, the buffered utterance is transcribed using a locally loaded Whisper model
- [ ] Transcribed text is printed to stdout immediately after transcription
- [ ] No data is sent to any external API or cloud service during transcription

### 2.2 Audio Device Management

**Description:** Allow users to select a specific microphone device or use the system default.

**Acceptance Criteria:**
- [ ] `--list-devices` flag prints all available audio input devices with their indices and marks the system default
- [ ] `--device <INDEX>` flag selects a specific input device
- [ ] When no device is specified, the system default microphone is used

### 2.3 Model Selection

**Description:** Support multiple Whisper model sizes to let users trade off speed vs. accuracy.

**Acceptance Criteria:**
- [ ] `--model` accepts: `tiny`, `base`, `small`, `medium`, `large`
- [ ] Default model is `base` in basic mode; `small` in agent mode (when `--model` is not explicitly specified)
- [ ] `--language <LANG>` allows forcing a language code (e.g., `en`, `fr`); auto-detects when omitted
- [ ] Model is loaded once at startup; a loading message is printed to inform the user

### 2.4 Silence Detection Tuning

**Description:** Allow tuning of VAD sensitivity to accommodate different environments.

**Acceptance Criteria:**
- [ ] `--silence-threshold <LEVEL>` sets the RMS amplitude below which audio is considered silence (default: `0.003`)
- [ ] `--silence-duration <SECS>` sets how long silence must persist before triggering transcription (default: `1.0`)
- [ ] Utterances shorter than 0.3 seconds of speech are discarded (noise rejection)

### 2.5 Debug Mode

**Description:** A `--debug` flag that enables verbose diagnostic logging to stderr, allowing users to diagnose microphone levels, VAD behavior, transcription timing, and Claude subprocess performance without interfering with normal stdout output.

**Acceptance Criteria:**
- [ ] `--debug` flag activates debug mode
- [ ] All debug output goes to **stderr** only — stdout output is unchanged
- [ ] All debug lines are timestamped with format `[DEBUG HH:MM:SS] <message>`
- [ ] On startup, debug mode prints: model name, language, agent mode status, silence threshold, silence duration
- [ ] During capture, RMS audio level is logged periodically (every 2–3 seconds) to allow silence threshold tuning
- [ ] When speech starts, a debug line is logged with the RMS value that triggered detection
- [ ] When silence is detected, a debug line is logged with the utterance duration
- [ ] Transcription timing is logged: duration in seconds and the resulting transcribed text
- [ ] In agent mode, Claude subprocess start, finish, and elapsed time are logged
- [ ] Debug mode is compatible with all flag combinations (`--agent`, `--model`, `--language`, etc.)

### 2.6 Transcription Accuracy

**Description:** Ensure transcription quality is sufficient for reliable voice-command use, particularly in agent mode. The default model should be tuned for agent mode where accuracy matters more than minimal resource usage.

**Acceptance Criteria:**
- [ ] When `--agent` is used without an explicit `--model` flag, the default model is `small` (not `base`) for better accuracy/speed tradeoff on CPU
- [ ] When `--model` is specified explicitly, that model is used regardless of mode
- [ ] Transcription handles common English commands accurately: file operations, code-related terms, and technical vocabulary
- [ ] If a transcription takes longer than 5 seconds (applicable with `medium` or `large` models on CPU), a warning is logged suggesting the user switch to a smaller model
- [ ] At startup, if `medium` or `large` model is selected without GPU, a warning is printed informing the user of potential latency

### 2.7 Voice-Controlled Claude Code Agent Mode

**Description:** The `--agent` flag enables a voice-to-Claude pipeline. Each completed utterance is sent to `claude -p "<text>"` and the response is printed in the terminal. Audio capture continues non-blocking while Claude is processing.

**Acceptance Criteria:**
- [ ] `--agent` flag activates agent mode
- [ ] Transcribed text is displayed as `> You: <transcribed text>` before Claude is called
- [ ] Claude's response is displayed as `Claude: <response>` after the call completes
- [ ] Claude is called in a background thread so audio capture is never paused
- [ ] The `CLAUDECODE` environment variable is stripped from the subprocess environment to prevent "nested session" errors when `stt.py` is launched from within a Claude Code session
- [ ] If `claude` CLI is not installed, a clear error message is printed: `[Error: 'claude' CLI not found. Is Claude Code installed?]`
- [ ] Claude subprocess calls time out after 120 seconds with message: `[Claude timed out after 120 seconds]`
- [ ] Non-zero exit codes and stderr output from Claude are surfaced to the user

---

## 3. Technical Requirements

### 3.1 Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3 |
| STT Model | faster-whisper (OpenAI Whisper, local CPU inference) |
| Audio Capture | sounddevice |
| Concurrency | threading + concurrent.futures.ThreadPoolExecutor |
| Claude Integration | subprocess (`claude -p`) |

### 3.2 Constraints

- All STT inference runs on local CPU; GPU is optional but not required
- No internet connection required at runtime (after initial model download)
- Must run as a standard Python CLI (`python stt.py [options]`)
- Must be deployable on Linux, macOS, and Windows (wherever sounddevice + Whisper are supported)

---

## 4. Non-Functional Requirements

### 4.1 Performance

- **STT latency:** Transcription of a completed utterance must begin within 2 seconds of silence detection
- **End-to-end agent latency:** Time from end-of-speech to first display of Claude's response must be under 10 seconds for typical short commands (excluding network/model variability outside the STT step)
- **Non-blocking audio:** Claude processing must never cause audio frames to be dropped

### 4.2 Security

- No credentials or audio data are transmitted outside the local machine
- Subprocess environment sanitization: `CLAUDECODE` env var is removed before spawning `claude -p` to prevent environment leakage and session conflicts

### 4.3 Usability

- Clear startup message confirming the model is ready and listening
- Audio warnings from sounddevice are surfaced with `[audio warning]` prefix
- Transcription errors are surfaced with `[transcription error]` prefix
- Graceful shutdown on `Ctrl+C` with cleanup of threads

---

## 5. Acceptance Criteria

### 5.1 MVP

- [ ] `python stt.py` captures mic audio and prints transcribed text to terminal
- [ ] `python stt.py --agent` pipes each utterance to `claude -p` and prints the response
- [ ] `python stt.py --list-devices` prints available input devices
- [ ] All STT processing is local (no external API calls)
- [ ] Agent mode is non-blocking: audio continues while Claude responds
- [ ] `CLAUDECODE` env var is stripped before spawning Claude subprocess
- [ ] End-to-end latency (speech end → Claude response displayed) is under 10 seconds for short commands
- [ ] STT transcription completes within 2 seconds of silence detection
- [ ] `--debug` flag produces timestamped diagnostic output to stderr without affecting stdout
- [ ] Agent mode defaults to `small` model when `--model` is not specified
- [ ] Slow transcription (>5s) produces a warning suggesting a smaller model

### 5.2 Future Enhancements

- Wake-word detection to toggle listening on/off
- Streaming Claude responses (print tokens as they arrive)
- GUI overlay or status indicator while Claude is processing
- Support for Vosk as an alternative lighter-weight STT backend
- Configurable output format for agent mode responses
- Session history / conversation context for multi-turn Claude interactions

---

*Document maintained by: PO Agent*
*Last updated: 2026-03-09*
