# Speech-to-Text Terminal Plugin

A terminal plugin that captures speech from the microphone and outputs transcribed text directly in the terminal. Speak and it responds in the terminal.

## Project Description

Create a speech-to-text (STT) plugin for the terminal that:
- Listens to the microphone input in real-time
- Transcribes speech to text using an open-source NLP model that runs locally (no cloud APIs)
- Displays the transcribed text in the terminal as you speak
- Can be deployed and run entirely on a local machine without internet dependency
- **Voice-controlled Claude Code (`--agent` mode):** Transcribed speech is piped to `claude -p` so users can voice-control coding tasks hands-free

## Requirements

- Use an open-source STT model (e.g., OpenAI Whisper, Vosk, or similar) that can be self-hosted locally
- Real-time or near-real-time transcription
- Works as a terminal/CLI application
- No external API calls for transcription - everything runs locally
- Easy setup and deployment on local machines

### Agent Mode Requirements

- `--agent` flag enables voice-to-Claude pipeline: each transcribed utterance is sent to `claude -p "<text>"` and the response is printed in the terminal
- Audio capture must continue while Claude is processing (non-blocking)
- Output format: `> You: <transcribed text>` followed by `Claude: <response>`
- **Response time:** End-to-end latency from end-of-speech to start of Claude's response displayed in terminal should be under 10 seconds for typical short commands (excluding network/model variability). The STT transcription step itself should complete within 2 seconds of silence detection.
- Graceful error handling: timeout (120s), missing CLI, subprocess failures — all surfaced to the user
- Must strip the `CLAUDECODE` environment variable when spawning `claude -p` subprocess to avoid "nested session" errors when launched from within an existing Claude Code session

### Debug Mode Requirements

- `--debug` flag enables verbose diagnostic logging to stderr (does not interfere with normal stdout output)
- Debug output must include:
  - **Startup info:** model name, language, agent mode, silence threshold, silence duration — printed immediately on launch to confirm debug is active
  - **Audio levels:** periodic RMS level logging (e.g. every 2-3 seconds) so users can verify the mic is capturing audio and tune the silence threshold
  - **Speech detection:** log when speech starts (with RMS value) and when silence is detected (with utterance duration)
  - **Transcription timing:** log how long Whisper transcription takes and the resulting text
  - **Claude call timing:** log when the Claude subprocess starts, finishes, and how long it took
- All debug lines must be timestamped with format `[DEBUG HH:MM:SS] <message>`
- Debug mode must work with all combinations of flags (--agent, --model, etc.)

### Transcription Accuracy Requirements

- The default model ("base") is insufficient for reliable voice commands. The tool should recommend or default to "small" model for agent mode, as it offers a better accuracy/speed tradeoff on CPU.
- When `--agent` is used without explicit `--model`, default to "small" instead of "base" for better accuracy
- Transcription must handle common English commands accurately: file operations, code-related terms, technical vocabulary
- With "medium" or "large" models, transcription must still complete within a reasonable time. If it exceeds 5 seconds, log a warning suggesting a smaller model

### Known Issues & Fixes

- **CLAUDECODE env var conflict:** When `stt.py --agent` is launched from within a Claude Code session, the `CLAUDECODE` environment variable is inherited by the subprocess. Claude Code detects this and refuses to start ("cannot be launched inside another Claude Code session"). The fix is to remove this env var from the subprocess environment.
- **Medium/large model performance:** On CPU, medium and large models can be very slow (10+ seconds per utterance), causing the tool to appear frozen. Debug mode is essential for diagnosing this. Consider warning users at startup if a heavy model is selected without GPU.

## Quick Start

### 1. Fork this repo

Click **"Use this template"** or **"Fork"** to create your own copy.

### 2. Set up the secret

Go to **Settings > Secrets and variables > Actions** and add:

| Secret | Description |
|--------|-------------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Your Claude Code OAuth token |

That's the only secret you need. The agent Docker image is public and requires no authentication to pull.

### 3. Create a working branch

```bash
git checkout -b dev/my-feature
```

Agents only trigger on non-master/main branches.

### 4. Describe your project

Edit `README.md` with your project description and requirements, then commit:

```bash
git add README.md
git commit -m "Describe my project requirements @PO"
git push origin dev/my-feature
```

The `@PO` trigger tells the PO agent to read your README and generate formal requirements in `REQUIREMENT.md`.

### 5. Trigger agents

Include an agent trigger in your commit message:

```bash
# Have the PO analyze requirements
git commit -m "Update project requirements @PO"

# Have the DEV implement a feature
git commit -m "Implement user authentication @DEV"

# Have the TESTER write tests
git commit -m "Write tests for auth module @TESTER"
```

You can also use bracket syntax: `[DEV]`, `[PO]`, `[TESTER]`.

### 6. Review PRs

Each agent session creates a PR with its changes. Review, provide feedback, and merge.

## How It Works

1. You push a commit with an agent trigger (e.g., `@DEV`)
2. GitHub Actions detects the trigger and starts the workflow
3. The pre-built Docker image is pulled from `ghcr.io/lightofthelight/touchfish-agent:latest`
4. Claude Code runs inside the container with the specified agent role
5. The agent reads its instructions, your requirements, and the commit message
6. Changes are pushed to a temporary branch and a PR is created

## Repository Structure

```
.
├── .github/workflows/
│   └── agent-trigger.yml    # GitHub Actions workflow
├── agents/
│   ├── PO/
│   │   ├── PO.md            # PO agent role definition
│   │   └── history.md       # PO session history
│   ├── DEV/
│   │   ├── DEV.md           # DEV agent role definition
│   │   └── history.md       # DEV session history
│   └── TESTER/
│       ├── TESTER.md         # TESTER agent role definition
│       └── history.md        # TESTER session history
├── REQUIREMENT.md            # Project requirements (maintained by PO)
└── README.md                 # Your project description (this file)
```

## Customization

- **Agent behavior**: Edit the agent definition files in `agents/` to customize how each agent works
- **Workflow**: Modify `.github/workflows/agent-trigger.yml` to change triggers or add steps
- **Requirements**: Edit `REQUIREMENT.md` directly or let the PO agent manage it

## Requirements

- A GitHub repository (this one, forked)
- A `CLAUDE_CODE_OAUTH_TOKEN` secret configured in your repo
- Commits pushed to a non-master/main branch with agent triggers

## Links

- [TouchFish Agent](https://github.com/LightOfTheLight/touchfish_agent) - The core agent system
- [Docker Image](https://github.com/LightOfTheLight/touchfish_agent/pkgs/container/touchfish-agent) - Pre-built agent image
