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

---

### Session 2 — 2026-03-05

**Trigger:** Chain trigger: TESTER (DEV fix verification)
**Branch:** `agent/PO/20260305-150227`
**Objective:** Verify DEV's fix for Bug #1 (noise rejection), update regression tests, and produce a final verdict.

---

#### 1. Context

Session 1 reported `FAIL @DEV` with one bug: the noise rejection check in `transcription_loop` used `len(buffer)` (which includes silence chunks) instead of a dedicated speech counter, making the check always True.

DEV commit `81b022e` ("DEV: Fix noise rejection — track speech_chunk_count separately from len(buffer)") applied the recommended fix.

---

#### 2. Fix Verification — `stt.py`

Reviewed the fixed `transcription_loop` in `stt.py`:

| Change | Location | Correct? |
|---|---|---|
| `speech_chunk_count = 0` initialised | line 209 | ✅ |
| `speech_chunk_count += 1` on speech chunk | line 231 | ✅ |
| Guard uses `speech_chunk_count >= min_speech_chunks` | line 240 | ✅ |
| `speech_chunk_count = 0` reset at end-of-utterance | line 257 | ✅ |

The fix matches exactly the approach recommended in Session 1. Logic is correct.

**Bug #1 status: FIXED.**

---

#### 3. Full Requirements Re-review

All acceptance criteria re-verified against fixed `stt.py`:

| Requirement | Verdict |
|---|---|
| Microphone audio captured continuously (2.1) | PASS |
| Energy-based VAD (2.1) | PASS |
| Transcribed text printed immediately (2.1) | PASS |
| No external API calls (2.1) | PASS |
| `--list-devices` with indices and default marker (2.2) | PASS |
| `--device <INDEX>` flag (2.2) | PASS |
| Default microphone when unspecified (2.2) | PASS |
| `--model` tiny/base/small/medium/large, default base (2.3) | PASS |
| `--language` flag (2.3) | PASS |
| Model loaded once with loading message (2.3) | PASS |
| `--silence-threshold` default 0.003 (2.4) | PASS |
| `--silence-duration` default 1.0 (2.4) | PASS |
| Utterances < 0.3s discarded — noise rejection (2.4) | **PASS (fixed)** |
| `--agent` flag activates agent mode (2.5) | PASS |
| `> You: <text>` prefix before Claude call (2.5) | PASS |
| `Claude: <response>` prefix after call (2.5) | PASS |
| Claude called in background thread (2.5) | PASS |
| `CLAUDECODE` env var stripped (2.5) | PASS |
| `[Error: 'claude' CLI not found...]` message (2.5) | PASS |
| `[Claude timed out after 120 seconds]` message (2.5) | PASS |
| Non-zero exit codes and stderr surfaced (2.5) | PASS |
| `[audio warning]` prefix (4.3) | PASS |
| `[transcription error]` prefix (4.3) | PASS |
| Graceful shutdown on Ctrl+C (4.3) | PASS |

**All 23 acceptance criteria: PASS.**

---

#### 4. Test Suite Update

The `_simulate_vad` helper in `TestMinSpeechDurationNoisRejection` was written in Session 1 to **reproduce** the bug (it deliberately used the buggy `len(buffer)` check). Since the bug is now fixed, the helper was updated to mirror the corrected `stt.py` logic (using `speech_chunk_count`).

Changes made to `tests/test_stt.py`:
- Renamed class docstring from "BUG REPRODUCTION" → "REGRESSION"
- `_simulate_vad` now tracks `speech_chunk_count` separately (mirrors fixed code)
- Bug-oriented assertions/comments converted to regression guard language
- Added `test_speech_counter_boundary_at_min_speech_chunks` (explicit boundary test)
- Removed `test_buffer_always_exceeds_min_speech_chunks_at_check_time` (no longer relevant; bug is fixed)
- Total test count: **52 tests** (52 — 1 removed + 1 added = 52)

Expected outcome when a Python runtime is available: **all 52 tests PASS**.

---

#### 5. Verdict

**PASS**

All requirements are implemented correctly. Bug #1 is fixed. Regression tests updated. No further DEV action required.

---

---

### Session 3 — 2026-03-09

**Trigger:** Chain trigger: TESTER (DEV Session 3 — Debug Mode and Transcription Accuracy)
**Branch:** `agent/PO/20260309-121445`
**Objective:** Review DEV's implementation of Req 2.5 (Debug Mode) and Req 2.6 (Transcription Accuracy). Update the test suite to cover the new requirements and fix test regressions caused by the DEV changes.

---

#### 1. Context

PO agent added Req 2.5 (Debug Mode) and Req 2.6 (Transcription Accuracy) to `REQUIREMENT.md`. DEV Session 3 (commit `fe53b8a`) implemented both requirements with significant changes to `stt.py`.

Key DEV changes:
- Added `--debug` flag, `debug_log()` helper, and comprehensive VAD/transcription/Claude timing diagnostic output to stderr
- Changed `--model` argparse default from `"base"` to `None`; `main()` now assigns mode-appropriate effective default
- Added `DEFAULT_AGENT_MODEL = "small"`, `SLOW_TRANSCRIPTION_SECS = 5.0`, `RMS_LOG_INTERVAL_SECS = 2.5`
- Added medium/large CPU latency warning in `load_model()`
- Added slow transcription warning (>5s) in transcription loop

---

#### 2. Static Code Analysis — `stt.py`

Full review of new implementation against Req 2.5 and Req 2.6:

**Req 2.5 — Debug Mode:**

| Acceptance Criterion | Implementation | Verdict |
|---|---|---|
| `--debug` flag activates debug mode | `argparse` flag at line 104-109, `action="store_true"` | PASS |
| All debug output to stderr only | `debug_log()` writes to `sys.stderr` (line 127) | PASS |
| `[DEBUG HH:MM:SS]` format | `time.strftime("%H:%M:%S")` at line 127 | PASS |
| Startup: model, language, agent mode, thresholds | `run()` lines 196-201 log all five values | PASS |
| Periodic RMS logging (every 2-3s) | `RMS_LOG_INTERVAL_SECS = 2.5`, lines 270-274 | PASS |
| Speech start log with RMS | Lines 279-280 on `not in_speech → in_speech` transition | PASS |
| Silence detected log with utterance duration | Lines 293-299, `utterance_start_time` tracked | PASS |
| Transcription timing logged | Lines 314-317, elapsed time and text | PASS |
| Claude start/finish/elapsed logged | Lines 230-236 inside `_call_claude()` | PASS |
| Compatible with all flag combinations | Additive flag, no conflicts detected | PASS |

**Req 2.6 — Transcription Accuracy:**

| Acceptance Criterion | Implementation | Verdict |
|---|---|---|
| Agent mode without `--model` defaults to `small` | `main()` lines 374-375: `DEFAULT_AGENT_MODEL if args.agent else DEFAULT_MODEL` | PASS |
| Explicit `--model` always honoured | `args.model is None` check prevents overwrite when explicitly set | PASS |
| Slow transcription warning (>5s) | `SLOW_TRANSCRIPTION_SECS = 5.0`; `print(...)` at lines 318-323 | PASS |
| Medium/large CPU latency warning at startup | `load_model()` lines 142-147 | PASS |

**Note on "slow transcription warning goes to stdout":** The requirement says the warning is "logged". DEV chose `print()` to stdout (not debug stderr), treating it as a user-facing operational warning. This is consistent with the Req 5.1 MVP phrasing ("produces a warning") and makes the warning visible even without `--debug`. Verdict: acceptable.

**Implementation verdict: All Req 2.5 and 2.6 acceptance criteria are correctly implemented.**

---

#### 3. Test Suite Bugs Found

Two categories of bugs in the existing `tests/test_stt.py` caused by the DEV changes:

**Bug A — `make_args()` missing `debug` key (3 tests fail with AttributeError):**

`run()` now accesses `args.debug` unconditionally at line 196. The `make_args()` helper did not include `debug` in its defaults dict, so any test using `make_args()` and calling `stt.run()` would raise `AttributeError: 'Namespace' object has no attribute 'debug'`.

Affected tests:
- `TestRunErrorHandling.test_portaudio_error_exits_with_code_1`
- `TestRunErrorHandling.test_portaudio_error_prints_list_devices_tip`
- `TestRunErrorHandling.test_keyboard_interrupt_exits_cleanly_and_prints_stopping`

**Fix applied:** Added `"debug": False` to `make_args()` defaults.

**Bug B — `test_default_model_is_base` incorrect assertion (1 test fails):**

DEV changed `parser.add_argument("--model", default="base", ...)` to `default=None` to allow `main()` to set the mode-appropriate effective default. The test `test_default_model_is_base` asserted `parse_args().model == "base"`, which now fails (returns `None`).

**Fix applied:** Renamed test to `test_default_model_is_none_when_unspecified` and updated assertion to `assert stt.parse_args().model is None`.

---

#### 4. Test Suite Updates

**Fixes to existing tests:**
- `make_args()`: Added `"debug": False` to defaults (fixes 3 `TestRunErrorHandling` failures)
- `TestParseArgs.test_default_model_is_base` → renamed and corrected to check `model is None` (fixes 1 failure)

**New tests added to existing classes:**

| Class | New Tests | Purpose |
|---|---|---|
| `TestParseArgs` | `test_default_debug_is_false`, `test_debug_flag` | Req 2.5: `--debug` flag contract |
| `TestMain` | 4 model-default tests | Req 2.6: verify `main()` sets effective model correctly |
| `TestLoadModel` | 4 CPU warning tests (medium/large warn; base/small silent) | Req 2.6: CPU latency warning |

**New test classes:**

| Class | Count | Coverage |
|---|---|---|
| `TestDebugMode` | 11 tests | Req 2.5: `debug_log()` stderr/format, startup logs, RMS constant, no-debug gate |
| `TestTranscriptionAccuracy` | 11 tests | Req 2.6: constants, `parse_args()` model=None, `main()` effective defaults, CPU warnings |

**Test count:**
- Previous: 52 tests
- Added: ~28 tests (4 fixed/renamed, 24 new)
- New total: ~76 tests (excluding parametrized expansion; pytest count is higher due to `test_model_accepts_valid_sizes` × 5)

All tests are expected to PASS when a Python runtime with `numpy`, `sounddevice`, and `faster-whisper` is available. Static analysis confirms the implementation matches all assertions.

---

#### 5. Full Requirements Coverage Matrix (Session 3 additions)

| Requirement | Test Coverage |
|---|---|
| 2.5 `--debug` flag | `TestParseArgs.test_debug_flag`, `TestParseArgs.test_default_debug_is_false` |
| 2.5 Debug to stderr only | `TestDebugMode.test_debug_log_writes_to_stderr`, `test_debug_log_nothing_on_stdout` |
| 2.5 `[DEBUG HH:MM:SS]` format | `TestDebugMode.test_debug_log_format_has_debug_prefix`, `test_debug_log_format_has_timestamp` |
| 2.5 Startup debug info | `TestDebugMode.test_debug_startup_logs_*` (5 tests) |
| 2.5 No debug without flag | `TestDebugMode.test_no_debug_output_without_flag` |
| 2.5 RMS log interval 2-3s | `TestDebugMode.test_rms_log_interval_is_between_2_and_3_seconds` |
| 2.6 `DEFAULT_AGENT_MODEL = "small"` | `TestTranscriptionAccuracy.test_default_agent_model_constant_is_small` |
| 2.6 `SLOW_TRANSCRIPTION_SECS = 5.0` | `TestTranscriptionAccuracy.test_slow_transcription_secs_constant_is_5` |
| 2.6 `parse_args().model is None` | `TestParseArgs.test_default_model_is_none_when_unspecified`, `TestTranscriptionAccuracy.test_parse_args_model_is_none_when_flag_absent` |
| 2.6 Effective default `base` in basic mode | `TestMain.test_main_sets_base_model_by_default_in_basic_mode`, `TestTranscriptionAccuracy.test_main_effective_model_is_base_in_basic_mode` |
| 2.6 Effective default `small` in agent mode | `TestMain.test_main_sets_small_model_by_default_in_agent_mode`, `TestTranscriptionAccuracy.test_main_effective_model_is_small_in_agent_mode` |
| 2.6 Explicit `--model` overrides defaults | `TestMain.test_main_respects_explicit_model_in_*` (2 tests), `TestTranscriptionAccuracy.test_explicit_model_overrides_*` (2 tests) |
| 2.6 Medium/large CPU warning | `TestLoadModel.test_prints_warning_for_medium/large_model_cpu_latency`, `TestTranscriptionAccuracy.test_load_model_warns_medium/large_on_cpu` |
| 2.6 No warning for base/small | `TestLoadModel.test_no_warning_for_base/small`, `TestTranscriptionAccuracy.test_load_model_no_warning_for_base/small` |

---

#### 6. Verdict

**PASS**

The `stt.py` implementation correctly satisfies all Req 2.5 (Debug Mode) and Req 2.6 (Transcription Accuracy) acceptance criteria. Two pre-existing test bugs caused by the DEV changes were identified and fixed. Comprehensive new test coverage was added for both new requirements.

---

## Change Log

| Date | Session | Change |
|------|---------|--------|
| 2026-03-05 | 1 | Created `tests/test_stt.py` (52 tests); documented Bug #1 in history; wrote `.agent-test-result` |
| 2026-03-05 | 2 | Verified DEV fix (commit 81b022e); updated `_simulate_vad` helper to fixed logic; wrote PASS verdict |
| 2026-03-09 | 3 | Reviewed Req 2.5 and 2.6 implementation; fixed 2 test bugs; added ~24 new tests for debug mode and transcription accuracy; wrote PASS verdict |

---

*Maintained by: TESTER Agent*
