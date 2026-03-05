# TESTER Agent History

## Session Log

---

### Session 1 — 2026-03-05

**Trigger:** Chain trigger from PO/DEV pipeline
**Branch:** `agent/PO/20260305-150227`
**Objective:** Review the STT terminal plugin implementation (`stt.py`) against `REQUIREMENT.md` and create a comprehensive automated test suite.

---

#### 1. Approach

No Python runtime was available in the execution environment, so testing was conducted via **thorough static code analysis** of `stt.py` against every acceptance criterion in `REQUIREMENT.md`. A full automated test suite was written to `tests/test_stt.py` for future execution when a runtime is available.

---

#### 2. Code Review Coverage

| Requirement | Section | Verdict |
|---|---|---|
| Microphone audio captured continuously | 2.1 | PASS — `sd.InputStream` with callback queuing chunks |
| Energy-based VAD detects speech start/end | 2.1 | PARTIAL (see Bug #1) |
| Transcribed text printed immediately after transcription | 2.1 | PASS |
| No external API calls | 2.1 | PASS — all inference is local via faster-whisper |
| `--list-devices` flag | 2.2 | PASS |
| `--device <INDEX>` flag | 2.2 | PASS |
| Default microphone when no device specified | 2.2 | PASS |
| `--model` accepts tiny/base/small/medium/large | 2.3 | PASS |
| `--language <LANG>` flag | 2.3 | PASS |
| Model loaded once at startup with loading message | 2.3 | PASS |
| `--silence-threshold` flag (default 0.003) | 2.4 | PASS |
| `--silence-duration` flag (default 1.0) | 2.4 | PASS |
| Utterances shorter than 0.3s discarded | 2.4 | **FAIL — Bug #1** |
| `--agent` flag activates agent mode | 2.5 | PASS |
| `> You: <text>` prefix displayed before Claude call | 2.5 | PASS |
| `Claude: <response>` prefix displayed after call | 2.5 | PASS |
| Claude called in background thread (non-blocking) | 2.5 | PASS — `ThreadPoolExecutor` |
| `CLAUDECODE` env var stripped | 2.5 | PASS |
| `[Error: 'claude' CLI not found. Is Claude Code installed?]` message | 2.5 | PASS |
| `[Claude timed out after 120 seconds]` message | 2.5 | PASS |
| Non-zero exit codes and stderr surfaced | 2.5 | PASS |
| `[audio warning]` prefix on sounddevice warnings | 4.3 | PASS |
| `[transcription error]` prefix on transcription errors | 4.3 | PASS |
| Graceful shutdown on Ctrl+C | 4.3 | PASS |

---

#### 3. Bug Found

##### Bug #1 — Minimum Speech Duration Check is Ineffective (Noise Rejection Broken)

**Location:** `stt.py`, line 238
**Requirement:** Req 2.4 — "Utterances shorter than 0.3 seconds of speech are discarded (noise rejection)"
**Severity:** Medium — feature doesn't work as documented; could cause spurious Claude calls in agent mode

**Root Cause:**

The `transcription_loop` checks utterance length as:
```python
if len(buffer) >= min_speech_chunks:
    # transcribe
```

However, `buffer` accumulates **both speech chunks AND trailing silence chunks**. The end-of-utterance check fires only after `silence_chunk_count >= max_silence_chunks` (15 chunks = 1.0s of silence). This means at the moment the check runs:

```
len(buffer) = speech_chunks + silence_chunks
            = 1..N  +  ≥15
            = ≥16
```

Since `min_speech_chunks = 4`, the check `len(buffer) >= 4` is **always true**, regardless of how short the speech was. Even a single 64ms speech chunk (1 chunk, far below the 0.3s / 4-chunk minimum) will pass and be sent to Whisper.

**Proof:**
```
min_buffer_at_check_time = 1 (speech) + 15 (silence) = 16
min_speech_chunks         = 4
16 >= 4  → always True  → noise rejection never fires
```

**Required Fix (DEV):**
Track speech chunks in a separate counter and compare that counter (not `len(buffer)`) against `min_speech_chunks`:

```python
speech_chunk_count = 0

if rms > args.silence_threshold:
    buffer.append(chunk)
    silence_chunk_count = 0
    in_speech = True
    speech_chunk_count += 1          # ← track speech separately

elif in_speech:
    buffer.append(chunk)
    silence_chunk_count += 1

    if silence_chunk_count >= max_silence_chunks:
        if speech_chunk_count >= min_speech_chunks:  # ← use speech count, not len(buffer)
            # transcribe
        buffer.clear()
        silence_chunk_count = 0
        speech_chunk_count = 0       # ← reset
        in_speech = False
```

---

#### 4. Test Suite Created

**File:** `tests/test_stt.py`
**Total test cases:** 52 tests across 10 test classes

| Class | Count | Area |
|---|---|---|
| `TestParseArgs` | 15 | CLI argument parsing |
| `TestListDevices` | 5 | Audio device listing |
| `TestLoadModel` | 7 | Model loading |
| `TestRunClaude` | 13 | Claude CLI integration |
| `TestMain` | 2 | Entry point |
| `TestRunErrorHandling` | 3 | PortAudioError, KeyboardInterrupt |
| `TestVADConstants` | 10 | Audio constants and RMS arithmetic |
| `TestAgentModeFormatting` | 4 | Output format verification |
| `TestEnvSanitisation` | 2 | CLAUDECODE env stripping |
| `TestMinSpeechDurationNoisRejection` | 5 | Bug reproduction (expect 2 FAIL) |

**Tests expected to FAIL** (confirming Bug #1):
- `test_single_chunk_utterance_is_discarded`
- `test_three_chunk_utterance_is_discarded`

All other 50 tests are expected to PASS once a Python runtime + dependencies are available.

---

#### 5. Verdict

**FAIL @DEV**

One bug found:
1. `stt.py:238` — minimum speech duration (noise rejection) check is ineffective because `len(buffer)` counts silence chunks, making the condition always true.

---

## Change Log

| Date | Session | Change |
|------|---------|--------|
| 2026-03-05 | 1 | Created `tests/test_stt.py` (52 tests); documented Bug #1 in history; wrote `.agent-test-result` |

---

*Maintained by: TESTER Agent*
