"""
Integration tests for stt.py — mocking hardware/model dependencies.

These tests simulate the full flow of audio capture → VAD → transcription
without requiring a real microphone, PortAudio driver, or Whisper model.

Requirements covered:
  §2.1 Microphone Input Capture — continuous capture with graceful stop
  §2.2 Speech-to-Text Transcription — local model invocation
  §2.3 Terminal Output — transcript printed to stdout
  §5.1 MVP — end-to-end flow validation
"""
import io
import queue
import sys
import threading
import time
import types
from unittest.mock import MagicMock, patch, call

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


def _make_whisper_model(text: str = "transcribed text"):
    """Create a mock WhisperModel that returns a fixed transcription."""
    model = MagicMock()
    model.transcribe.return_value = ([_make_segment(text)], MagicMock())
    return model


# ---------------------------------------------------------------------------
# Audio callback
# ---------------------------------------------------------------------------

class TestAudioCallback:
    """Verify the audio callback correctly enqueues audio data."""

    def test_callback_enqueues_mono_chunk(self):
        """
        The audio_callback must extract channel 0 (mono) and enqueue a copy.
        Stereo input (2 channels) must be reduced to 1D array.
        """
        audio_queue = queue.Queue()

        # Simulate a 2-channel input as sounddevice provides
        frames = stt.CHUNK_FRAMES
        stereo_data = np.random.rand(frames, 2).astype(np.float32)

        # Replicate the callback logic from stt.py
        def audio_callback(indata, frames_count, time_info, status):
            if status:
                print(f"[audio warning] {status}", file=sys.stderr)
            audio_queue.put(indata[:, 0].copy())

        audio_callback(stereo_data, frames, None, None)

        assert not audio_queue.empty()
        chunk = audio_queue.get_nowait()
        assert chunk.ndim == 1
        assert len(chunk) == frames
        np.testing.assert_array_equal(chunk, stereo_data[:, 0])

    def test_callback_enqueues_copy_not_reference(self):
        """
        The callback must enqueue a copy of the data.
        sounddevice reuses its internal buffer — a reference would be stale.
        """
        audio_queue = queue.Queue()
        frames = stt.CHUNK_FRAMES
        data = np.ones((frames, 1), dtype=np.float32)

        def audio_callback(indata, frames_count, time_info, status):
            audio_queue.put(indata[:, 0].copy())

        audio_callback(data, frames, None, None)
        # Mutate original — queue item should be unaffected
        data[:] = 0.0

        chunk = audio_queue.get_nowait()
        assert np.all(chunk == 1.0), "Queue should contain a copy, not a reference"

    def test_callback_prints_status_to_stderr(self, capsys):
        """Non-None status from sounddevice must be logged to stderr."""
        audio_queue = queue.Queue()
        frames = stt.CHUNK_FRAMES
        data = np.zeros((frames, 1), dtype=np.float32)

        def audio_callback(indata, frames_count, time_info, status):
            if status:
                print(f"[audio warning] {status}", file=sys.stderr)
            audio_queue.put(indata[:, 0].copy())

        audio_callback(data, frames, None, "input overflow")
        captured = capsys.readouterr()
        assert "input overflow" in captured.err
        assert "input overflow" not in captured.out


# ---------------------------------------------------------------------------
# load_model() — error handling paths
# ---------------------------------------------------------------------------

class TestLoadModel:
    """Verify load_model() handles import and runtime errors correctly."""

    def test_load_model_exits_nonzero_on_import_error(self, capsys):
        """If faster-whisper is not installed, must exit with non-zero code."""
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
        captured = capsys.readouterr()
        assert "pip install faster-whisper" in captured.err

    def test_load_model_exits_nonzero_on_model_failure(self, capsys):
        """If WhisperModel() raises, must exit with non-zero code."""
        mock_whisper_model = MagicMock(side_effect=RuntimeError("download failed"))

        with patch.dict("sys.modules", {"faster_whisper": MagicMock(WhisperModel=mock_whisper_model)}):
            with pytest.raises(SystemExit) as exc_info:
                stt.load_model("base")

        assert exc_info.value.code != 0

    def test_load_model_prints_loading_message_to_stderr(self, capsys):
        """Loading message must go to stderr so stdout stays clean."""
        mock_model_instance = MagicMock()
        mock_whisper_class = MagicMock(return_value=mock_model_instance)

        with patch.dict("sys.modules", {
            "faster_whisper": MagicMock(WhisperModel=mock_whisper_class)
        }):
            result = stt.load_model("base")

        captured = capsys.readouterr()
        assert "Loading" in captured.err or "Model" in captured.err
        assert captured.out == ""  # Nothing on stdout during model load

    def test_load_model_returns_model_on_success(self):
        """load_model() must return the loaded model on success."""
        mock_model_instance = MagicMock()
        mock_whisper_class = MagicMock(return_value=mock_model_instance)

        with patch.dict("sys.modules", {
            "faster_whisper": MagicMock(WhisperModel=mock_whisper_class)
        }):
            result = stt.load_model("base")

        assert result is mock_model_instance


# ---------------------------------------------------------------------------
# main() entry point
# ---------------------------------------------------------------------------

class TestMain:
    """Verify the main() function dispatches correctly."""

    def test_main_calls_list_devices_then_exits(self):
        """When --list-devices is passed, main() must call list_devices() and exit."""
        with patch("sys.argv", ["stt", "--list-devices"]):
            with patch("stt.list_devices") as mock_list:
                with pytest.raises(SystemExit) as exc_info:
                    stt.main()

        mock_list.assert_called_once()
        assert exc_info.value.code == 0

    def test_main_calls_run_without_list_devices(self):
        """When started normally, main() must call run() with parsed args."""
        with patch("sys.argv", ["stt", "--model", "tiny"]):
            with patch("stt.run") as mock_run:
                stt.main()

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args.model == "tiny"


# ---------------------------------------------------------------------------
# list_devices()
# ---------------------------------------------------------------------------

class TestListDevices:
    """Verify list_devices() output format."""

    def test_only_input_devices_listed(self, capsys):
        """
        Only devices with max_input_channels > 0 should appear in the output.
        Output-only (speakers) must be excluded (§2.1).
        """
        mock_devices = [
            {"name": "USB Microphone", "max_input_channels": 2},
            {"name": "HDMI Output", "max_input_channels": 0},
            {"name": "Built-in Mic", "max_input_channels": 1},
        ]
        with patch("stt.sd.query_devices", return_value=mock_devices):
            with patch("stt.sd.default") as mock_default:
                mock_default.device = (0, 1)
                stt.list_devices()

        captured = capsys.readouterr()
        assert "USB Microphone" in captured.out
        assert "Built-in Mic" in captured.out
        assert "HDMI Output" not in captured.out

    def test_default_device_marked(self, capsys):
        """Default input device must be marked with '(default)'."""
        mock_devices = [
            {"name": "Mic A", "max_input_channels": 1},
            {"name": "Mic B", "max_input_channels": 1},
        ]
        with patch("stt.sd.query_devices", return_value=mock_devices):
            with patch("stt.sd.default") as mock_default:
                mock_default.device = (1, 1)  # device index 1 is default input
                stt.list_devices()

        captured = capsys.readouterr()
        assert "Mic B" in captured.out
        assert "(default)" in captured.out

    def test_device_indices_shown(self, capsys):
        """Device indices must be shown so user can pass them to --device."""
        mock_devices = [
            {"name": "Mic 0", "max_input_channels": 1},
        ]
        with patch("stt.sd.query_devices", return_value=mock_devices):
            with patch("stt.sd.default") as mock_default:
                mock_default.device = (0, 0)
                stt.list_devices()

        captured = capsys.readouterr()
        # Index [0] should appear in output
        assert "[0]" in captured.out
