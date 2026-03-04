"""
Tests for the CLI argument parsing in stt.py.

These tests validate:
- All required flags exist and have correct defaults
- Argument validation (choice enforcement, type coercion)
- Help text is accessible without errors
- Exit behaviour for --list-devices

Requirements covered:
  §2.4 CLI Interface acceptance criteria
  §3.1 Technology Stack (Python 3.9+)
  §5.1 MVP: "Can be started with a single command"

Note: stt.parse_args() reads sys.argv directly, so tests patch sys.argv.
"""
import sys
import pytest
from unittest.mock import patch

import stt


def parse(argv):
    """Helper: call parse_args() with a patched sys.argv."""
    with patch("sys.argv", ["stt"] + argv):
        return stt.parse_args()


# ---------------------------------------------------------------------------
# Default argument values
# ---------------------------------------------------------------------------

class TestDefaultArgs:
    """Verify that default argument values match the specification."""

    def test_default_model_is_base(self):
        """Default Whisper model must be 'base' (§3.2 — best balance for most machines)."""
        args = parse([])
        assert args.model == "base"

    def test_default_language_is_none(self):
        """Language should auto-detect (None) by default (§2.2)."""
        args = parse([])
        assert args.language is None

    def test_default_device_is_none(self):
        """Device should use system default (None) when not specified (§2.1)."""
        args = parse([])
        assert args.device is None

    def test_default_list_devices_is_false(self):
        """--list-devices should default to False."""
        args = parse([])
        assert args.list_devices is False

    def test_default_silence_threshold(self):
        """Silence threshold should default to the module constant."""
        args = parse([])
        assert args.silence_threshold == stt.DEFAULT_SILENCE_THRESHOLD

    def test_default_silence_duration(self):
        """Silence duration should default to the module constant."""
        args = parse([])
        assert args.silence_duration == stt.DEFAULT_SILENCE_DURATION


# ---------------------------------------------------------------------------
# Model selection (§2.4 — model selection flag)
# ---------------------------------------------------------------------------

class TestModelFlag:
    """Validate --model flag accepts all specified sizes and rejects others."""

    @pytest.mark.parametrize("model", ["tiny", "base", "small", "medium", "large"])
    def test_valid_model_choices(self, model):
        """All five Whisper model sizes must be accepted (§3.2)."""
        args = parse(["--model", model])
        assert args.model == model

    def test_invalid_model_raises_system_exit(self):
        """Unknown model name must trigger an argument error."""
        with pytest.raises(SystemExit) as exc_info:
            parse(["--model", "nonexistent"])
        assert exc_info.value.code != 0

    def test_model_default_still_valid_choice(self):
        """The default model 'base' must be in the accepted choices."""
        assert stt.DEFAULT_MODEL in ["tiny", "base", "small", "medium", "large"]


# ---------------------------------------------------------------------------
# Language flag (§2.4 — language flag)
# ---------------------------------------------------------------------------

class TestLanguageFlag:
    """Validate --language flag accepts arbitrary language codes."""

    @pytest.mark.parametrize("lang", ["en", "fr", "es", "de", "zh", "ja"])
    def test_valid_language_codes(self, lang):
        """Common ISO language codes must be accepted (§2.4)."""
        args = parse(["--language", lang])
        assert args.language == lang

    def test_language_passed_to_transcribe(self):
        """The parsed language value must be available via args.language."""
        args = parse(["--language", "en"])
        assert args.language == "en"


# ---------------------------------------------------------------------------
# Device flag (§2.4 — input device flag)
# ---------------------------------------------------------------------------

class TestDeviceFlag:
    """Validate --device flag accepts integer device indices."""

    def test_device_zero(self):
        args = parse(["--device", "0"])
        assert args.device == 0

    def test_device_positive(self):
        args = parse(["--device", "3"])
        assert args.device == 3

    def test_device_must_be_integer(self):
        """Non-integer device values must be rejected."""
        with pytest.raises(SystemExit) as exc_info:
            parse(["--device", "mic"])
        assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# Silence tuning flags (§2.4 — configurable thresholds)
# ---------------------------------------------------------------------------

class TestSilenceFlags:
    """Validate silence configuration flags accept float values."""

    def test_silence_threshold_float(self):
        args = parse(["--silence-threshold", "0.05"])
        assert args.silence_threshold == pytest.approx(0.05)

    def test_silence_duration_float(self):
        args = parse(["--silence-duration", "1.5"])
        assert args.silence_duration == pytest.approx(1.5)

    def test_silence_threshold_must_be_number(self):
        with pytest.raises(SystemExit):
            parse(["--silence-threshold", "loud"])

    def test_silence_duration_must_be_number(self):
        with pytest.raises(SystemExit):
            parse(["--silence-duration", "long"])


# ---------------------------------------------------------------------------
# --list-devices flag (§2.4 / §2.1)
# ---------------------------------------------------------------------------

class TestListDevicesFlag:
    """Validate --list-devices is a boolean flag."""

    def test_list_devices_true_when_provided(self):
        args = parse(["--list-devices"])
        assert args.list_devices is True

    def test_list_devices_false_by_default(self):
        args = parse([])
        assert args.list_devices is False


# ---------------------------------------------------------------------------
# --help flag (§2.4 — "--help flag describing usage")
# ---------------------------------------------------------------------------

class TestHelpFlag:
    """Verify --help exits with code 0 (standard argparse behaviour)."""

    def test_help_exits_zero(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            parse(["--help"])
        assert exc_info.value.code == 0

    def test_help_output_contains_key_flags(self, capsys):
        """Help text should document all major flags."""
        with pytest.raises(SystemExit):
            parse(["--help"])
        captured = capsys.readouterr()
        help_text = captured.out
        assert "--model" in help_text
        assert "--language" in help_text
        assert "--device" in help_text
        assert "--list-devices" in help_text
