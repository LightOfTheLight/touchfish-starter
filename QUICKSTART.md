# Quick Start — Speech-to-Text Terminal Plugin

Transcribe speech locally in your terminal using the Whisper model. No cloud API required.

---

## Prerequisites

**Python 3.9+** and **pip** are required.

On Linux/macOS you also need the PortAudio system library (required by `sounddevice`):

```bash
# Debian / Ubuntu
sudo apt install portaudio19-dev

# Fedora / RHEL
sudo dnf install portaudio-devel

# macOS (Homebrew)
brew install portaudio

# Windows — no extra step needed (portaudio is bundled)
```

---

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

On the first run the Whisper model is downloaded automatically (~145 MB for the default `base` model). No account or API key is needed.

---

## 2. Start Transcribing

```bash
python stt.py
```

Speak into your microphone. After a brief pause, the transcribed text appears on a new line. Press **Ctrl+C** to stop.

---

## Common Usage Examples

```bash
# Default: Whisper 'base' model, auto-detect language
python stt.py

# Higher accuracy (slower on CPU)
python stt.py --model small

# Pin to English for faster detection
python stt.py --language en

# List microphone devices
python stt.py --list-devices

# Use a specific device by index
python stt.py --device 2

# Adjust silence sensitivity (raise if noise triggers false positives)
python stt.py --silence-threshold 0.02
```

---

## CLI Reference

```
usage: stt [--model {tiny,base,small,medium,large}]
           [--language LANG] [--device INDEX]
           [--list-devices]
           [--silence-threshold LEVEL] [--silence-duration SECS]
           [--help]

Options:
  --model         Whisper model size (default: base)
                    tiny   ~75 MB  — fastest, lower accuracy
                    base   ~145 MB — balanced (default)
                    small  ~490 MB — higher accuracy
  --language      Language code, e.g. 'en', 'fr', 'es'.
                  Auto-detects if omitted.
  --device        Microphone device index (see --list-devices).
  --list-devices  Print available input devices and exit.
  --silence-threshold
                  RMS level below which audio is treated as silence.
                  Default: 0.01. Raise if noisy environment.
  --silence-duration
                  Seconds of silence before an utterance is sent
                  for transcription. Default: 1.0.
```

---

## Model Selection Guide

| Model  | Size   | Speed (CPU) | Accuracy | Recommended for |
|--------|--------|-------------|----------|-----------------|
| tiny   | ~75 MB  | Very fast   | Lower    | Quick demos     |
| base   | ~145 MB | Fast        | Good     | General use (default) |
| small  | ~490 MB | Moderate    | Better   | Higher accuracy needs |

---

## Troubleshooting

**No audio captured / no output:**
- Check that your microphone is plugged in and not muted.
- Run `python stt.py --list-devices` and pass the correct index with `--device`.

**False positives from background noise:**
- Raise the silence threshold: `--silence-threshold 0.02`

**PortAudio / sounddevice install error:**
- Ensure the `portaudio` system library is installed (see Prerequisites above).

**Model download fails:**
- Confirm you have internet access for the initial model download.
- Subsequent runs work fully offline.

**Slow transcription:**
- Use a smaller model: `--model tiny`
- Ensure you are not running other CPU-intensive tasks.
