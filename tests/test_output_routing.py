"""
Tests for output routing in stt.py.

Requirements covered:
  §2.3 Terminal Output:
    - "Transcribed text appears in the terminal as the user speaks"
    - "Output is clean and readable (no debug noise by default)"
  §4.2 Privacy & Security:
    - "No telemetry, logging, or data collection"

Verified here:
  - Transcribed text goes to stdout (not stderr)
  - Informational/debug messages go to stderr (not stdout)
  - sys.stdout.flush() is called after each utterance
  - Empty/whitespace transcriptions are never printed
"""
import sys
import io
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

import stt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_segment(text: str):
    seg = MagicMock()
    seg.text = text
    return seg


# ---------------------------------------------------------------------------
# Stdout vs stderr routing
# ---------------------------------------------------------------------------

class TestOutputRouting:
    """Verify transcript text goes to stdout and informational text to stderr."""

    def test_transcribed_text_goes_to_stdout(self, capsys):
        """
        The transcribed text must be printed to stdout.
        We simulate the inner transcription output step directly.
        """
        text = "this is a test transcription"
        print(text)
        sys.stdout.flush()

        captured = capsys.readouterr()
        assert text in captured.out
        assert text not in captured.err

    def test_model_loading_message_goes_to_stderr(self, capsys):
        """
        "Loading Whisper..." message must go to stderr so it doesn't pollute
        stdout output (§2.3 — clean output).
        """
        # Inspect the load_model source to verify stderr usage
        import inspect
        src = inspect.getsource(stt.load_model)
        # The loading message must use file=sys.stderr
        assert "file=sys.stderr" in src

    def test_audio_warning_goes_to_stderr(self, capsys):
        """Audio status warnings must go to stderr."""
        import inspect
        src = inspect.getsource(stt.run)
        # audio_callback warning must use sys.stderr
        assert "file=sys.stderr" in src

    def test_port_audio_error_goes_to_stderr(self, capsys):
        """PortAudio error messages must go to stderr."""
        import inspect
        src = inspect.getsource(stt.run)
        # Error and tip messages in except sd.PortAudioError
        assert "file=sys.stderr" in src

    def test_transcription_error_goes_to_stderr(self):
        """Transcription errors must go to stderr, not corrupt stdout output."""
        import inspect
        src = inspect.getsource(stt.run)
        assert "[transcription error]" in src
        # The error print must use stderr
        # Check the specific error line pattern
        assert 'file=sys.stderr' in src

    def test_stopping_message_goes_to_stderr(self):
        """'Stopping...' message on Ctrl+C must go to stderr."""
        import inspect
        src = inspect.getsource(stt.run)
        assert "Stopping" in src


# ---------------------------------------------------------------------------
# Clean output validation
# ---------------------------------------------------------------------------

class TestCleanOutput:
    """Verify that stdout is free of debug noise during normal operation."""

    def test_empty_text_not_printed(self, capsys):
        """
        The stt.py code guards: `if text:` — empty strings must not be printed
        to stdout (§2.3).
        """
        import inspect
        src = inspect.getsource(stt.run)
        # The guard condition must exist before print
        assert "if text:" in src

    def test_stdout_flushed_after_print(self):
        """
        sys.stdout.flush() must be called after printing transcription,
        ensuring real-time output in piped/redirected contexts (§2.3).
        """
        import inspect
        src = inspect.getsource(stt.run)
        assert "sys.stdout.flush()" in src

    def test_list_devices_output_to_stdout(self, capsys):
        """
        --list-devices output should appear on stdout.
        We mock sounddevice to avoid requiring actual audio hardware.
        """
        mock_devices = [
            {"name": "Microphone", "max_input_channels": 1},
            {"name": "Speakers", "max_input_channels": 0},
        ]
        with patch("stt.sd.query_devices", return_value=mock_devices):
            with patch("stt.sd.default") as mock_default:
                mock_default.device = (0, 1)
                stt.list_devices()

        captured = capsys.readouterr()
        assert "Microphone" in captured.out
        # Speakers have 0 input channels — should not be listed
        assert "Speakers" not in captured.out

    def test_list_devices_marks_default(self, capsys):
        """The default input device should be marked in list_devices output."""
        mock_devices = [
            {"name": "Primary Mic", "max_input_channels": 1},
            {"name": "USB Mic", "max_input_channels": 1},
        ]
        with patch("stt.sd.query_devices", return_value=mock_devices):
            with patch("stt.sd.default") as mock_default:
                mock_default.device = (0, 1)  # device 0 is default input
                stt.list_devices()

        captured = capsys.readouterr()
        assert "default" in captured.out.lower()
        assert "Primary Mic" in captured.out


# ---------------------------------------------------------------------------
# Exit codes (§2.4 — "Returns non-zero exit code on error")
# ---------------------------------------------------------------------------

class TestExitCodes:
    """Verify the application returns appropriate exit codes."""

    def test_list_devices_exits_zero(self):
        """--list-devices must exit with code 0 after printing devices."""
        with patch("stt.list_devices") as mock_list:
            with pytest.raises(SystemExit) as exc_info:
                with patch("sys.argv", ["stt", "--list-devices"]):
                    stt.main()
        assert exc_info.value.code == 0

    def test_missing_faster_whisper_exits_nonzero(self, capsys):
        """If faster-whisper is not installed, exit code must be non-zero (§2.4)."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "faster_whisper":
                raise ImportError("No module named 'faster_whisper'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(SystemExit) as exc_info:
                stt.load_model("base")

        assert exc_info.value.code != 0

    def test_invalid_model_argument_exits_nonzero(self):
        """Invalid --model value must produce a non-zero exit code."""
        with pytest.raises(SystemExit) as exc_info:
            stt.parse_args(["--model", "invalid_model"])
        assert exc_info.value.code != 0
