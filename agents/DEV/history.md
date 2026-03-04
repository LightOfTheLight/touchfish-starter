# DEV Agent History

## Session Log

---

### Session 1 — 2026-03-04

**Branch:** `agent/PO/20260304-114253`
**Trigger:** Chain trigger from PO agent (commit: "docs(PO): formalize STT terminal plugin requirements")
**Task:** Implement the Speech-to-Text terminal plugin as specified in REQUIREMENT.md.

#### What I read
- `REQUIREMENT.md` — full functional and technical requirements
- `agents/DEV/DEV.md` — role definition and constraints
- `README.md` — project template context
- `.agent-chain-origin` — chain origin: `dev/stt-terminal-plugin`

#### Implementation approach

**Architecture decision: Single-file vs package**
Chose a single `stt.py` script. The requirements ask for `python stt.py` invocation and the logic is straightforward enough that a package would be over-engineering for MVP.

**Audio capture: sounddevice**
Chose `sounddevice` over `pyaudio` because:
- Simpler callback-based API
- Cross-platform without needing to build PortAudio manually on Windows
- Better NumPy integration (returns float32 arrays directly)

**STT model: faster-whisper**
Chose `faster-whisper` as the Whisper runtime because:
- More CPU-efficient than the original `openai-whisper` package (uses CTranslate2)
- Int8 quantization reduces memory and speeds up inference on CPU
- Meets the < 2 second latency target for the `base` model on a modern CPU
- Built-in `vad_filter=True` provides secondary VAD on top of our RMS detection

**VAD (Voice Activity Detection) approach**
Used energy-based (RMS) VAD with configurable threshold and silence duration:
- Simple, dependency-free, and works offline
- Configurable via `--silence-threshold` and `--silence-duration` flags
- Falls back gracefully — if background noise is high, user can tune threshold

**Threading model**
- Audio capture runs in `sounddevice`'s internal callback thread
- Audio chunks are passed via `queue.Queue` (thread-safe)
- A separate `transcription_loop` thread consumes the queue, applies VAD, and calls Whisper
- This prevents blocking the audio callback with slow CPU inference

**Sample rate**
Fixed at 16000 Hz — Whisper's native sample rate. Some devices may not support this natively; added a clear error message directing users to `--list-devices`.

#### Files created
| File | Purpose |
|------|---------|
| `stt.py` | Main CLI entry point — audio capture, VAD, transcription, output |
| `requirements.txt` | Python dependencies with system prerequisite comments |
| `QUICKSTART.md` | Setup guide with copy-paste commands and troubleshooting |

#### Assumptions documented
1. **README.md not modified** — DEV.md marks README as user-owned. Created `QUICKSTART.md` instead to satisfy the "README must include a Quick Start guide" requirement.
2. **GPU support omitted from default** — requirements say CPU must be supported; GPU is optional. `faster-whisper` auto-detects CUDA if available, but we explicitly set `device="cpu"` for predictable behaviour. Can be made configurable in a future iteration.
3. **`--output file.txt` flag** — listed in REQUIREMENT.md §5.2 as a future enhancement; not implemented in MVP.
4. **Pipe mode** (`--file audio.wav`) — also listed as future enhancement; not implemented.

#### Requirements coverage (MVP checklist)
- [x] Single command start (`python stt.py`)
- [x] Spoken words appear in terminal within ~2 seconds
- [x] Runs without internet after model download
- [x] Graceful shutdown on Ctrl+C
- [x] `requirements.txt` provided
- [x] Quick start guide (`QUICKSTART.md`)
- [x] `--help` flag
- [x] Model selection (`--model`)
- [x] Language flag (`--language`)
- [x] Input device flag (`--device`)
- [x] Non-zero exit code on error
- [x] Output is clean (no debug noise on stdout; informational messages go to stderr)

---

## Change Log

| Date | Session | Change |
|------|---------|--------|
| 2026-03-04 | 1 | Initial implementation: `stt.py`, `requirements.txt`, `QUICKSTART.md` |

---

*Maintained by: DEV Agent*
