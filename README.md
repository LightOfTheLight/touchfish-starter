# Speech-to-Text Terminal Plugin

A terminal plugin that captures speech from the microphone and outputs transcribed text directly in the terminal. Speak and it responds in the terminal.

## Project Description

Create a speech-to-text (STT) plugin for the terminal that:
- Listens to the microphone input in real-time
- Transcribes speech to text using an open-source NLP model that runs locally (no cloud APIs)
- Displays the transcribed text in the terminal as you speak
- Can be deployed and run entirely on a local machine without internet dependency

## Requirements

- Use an open-source STT model (e.g., OpenAI Whisper, Vosk, or similar) that can be self-hosted locally
- Real-time or near-real-time transcription
- Works as a terminal/CLI application
- No external API calls for transcription - everything runs locally
- Easy setup and deployment on local machines

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
