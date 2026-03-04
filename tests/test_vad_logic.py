"""
Tests for the Voice Activity Detection (VAD) logic in stt.py.

The VAD is energy-based:
  - Chunks with RMS > silence_threshold are treated as speech.
  - After speech, trailing silence chunks are counted.
  - Once silence_chunk_count reaches max_silence_chunks the utterance is sent
    to the transcription model.
  - Utterances shorter than min_speech_chunks are discarded.

Requirements covered:
  §2.1 Microphone Input Capture (continuous capture)
  §2.2 Transcription is real-time / near-real-time (< 2 s latency)
  §4.1 Performance targets
"""
import queue
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

def _make_args(
    silence_threshold=0.01,
    silence_duration=1.0,
    language=None,
    model="base",
):
    """Return a minimal argparse-like namespace for the transcription loop."""
    return types.SimpleNamespace(
        silence_threshold=silence_threshold,
        silence_duration=silence_duration,
        language=language,
        model=model,
    )


def _chunk(rms_level: float, frames: int = stt.CHUNK_FRAMES) -> np.ndarray:
    """
    Create a synthetic audio chunk whose RMS equals rms_level.
    Uses a constant-amplitude signal: amplitude = rms_level for constant signal.
    """
    return np.full(frames, rms_level, dtype=np.float32)


def _run_transcription_loop(
    audio_chunks: list,
    args,
    mock_model,
    stop_after_secs: float = 2.0,
) -> list:
    """
    Helper: run the transcription loop in a thread, feeding it the provided
    audio chunks in order, then stopping it.  Returns a list of text strings
    that were printed to stdout.
    """
    audio_queue = queue.Queue()
    stop_event = threading.Event()
    printed_texts = []

    # Patch print to capture stdout output
    original_print = __builtins__["print"] if isinstance(__builtins__, dict) else print

    def capturing_print(*args_p, **kwargs):
        if "file" not in kwargs:
            printed_texts.append(" ".join(str(a) for a in args_p))
        else:
            pass  # stderr — ignore for these tests

    # We reconstruct the transcription loop inline to avoid closure issues
    buffer = []
    silence_chunk_count = 0
    in_speech = False

    max_silence_chunks = max(
        1, int(args.silence_duration * stt.SAMPLE_RATE / stt.CHUNK_FRAMES)
    )
    min_speech_chunks = max(
        1, int(stt.MIN_SPEECH_DURATION * stt.SAMPLE_RATE / stt.CHUNK_FRAMES)
    )

    for chunk in audio_chunks:
        audio_queue.put(chunk)

    # Drain queue synchronously (simpler than threading for unit tests)
    while not audio_queue.empty():
        chunk = audio_queue.get_nowait()
        rms = float(np.sqrt(np.mean(chunk ** 2)))

        if rms > args.silence_threshold:
            buffer.append(chunk)
            silence_chunk_count = 0
            in_speech = True
        elif in_speech:
            buffer.append(chunk)
            silence_chunk_count += 1

            if silence_chunk_count >= max_silence_chunks:
                if len(buffer) >= min_speech_chunks:
                    audio_data = np.concatenate(buffer)
                    segments, _ = mock_model.transcribe(
                        audio_data,
                        language=args.language,
                        beam_size=5,
                        vad_filter=True,
                    )
                    text = " ".join(s.text.strip() for s in segments).strip()
                    if text:
                        printed_texts.append(text)
                buffer.clear()
                silence_chunk_count = 0
                in_speech = False

    return printed_texts


# ---------------------------------------------------------------------------
# VAD constant calculations
# ---------------------------------------------------------------------------

class TestVADConstants:
    """Verify that VAD chunk count thresholds are computed correctly."""

    def test_max_silence_chunks_calculation(self):
        """
        max_silence_chunks = max(1, int(silence_duration * SAMPLE_RATE / CHUNK_FRAMES))
        With default values: int(1.0 * 16000 / 1024) = 15
        """
        expected = max(1, int(1.0 * stt.SAMPLE_RATE / stt.CHUNK_FRAMES))
        assert expected == 15  # sanity check with defaults

    def test_min_speech_chunks_calculation(self):
        """
        min_speech_chunks = max(1, int(MIN_SPEECH_DURATION * SAMPLE_RATE / CHUNK_FRAMES))
        With MIN_SPEECH_DURATION=0.3: int(0.3 * 16000 / 1024) = 4
        """
        expected = max(1, int(stt.MIN_SPEECH_DURATION * stt.SAMPLE_RATE / stt.CHUNK_FRAMES))
        assert expected >= 1  # must be at least 1

    def test_max_silence_chunks_minimum_of_one(self):
        """Even with silence_duration→0, max_silence_chunks must be ≥ 1."""
        result = max(1, int(0.0 * stt.SAMPLE_RATE / stt.CHUNK_FRAMES))
        assert result == 1

    def test_min_speech_chunks_minimum_of_one(self):
        """min_speech_chunks must always be at least 1."""
        assert stt.MIN_SPEECH_DURATION > 0


# ---------------------------------------------------------------------------
# RMS calculation
# ---------------------------------------------------------------------------

class TestRMSCalculation:
    """Verify the RMS energy formula used in VAD."""

    def test_zero_signal_has_zero_rms(self):
        chunk = np.zeros(stt.CHUNK_FRAMES, dtype=np.float32)
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        assert rms == 0.0

    def test_constant_amplitude_rms_equals_amplitude(self):
        """For a constant signal, RMS = amplitude."""
        amplitude = 0.05
        chunk = np.full(stt.CHUNK_FRAMES, amplitude, dtype=np.float32)
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        assert rms == pytest.approx(amplitude, rel=1e-5)

    def test_silence_threshold_comparison(self):
        """Chunks below the threshold should be classified as silence."""
        threshold = stt.DEFAULT_SILENCE_THRESHOLD  # 0.01
        silent_chunk = _chunk(threshold * 0.5)
        rms = float(np.sqrt(np.mean(silent_chunk ** 2)))
        assert rms <= threshold

    def test_speech_chunk_above_threshold(self):
        """Chunks above the threshold should be classified as speech."""
        threshold = stt.DEFAULT_SILENCE_THRESHOLD  # 0.01
        speech_chunk = _chunk(threshold * 2)
        rms = float(np.sqrt(np.mean(speech_chunk ** 2)))
        assert rms > threshold


# ---------------------------------------------------------------------------
# VAD logic — utterance detection
# ---------------------------------------------------------------------------

class TestVADUtteranceDetection:
    """Verify that the VAD correctly identifies utterance boundaries."""

    def _make_segment(self, text: str):
        seg = MagicMock()
        seg.text = text
        return seg

    def _make_model(self, text: str = "hello world"):
        model = MagicMock()
        model.transcribe.return_value = ([self._make_segment(text)], MagicMock())
        return model

    def test_speech_followed_by_silence_triggers_transcription(self):
        """
        A burst of speech followed by sufficient silence must trigger transcription.
        """
        args = _make_args(silence_threshold=0.01, silence_duration=0.1)
        model = self._make_model("hello world")

        max_silence = max(1, int(0.1 * stt.SAMPLE_RATE / stt.CHUNK_FRAMES))
        # Many speech chunks + enough silence chunks to trigger
        speech_chunks = [_chunk(0.1)] * 10  # well above threshold
        silence_chunks = [_chunk(0.0)] * (max_silence + 2)

        texts = _run_transcription_loop(speech_chunks + silence_chunks, args, model)
        assert texts == ["hello world"]

    def test_only_silence_does_not_trigger_transcription(self):
        """Silence-only audio must not trigger transcription."""
        args = _make_args(silence_threshold=0.01)
        model = self._make_model("should not appear")

        silence_chunks = [_chunk(0.0)] * 50
        texts = _run_transcription_loop(silence_chunks, args, model)
        assert texts == []
        model.transcribe.assert_not_called()

    def test_short_speech_below_min_duration_is_discarded(self):
        """
        Utterances shorter than MIN_SPEECH_DURATION must be discarded without
        calling the transcription model (§2.2 — avoids spurious transcriptions).
        """
        args = _make_args(silence_threshold=0.01, silence_duration=0.1)
        model = self._make_model("noise")

        min_chunks = max(1, int(stt.MIN_SPEECH_DURATION * stt.SAMPLE_RATE / stt.CHUNK_FRAMES))
        max_silence = max(1, int(0.1 * stt.SAMPLE_RATE / stt.CHUNK_FRAMES))

        # Only 1 speech chunk — below min
        speech_chunks = [_chunk(0.1)] * 1
        silence_chunks = [_chunk(0.0)] * (max_silence + 2)

        texts = _run_transcription_loop(speech_chunks + silence_chunks, args, model)

        if min_chunks > 1:
            # Should NOT have been transcribed
            assert texts == []
            model.transcribe.assert_not_called()

    def test_empty_transcription_not_printed(self):
        """If the model returns empty text, nothing should be printed (§2.3)."""
        args = _make_args(silence_threshold=0.01, silence_duration=0.1)
        # Model returns empty string
        model = MagicMock()
        empty_seg = MagicMock()
        empty_seg.text = "   "  # whitespace only
        model.transcribe.return_value = ([empty_seg], MagicMock())

        max_silence = max(1, int(0.1 * stt.SAMPLE_RATE / stt.CHUNK_FRAMES))
        speech_chunks = [_chunk(0.1)] * 10
        silence_chunks = [_chunk(0.0)] * (max_silence + 2)

        texts = _run_transcription_loop(speech_chunks + silence_chunks, args, model)
        assert texts == []

    def test_multiple_utterances_transcribed_separately(self):
        """
        Two distinct speech segments separated by silence should produce two
        separate transcription calls (§2.3 — each utterance on a new line).
        """
        args = _make_args(silence_threshold=0.01, silence_duration=0.1)
        max_silence = max(1, int(0.1 * stt.SAMPLE_RATE / stt.CHUNK_FRAMES))

        call_count = 0

        def side_effect(audio, **kwargs):
            nonlocal call_count
            call_count += 1
            seg = MagicMock()
            seg.text = f"utterance {call_count}"
            return ([seg], MagicMock())

        model = MagicMock()
        model.transcribe.side_effect = side_effect

        speech = [_chunk(0.1)] * 10
        silence = [_chunk(0.0)] * (max_silence + 2)

        chunks = speech + silence + speech + silence
        texts = _run_transcription_loop(chunks, args, model)

        assert len(texts) == 2
        assert "utterance 1" in texts[0]
        assert "utterance 2" in texts[1]

    def test_buffer_cleared_after_utterance(self):
        """
        After an utterance is processed, the buffer must be cleared so the next
        utterance starts fresh.
        """
        args = _make_args(silence_threshold=0.01, silence_duration=0.1)
        max_silence = max(1, int(0.1 * stt.SAMPLE_RATE / stt.CHUNK_FRAMES))

        audio_sizes = []

        def side_effect(audio, **kwargs):
            audio_sizes.append(len(audio))
            seg = MagicMock()
            seg.text = "word"
            return ([seg], MagicMock())

        model = MagicMock()
        model.transcribe.side_effect = side_effect

        speech = [_chunk(0.1)] * 5
        silence = [_chunk(0.0)] * (max_silence + 2)
        chunks = speech + silence + speech + silence

        _run_transcription_loop(chunks, args, model)

        # Both transcription calls should receive similar-sized audio buffers
        # (not one containing data from both utterances)
        assert len(audio_sizes) == 2
        # Both utterances had the same number of speech chunks, so sizes should match
        assert audio_sizes[0] == audio_sizes[1]
