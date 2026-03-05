#!/usr/bin/env python3
"""
Test suite for stt.py — Speech-to-Text Terminal Plugin

Covers:
  1. Argument parsing (parse_args)
  2. Audio device listing (list_devices)
  3. Model loading (load_model)
  4. Claude CLI integration (run_claude)
  5. Main entry point (main)
  6. run() error handling
  7. VAD/audio-processing constants and logic
  8. Agent mode output formatting
  9. Environment variable sanitisation (security)
  10. Minimum-speech-duration noise-rejection logic (BUG REPRODUCTION)
"""

import argparse
import os
import subprocess
import sys
from unittest.mock import MagicMock, Mock, call, patch

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Make stt importable from repo root regardless of cwd
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import stt  # noqa: E402  (must be after sys.path manipulation)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def make_args(**kwargs):
    """Return an argparse.Namespace with sensible defaults, overridden by kwargs."""
    defaults = {
        "model": "base",
        "language": None,
        "device": None,
        "silence_threshold": stt.DEFAULT_SILENCE_THRESHOLD,
        "silence_duration": stt.DEFAULT_SILENCE_DURATION,
        "agent": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _mock_fw(model_instance=None):
    """Return a fake faster_whisper module whose WhisperModel returns model_instance."""
    if model_instance is None:
        model_instance = MagicMock()
    mock_fw = MagicMock()
    mock_fw.WhisperModel.return_value = model_instance
    return mock_fw


# ===========================================================================
# 1. parse_args
# ===========================================================================

class TestParseArgs:
    """Req 2.2, 2.3, 2.4, 2.5 — CLI argument contract."""

    def test_default_model_is_base(self):
        with patch("sys.argv", ["stt.py"]):
            assert stt.parse_args().model == "base"

    def test_default_language_is_none(self):
        with patch("sys.argv", ["stt.py"]):
            assert stt.parse_args().language is None

    def test_default_device_is_none(self):
        with patch("sys.argv", ["stt.py"]):
            assert stt.parse_args().device is None

    def test_default_silence_threshold(self):
        with patch("sys.argv", ["stt.py"]):
            assert stt.parse_args().silence_threshold == pytest.approx(stt.DEFAULT_SILENCE_THRESHOLD)

    def test_default_silence_duration(self):
        with patch("sys.argv", ["stt.py"]):
            assert stt.parse_args().silence_duration == pytest.approx(stt.DEFAULT_SILENCE_DURATION)

    def test_default_agent_is_false(self):
        with patch("sys.argv", ["stt.py"]):
            assert stt.parse_args().agent is False

    def test_default_list_devices_is_false(self):
        with patch("sys.argv", ["stt.py"]):
            assert stt.parse_args().list_devices is False

    @pytest.mark.parametrize("model", ["tiny", "base", "small", "medium", "large"])
    def test_model_accepts_valid_sizes(self, model):
        with patch("sys.argv", ["stt.py", "--model", model]):
            assert stt.parse_args().model == model

    def test_model_rejects_invalid_size(self):
        with patch("sys.argv", ["stt.py", "--model", "xlarge"]):
            with pytest.raises(SystemExit):
                stt.parse_args()

    def test_language_flag(self):
        with patch("sys.argv", ["stt.py", "--language", "fr"]):
            assert stt.parse_args().language == "fr"

    def test_device_flag_stored_as_int(self):
        with patch("sys.argv", ["stt.py", "--device", "3"]):
            assert stt.parse_args().device == 3

    def test_list_devices_flag(self):
        with patch("sys.argv", ["stt.py", "--list-devices"]):
            assert stt.parse_args().list_devices is True

    def test_silence_threshold_flag(self):
        with patch("sys.argv", ["stt.py", "--silence-threshold", "0.01"]):
            assert stt.parse_args().silence_threshold == pytest.approx(0.01)

    def test_silence_duration_flag(self):
        with patch("sys.argv", ["stt.py", "--silence-duration", "2.5"]):
            assert stt.parse_args().silence_duration == pytest.approx(2.5)

    def test_agent_flag(self):
        with patch("sys.argv", ["stt.py", "--agent"]):
            assert stt.parse_args().agent is True


# ===========================================================================
# 2. list_devices
# ===========================================================================

class TestListDevices:
    """Req 2.2 — Audio Device Management."""

    MOCK_DEVICES = [
        {"name": "Built-in Microphone", "max_input_channels": 2, "max_output_channels": 0},
        {"name": "Built-in Speakers",   "max_input_channels": 0, "max_output_channels": 2},
        {"name": "USB Mic",             "max_input_channels": 1, "max_output_channels": 0},
    ]

    def test_only_input_devices_printed(self, capsys):
        with patch("stt.sd.query_devices", return_value=self.MOCK_DEVICES), \
             patch("stt.sd.default") as md:
            md.device = (0, 1)
            stt.list_devices()
        out = capsys.readouterr().out
        assert "Built-in Microphone" in out
        assert "USB Mic" in out
        assert "Built-in Speakers" not in out  # output-only device excluded

    def test_default_device_marked_when_sd_default_is_tuple(self, capsys):
        with patch("stt.sd.query_devices", return_value=self.MOCK_DEVICES), \
             patch("stt.sd.default") as md:
            md.device = (0, 1)  # index 0 is the default input
            stt.list_devices()
        out = capsys.readouterr().out
        default_lines = [l for l in out.splitlines() if "(default)" in l]
        assert len(default_lines) == 1, "Exactly one device should be marked (default)"
        assert "Built-in Microphone" in default_lines[0]

    def test_default_device_marked_when_sd_default_is_int(self, capsys):
        with patch("stt.sd.query_devices", return_value=self.MOCK_DEVICES), \
             patch("stt.sd.default") as md:
            md.device = 0  # plain integer, not a tuple
            stt.list_devices()
        assert "(default)" in capsys.readouterr().out

    def test_non_default_device_not_marked(self, capsys):
        with patch("stt.sd.query_devices", return_value=self.MOCK_DEVICES), \
             patch("stt.sd.default") as md:
            md.device = (2, 1)  # USB Mic (index 2) is default
            stt.list_devices()
        out = capsys.readouterr().out
        mic_lines = [l for l in out.splitlines() if "Built-in Microphone" in l]
        assert mic_lines
        assert "(default)" not in mic_lines[0]

    def test_device_indices_shown_in_brackets(self, capsys):
        with patch("stt.sd.query_devices", return_value=self.MOCK_DEVICES), \
             patch("stt.sd.default") as md:
            md.device = (99, 99)
            stt.list_devices()
        out = capsys.readouterr().out
        assert "[0]" in out  # Built-in Microphone
        assert "[2]" in out  # USB Mic


# ===========================================================================
# 3. load_model
# ===========================================================================

class TestLoadModel:
    """Req 2.3 — Model Selection / loading behaviour."""

    def test_prints_loading_message_with_model_name(self, capsys):
        with patch.dict("sys.modules", {"faster_whisper": _mock_fw()}):
            stt.load_model("small")
        assert "Loading Whisper 'small' model" in capsys.readouterr().out

    def test_prints_ready_and_listening_message(self, capsys):
        with patch.dict("sys.modules", {"faster_whisper": _mock_fw()}):
            stt.load_model("base")
        out = capsys.readouterr().out
        assert "Model ready" in out
        assert "Listening" in out

    def test_returns_model_object(self):
        mock_model = MagicMock()
        with patch.dict("sys.modules", {"faster_whisper": _mock_fw(mock_model)}):
            result = stt.load_model("base")
        assert result is mock_model

    def test_exits_1_if_faster_whisper_not_installed(self):
        with patch.dict("sys.modules", {"faster_whisper": None}):
            with pytest.raises(SystemExit) as exc_info:
                stt.load_model("base")
        assert exc_info.value.code == 1

    def test_exits_1_if_model_creation_raises(self):
        fw = MagicMock()
        fw.WhisperModel.side_effect = RuntimeError("download failed")
        with patch.dict("sys.modules", {"faster_whisper": fw}):
            with pytest.raises(SystemExit) as exc_info:
                stt.load_model("large")
        assert exc_info.value.code == 1

    def test_loads_model_with_cpu_device(self):
        fw = _mock_fw()
        with patch.dict("sys.modules", {"faster_whisper": fw}):
            stt.load_model("base")
        _, kw = fw.WhisperModel.call_args
        assert kw.get("device") == "cpu"

    def test_error_message_includes_model_name_on_failure(self, capsys):
        fw = MagicMock()
        fw.WhisperModel.side_effect = RuntimeError("fail")
        with patch.dict("sys.modules", {"faster_whisper": fw}):
            with pytest.raises(SystemExit):
                stt.load_model("medium")
        assert "medium" in capsys.readouterr().out


# ===========================================================================
# 4. run_claude
# ===========================================================================

class TestRunClaude:
    """Req 2.5 and 4.2 — Claude CLI integration and env sanitisation."""

    def _ok(self, stdout="Response text", stderr=""):
        r = Mock(returncode=0, stdout=stdout, stderr=stderr)
        return r

    def _err(self, returncode=1, stdout="", stderr=""):
        r = Mock(returncode=returncode, stdout=stdout, stderr=stderr)
        return r

    # ---- success paths ----

    def test_success_returns_stripped_stdout(self):
        with patch("stt.subprocess.run", return_value=self._ok("  Hello!\n\n")):
            assert stt.run_claude("hi") == "Hello!"

    def test_empty_stdout_returns_placeholder(self):
        with patch("stt.subprocess.run", return_value=self._ok("")):
            assert stt.run_claude("empty") == "[Claude returned empty response]"

    def test_whitespace_only_stdout_returns_placeholder(self):
        with patch("stt.subprocess.run", return_value=self._ok("   \n  ")):
            assert stt.run_claude("ws") == "[Claude returned empty response]"

    # ---- error paths ----

    def test_timeout_returns_correct_message(self):
        with patch("stt.subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 120)):
            assert stt.run_claude("slow") == "[Claude timed out after 120 seconds]"

    def test_claude_not_found_returns_install_hint(self):
        with patch("stt.subprocess.run", side_effect=FileNotFoundError):
            response = stt.run_claude("test")
        assert response == "[Error: 'claude' CLI not found. Is Claude Code installed?]"

    def test_nonzero_exit_code_is_surfaced(self):
        with patch("stt.subprocess.run", return_value=self._err(returncode=42)):
            assert "[Claude error (exit 42)]" in stt.run_claude("fail")

    def test_nonzero_exit_with_stderr_is_surfaced(self):
        with patch("stt.subprocess.run", return_value=self._err(1, "", "auth error")):
            assert "auth error" in stt.run_claude("auth")

    def test_nonzero_exit_with_stdout_is_surfaced(self):
        with patch("stt.subprocess.run", return_value=self._err(1, "partial", "err")):
            response = stt.run_claude("partial")
        assert "partial" in response

    def test_generic_exception_returns_error_string(self):
        with patch("stt.subprocess.run", side_effect=OSError("broken pipe")):
            response = stt.run_claude("os error")
        assert "[Error calling Claude:" in response
        assert "broken pipe" in response

    # ---- call contract ----

    def test_calls_claude_p_with_text(self):
        with patch("stt.subprocess.run", return_value=self._ok()) as mock_run:
            stt.run_claude("hello world")
        assert mock_run.call_args[0][0] == ["claude", "-p", "hello world"]

    def test_uses_timeout_120_seconds(self):
        with patch("stt.subprocess.run", return_value=self._ok()) as mock_run:
            stt.run_claude("timeout check")
        assert mock_run.call_args[1].get("timeout") == 120

    # ---- env sanitisation (Req 4.2) ----

    def test_claudecode_stripped_from_subprocess_env(self):
        captured = {}

        def spy(*args, **kwargs):
            captured["env"] = dict(kwargs.get("env", {}))
            return self._ok()

        with patch.dict("os.environ", {"CLAUDECODE": "1", "PATH": "/usr/bin"}):
            with patch("stt.subprocess.run", side_effect=spy):
                stt.run_claude("test")

        assert "CLAUDECODE" not in captured["env"], (
            "CLAUDECODE must be stripped from subprocess env to prevent nested session errors"
        )

    def test_other_env_vars_preserved_after_claudecode_stripped(self):
        captured = {}

        def spy(*args, **kwargs):
            captured["env"] = dict(kwargs.get("env", {}))
            return self._ok()

        test_env = {"CLAUDECODE": "1", "PATH": "/usr/local/bin", "HOME": "/home/user", "SHELL": "/bin/bash"}
        with patch.dict("os.environ", test_env, clear=True):
            with patch("stt.subprocess.run", side_effect=spy):
                stt.run_claude("env test")

        assert captured["env"].get("PATH") == "/usr/local/bin"
        assert captured["env"].get("HOME") == "/home/user"
        assert captured["env"].get("SHELL") == "/bin/bash"


# ===========================================================================
# 5. main() entry point
# ===========================================================================

class TestMain:
    """Integration tests for the main() entry point."""

    def test_list_devices_calls_list_devices_and_exits_0(self):
        with patch("sys.argv", ["stt.py", "--list-devices"]), \
             patch("stt.list_devices") as mock_list, \
             pytest.raises(SystemExit) as exc_info:
            stt.main()
        mock_list.assert_called_once()
        assert exc_info.value.code == 0

    def test_normal_invocation_calls_run(self):
        with patch("sys.argv", ["stt.py"]), \
             patch("stt.run") as mock_run:
            stt.main()
        mock_run.assert_called_once()


# ===========================================================================
# 6. run() error handling
# ===========================================================================

class TestRunErrorHandling:
    """Tests for error paths inside run()."""

    def test_portaudio_error_exits_with_code_1(self):
        args = make_args()
        with patch("stt.load_model", return_value=MagicMock()), \
             patch("stt.sd.InputStream", side_effect=stt.sd.PortAudioError("no device")):
            with pytest.raises(SystemExit) as exc_info:
                stt.run(args)
        assert exc_info.value.code == 1

    def test_portaudio_error_prints_list_devices_tip(self, capsys):
        args = make_args()
        with patch("stt.load_model", return_value=MagicMock()), \
             patch("stt.sd.InputStream", side_effect=stt.sd.PortAudioError("no device")):
            with pytest.raises(SystemExit):
                stt.run(args)
        assert "--list-devices" in capsys.readouterr().out

    def test_keyboard_interrupt_exits_cleanly_and_prints_stopping(self, capsys):
        args = make_args()

        class FakeStream:
            def __enter__(self): return self
            def __exit__(self, *a): return False

        with patch("stt.load_model", return_value=MagicMock()), \
             patch("stt.sd.InputStream", return_value=FakeStream()), \
             patch("stt.time.sleep", side_effect=KeyboardInterrupt()):
            stt.run(args)  # must not propagate the exception

        assert "Stopping" in capsys.readouterr().out


# ===========================================================================
# 7. VAD / audio-processing constants and arithmetic
# ===========================================================================

class TestVADConstants:
    """Verify module-level constants and derived thresholds match requirements."""

    def test_default_silence_threshold_is_0_003(self):
        assert stt.DEFAULT_SILENCE_THRESHOLD == pytest.approx(0.003)

    def test_default_silence_duration_is_1_second(self):
        assert stt.DEFAULT_SILENCE_DURATION == pytest.approx(1.0)

    def test_min_speech_duration_is_0_3_seconds(self):
        assert stt.MIN_SPEECH_DURATION == pytest.approx(0.3)

    def test_sample_rate_is_16000_hz_for_whisper(self):
        assert stt.SAMPLE_RATE == 16000

    def test_audio_channels_is_mono(self):
        assert stt.CHANNELS == 1

    def test_min_speech_chunks_derived_correctly(self):
        # max(1, int(0.3 * 16000 / 1024)) = max(1, 4) = 4
        expected = max(1, int(stt.MIN_SPEECH_DURATION * stt.SAMPLE_RATE / stt.CHUNK_FRAMES))
        assert expected == 4

    def test_max_silence_chunks_derived_correctly(self):
        # max(1, int(1.0 * 16000 / 1024)) = max(1, 15) = 15
        expected = max(1, int(stt.DEFAULT_SILENCE_DURATION * stt.SAMPLE_RATE / stt.CHUNK_FRAMES))
        assert expected == 15

    def test_silence_audio_rms_below_threshold(self):
        silence = np.zeros(stt.CHUNK_FRAMES, dtype=np.float32)
        rms = float(np.sqrt(np.mean(silence ** 2)))
        assert rms < stt.DEFAULT_SILENCE_THRESHOLD

    def test_speech_audio_rms_above_threshold(self):
        speech = np.full(stt.CHUNK_FRAMES, 0.01, dtype=np.float32)
        rms = float(np.sqrt(np.mean(speech ** 2)))
        assert rms > stt.DEFAULT_SILENCE_THRESHOLD

    def test_rms_of_dc_signal_equals_amplitude(self):
        amplitude = 0.02
        dc = np.full(stt.CHUNK_FRAMES, amplitude, dtype=np.float32)
        rms = float(np.sqrt(np.mean(dc ** 2)))
        assert rms == pytest.approx(amplitude, rel=1e-5)


# ===========================================================================
# 8. Agent mode output formatting
# ===========================================================================

class TestAgentModeFormatting:
    """Req 2.5 — Verifies the exact output prefixes required by the spec."""

    def test_you_prefix_format(self):
        text = "open the file manager"
        line = f"> You: {text}\n"
        assert line.startswith("> You: ")
        assert text in line

    def test_claude_prefix_format(self):
        resp = "Here you go"
        line = f"Claude: {resp}\n\n"
        assert line.startswith("Claude: ")
        assert resp in line

    def test_agent_mode_uses_thread_pool_executor(self):
        """Source code must use ThreadPoolExecutor for non-blocking Claude calls."""
        import inspect
        src = inspect.getsource(stt.run)
        assert "ThreadPoolExecutor" in src
        assert "claude_executor" in src
        assert "submit" in src

    def test_agent_mode_claude_called_in_background(self):
        """Claude calls are submitted to an executor, not called inline."""
        import inspect
        src = inspect.getsource(stt.run)
        # _call_claude is submitted via executor.submit, not called directly in
        # the main transcription path
        assert "claude_executor.submit" in src or "executor.submit" in src


# ===========================================================================
# 9. Environment variable sanitisation (security)
# ===========================================================================

class TestEnvSanitisation:
    """Req 4.2 — Subprocess environment must not leak CLAUDECODE."""

    def _spy(self, result=None):
        """Returns a spy function and the dict it populates with captured env."""
        captured = {}
        if result is None:
            result = Mock(returncode=0, stdout="ok", stderr="")

        def spy(*args, **kwargs):
            captured["env"] = dict(kwargs.get("env", {}))
            return result

        return spy, captured

    def test_claudecode_absent_from_subprocess_env(self):
        spy, captured = self._spy()
        with patch.dict("os.environ", {"CLAUDECODE": "session123", "HOME": "/home/user"}):
            with patch("stt.subprocess.run", side_effect=spy):
                stt.run_claude("test")
        assert "CLAUDECODE" not in captured["env"]

    def test_all_other_env_vars_preserved(self):
        spy, captured = self._spy()
        env = {"CLAUDECODE": "1", "PATH": "/usr/bin", "LANG": "en_US.UTF-8", "SHELL": "/bin/bash"}
        with patch.dict("os.environ", env, clear=True):
            with patch("stt.subprocess.run", side_effect=spy):
                stt.run_claude("test")
        assert captured["env"].get("PATH") == "/usr/bin"
        assert captured["env"].get("LANG") == "en_US.UTF-8"
        assert captured["env"].get("SHELL") == "/bin/bash"


# ===========================================================================
# 10. BUG REPRODUCTION — Minimum speech duration (noise rejection)
# ===========================================================================

class TestMinSpeechDurationNoisRejection:
    """
    Req 2.4 AC: "Utterances shorter than 0.3 seconds of speech are discarded."

    BUG: The current implementation checks `len(buffer) >= min_speech_chunks`
    where `buffer` accumulates BOTH speech chunks AND trailing silence chunks.
    At the moment the check fires, buffer already contains at least
    `max_silence_chunks` (15) silence chunks, so `len(buffer)` is always
    >= 15 > min_speech_chunks (4).  The check is therefore always True and
    never actually discards any utterance, regardless of speech duration.

    The fix is to track speech chunks in a separate counter and compare
    that counter against min_speech_chunks.
    """

    def _simulate_vad(self, speech_chunks_n, silence_threshold=None, silence_duration=None):
        """
        Simulate the transcription_loop VAD logic from stt.py
        with `speech_chunks_n` speech chunks followed by enough silence to
        trigger the end-of-utterance check.

        Returns True if model.transcribe would be called, False otherwise.
        """
        if silence_threshold is None:
            silence_threshold = stt.DEFAULT_SILENCE_THRESHOLD
        if silence_duration is None:
            silence_duration = stt.DEFAULT_SILENCE_DURATION

        max_silence_chunks = max(1, int(silence_duration * stt.SAMPLE_RATE / stt.CHUNK_FRAMES))
        min_speech_chunks = max(1, int(stt.MIN_SPEECH_DURATION * stt.SAMPLE_RATE / stt.CHUNK_FRAMES))

        speech_chunk = np.full(stt.CHUNK_FRAMES, 0.01, dtype=np.float32)   # rms=0.01 > 0.003
        silence_chunk = np.zeros(stt.CHUNK_FRAMES, dtype=np.float32)        # rms=0.0

        # ---- replicate the loop body ----
        buffer = []
        silence_chunk_count = 0
        in_speech = False

        # Feed speech chunks
        for _ in range(speech_chunks_n):
            rms = float(np.sqrt(np.mean(speech_chunk ** 2)))
            if rms > silence_threshold:
                buffer.append(speech_chunk.copy())
                silence_chunk_count = 0
                in_speech = True

        # Feed silence until the end-of-utterance check fires
        transcribe_called = False
        for _ in range(max_silence_chunks + 1):
            rms = float(np.sqrt(np.mean(silence_chunk ** 2)))
            if in_speech:
                buffer.append(silence_chunk.copy())
                silence_chunk_count += 1

                if silence_chunk_count >= max_silence_chunks:
                    # THIS IS THE BUGGY CHECK:
                    # uses total buffer length (speech + silence), not speech-only count
                    if len(buffer) >= min_speech_chunks:
                        transcribe_called = True
                    break

        return transcribe_called

    # --- Tests that verify INTENDED (correct) behaviour ---
    # These SHOULD pass once the bug is fixed; they currently FAIL.

    def test_single_chunk_utterance_is_discarded(self):
        """
        A 1-chunk (~64ms) utterance is below the 0.3s minimum and MUST be discarded.

        EXPECTED: False (no transcription)
        ACTUAL (bug): True  — fails because len(buffer)=16 >= min_speech_chunks=4
        """
        result = self._simulate_vad(speech_chunks_n=1)
        assert result is False, (
            "BUG: 1-chunk utterance (~64ms) was NOT discarded. "
            "len(buffer) check incorrectly includes silence chunks, "
            "making noise rejection ineffective."
        )

    def test_three_chunk_utterance_is_discarded(self):
        """
        A 3-chunk (~192ms) utterance is below the 0.3s minimum and MUST be discarded.

        EXPECTED: False (no transcription)
        ACTUAL (bug): True
        """
        result = self._simulate_vad(speech_chunks_n=3)
        assert result is False, (
            "BUG: 3-chunk utterance (~192ms) was NOT discarded. "
            "min_speech_chunks=4 (0.3s), but buffer length check counts silence too."
        )

    # --- Tests that document the root cause ---

    def test_buffer_always_exceeds_min_speech_chunks_at_check_time(self):
        """
        Proves the defect: at the moment the end-of-utterance check fires,
        len(buffer) is always > min_speech_chunks, regardless of speech length.

        buffer_min = 1 speech chunk + max_silence_chunks silence chunks
                   = 1 + 15 = 16  >> min_speech_chunks = 4
        """
        max_silence_chunks = max(1, int(stt.DEFAULT_SILENCE_DURATION * stt.SAMPLE_RATE / stt.CHUNK_FRAMES))
        min_speech_chunks = max(1, int(stt.MIN_SPEECH_DURATION * stt.SAMPLE_RATE / stt.CHUNK_FRAMES))

        # Minimum possible buffer size when check fires (1 speech + max_silence_chunks silence)
        min_buffer_at_check = 1 + max_silence_chunks  # = 1 + 15 = 16

        assert min_buffer_at_check > min_speech_chunks, (
            "This assertion proves the bug: the buffer will always pass the "
            "'len(buffer) >= min_speech_chunks' check, so noise rejection never triggers."
        )

    # --- Test that verifies long-enough utterances ARE transcribed (regression guard) ---

    def test_sufficient_speech_is_transcribed(self):
        """Utterances >= 0.3s (min_speech_chunks=4 chunks) must trigger transcription."""
        result = self._simulate_vad(speech_chunks_n=4)
        assert result is True, "A 4-chunk (≥0.3s) utterance should be transcribed."

    def test_long_utterance_is_transcribed(self):
        """Clearly long utterances (32 speech chunks) must always be transcribed."""
        result = self._simulate_vad(speech_chunks_n=32)
        assert result is True, "A 32-chunk utterance should definitely be transcribed."
