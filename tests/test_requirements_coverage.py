"""
Static requirements coverage tests for the Speech-to-Text Terminal Plugin.

These tests verify that the implementation satisfies MVP acceptance criteria
from REQUIREMENT.md §5.1 through code inspection rather than live execution.

Requirements covered:
  §2.1 Microphone Input Capture
  §2.2 Speech-to-Text Transcription
  §2.3 Terminal Output
  §2.4 CLI Interface
  §3.1 Technology Stack
  §3.3 Constraints
  §4.2 Privacy & Security
  §5.1 MVP Acceptance Criteria
"""
import ast
import inspect
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
STT_FILE = ROOT / "stt.py"
REQUIREMENTS_FILE = ROOT / "requirements.txt"
QUICKSTART_FILE = ROOT / "QUICKSTART.md"

import stt


# ---------------------------------------------------------------------------
# File existence checks (§5.1 MVP)
# ---------------------------------------------------------------------------

class TestRequiredFilesExist:
    """All required MVP files must exist in the repository."""

    def test_stt_py_exists(self):
        """Main entry point must exist (§5.1 — single command start)."""
        assert STT_FILE.exists(), "stt.py not found"

    def test_requirements_txt_exists(self):
        """requirements.txt must exist (§5.1 MVP criterion)."""
        assert REQUIREMENTS_FILE.exists(), "requirements.txt not found"

    def test_quickstart_documentation_exists(self):
        """Quick Start guide must exist (§4.3 Usability / §5.1)."""
        assert QUICKSTART_FILE.exists(), "QUICKSTART.md not found"


# ---------------------------------------------------------------------------
# Technology stack (§3.1)
# ---------------------------------------------------------------------------

class TestTechnologyStack:
    """Verify the correct libraries are used."""

    def test_sounddevice_in_requirements(self):
        """sounddevice must be listed as a dependency (§3.1)."""
        content = REQUIREMENTS_FILE.read_text()
        assert "sounddevice" in content

    def test_faster_whisper_in_requirements(self):
        """faster-whisper must be listed as a dependency (§3.1)."""
        content = REQUIREMENTS_FILE.read_text()
        assert "faster-whisper" in content

    def test_numpy_in_requirements(self):
        """numpy must be listed as a dependency (§3.1 — transitive, but explicit)."""
        content = REQUIREMENTS_FILE.read_text()
        assert "numpy" in content

    def test_stt_imports_sounddevice(self):
        """stt.py must import sounddevice for audio capture (§3.1)."""
        src = STT_FILE.read_text()
        assert "import sounddevice" in src

    def test_stt_imports_numpy(self):
        """stt.py must import numpy (used for RMS and audio processing)."""
        src = STT_FILE.read_text()
        assert "import numpy" in src

    def test_stt_uses_faster_whisper(self):
        """stt.py must use faster-whisper for local inference (§3.1)."""
        src = STT_FILE.read_text()
        assert "faster_whisper" in src

    def test_model_uses_cpu_device(self):
        """
        Model must be loaded on CPU to satisfy §3.3 — no mandatory GPU requirement.
        """
        src = STT_FILE.read_text()
        assert 'device="cpu"' in src or "device='cpu'" in src

    def test_sample_rate_is_16000(self):
        """Whisper requires 16000 Hz sample rate."""
        assert stt.SAMPLE_RATE == 16000

    def test_audio_is_mono(self):
        """Audio must be mono (1 channel) as required by Whisper."""
        assert stt.CHANNELS == 1


# ---------------------------------------------------------------------------
# Privacy / Security (§4.2)
# ---------------------------------------------------------------------------

class TestPrivacyAndSecurity:
    """Verify the implementation does not make external network calls."""

    def test_no_http_requests_in_code(self):
        """
        stt.py must not contain HTTP/HTTPS request code.
        All transcription is local (§4.2 — data never transmitted externally).
        """
        src = STT_FILE.read_text()
        # Must not use requests, urllib, httpx, aiohttp, or socket for HTTP
        forbidden_patterns = [
            r"requests\.(get|post|put|delete|patch)",
            r"urllib\.request",
            r"httpx\.",
            r"aiohttp\.",
        ]
        for pattern in forbidden_patterns:
            assert not re.search(pattern, src), (
                f"Found potential network call pattern: {pattern}"
            )

    def test_no_api_key_references(self):
        """No API keys or cloud service references should be present (§4.2)."""
        src = STT_FILE.read_text()
        forbidden = ["api_key", "API_KEY", "openai.api", "OPENAI_API"]
        for term in forbidden:
            assert term not in src, f"Found cloud API reference: {term}"

    def test_model_loaded_locally(self):
        """WhisperModel is called with local model name, not an API endpoint."""
        src = STT_FILE.read_text()
        # faster-whisper's WhisperModel loads locally by model name
        assert "WhisperModel(" in src


# ---------------------------------------------------------------------------
# CLI interface requirements (§2.4)
# ---------------------------------------------------------------------------

class TestCLIInterface:
    """Verify CLI interface meets specification."""

    def test_parse_args_function_exists(self):
        """parse_args() function must exist."""
        assert callable(stt.parse_args)

    def test_main_function_exists(self):
        """main() function must exist (§5.1 — single command entry point)."""
        assert callable(stt.main)

    def test_list_devices_function_exists(self):
        """list_devices() must exist (§2.4 — input device flag support)."""
        assert callable(stt.list_devices)

    def test_load_model_function_exists(self):
        """load_model() function must exist."""
        assert callable(stt.load_model)

    def test_run_function_exists(self):
        """run() must exist (main application loop)."""
        assert callable(stt.run)

    def test_model_flag_choices(self):
        """--model must accept exactly the Whisper sizes from §3.2."""
        args = stt.parse_args([])
        # Verify by passing each valid choice
        for model in ["tiny", "base", "small", "medium", "large"]:
            a = stt.parse_args(["--model", model])
            assert a.model == model

    def test_prog_name_is_stt(self):
        """The parser prog name should be 'stt' (§2.4 — invoked as 'stt')."""
        # Access the argparse prog via help output
        src = STT_FILE.read_text()
        assert 'prog="stt"' in src or "prog='stt'" in src


# ---------------------------------------------------------------------------
# Graceful shutdown (§5.1 MVP)
# ---------------------------------------------------------------------------

class TestGracefulShutdown:
    """Verify Ctrl+C / KeyboardInterrupt is handled gracefully."""

    def test_keyboard_interrupt_handler_present(self):
        """
        KeyboardInterrupt must be caught so the application shuts down cleanly
        (§5.1 — Graceful shutdown on Ctrl+C).
        """
        src = STT_FILE.read_text()
        assert "KeyboardInterrupt" in src

    def test_stop_event_set_on_shutdown(self):
        """
        A stop_event must be signalled so the transcription thread exits
        cleanly rather than being killed abruptly.
        """
        src = STT_FILE.read_text()
        assert "stop_event.set()" in src

    def test_transcription_thread_joined(self):
        """The transcription thread must be joined on exit to prevent resource leaks."""
        src = STT_FILE.read_text()
        assert "transcription_thread.join" in src


# ---------------------------------------------------------------------------
# Error handling (§2.4 — non-zero exit on error)
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Verify error paths exit with non-zero codes and user-friendly messages."""

    def test_portaudio_error_handled(self):
        """PortAudio error must be caught and reported (§4.3 — actionable errors)."""
        src = STT_FILE.read_text()
        assert "PortAudioError" in src

    def test_import_error_handled_gracefully(self):
        """
        If faster-whisper is not installed, the application must print a helpful
        error and exit (§4.3 — human-readable error messages).
        """
        src = STT_FILE.read_text()
        assert "ImportError" in src
        assert "pip install faster-whisper" in src

    def test_model_load_exception_caught(self):
        """Model loading failure must be caught and reported."""
        src = STT_FILE.read_text()
        assert "Failed to load model" in src

    def test_transcription_exception_does_not_crash_loop(self):
        """
        Transcription errors must be caught so the loop continues
        (a single bad audio chunk should not kill the application).
        """
        src = STT_FILE.read_text()
        assert "[transcription error]" in src


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

class TestModuleConstants:
    """Verify module constants have sensible values."""

    def test_chunk_frames_positive(self):
        assert stt.CHUNK_FRAMES > 0

    def test_default_silence_threshold_positive(self):
        assert stt.DEFAULT_SILENCE_THRESHOLD > 0

    def test_default_silence_duration_positive(self):
        assert stt.DEFAULT_SILENCE_DURATION > 0

    def test_min_speech_duration_positive(self):
        assert stt.MIN_SPEECH_DURATION > 0

    def test_default_model_string(self):
        assert isinstance(stt.DEFAULT_MODEL, str)
        assert len(stt.DEFAULT_MODEL) > 0
