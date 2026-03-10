# DEV Agent History

## Session Log

---

### Session 1 — 2026-03-05

**Trigger:** Commit `6380214` — "PO: Formalize requirements for STT terminal plugin with agent mode"

**Branch:** `agent/PO/20260305-150227`

**Context:**

The PO agent had already formalized `REQUIREMENT.md` from README.md. Prior DEV sessions produced a near-complete `stt.py` implementing the STT terminal plugin. This DEV session performs a gap analysis and delivers any missing pieces.

**Gap Analysis:**

Compared every REQUIREMENT.md acceptance criterion against the existing `stt.py`:

| Requirement | Status | Notes |
|-------------|--------|-------|
| 2.1 Continuous mic capture | ✅ Implemented | `sounddevice.InputStream` with callback |
| 2.1 Energy-based VAD | ✅ Implemented | RMS threshold per chunk |
| 2.1 Transcribe on silence | ✅ Implemented | `transcription_loop()` accumulates buffer |
| 2.1 Print text immediately | ✅ Implemented | `handle_transcription()` flushes stdout |
| 2.1 No cloud API calls | ✅ Implemented | `faster-whisper` runs locally on CPU |
| 2.2 `--list-devices` flag | ✅ Implemented | `list_devices()` marks default |
| 2.2 `--device <INDEX>` | ✅ Implemented | Passed to `sd.InputStream` |
| 2.2 System default fallback | ✅ Implemented | `device=None` uses system default |
| 2.3 `--model` with 5 sizes | ✅ Implemented | choices validated by argparse |
| 2.3 `--language` with auto | ✅ Implemented | `language=None` → auto-detect |
| 2.3 Model loaded once | ✅ Implemented | `load_model()` called once in `run()` |
| 2.4 `--silence-threshold` | ✅ Implemented | default 0.003 |
| 2.4 `--silence-duration` | ✅ Implemented | default 1.0s |
| 2.4 Min speech 0.3s reject | ✅ Implemented | `MIN_SPEECH_DURATION = 0.3` |
| 2.5 `--agent` flag | ✅ Implemented | |
| 2.5 `> You:` output format | ✅ Implemented | |
| 2.5 `Claude:` response format | ✅ Implemented | |
| 2.5 Non-blocking Claude calls | ✅ Implemented | `ThreadPoolExecutor(max_workers=1)` |
| 2.5 Strip `CLAUDECODE` env | ✅ Implemented | dict comprehension strips it |
| 2.5 Missing CLI error | ✅ Implemented | `FileNotFoundError` → clear message |
| 2.5 120s timeout message | ✅ Implemented | `TimeoutExpired` → message |
| 2.5 Non-zero exit surfaced | ⚠️ **BUG FIXED** | See below |

**Bug Found & Fixed — `run_claude` exit code surfacing:**

The original code used `if result.returncode != 0 and result.stderr`. If Claude exited non-zero but produced no stderr, the condition was False and the function fell through to return stdout as if it were a success response. The requirement explicitly states "Non-zero exit codes and stderr output from Claude are surfaced to the user."

Fixed to:
```python
if result.returncode != 0:
    parts = [f"[Claude error (exit {result.returncode})]"]
    if result.stderr:
        parts.append(result.stderr.strip())
    if result.stdout:
        parts.append(result.stdout.strip())
    return ": ".join(parts)
```

This ensures any non-zero exit is always flagged, and includes both stderr and stdout in the error message when present.

**New Files Created:**

- `requirements.txt` — declares the three runtime dependencies (`faster-whisper`, `sounddevice`, `numpy`) so users can install with `pip install -r requirements.txt`

**Decisions & Assumptions:**

| Item | Decision |
|------|----------|
| Existing implementation | Preserved in full; only targeted the one bug |
| requirements.txt versions | Used `>=` lower bounds matching the API surface used; not pinned to avoid unnecessary constraint |
| No test file | TESTER agent not yet triggered; testability not in scope for this session |
| Docstring/comment changes | None — only changed code that was directly fixing the bug |

**Files Modified:**
- `stt.py` — Fixed `run_claude` non-zero exit handling (lines 151–153)
- `requirements.txt` — Created with three runtime dependencies
- `agents/DEV/history.md` — This file

---

---

### Session 2 — 2026-03-05

**Trigger:** Chain trigger from TESTER — `FAIL @DEV` verdict on Bug #1

**Branch:** `agent/PO/20260305-150227`

**Context:**

TESTER agent completed a static analysis of `stt.py` against all `REQUIREMENT.md` acceptance criteria. 50/52 tests were expected to pass; 2 tests were expected to FAIL, both reproducing Bug #1: the minimum speech duration (noise rejection) check was always True.

**Bug Fixed — Noise Rejection (Bug #1):**

**Root cause (from TESTER analysis):**
`transcription_loop` tracked `len(buffer)` to test for minimum speech duration. However, `buffer` accumulates both speech and trailing silence chunks. By the time the end-of-utterance check fires (after `max_silence_chunks = 15` silence chunks), `len(buffer) >= 16` regardless of how few speech chunks were present. Since `min_speech_chunks = 4`, the condition `len(buffer) >= 4` was always True — noise rejection never fired.

**Fix applied:**
Added a dedicated `speech_chunk_count` counter that increments only when `rms > args.silence_threshold` (i.e., only on actual speech chunks). Changed the utterance length guard from `len(buffer) >= min_speech_chunks` to `speech_chunk_count >= min_speech_chunks`. Reset `speech_chunk_count = 0` alongside the other counters at end-of-utterance.

```python
# Before (always True — bug):
if len(buffer) >= min_speech_chunks:

# After (correctly tracks speech-only chunks):
if speech_chunk_count >= min_speech_chunks:
```

**Files Modified:**
- `stt.py` — Fixed `transcription_loop` noise rejection (lines 209, 231, 240, 257)
- `agents/DEV/history.md` — This file

**Decisions & Assumptions:**

| Item | Decision |
|------|----------|
| Fix scope | Minimal — only the three-line change needed; no other code altered |
| Comment updated | Updated inline comment at the guard from "if long enough" to "if enough speech (not silence) was captured" for clarity |
| test_stt.py | Not modified — TESTER owns that file; the 2 previously-failing tests should now pass |

---

---

### Session 3 — 2026-03-09

**Trigger:** Chain trigger from PO — new requirements added in commit `90198ab` ("PO: Add Debug Mode and Transcription Accuracy requirements")

**Branch:** `agent/PO/20260309-121445`

**Context:**

PO agent added two new requirement sections to `REQUIREMENT.md`:
- **2.5 Debug Mode** — `--debug` flag with verbose timestamped diagnostic output to stderr
- **2.6 Transcription Accuracy** — Agent mode defaults to `small` model; medium/large CPU warnings; slow transcription warning

**Gap Analysis:**

| Requirement | Prior Status | Action Taken |
|-------------|-------------|--------------|
| 2.5 `--debug` flag | ❌ Missing | Added to argparse |
| 2.5 Debug output to stderr only | ❌ Missing | `debug_log()` writes to `sys.stderr` |
| 2.5 Timestamped `[DEBUG HH:MM:SS]` format | ❌ Missing | `debug_log()` uses `time.strftime("%H:%M:%S")` |
| 2.5 Startup: model, language, agent mode, thresholds | ❌ Missing | Added at top of `run()` |
| 2.5 Periodic RMS logging (~2-3s interval) | ❌ Missing | `last_rms_log_time` tracking in `transcription_loop()` |
| 2.5 Speech start log with RMS | ❌ Missing | Logged on `in_speech` transition |
| 2.5 Silence detected log with utterance duration | ❌ Missing | `utterance_start_time` tracked; logged at end-of-utterance |
| 2.5 Transcription timing logged | ❌ Missing | `t_transcribe` timer; logged after `model.transcribe()` |
| 2.5 Claude start/finish/elapsed logged | ❌ Missing | Added to `_call_claude()` in `handle_transcription()` |
| 2.6 Agent mode default `small` | ❌ Missing | `--model` default changed to `None`; `main()` sets effective default |
| 2.6 Explicit `--model` overrides mode default | ✅ Now correct | `args.model is None` check in `main()` |
| 2.6 Medium/large CPU latency warning at startup | ❌ Missing | Added to `load_model()` |
| 2.6 Slow transcription warning (>5s) | ❌ Missing | `SLOW_TRANSCRIPTION_SECS = 5.0`; logged after transcription |

**Implementation Details:**

**`--model` default handling:**

Changed from `default=DEFAULT_MODEL` (always `"base"`) to `default=None`. In `main()`, after `parse_args()`:
```python
if args.model is None:
    args.model = DEFAULT_AGENT_MODEL if args.agent else DEFAULT_MODEL
```
This correctly handles all three cases: no flag (mode-appropriate default), explicit flag (always honoured), agent flag without model flag (defaults to `small`).

**`debug_log()` function:**
```python
def debug_log(message: str) -> None:
    ts = time.strftime("%H:%M:%S")
    sys.stderr.write(f"[DEBUG {ts}] {message}\n")
    sys.stderr.flush()
```
Module-level helper. All call sites guard with `if args.debug:` (available via closure or local scope), so the function itself doesn't need the flag.

**Periodic RMS logging:**
Used `last_rms_log_time` float (initialized to `0.0`) compared against `time.time()` with a `RMS_LOG_INTERVAL_SECS = 2.5` threshold. Logged unconditionally each interval (regardless of speech/silence state) to help with threshold tuning.

**Utterance duration tracking:**
Added `utterance_start_time: Optional[float] = None` to `transcription_loop()`. Set on the `not in_speech → in_speech` transition, reset to `None` at end-of-utterance cleanup.

**Claude timing:**
Moved inside `_call_claude()` closure which already has access to `args` via closure. Start/finish debug lines added with `time.time()` elapsed.

**New Constants:**
- `DEFAULT_AGENT_MODEL = "small"`
- `SLOW_TRANSCRIPTION_SECS = 5.0`
- `RMS_LOG_INTERVAL_SECS = 2.5`

**Files Modified:**
- `stt.py` — Implemented all new requirements (debug mode, model defaults, warnings)
- `agents/DEV/history.md` — This file

**Decisions & Assumptions:**

| Item | Decision |
|------|----------|
| Slow transcription warning | Goes to stdout (print) not debug stderr — it's a user-facing operational warning, not a debug diagnostic |
| Medium/large warning | Printed unconditionally (not gated on --debug) per requirement: "a warning is printed" |
| RMS interval | 2.5s (midpoint of 2–3s range specified in requirement) |
| debug_log prompt truncation | Full prompt logged in `_call_claude` debug line — short commands are typical; no truncation needed |
| list_devices order | List-devices check kept before model assignment in `main()` — device listing doesn't need a model |

---

---

### Session 4 — 2026-03-10

**Trigger:** Chain trigger from PO — commit `da7adee` ("PO: Update requirements for Windows debug fix and silence threshold")

**Branch:** `agent/PO/20260310-154557`

**Context:**

PO updated two requirements in `REQUIREMENT.md` to reflect field-tested findings from hotfix `57a8b99`:

1. **Req 2.4 Silence Detection:** Default silence threshold raised from `0.003` → `0.01`. Field testing confirmed `0.003` is too sensitive for typical ambient noise environments (fans, HVAC, keyboard sounds).

2. **Req 2.5 Debug Mode:** Debug output channel changed from stderr to stdout (binary buffer, UTF-8 encoded). `sys.stderr` has an invalid handle on some Windows terminals (WinError 6). The hotfix (`57a8b99`) had already patched `debug_log()` in `stt.py` to use `sys.stdout.buffer`; however, `DEFAULT_SILENCE_THRESHOLD` and the `--debug` argparse help text were not updated, and the test suite still asserted the old stderr behaviour.

**Gap Analysis:**

| Item | Prior State | Action Taken |
|------|-------------|--------------|
| `DEFAULT_SILENCE_THRESHOLD` in `stt.py` | `0.003` | Updated to `0.01` |
| `--debug` argparse help text | "to stderr" | Updated to "to stdout" |
| `test_default_silence_threshold_is_0_003` | Asserted `0.003` | Renamed and updated to assert `0.01` |
| `test_speech_audio_rms_above_threshold` | Speech chunk `0.01` (equal to new threshold, not above) | Changed to `0.02` so rms > threshold |
| `_simulate_vad` speech chunk | `0.01` (equal to new threshold — never classified as speech) | Changed to `0.02` and updated comment |
| `TestDebugMode` class docstring | "to stderr" | Updated to "to stdout" |
| `test_debug_log_writes_to_stderr` | Checked `.err` | Renamed to `test_debug_log_writes_to_stdout`; checks `.out` |
| `test_debug_log_nothing_on_stdout` | Asserted message NOT in `.out` | Renamed to `test_debug_log_nothing_on_stderr`; asserts message NOT in `.err` |
| `test_debug_log_format_has_debug_prefix` | Checked `.err` | Updated to check `.out` |
| `test_debug_log_format_has_timestamp` | Checked `.err` | Updated to check `.out` |
| `_run_with_debug` helper | Returned `capsys.readouterr().err` | Updated to return `.out` |
| `test_no_debug_output_without_flag` | Checked `.err` for `[DEBUG` | Updated to check `.out` |

**Key decision — speech chunk amplitude in tests:**

The VAD simulation uses `np.full(CHUNK_FRAMES, amplitude)` where amplitude == rms for a DC signal. The VAD check is `rms > silence_threshold` (strictly greater than). With the new threshold of `0.01`, any test using amplitude `0.01` would be classified as silence (equal, not greater). Changed all such test chunks to amplitude `0.02` to remain clearly above the threshold.

**Files Modified:**
- `stt.py` — Updated `DEFAULT_SILENCE_THRESHOLD` (0.003→0.01) and `--debug` help text (stderr→stdout)
- `tests/test_stt.py` — Updated 10 test locations to align with new threshold and stdout debug output
- `agents/DEV/history.md` — This file

**Decisions & Assumptions:**

| Item | Decision |
|------|----------|
| `debug_log()` implementation | Already correct (hotfix 57a8b99); no change needed |
| Speech chunk amplitude in tests | 0.02 (strictly above 0.01 threshold, clean margin) |
| Other test assertions | Unchanged — all other tests remain valid with new threshold |

---

## Change Log

| Date | Session | Change |
|------|---------|--------|
| 2026-03-05 | Session 1 | Gap analysis; fixed run_claude exit code bug; added requirements.txt |
| 2026-03-05 | Session 2 | Fixed Bug #1: noise rejection always-True condition (speech_chunk_count vs len(buffer)) |
| 2026-03-09 | Session 3 | Implemented Debug Mode (Req 2.5) and Transcription Accuracy (Req 2.6) |
| 2026-03-10 | Session 4 | Updated silence threshold (0.003→0.01), debug output channel (stderr→stdout); aligned tests |

---

*Maintained by: DEV Agent*
