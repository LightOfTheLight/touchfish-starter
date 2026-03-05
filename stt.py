#!/usr/bin/env python3
"""
Speech-to-Text Terminal Plugin

Captures microphone audio and transcribes speech locally using the Whisper model.
All processing is on-device; no data is sent to external services.

Usage:
    python stt.py
    python stt.py --model small --language en
    python stt.py --list-devices
"""

import argparse
import concurrent.futures
import os
import queue
import subprocess
import sys
import threading
import time
from typing import Optional

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000       # Hz — required by Whisper
CHANNELS = 1              # Mono
CHUNK_FRAMES = 1024       # Audio frames per callback
DEFAULT_MODEL = "base"
DEFAULT_SILENCE_THRESHOLD = 0.003  # RMS below this is treated as silence
DEFAULT_SILENCE_DURATION = 1.0     # Seconds of silence before transcribing
MIN_SPEECH_DURATION = 0.3          # Minimum seconds of speech to attempt transcription


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="stt",
        description="Real-time local speech-to-text transcription in your terminal.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python stt.py
  python stt.py --model small --language en
  python stt.py --device 1
  python stt.py --list-devices
        """,
    )
    parser.add_argument(
        "--model",
        choices=["tiny", "base", "small", "medium", "large"],
        default=DEFAULT_MODEL,
        help=f"Whisper model size (default: {DEFAULT_MODEL}). "
             "Larger models are more accurate but slower.",
    )
    parser.add_argument(
        "--language",
        default=None,
        metavar="LANG",
        help="Language code (e.g. 'en', 'fr', 'es'). "
             "Auto-detects language if not specified.",
    )
    parser.add_argument(
        "--device",
        type=int,
        default=None,
        metavar="INDEX",
        help="Microphone device index. Uses the system default if not set. "
             "Run --list-devices to see available devices.",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio input devices and exit.",
    )
    parser.add_argument(
        "--silence-threshold",
        type=float,
        default=DEFAULT_SILENCE_THRESHOLD,
        metavar="LEVEL",
        help=f"RMS amplitude threshold for silence detection (default: {DEFAULT_SILENCE_THRESHOLD}). "
             "Increase if background noise triggers false positives. "
             "Decrease if speech is not being detected.",
    )
    parser.add_argument(
        "--silence-duration",
        type=float,
        default=DEFAULT_SILENCE_DURATION,
        metavar="SECS",
        help=f"Seconds of silence required before transcribing (default: {DEFAULT_SILENCE_DURATION}).",
    )
    parser.add_argument(
        "--agent",
        action="store_true",
        help="Pass transcribed speech to Claude Code CLI for processing.",
    )
    return parser.parse_args()


def list_devices() -> None:
    """Print available audio input devices with their indices."""
    print("Available audio input devices:\n")
    devices = sd.query_devices()
    default_input = sd.default.device[0] if isinstance(sd.default.device, tuple) else sd.default.device
    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            marker = " (default)" if i == default_input else ""
            print(f"  [{i}] {dev['name']}{marker}")


def load_model(model_name: str):
    """Load the Whisper model for local CPU inference."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print(
            "Error: 'faster-whisper' is not installed.\n"
            "Install it with: pip install faster-whisper",
        )
        sys.exit(1)

    print(f"Loading Whisper '{model_name}' model...", flush=True)
    print(
        "(First run will download the model. This may take a moment.)",
        flush=True,
    )
    try:
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
    except Exception as exc:
        print(f"Error: Failed to load model '{model_name}': {exc}")
        sys.exit(1)

    print(f"Model ready. Listening... (Ctrl+C to stop)\n", flush=True)
    return model


def run_claude(text: str) -> str:
    """Send text to Claude Code CLI and return the response."""
    try:
        # Remove CLAUDECODE env var so nested claude invocation is allowed
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        result = subprocess.run(
            ["claude", "-p", text],
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        if result.returncode != 0:
            parts = [f"[Claude error (exit {result.returncode})]"]
            if result.stderr:
                parts.append(result.stderr.strip())
            if result.stdout:
                parts.append(result.stdout.strip())
            return ": ".join(parts)
        return result.stdout.strip() or "[Claude returned empty response]"
    except subprocess.TimeoutExpired:
        return "[Claude timed out after 120 seconds]"
    except FileNotFoundError:
        return "[Error: 'claude' CLI not found. Is Claude Code installed?]"
    except Exception as exc:
        return f"[Error calling Claude: {exc}]"


def run(args: argparse.Namespace) -> None:
    """Main run loop: capture audio, detect utterances, transcribe, print."""
    model = load_model(args.model)

    audio_queue: queue.Queue = queue.Queue()
    stop_event = threading.Event()

    def audio_callback(indata, frames, time_info, status) -> None:
        """Sounddevice callback — runs in a separate audio thread."""
        if status:
            print(f"[audio warning] {status}", flush=True)
        # Enqueue mono float32 audio chunk
        audio_queue.put(indata[:, 0].copy())

    # Thread pool for non-blocking Claude calls in --agent mode
    claude_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1) if args.agent else None

    def handle_transcription(text: str) -> None:
        """Handle a completed transcription — print it or send to Claude."""
        if not args.agent:
            sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))
            sys.stdout.buffer.flush()
            return

        # Agent mode: show user speech, then call Claude
        sys.stdout.buffer.write(f"> You: {text}\n".encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()

        def _call_claude():
            response = run_claude(text)
            sys.stdout.buffer.write(f"Claude: {response}\n\n".encode("utf-8", errors="replace"))
            sys.stdout.buffer.flush()

        claude_executor.submit(_call_claude)

    def transcription_loop() -> None:
        """
        Reads audio chunks from the queue, applies simple energy-based VAD,
        and transcribes complete utterances.
        """
        buffer = []
        silence_chunk_count = 0
        speech_chunk_count = 0
        in_speech = False

        max_silence_chunks = max(
            1, int(args.silence_duration * SAMPLE_RATE / CHUNK_FRAMES)
        )
        min_speech_chunks = max(
            1, int(MIN_SPEECH_DURATION * SAMPLE_RATE / CHUNK_FRAMES)
        )

        while not stop_event.is_set():
            try:
                chunk = audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            rms = float(np.sqrt(np.mean(chunk ** 2)))

            if rms > args.silence_threshold:
                # Speech energy detected — accumulate
                buffer.append(chunk)
                silence_chunk_count = 0
                speech_chunk_count += 1
                in_speech = True
            elif in_speech:
                # Trailing silence after speech
                buffer.append(chunk)
                silence_chunk_count += 1

                if silence_chunk_count >= max_silence_chunks:
                    # End of utterance — transcribe if enough speech (not silence) was captured
                    if speech_chunk_count >= min_speech_chunks:
                        audio_data = np.concatenate(buffer)
                        try:
                            segments, _ = model.transcribe(
                                audio_data,
                                language=args.language,
                                beam_size=5,
                                vad_filter=True,
                            )
                            text = " ".join(s.text.strip() for s in segments).strip()
                            if text:
                                handle_transcription(text)
                        except Exception as exc:
                            print(f"[transcription error] {exc}", flush=True)

                    buffer.clear()
                    silence_chunk_count = 0
                    speech_chunk_count = 0
                    in_speech = False

    transcription_thread = threading.Thread(target=transcription_loop, daemon=True)
    transcription_thread.start()

    try:
        with sd.InputStream(
            device=args.device,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            blocksize=CHUNK_FRAMES,
            dtype="float32",
            callback=audio_callback,
        ):
            while True:
                time.sleep(0.1)
    except sd.PortAudioError as exc:
        print(f"Error: Microphone error: {exc}")
        print(
            "Tip: Try specifying a device with --device. "
            "Run --list-devices to see options.",
        )
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        stop_event.set()
        transcription_thread.join(timeout=2.0)
        if claude_executor:
            claude_executor.shutdown(wait=False)


def main() -> None:
    args = parse_args()

    if args.list_devices:
        list_devices()
        sys.exit(0)

    run(args)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
