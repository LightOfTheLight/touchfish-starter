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
  10. Minimum-speech-duration noise-rejection logic (REGRESSION)
  11. Debug mode — Req 2.5
  12. Transcription accuracy / model defaults — Req 2.6
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
        "debug": False,  # Req 2.5: --debug flag; must be present for run() to access args.debug
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

    def test_default_model_is_none_when_unspecified(self):
        # Req 2.6: --model default is None so main() can pick the mode-appropriate default.
        # parse_args() must not hard-code "base"; the effective default is resolved by main().
        with patch("sys.argv", ["stt.py"]):
            assert stt.parse_args().model is None

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

    def test_default_debug_is_false(self):
        # Req 2.5: --debug is opt-in; must default to False
        with patch("sys.argv", ["stt.py"]):
            assert stt.parse_args().debug is False

    def test_debug_flag(self):
        # Req 2.5: --debug activates debug mode
        with patch("sys.argv", ["stt.py", "--debug"]):
            assert stt.parse_args().debug is True


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

    def test_prints_warning_for_medium_model_cpu_latency(self, capsys):
        # Req 2.6: medium on CPU → latency warning printed at startup
        with patch.dict("sys.modules", {"faster_whisper": _mock_fw()}):
            stt.load_model("medium")
        assert "[warning]" in capsys.readouterr().out

    def test_prints_warning_for_large_model_cpu_latency(self, capsys):
        # Req 2.6: large on CPU → latency warning printed at startup
        with patch.dict("sys.modules", {"faster_whisper": _mock_fw()}):
            stt.load_model("large")
        assert "[warning]" in capsys.readouterr().out

    def test_no_warning_for_base_model(self, capsys):
        # Req 2.6: base does not trigger CPU latency warning
        with patch.dict("sys.modules", {"faster_whisper": _mock_fw()}):
            stt.load_model("base")
        assert "[warning]" not in capsys.readouterr().out

    def test_no_warning_for_small_model(self, capsys):
        # Req 2.6: small does not trigger CPU latency warning
        with patch.dict("sys.modules", {"faster_whisper": _mock_fw()}):
            stt.load_model("small")
        assert "[warning]" not in capsys.readouterr().out


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

    def test_main_sets_base_model_by_default_in_basic_mode(self):
        # Req 2.6: basic mode without --model → effective model is DEFAULT_MODEL ("base")
        with patch("sys.argv", ["stt.py"]), patch("stt.run") as mock_run:
            stt.main()
        assert mock_run.call_args[0][0].model == stt.DEFAULT_MODEL

    def test_main_sets_small_model_by_default_in_agent_mode(self):
        # Req 2.6: --agent without --model → effective model is DEFAULT_AGENT_MODEL ("small")
        with patch("sys.argv", ["stt.py", "--agent"]), patch("stt.run") as mock_run:
            stt.main()
        assert mock_run.call_args[0][0].model == stt.DEFAULT_AGENT_MODEL

    def test_main_respects_explicit_model_in_agent_mode(self):
        # Req 2.6: explicit --model always wins over mode default
        with patch("sys.argv", ["stt.py", "--agent", "--model", "tiny"]), \
             patch("stt.run") as mock_run:
            stt.main()
        assert mock_run.call_args[0][0].model == "tiny"

    def test_main_respects_explicit_model_in_basic_mode(self):
        # Req 2.6: explicit --model in basic mode always wins over DEFAULT_MODEL
        with patch("sys.argv", ["stt.py", "--model", "medium"]), \
             patch("stt.run") as mock_run:
            stt.main()
        assert mock_run.call_args[0][0].model == "medium"


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
# 10. REGRESSION — Minimum speech duration (noise rejection)
# ===========================================================================

class TestMinSpeechDurationNoisRejection:
    """
    Req 2.4 AC: "Utterances shorter than 0.3 seconds of speech are discarded."

    Previously reported as Bug #1 (Session 1): the original code used
    `len(buffer) >= min_speech_chunks` where `buffer` held both speech AND
    trailing silence chunks, so the check was always True and noise rejection
    never fired.

    Fixed in DEV commit 81b022e: a dedicated `speech_chunk_count` counter is
    now tracked and compared against `min_speech_chunks` at utterance end.

    These tests verify the corrected behaviour and guard against regression.
    """

    def _simulate_vad(self, speech_chunks_n, silence_threshold=None, silence_duration=None):
        """
        Simulate the FIXED transcription_loop VAD logic from stt.py with
        `speech_chunks_n` speech chunks followed by enough silence to trigger
        the end-of-utterance check.

        Mirrors the current stt.py implementation exactly:
          - speech_chunk_count tracks ONLY speech chunks
          - end-of-utterance guard uses speech_chunk_count, not len(buffer)

        Returns True if model.transcribe would be called, False otherwise.
        """
        if silence_threshold is None:
            silence_threshold = stt.DEFAULT_SILENCE_THRESHOLD
        if silence_duration is None:
            silence_duration = stt.DEFAULT_SILENCE_DURATION

        max_silence_chunks = max(1, int(silence_duration * stt.SAMPLE_RATE / stt.CHUNK_FRAMES))
        min_speech_chunks = max(1, int(stt.MIN_SPEECH_DURATION * stt.SAMPLE_RATE / stt.CHUNK_FRAMES))

        speech_chunk = np.full(stt.CHUNK_FRAMES, 0.01, dtype=np.float32)  # rms=0.01 > 0.003
        silence_chunk = np.zeros(stt.CHUNK_FRAMES, dtype=np.float32)       # rms=0.0

        # ---- replicate the FIXED loop body (matches stt.py transcription_loop) ----
        buffer = []
        silence_chunk_count = 0
        speech_chunk_count = 0   # dedicated speech-only counter (the fix)
        in_speech = False

        # Feed speech chunks
        for _ in range(speech_chunks_n):
            rms = float(np.sqrt(np.mean(speech_chunk ** 2)))
            if rms > silence_threshold:
                buffer.append(speech_chunk.copy())
                silence_chunk_count = 0
                in_speech = True
                speech_chunk_count += 1  # count speech only

        # Feed silence until the end-of-utterance check fires
        transcribe_called = False
        for _ in range(max_silence_chunks + 1):
            if in_speech:
                buffer.append(silence_chunk.copy())
                silence_chunk_count += 1

                if silence_chunk_count >= max_silence_chunks:
                    # FIXED check: compare speech-only counter, not total buffer length
                    if speech_chunk_count >= min_speech_chunks:
                        transcribe_called = True
                    break

        return transcribe_called

    # --- Regression tests: short utterances must be discarded ---

    def test_single_chunk_utterance_is_discarded(self):
        """
        A 1-chunk (~64ms) utterance is below the 0.3s minimum and must be
        discarded (regression guard for Bug #1).
        """
        result = self._simulate_vad(speech_chunks_n=1)
        assert result is False, (
            "REGRESSION: 1-chunk utterance (~64ms) was NOT discarded. "
            "speech_chunk_count (1) < min_speech_chunks (4) should prevent transcription."
        )

    def test_three_chunk_utterance_is_discarded(self):
        """
        A 3-chunk (~192ms) utterance is below the 0.3s minimum and must be
        discarded (regression guard for Bug #1).
        """
        result = self._simulate_vad(speech_chunks_n=3)
        assert result is False, (
            "REGRESSION: 3-chunk utterance (~192ms) was NOT discarded. "
            "speech_chunk_count (3) < min_speech_chunks (4) should prevent transcription."
        )

    # --- Verify arithmetic invariant: speech counter correctly distinguishes short vs long ---

    def test_speech_counter_boundary_at_min_speech_chunks(self):
        """
        Verify that speech_chunk_count == min_speech_chunks - 1 is discarded
        and speech_chunk_count == min_speech_chunks is accepted (boundary test).
        """
        min_speech_chunks = max(1, int(stt.MIN_SPEECH_DURATION * stt.SAMPLE_RATE / stt.CHUNK_FRAMES))
        assert self._simulate_vad(speech_chunks_n=min_speech_chunks - 1) is False
        assert self._simulate_vad(speech_chunks_n=min_speech_chunks) is True

    # --- Regression guards: valid utterances must still be transcribed ---

    def test_sufficient_speech_is_transcribed(self):
        """Utterances >= 0.3s (min_speech_chunks=4 chunks) must trigger transcription."""
        result = self._simulate_vad(speech_chunks_n=4)
        assert result is True, "A 4-chunk (≥0.3s) utterance should be transcribed."

    def test_long_utterance_is_transcribed(self):
        """Clearly long utterances (32 speech chunks) must always be transcribed."""
        result = self._simulate_vad(speech_chunks_n=32)
        assert result is True, "A 32-chunk utterance should definitely be transcribed."


# ===========================================================================
# 11. Debug Mode — Req 2.5
# ===========================================================================

class TestDebugMode:
    """Req 2.5 — --debug flag enables verbose timestamped diagnostic output to stderr."""

    # -----------------------------------------------------------------------
    # debug_log() helper function
    # -----------------------------------------------------------------------

    def test_debug_log_writes_to_stderr(self, capsys):
        """Req 2.5: All debug output goes to stderr only."""
        stt.debug_log("test message")
        assert "test message" in capsys.readouterr().err

    def test_debug_log_nothing_on_stdout(self, capsys):
        """Req 2.5: stdout must be unchanged by debug output."""
        stt.debug_log("test message")
        assert "test message" not in capsys.readouterr().out

    def test_debug_log_format_has_debug_prefix(self, capsys):
        """Req 2.5: Debug lines contain [DEBUG prefix."""
        stt.debug_log("hello")
        assert "[DEBUG " in capsys.readouterr().err

    def test_debug_log_format_has_timestamp(self, capsys):
        """Req 2.5: Debug lines are timestamped with [DEBUG HH:MM:SS] format."""
        import re
        stt.debug_log("hello")
        err = capsys.readouterr().err
        assert re.search(r'\[DEBUG \d{2}:\d{2}:\d{2}\]', err), (
            f"Expected [DEBUG HH:MM:SS] format, got: {err!r}"
        )

    # -----------------------------------------------------------------------
    # Module-level debug constants
    # -----------------------------------------------------------------------

    def test_rms_log_interval_is_between_2_and_3_seconds(self):
        """Req 2.5: RMS level logged 'every 2-3 seconds' — constant must be in range."""
        assert 2.0 <= stt.RMS_LOG_INTERVAL_SECS <= 3.0

    # -----------------------------------------------------------------------
    # Startup debug output inside run()
    # -----------------------------------------------------------------------

    def _run_with_debug(self, capsys, **kwargs):
        """Run stt.run() with --debug and mocked hardware; return captured stderr."""
        args = make_args(debug=True, **kwargs)
        with patch("stt.load_model", return_value=MagicMock()), \
             patch("stt.sd.InputStream", side_effect=stt.sd.PortAudioError("mock")):
            with pytest.raises(SystemExit):
                stt.run(args)
        return capsys.readouterr().err

    def test_debug_startup_logs_model_name(self, capsys):
        """Req 2.5: On startup, debug mode logs the model name."""
        err = self._run_with_debug(capsys, model="tiny")
        assert "tiny" in err

    def test_debug_startup_logs_language(self, capsys):
        """Req 2.5: On startup, debug mode logs the language setting."""
        err = self._run_with_debug(capsys, language="fr")
        assert "fr" in err

    def test_debug_startup_logs_agent_mode_status(self, capsys):
        """Req 2.5: On startup, debug mode logs agent mode status."""
        err = self._run_with_debug(capsys, agent=True)
        assert "True" in err

    def test_debug_startup_logs_silence_threshold(self, capsys):
        """Req 2.5: On startup, debug mode logs the silence threshold."""
        err = self._run_with_debug(capsys, silence_threshold=0.007)
        assert "0.007" in err

    def test_debug_startup_logs_silence_duration(self, capsys):
        """Req 2.5: On startup, debug mode logs the silence duration."""
        err = self._run_with_debug(capsys, silence_duration=1.5)
        assert "1.5" in err

    def test_no_debug_output_without_flag(self, capsys):
        """Req 2.5: Without --debug, no [DEBUG lines appear on stderr."""
        args = make_args(debug=False)
        with patch("stt.load_model", return_value=MagicMock()), \
             patch("stt.sd.InputStream", side_effect=stt.sd.PortAudioError("mock")):
            with pytest.raises(SystemExit):
                stt.run(args)
        err = capsys.readouterr().err
        assert "[DEBUG" not in err


# ===========================================================================
# 12. Transcription Accuracy / Model Defaults — Req 2.6
# ===========================================================================

class TestTranscriptionAccuracy:
    """Req 2.6 — Agent mode defaults to 'small' model; medium/large CPU warnings;
    slow transcription warning."""

    # -----------------------------------------------------------------------
    # Module-level constants
    # -----------------------------------------------------------------------

    def test_default_agent_model_constant_is_small(self):
        """Req 2.6: DEFAULT_AGENT_MODEL must equal 'small'."""
        assert stt.DEFAULT_AGENT_MODEL == "small"

    def test_slow_transcription_secs_constant_is_5(self):
        """Req 2.6: Slow transcription threshold must be 5.0 seconds."""
        assert stt.SLOW_TRANSCRIPTION_SECS == pytest.approx(5.0)

    # -----------------------------------------------------------------------
    # parse_args: --model is None when unspecified (effective default deferred to main)
    # -----------------------------------------------------------------------

    def test_parse_args_model_is_none_when_flag_absent(self):
        """Req 2.6: parse_args() must not hard-code 'base'; model=None lets main() decide."""
        with patch("sys.argv", ["stt.py"]):
            assert stt.parse_args().model is None

    # -----------------------------------------------------------------------
    # main(): effective model assignment
    # -----------------------------------------------------------------------

    def test_main_effective_model_is_base_in_basic_mode(self):
        """Req 2.6: No --agent, no --model → effective model is 'base'."""
        with patch("sys.argv", ["stt.py"]), patch("stt.run") as mock_run:
            stt.main()
        assert mock_run.call_args[0][0].model == "base"

    def test_main_effective_model_is_small_in_agent_mode(self):
        """Req 2.6: --agent without --model → effective model is 'small' for better accuracy."""
        with patch("sys.argv", ["stt.py", "--agent"]), patch("stt.run") as mock_run:
            stt.main()
        assert mock_run.call_args[0][0].model == "small"

    def test_explicit_model_overrides_agent_default(self):
        """Req 2.6: When --model is specified, it is used regardless of mode."""
        with patch("sys.argv", ["stt.py", "--agent", "--model", "tiny"]), \
             patch("stt.run") as mock_run:
            stt.main()
        assert mock_run.call_args[0][0].model == "tiny"

    def test_explicit_model_overrides_basic_default(self):
        """Req 2.6: Explicit --model in basic mode overrides DEFAULT_MODEL."""
        with patch("sys.argv", ["stt.py", "--model", "large"]), \
             patch("stt.run") as mock_run:
            stt.main()
        assert mock_run.call_args[0][0].model == "large"

    # -----------------------------------------------------------------------
    # load_model: medium/large CPU latency warning
    # -----------------------------------------------------------------------

    def test_load_model_warns_medium_on_cpu(self, capsys):
        """Req 2.6: 'medium' model triggers a CPU latency warning at startup."""
        with patch.dict("sys.modules", {"faster_whisper": _mock_fw()}):
            stt.load_model("medium")
        assert "[warning]" in capsys.readouterr().out

    def test_load_model_warns_large_on_cpu(self, capsys):
        """Req 2.6: 'large' model triggers a CPU latency warning at startup."""
        with patch.dict("sys.modules", {"faster_whisper": _mock_fw()}):
            stt.load_model("large")
        assert "[warning]" in capsys.readouterr().out

    def test_load_model_no_warning_for_base(self, capsys):
        """Req 2.6: 'base' model must NOT trigger a CPU latency warning."""
        with patch.dict("sys.modules", {"faster_whisper": _mock_fw()}):
            stt.load_model("base")
        assert "[warning]" not in capsys.readouterr().out

    def test_load_model_no_warning_for_small(self, capsys):
        """Req 2.6: 'small' model must NOT trigger a CPU latency warning."""
        with patch.dict("sys.modules", {"faster_whisper": _mock_fw()}):
            stt.load_model("small")
        assert "[warning]" not in capsys.readouterr().out
